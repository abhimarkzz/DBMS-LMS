-- =============================================================================
-- Database Views
-- =============================================================================
-- Views provide pre-joined, readable representations of common data needs.
-- They simplify application queries and centralize join logic.
-- Changes to underlying tables only need view updates here.
-- =============================================================================


-- =============================================================================
-- View 1: student_course_progress_view
-- Purpose: One-stop view for a student's progress in each enrolled course.
-- Used by: Student dashboard, teacher progress tracker, admin reports.
-- =============================================================================
CREATE OR REPLACE VIEW student_course_progress_view AS
SELECT
    s.student_id,
    u.first_name || ' ' || u.last_name   AS student_name,
    u.email                               AS student_email,
    s.registration_number,
    s.department                          AS student_department,
    c.course_id,
    c.course_code,
    c.course_name,
    c.department                          AS course_department,
    c.semester,
    e.status                              AS enrollment_status,
    e.enrolled_at,

    -- Total assignments published for this course
    COUNT(DISTINCT a.assignment_id)                                 AS total_assignments,

    -- Assignments this student has submitted (any attempt)
    COUNT(DISTINCT sub.assignment_id)                               AS submitted_assignments,

    -- Assignments that have been graded for this student
    COUNT(DISTINCT CASE WHEN g.grade_id IS NOT NULL THEN sub.assignment_id END) AS graded_assignments,

    -- Average marks obtained (only from graded submissions)
    ROUND(AVG(g.marks_obtained), 2)                                 AS average_marks_obtained,

    -- Average total marks for those assignments (to compute percentage)
    ROUND(AVG(a.total_marks), 2)                                    AS average_assignment_total,

    -- Submission rate: (submitted / total) * 100
    CASE
        WHEN COUNT(DISTINCT a.assignment_id) = 0 THEN 0.00
        ELSE ROUND(
            (COUNT(DISTINCT sub.assignment_id)::DECIMAL / COUNT(DISTINCT a.assignment_id)) * 100,
            2
        )
    END                                                             AS submission_rate_pct,

    -- Completion percentage from the enrollment record (updated by trigger)
    e.completion_percentage

FROM enrollments e
JOIN students s ON s.student_id = e.student_id
JOIN users u ON u.user_id = s.user_id
JOIN courses c ON c.course_id = e.course_id
-- Left joins because students may not have submitted anything yet
LEFT JOIN assignments a ON a.course_id = c.course_id AND a.status = 'PUBLISHED'
LEFT JOIN submissions sub ON sub.assignment_id = a.assignment_id
    AND sub.student_id = s.student_id
LEFT JOIN submission_grades g ON g.submission_id = sub.submission_id

GROUP BY
    s.student_id,
    u.first_name, u.last_name, u.email,
    s.registration_number, s.department,
    c.course_id, c.course_code, c.course_name, c.department, c.semester,
    e.status, e.enrolled_at, e.completion_percentage;


-- =============================================================================
-- View 2: teacher_assignment_summary_view
-- Purpose: Shows assignment statistics for each teacher's courses.
-- Used by: Teacher dashboard, admin reporting.
-- =============================================================================
CREATE OR REPLACE VIEW teacher_assignment_summary_view AS
SELECT
    t.teacher_id,
    u.first_name || ' ' || u.last_name  AS teacher_name,
    u.email                             AS teacher_email,
    t.employee_id,
    t.department                        AS teacher_department,
    c.course_id,
    c.course_code,
    c.course_name,
    a.assignment_id,
    a.title                             AS assignment_title,
    a.total_marks,
    a.due_date,
    a.status                            AS assignment_status,

    -- How many students are enrolled in this course
    COUNT(DISTINCT e.student_id)        AS enrolled_students,

    -- How many have submitted
    COUNT(DISTINCT sub.student_id)      AS submitted_count,

    -- How many have been graded
    COUNT(DISTINCT g.grade_id)          AS graded_count,

    -- Pending (submitted but not graded)
    COUNT(DISTINCT sub.student_id) - COUNT(DISTINCT g.grade_id) AS pending_grading,

    -- Average marks for this assignment
    ROUND(AVG(g.marks_obtained), 2)     AS average_marks,

    -- Highest marks obtained
    MAX(g.marks_obtained)               AS highest_marks,

    -- Lowest marks obtained
    MIN(g.marks_obtained)               AS lowest_marks

FROM teachers t
JOIN users u ON u.user_id = t.user_id
JOIN courses c ON c.teacher_id = t.teacher_id
JOIN assignments a ON a.course_id = c.course_id
LEFT JOIN enrollments e ON e.course_id = c.course_id AND e.status = 'ENROLLED'
LEFT JOIN submissions sub ON sub.assignment_id = a.assignment_id
LEFT JOIN submission_grades g ON g.submission_id = sub.submission_id

GROUP BY
    t.teacher_id, u.first_name, u.last_name, u.email,
    t.employee_id, t.department,
    c.course_id, c.course_code, c.course_name,
    a.assignment_id, a.title, a.total_marks, a.due_date, a.status;


-- =============================================================================
-- View 3: admin_course_overview_view
-- Purpose: High-level course statistics for admin dashboard.
-- =============================================================================
CREATE OR REPLACE VIEW admin_course_overview_view AS
SELECT
    c.course_id,
    c.course_code,
    c.course_name,
    c.department,
    c.semester,
    c.credits,
    c.status,
    c.created_at,
    tu.first_name || ' ' || tu.last_name    AS teacher_name,
    t.employee_id,

    COUNT(DISTINCT e.student_id)            AS total_enrolled,
    COUNT(DISTINCT a.assignment_id)         AS total_assignments,
    COUNT(DISTINCT cm.material_id)          AS total_materials,
    COUNT(DISTINCT q.quiz_id)               AS total_quizzes

FROM courses c
JOIN teachers t ON t.teacher_id = c.teacher_id
JOIN users tu ON tu.user_id = t.user_id
LEFT JOIN enrollments e ON e.course_id = c.course_id AND e.status = 'ENROLLED'
LEFT JOIN assignments a ON a.course_id = c.course_id AND a.status = 'PUBLISHED'
LEFT JOIN course_materials cm ON cm.course_id = c.course_id AND cm.status = 'READY'
LEFT JOIN quizzes q ON q.course_id = c.course_id AND q.status = 'PUBLISHED'

GROUP BY
    c.course_id, c.course_code, c.course_name, c.department,
    c.semester, c.credits, c.status, c.created_at,
    tu.first_name, tu.last_name, t.employee_id;


-- =============================================================================
-- View 4: student_result_summary_view
-- Purpose: Student's results across all courses with GPA calculation.
-- =============================================================================
CREATE OR REPLACE VIEW student_result_summary_view AS
SELECT
    s.student_id,
    u.first_name || ' ' || u.last_name  AS student_name,
    s.registration_number,
    s.department,
    s.semester,
    c.course_id,
    c.course_code,
    c.course_name,
    c.credits,
    cr.total_marks,
    cr.max_marks,
    cr.percentage,
    cr.grade,
    cr.grade_points,
    cr.status                           AS result_status,
    cr.published_at,

    -- Weighted grade points for GPA: grade_points * credits
    COALESCE(cr.grade_points, 0) * c.credits AS weighted_grade_points

FROM students s
JOIN users u ON u.user_id = s.user_id
JOIN enrollments e ON e.student_id = s.student_id
JOIN courses c ON c.course_id = e.course_id
LEFT JOIN course_results cr ON cr.student_id = s.student_id
    AND cr.course_id = c.course_id
    AND cr.status = 'PUBLISHED';

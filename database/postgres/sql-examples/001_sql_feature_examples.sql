-- =============================================================================
-- SQL Examples — Academic Demonstration Queries
-- =============================================================================
-- These queries demonstrate advanced SQL features using the actual LMS schema.
-- Run against a seeded database to see results.
-- All queries are read-only (SELECT only).
-- =============================================================================


-- =============================================================================
-- 1. INNER JOIN — Students enrolled in a specific course
-- =============================================================================
-- Find all students enrolled in CS501 with their contact details.
-- INNER JOIN ensures only students with actual enrollment records are returned.

SELECT
    u.first_name || ' ' || u.last_name  AS student_name,
    u.email,
    s.registration_number,
    s.semester,
    s.section,
    e.enrolled_at,
    e.status                            AS enrollment_status
FROM enrollments e
INNER JOIN students s ON s.student_id = e.student_id
INNER JOIN users u ON u.user_id = s.user_id
INNER JOIN courses c ON c.course_id = e.course_id
WHERE c.course_code = 'CS501'
  AND e.status = 'ENROLLED'
ORDER BY u.last_name;


-- =============================================================================
-- 2. LEFT JOIN — All assignments and their submission counts
-- =============================================================================
-- Show every assignment in CS501, including those with zero submissions.
-- LEFT JOIN preserves assignments even when no student has submitted.

SELECT
    a.title                         AS assignment_title,
    a.total_marks,
    a.due_date,
    a.status,
    COUNT(s.submission_id)          AS total_submissions,
    COUNT(g.grade_id)               AS graded_submissions,
    ROUND(AVG(g.marks_obtained), 2) AS average_marks
FROM assignments a
LEFT JOIN submissions s ON s.assignment_id = a.assignment_id
LEFT JOIN submission_grades g ON g.submission_id = s.submission_id
INNER JOIN courses c ON c.course_id = a.course_id
WHERE c.course_code = 'CS501'
GROUP BY a.assignment_id, a.title, a.total_marks, a.due_date, a.status
ORDER BY a.due_date;


-- =============================================================================
-- 3. GROUP BY + HAVING — Courses with more than 2 enrolled students
-- =============================================================================
-- Find courses that are popular enough to justify full operation.
-- HAVING filters AFTER aggregation (unlike WHERE which filters before).

SELECT
    c.course_code,
    c.course_name,
    c.department,
    COUNT(e.student_id)     AS enrolled_count
FROM courses c
INNER JOIN enrollments e ON e.course_id = c.course_id AND e.status = 'ENROLLED'
GROUP BY c.course_id, c.course_code, c.course_name, c.department
HAVING COUNT(e.student_id) >= 2
ORDER BY enrolled_count DESC;


-- =============================================================================
-- 4. Aggregate Functions — Assignment statistics per course
-- =============================================================================
-- COUNT, AVG, SUM, MIN, MAX in a single query

SELECT
    c.course_code,
    c.course_name,
    COUNT(DISTINCT a.assignment_id)     AS total_assignments,
    COUNT(DISTINCT s.submission_id)     AS total_submissions,
    ROUND(AVG(g.marks_obtained), 2)     AS avg_marks_obtained,
    SUM(g.marks_obtained)               AS total_marks_given,
    MIN(g.marks_obtained)               AS lowest_marks,
    MAX(g.marks_obtained)               AS highest_marks,
    ROUND(
        (COUNT(DISTINCT s.submission_id)::DECIMAL /
         NULLIF(COUNT(DISTINCT a.assignment_id) * COUNT(DISTINCT e.student_id), 0)) * 100,
        2
    )                                   AS overall_submission_rate_pct
FROM courses c
LEFT JOIN enrollments e ON e.course_id = c.course_id AND e.status = 'ENROLLED'
LEFT JOIN assignments a ON a.course_id = c.course_id AND a.status = 'PUBLISHED'
LEFT JOIN submissions s ON s.assignment_id = a.assignment_id
LEFT JOIN submission_grades g ON g.submission_id = s.submission_id
GROUP BY c.course_id, c.course_code, c.course_name;


-- =============================================================================
-- 5. Subquery — Students with above-average marks in CS501
-- =============================================================================
-- Find students whose marks in CS501 are above the class average.
-- The subquery computes the class average independently.

SELECT
    u.first_name || ' ' || u.last_name  AS student_name,
    s.registration_number,
    ROUND(AVG(g.marks_obtained), 2)     AS student_avg_marks,
    (
        -- Subquery: average marks for all students in this course
        SELECT ROUND(AVG(sg.marks_obtained), 2)
        FROM submission_grades sg
        JOIN submissions sub ON sub.submission_id = sg.submission_id
        JOIN assignments a ON a.assignment_id = sub.assignment_id
        JOIN courses c ON c.course_id = a.course_id
        WHERE c.course_code = 'CS501'
    )                                   AS class_average_marks
FROM students s
JOIN users u ON u.user_id = s.user_id
JOIN submissions sub ON sub.student_id = s.student_id
JOIN assignments a ON a.assignment_id = sub.assignment_id
JOIN courses c ON c.course_id = a.course_id
JOIN submission_grades g ON g.submission_id = sub.submission_id
WHERE c.course_code = 'CS501'
GROUP BY s.student_id, u.first_name, u.last_name, s.registration_number
HAVING ROUND(AVG(g.marks_obtained), 2) > (
    SELECT AVG(sg.marks_obtained)
    FROM submission_grades sg
    JOIN submissions sub2 ON sub2.submission_id = sg.submission_id
    JOIN assignments a2 ON a2.assignment_id = sub2.assignment_id
    JOIN courses c2 ON c2.course_id = a2.course_id
    WHERE c2.course_code = 'CS501'
)
ORDER BY student_avg_marks DESC;


-- =============================================================================
-- 6. CTE — Students whose average is above the course average
-- =============================================================================
-- Same as above but using WITH (CTE) for much better readability.
-- CTE computes class averages once; results referenced multiple times.

WITH course_averages AS (
    SELECT
        c.course_id,
        c.course_code,
        ROUND(AVG(g.marks_obtained), 2) AS class_average
    FROM courses c
    JOIN assignments a ON a.course_id = c.course_id
    JOIN submissions sub ON sub.assignment_id = a.assignment_id
    JOIN submission_grades g ON g.submission_id = sub.submission_id
    WHERE a.status = 'PUBLISHED'
    GROUP BY c.course_id, c.course_code
),
student_averages AS (
    SELECT
        sub.student_id,
        a.course_id,
        ROUND(AVG(g.marks_obtained), 2) AS student_average
    FROM submissions sub
    JOIN assignments a ON a.assignment_id = sub.assignment_id
    JOIN submission_grades g ON g.submission_id = sub.submission_id
    WHERE a.status = 'PUBLISHED'
    GROUP BY sub.student_id, a.course_id
)
SELECT
    u.first_name || ' ' || u.last_name  AS student_name,
    s.registration_number,
    ca.course_code,
    sa.student_average,
    ca.class_average,
    ROUND(sa.student_average - ca.class_average, 2) AS above_average_by
FROM student_averages sa
JOIN course_averages ca ON ca.course_id = sa.course_id
JOIN students s ON s.student_id = sa.student_id
JOIN users u ON u.user_id = s.user_id
WHERE sa.student_average > ca.class_average
ORDER BY ca.course_code, above_average_by DESC;


-- =============================================================================
-- 7. Window Functions — RANK, DENSE_RANK, ROW_NUMBER
-- =============================================================================
-- Rank students by their average marks within each course.
-- Window functions compute rankings without collapsing rows (unlike GROUP BY).

SELECT
    u.first_name || ' ' || u.last_name      AS student_name,
    s.registration_number,
    c.course_code,
    c.course_name,
    ROUND(AVG(g.marks_obtained), 2)         AS avg_marks,

    -- RANK: skips numbers after ties (1, 1, 3, 4...)
    RANK() OVER (
        PARTITION BY c.course_id
        ORDER BY AVG(g.marks_obtained) DESC
    )                                       AS rank_with_gaps,

    -- DENSE_RANK: no gaps after ties (1, 1, 2, 3...)
    DENSE_RANK() OVER (
        PARTITION BY c.course_id
        ORDER BY AVG(g.marks_obtained) DESC
    )                                       AS dense_rank,

    -- ROW_NUMBER: unique position regardless of ties (1, 2, 3, 4...)
    ROW_NUMBER() OVER (
        PARTITION BY c.course_id
        ORDER BY AVG(g.marks_obtained) DESC, s.registration_number
    )                                       AS row_number

FROM students s
JOIN users u ON u.user_id = s.user_id
JOIN submissions sub ON sub.student_id = s.student_id
JOIN assignments a ON a.assignment_id = sub.assignment_id
JOIN courses c ON c.course_id = a.course_id
JOIN submission_grades g ON g.submission_id = sub.submission_id
WHERE a.status = 'PUBLISHED'
GROUP BY s.student_id, u.first_name, u.last_name, s.registration_number, c.course_id, c.course_code, c.course_name
ORDER BY c.course_code, rank_with_gaps;


-- =============================================================================
-- 8. Students who have NOT submitted a specific assignment
-- =============================================================================
-- Using LEFT JOIN + IS NULL pattern (often more readable than NOT IN with subquery)

SELECT
    u.first_name || ' ' || u.last_name  AS student_name,
    u.email,
    s.registration_number,
    e.enrollment_status
FROM enrollments e
JOIN students s ON s.student_id = e.student_id
JOIN users u ON u.user_id = s.user_id
-- Left join to submissions — students without submissions will have NULL
LEFT JOIN submissions sub ON sub.student_id = s.student_id
    AND sub.assignment_id = 'g0000000-0000-0000-0000-000000000001'  -- ER Diagram Assignment
WHERE e.course_id = 'f0000000-0000-0000-0000-000000000001'          -- CS501
  AND e.status = 'ENROLLED'
  AND sub.submission_id IS NULL    -- No submission found
ORDER BY u.last_name;


-- =============================================================================
-- 9. CTE with Window Function — Top student per course (only rank 1)
-- =============================================================================

WITH ranked_students AS (
    SELECT
        u.first_name || ' ' || u.last_name                  AS student_name,
        s.registration_number,
        c.course_code,
        c.course_name,
        ROUND(AVG(g.marks_obtained), 2)                     AS avg_marks,
        RANK() OVER (
            PARTITION BY c.course_id
            ORDER BY AVG(g.marks_obtained) DESC
        )                                                   AS student_rank
    FROM students s
    JOIN users u ON u.user_id = s.user_id
    JOIN submissions sub ON sub.student_id = s.student_id
    JOIN assignments a ON a.assignment_id = sub.assignment_id
    JOIN courses c ON c.course_id = a.course_id
    JOIN submission_grades g ON g.submission_id = sub.submission_id
    WHERE a.status = 'PUBLISHED'
    GROUP BY s.student_id, u.first_name, u.last_name, s.registration_number,
             c.course_id, c.course_code, c.course_name
)
SELECT student_name, registration_number, course_code, course_name, avg_marks
FROM ranked_students
WHERE student_rank = 1
ORDER BY course_code;


-- =============================================================================
-- 10. Admin report — Course enrollment and submission summary
-- =============================================================================

SELECT
    c.course_code,
    c.course_name,
    c.department,
    tu.first_name || ' ' || tu.last_name                    AS teacher_name,
    COUNT(DISTINCT e.student_id)                            AS enrolled_students,
    COUNT(DISTINCT a.assignment_id)                         AS published_assignments,
    COUNT(DISTINCT sub.submission_id)                       AS total_submissions,
    COUNT(DISTINCT g.grade_id)                              AS graded_submissions,
    ROUND(AVG(g.marks_obtained), 2)                         AS overall_avg_marks,
    COUNT(DISTINCT cm.material_id)                          AS study_materials_count
FROM courses c
JOIN teachers t ON t.teacher_id = c.teacher_id
JOIN users tu ON tu.user_id = t.user_id
LEFT JOIN enrollments e ON e.course_id = c.course_id AND e.status = 'ENROLLED'
LEFT JOIN assignments a ON a.course_id = c.course_id AND a.status = 'PUBLISHED'
LEFT JOIN submissions sub ON sub.assignment_id = a.assignment_id
LEFT JOIN submission_grades g ON g.submission_id = sub.submission_id
LEFT JOIN course_materials cm ON cm.course_id = c.course_id AND cm.status = 'READY'
WHERE c.status = 'ACTIVE'
GROUP BY c.course_id, c.course_code, c.course_name, c.department,
         tu.first_name, tu.last_name
ORDER BY enrolled_students DESC;


-- =============================================================================
-- 11. Vector similarity search example (requires embeddings to be populated)
-- =============================================================================
-- This demonstrates pgvector search. Replace the embedding with an actual
-- vector generated from the query text.
-- Example: "What are ACID properties in a database?"
-- The <=> operator computes cosine distance (lower = more similar).

/*
SELECT
    chunk_id,
    material_id,
    content,
    page_number,
    1 - (embedding <=> '[0.1, 0.2, ..., 0.05]'::vector)  AS cosine_similarity
FROM material_chunks
WHERE embedding IS NOT NULL
ORDER BY embedding <=> '[0.1, 0.2, ..., 0.05]'::vector
LIMIT 5;
*/

-- Using the search function with authorization (preferred approach):
/*
SELECT *
FROM search_material_chunks_semantic(
    '[0.1, 0.2, ..., 0.05]'::vector(384),   -- query embedding
    ARRAY[
        'f0000000-0000-0000-0000-000000000001'::uuid,   -- CS501
        'f0000000-0000-0000-0000-000000000002'::uuid    -- CS502
    ],
    5,    -- top_k
    0.3   -- minimum similarity
);
*/

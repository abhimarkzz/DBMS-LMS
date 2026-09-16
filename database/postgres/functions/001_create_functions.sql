-- =============================================================================
-- Database Functions and Stored Procedures
-- =============================================================================
-- Functions are used for business logic that benefits from running close
-- to the data (reducing round-trips) or needs to be reused across services.
--
-- Rule: Major business logic stays in the application service layer.
-- Functions here handle data-intensive calculations and atomic operations.
-- =============================================================================


-- =============================================================================
-- Function 1: calculate_student_grade
-- Converts a percentage score to a grade letter and grade points.
-- Uses the standard 10-point grading scale common in Indian universities.
-- =============================================================================
CREATE OR REPLACE FUNCTION calculate_student_grade(percentage DECIMAL)
RETURNS TABLE(grade VARCHAR(5), grade_points DECIMAL(4,2)) AS $$
BEGIN
    RETURN QUERY
    SELECT
        CASE
            WHEN percentage >= 90 THEN 'A+'
            WHEN percentage >= 80 THEN 'A'
            WHEN percentage >= 70 THEN 'B+'
            WHEN percentage >= 60 THEN 'B'
            WHEN percentage >= 50 THEN 'C'
            WHEN percentage >= 40 THEN 'D'
            ELSE 'F'
        END::VARCHAR(5)                     AS grade,
        CASE
            WHEN percentage >= 90 THEN 10.0
            WHEN percentage >= 80 THEN 9.0
            WHEN percentage >= 70 THEN 8.0
            WHEN percentage >= 60 THEN 7.0
            WHEN percentage >= 50 THEN 6.0
            WHEN percentage >= 40 THEN 5.0
            ELSE 0.0
        END::DECIMAL(4,2)                   AS grade_points;
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- =============================================================================
-- Function 2: generate_student_course_result
-- Calculates and upserts the final result for a student in a course.
--
-- This function aggregates all graded submissions for a student in a course,
-- computes the percentage and grade, and writes it to course_results.
--
-- Called by: Result Service (Spring Boot) when a teacher publishes results.
-- Also called by the trigger in triggers/001_create_triggers.sql when a
-- submission grade is inserted.
--
-- Parameters:
--   p_student_id  — The student's UUID
--   p_course_id   — The course UUID
--
-- Returns: The result_id of the created/updated course_results row
-- =============================================================================
CREATE OR REPLACE FUNCTION generate_student_course_result(
    p_student_id UUID,
    p_course_id  UUID
)
RETURNS UUID AS $$
DECLARE
    v_total_obtained    DECIMAL(8,2) := 0;
    v_total_possible    DECIMAL(8,2) := 0;
    v_percentage        DECIMAL(5,2);
    v_grade             VARCHAR(5);
    v_grade_points      DECIMAL(4,2);
    v_result_id         UUID;
BEGIN
    -- Sum up marks from all graded submissions for published assignments
    SELECT
        COALESCE(SUM(g.marks_obtained), 0),
        COALESCE(SUM(a.total_marks), 0)
    INTO
        v_total_obtained,
        v_total_possible
    FROM assignments a
    JOIN submissions sub ON sub.assignment_id = a.assignment_id
        AND sub.student_id = p_student_id
    JOIN submission_grades g ON g.submission_id = sub.submission_id
    WHERE a.course_id = p_course_id
      AND a.status = 'PUBLISHED';

    -- Cannot calculate if no graded work exists
    IF v_total_possible = 0 THEN
        RAISE NOTICE 'No graded assignments found for student % in course %',
            p_student_id, p_course_id;
        RETURN NULL;
    END IF;

    -- Calculate percentage
    v_percentage := ROUND((v_total_obtained / v_total_possible) * 100, 2);

    -- Get grade and grade points from the grade function
    SELECT grade, grade_points
    INTO v_grade, v_grade_points
    FROM calculate_student_grade(v_percentage);

    -- Upsert the result record
    INSERT INTO course_results (
        student_id, course_id,
        total_marks, max_marks, percentage,
        grade, grade_points,
        status, calculated_at
    )
    VALUES (
        p_student_id, p_course_id,
        v_total_obtained, v_total_possible, v_percentage,
        v_grade, v_grade_points,
        'PENDING', NOW()
    )
    ON CONFLICT (student_id, course_id)
    DO UPDATE SET
        total_marks     = EXCLUDED.total_marks,
        max_marks       = EXCLUDED.max_marks,
        percentage      = EXCLUDED.percentage,
        grade           = EXCLUDED.grade,
        grade_points    = EXCLUDED.grade_points,
        calculated_at   = NOW(),
        updated_at      = NOW()
    RETURNING result_id INTO v_result_id;

    RETURN v_result_id;

EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Error generating result for student % in course %: %',
            p_student_id, p_course_id, SQLERRM;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- Function 3: calculate_student_gpa
-- Calculates the cumulative GPA for a student across all published results.
-- Uses the standard weighted average: sum(grade_points * credits) / sum(credits)
-- =============================================================================
CREATE OR REPLACE FUNCTION calculate_student_gpa(p_student_id UUID)
RETURNS DECIMAL(4,2) AS $$
DECLARE
    v_gpa DECIMAL(4,2);
BEGIN
    SELECT
        CASE
            WHEN SUM(c.credits) = 0 THEN 0.00
            ELSE ROUND(
                SUM(cr.grade_points * c.credits) / SUM(c.credits),
                2
            )
        END
    INTO v_gpa
    FROM course_results cr
    JOIN courses c ON c.course_id = cr.course_id
    WHERE cr.student_id = p_student_id
      AND cr.status = 'PUBLISHED'
      AND cr.grade_points IS NOT NULL;

    RETURN COALESCE(v_gpa, 0.00);
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- Function 4: get_course_enrollment_count
-- Returns the count of active enrollments for a course.
-- Simple function but called in many places; centralizes the query.
-- =============================================================================
CREATE OR REPLACE FUNCTION get_course_enrollment_count(p_course_id UUID)
RETURNS INTEGER AS $$
    SELECT COUNT(*)::INTEGER
    FROM enrollments
    WHERE course_id = p_course_id
      AND status = 'ENROLLED';
$$ LANGUAGE sql STABLE;


-- =============================================================================
-- Function 5: search_material_chunks_semantic
-- Performs vector similarity search for AI search service.
-- Returns top-N chunks from materials the user is authorized to access.
--
-- Parameters:
--   p_query_embedding  — The embedding vector of the user's question
--   p_course_ids       — UUIDs of courses the student is enrolled in
--   p_top_k            — Number of results to return (default 5)
--   p_similarity_threshold — Minimum similarity score (0 to 1, default 0.3)
-- =============================================================================
CREATE OR REPLACE FUNCTION search_material_chunks_semantic(
    p_query_embedding       vector(384),
    p_course_ids            UUID[],
    p_top_k                 INTEGER DEFAULT 5,
    p_similarity_threshold  FLOAT DEFAULT 0.3
)
RETURNS TABLE(
    chunk_id        UUID,
    material_id     UUID,
    course_id       UUID,
    course_code     VARCHAR,
    course_name     VARCHAR,
    material_title  VARCHAR,
    content         TEXT,
    page_number     INTEGER,
    chunk_number    INTEGER,
    similarity      FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mc.chunk_id,
        mc.material_id,
        cm.course_id,
        c.course_code,
        c.course_name,
        cm.title                                            AS material_title,
        mc.content,
        mc.page_number,
        mc.chunk_number,
        -- Cosine similarity: 1 - cosine_distance
        (1 - (mc.embedding <=> p_query_embedding))::FLOAT  AS similarity
    FROM material_chunks mc
    JOIN course_materials cm ON cm.material_id = mc.material_id
    JOIN courses c ON c.course_id = cm.course_id
    WHERE
        -- Authorization: only return chunks from authorized courses
        cm.course_id = ANY(p_course_ids)
        AND cm.status = 'READY'
        AND mc.embedding IS NOT NULL
        -- Filter by minimum similarity to avoid returning irrelevant results
        AND (1 - (mc.embedding <=> p_query_embedding)) >= p_similarity_threshold
    ORDER BY
        mc.embedding <=> p_query_embedding   -- HNSW uses this operator
    LIMIT p_top_k;
END;
$$ LANGUAGE plpgsql STABLE;


-- =============================================================================
-- Function 6: update_enrollment_completion
-- Recalculates and updates completion_percentage for a student's enrollment.
-- Called by triggers when submissions are graded.
-- =============================================================================
CREATE OR REPLACE FUNCTION update_enrollment_completion(
    p_student_id UUID,
    p_course_id  UUID
)
RETURNS VOID AS $$
DECLARE
    v_total_assignments INTEGER;
    v_graded_assignments INTEGER;
    v_completion DECIMAL(5,2);
BEGIN
    -- Count published assignments in the course
    SELECT COUNT(*) INTO v_total_assignments
    FROM assignments
    WHERE course_id = p_course_id AND status = 'PUBLISHED';

    IF v_total_assignments = 0 THEN
        RETURN;  -- Nothing to calculate
    END IF;

    -- Count assignments this student has a grade for
    SELECT COUNT(DISTINCT a.assignment_id)
    INTO v_graded_assignments
    FROM assignments a
    JOIN submissions sub ON sub.assignment_id = a.assignment_id
        AND sub.student_id = p_student_id
    JOIN submission_grades g ON g.submission_id = sub.submission_id
    WHERE a.course_id = p_course_id AND a.status = 'PUBLISHED';

    v_completion := ROUND(
        (v_graded_assignments::DECIMAL / v_total_assignments) * 100,
        2
    );

    UPDATE enrollments
    SET completion_percentage = v_completion,
        updated_at = NOW()
    WHERE student_id = p_student_id
      AND course_id = p_course_id;
END;
$$ LANGUAGE plpgsql;

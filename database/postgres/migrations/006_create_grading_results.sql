-- =============================================================================
-- Migration 006: Grading and Results
-- =============================================================================
-- submission_grades: The raw act of grading a single submission.
-- course_results: The final computed result for a student in a course.
-- result_components: The breakdown (assignment total, quiz total, exam, etc.)
--
-- Design principle: results are computed from components, not duplicated
-- from submissions. The stored function generate_student_course_result()
-- in a later migration performs the actual calculation.
-- =============================================================================

-- Grade given by a teacher for a specific submission
CREATE TABLE submission_grades (
    grade_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id   UUID NOT NULL REFERENCES submissions(submission_id) ON DELETE CASCADE,
    evaluator_id    UUID NOT NULL REFERENCES teachers(teacher_id) ON DELETE RESTRICT,
    marks_obtained  DECIMAL(6,2) NOT NULL,
    feedback        TEXT,
    graded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Only one grade record per submission (teacher updates via PATCH)
    CONSTRAINT submission_grades_submission_unique UNIQUE (submission_id),

    -- Marks cannot be negative
    CONSTRAINT submission_grades_marks_non_negative CHECK (marks_obtained >= 0)

    -- Note: marks_obtained <= assignment.total_marks is enforced by the
    -- application service and the trigger defined in migration 015,
    -- since cross-table CHECK constraints are not standard SQL.
);

CREATE TRIGGER trg_submission_grades_updated_at
    BEFORE UPDATE ON submission_grades
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Represents the final result for a student in a specific course.
-- This is populated after all grading is complete and result is published.
CREATE TYPE result_status AS ENUM ('PENDING', 'PUBLISHED', 'WITHHELD');

CREATE TABLE course_results (
    result_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id          UUID NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    course_id           UUID NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT,
    total_marks         DECIMAL(6,2),           -- Calculated from components
    max_marks           DECIMAL(6,2),           -- Maximum possible marks
    percentage          DECIMAL(5,2),           -- (total_marks/max_marks)*100
    grade               VARCHAR(5),             -- A+, A, B+, B, C, D, F
    grade_points        DECIMAL(4,2),           -- For GPA calculation (e.g., 9.0)
    status              result_status NOT NULL DEFAULT 'PENDING',
    published_at        TIMESTAMPTZ,
    calculated_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- A student has exactly one result record per course
    CONSTRAINT course_results_student_course_unique UNIQUE (student_id, course_id),

    CONSTRAINT course_results_percentage_range CHECK (
        percentage IS NULL OR (percentage >= 0 AND percentage <= 100)
    )
);

CREATE TRIGGER trg_course_results_updated_at
    BEFORE UPDATE ON course_results
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Result components track what contributed to the final result.
-- This allows flexibility: add exam marks, internal marks separately.
CREATE TYPE result_component_type AS ENUM (
    'ASSIGNMENT', 'QUIZ', 'MIDTERM_EXAM', 'FINAL_EXAM', 'INTERNAL', 'PROJECT', 'OTHER'
);

CREATE TABLE result_components (
    component_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    result_id           UUID NOT NULL REFERENCES course_results(result_id) ON DELETE CASCADE,
    component_type      result_component_type NOT NULL,
    component_name      VARCHAR(100) NOT NULL,   -- e.g., "Assignment Average", "Quiz 1"
    marks_obtained      DECIMAL(6,2) NOT NULL,
    max_marks           DECIMAL(6,2) NOT NULL,
    weight_percentage   DECIMAL(5,2) NOT NULL,   -- How much this counts toward final (e.g., 30.0)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT result_components_marks_valid CHECK (
        marks_obtained >= 0 AND marks_obtained <= max_marks
    ),

    CONSTRAINT result_components_weight_valid CHECK (
        weight_percentage > 0 AND weight_percentage <= 100
    )
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Teacher finds grade for a submission
CREATE INDEX idx_submission_grades_submission_id ON submission_grades(submission_id);

-- Evaluator's grading history
CREATE INDEX idx_submission_grades_evaluator_id ON submission_grades(evaluator_id);

-- Student views own results
CREATE INDEX idx_course_results_student_id ON course_results(student_id);

-- Results for a specific course (admin/teacher view)
CREATE INDEX idx_course_results_course_id ON course_results(course_id);

-- Filter published results
CREATE INDEX idx_course_results_status ON course_results(status);

-- Components for a result (result detail page)
CREATE INDEX idx_result_components_result_id ON result_components(result_id);

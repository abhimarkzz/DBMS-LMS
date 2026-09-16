-- =============================================================================
-- Migration 005: Assignments and Submissions
-- =============================================================================
-- Assignments belong to a course (1:N).
-- Submissions resolve Student M:N Assignment.
--
-- Design note on multiple attempts:
-- We allow multiple attempts per student per assignment, controlled by
-- assignment.max_attempts. The application enforces this, backed by the
-- check constraint. Each attempt is a separate submission row.
-- The most recent graded submission is the canonical one.
-- =============================================================================

CREATE TYPE assignment_status AS ENUM ('DRAFT', 'PUBLISHED', 'CLOSED', 'ARCHIVED');
CREATE TYPE submission_status AS ENUM ('SUBMITTED', 'LATE', 'GRADED', 'RETURNED', 'RESUBMITTED');

-- Assignments created by teachers for a course
CREATE TABLE assignments (
    assignment_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    instructions    TEXT,
    total_marks     DECIMAL(6,2) NOT NULL,
    due_date        TIMESTAMPTZ NOT NULL,
    status          assignment_status NOT NULL DEFAULT 'DRAFT',
    max_attempts    SMALLINT NOT NULL DEFAULT 1,
    created_by      UUID NOT NULL REFERENCES teachers(teacher_id) ON DELETE RESTRICT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT assignments_total_marks_positive CHECK (total_marks > 0),
    CONSTRAINT assignments_max_attempts_positive CHECK (max_attempts >= 1)
);

CREATE TRIGGER trg_assignments_updated_at
    BEFORE UPDATE ON assignments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Student submissions for assignments
-- file_url points to the storage location (local path or S3 key).
-- We never store the actual file in PostgreSQL.
CREATE TABLE submissions (
    submission_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id       UUID NOT NULL REFERENCES assignments(assignment_id) ON DELETE CASCADE,
    student_id          UUID NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    submission_text     TEXT,               -- Optional text submission
    file_url            VARCHAR(500),       -- Optional file submission path
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              submission_status NOT NULL DEFAULT 'SUBMITTED',
    attempt_number      SMALLINT NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- At least one of text or file must be provided
    CONSTRAINT submissions_content_required CHECK (
        submission_text IS NOT NULL OR file_url IS NOT NULL
    ),

    CONSTRAINT submissions_attempt_positive CHECK (attempt_number >= 1),

    -- A student cannot have two submissions with the same attempt number
    -- for the same assignment. The application enforces max_attempts.
    CONSTRAINT submissions_attempt_unique UNIQUE (assignment_id, student_id, attempt_number)
);

CREATE TRIGGER trg_submissions_updated_at
    BEFORE UPDATE ON submissions
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- Indexes
-- =============================================================================

-- Teacher views all submissions for an assignment
CREATE INDEX idx_assignments_course_id ON assignments(course_id);

-- Filter published assignments (student view)
CREATE INDEX idx_assignments_status ON assignments(status);

-- Upcoming deadline filter (student dashboard: assignments due soon)
CREATE INDEX idx_assignments_due_date ON assignments(due_date);

-- All submissions for an assignment (teacher grading view)
CREATE INDEX idx_submissions_assignment_id ON submissions(assignment_id);

-- All submissions by a student (student history)
CREATE INDEX idx_submissions_student_id ON submissions(student_id);

-- Composite: find a specific student's submissions for a specific assignment
CREATE INDEX idx_submissions_assignment_student ON submissions(assignment_id, student_id);

-- Filter by status (find all graded submissions, or pending ones)
CREATE INDEX idx_submissions_status ON submissions(status);

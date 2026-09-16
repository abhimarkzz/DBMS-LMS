-- =============================================================================
-- Migration 004: Courses and Enrollments
-- =============================================================================
-- Courses represent the academic course catalog.
-- Enrollments resolve the M:N relationship between students and courses.
--
-- Design note: A course currently has one primary teacher. The schema is
-- designed so that multiple instructors can be added later via a
-- course_instructors junction table without breaking anything.
-- =============================================================================

-- Status for course lifecycle
CREATE TYPE course_status AS ENUM ('DRAFT', 'ACTIVE', 'ARCHIVED');

-- Enrollment status for tracking student progress
CREATE TYPE enrollment_status AS ENUM ('ENROLLED', 'COMPLETED', 'DROPPED', 'SUSPENDED');

-- Course catalog
CREATE TABLE courses (
    course_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code     VARCHAR(20) NOT NULL,
    course_name     VARCHAR(200) NOT NULL,
    description     TEXT,
    credits         SMALLINT NOT NULL,
    department      VARCHAR(100) NOT NULL,
    semester        SMALLINT NOT NULL,
    teacher_id      UUID NOT NULL REFERENCES teachers(teacher_id) ON DELETE RESTRICT,
    status          course_status NOT NULL DEFAULT 'DRAFT',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Course code uniquely identifies a course across all departments
    CONSTRAINT courses_code_unique UNIQUE (course_code),

    -- Credits must be positive
    CONSTRAINT courses_credits_positive CHECK (credits > 0),

    CONSTRAINT courses_semester_range CHECK (semester BETWEEN 1 AND 12)
);

-- updated_at auto-maintenance
CREATE TRIGGER trg_courses_updated_at
    BEFORE UPDATE ON courses
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Announcements are course-level broadcasts from teachers
CREATE TABLE announcements (
    announcement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    posted_by       UUID NOT NULL REFERENCES teachers(teacher_id) ON DELETE RESTRICT,
    title           VARCHAR(255) NOT NULL,
    content         TEXT NOT NULL,
    is_pinned       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_announcements_updated_at
    BEFORE UPDATE ON announcements
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Resolves Student M:N Course relationship
-- Each row represents one student enrolled in one course.
CREATE TABLE enrollments (
    enrollment_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id              UUID NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    course_id               UUID NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT,
    enrolled_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status                  enrollment_status NOT NULL DEFAULT 'ENROLLED',
    -- Completion percentage is updated by triggers when assignments are graded
    completion_percentage   DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- A student can only be enrolled once in a given course
    CONSTRAINT enrollments_student_course_unique UNIQUE (student_id, course_id),

    CONSTRAINT enrollments_completion_range CHECK (
        completion_percentage >= 0.00 AND completion_percentage <= 100.00
    )
);

CREATE TRIGGER trg_enrollments_updated_at
    BEFORE UPDATE ON enrollments
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- Indexes
-- =============================================================================

-- Most common course lookup: by code (used in admin and enrollment flows)
CREATE INDEX idx_courses_course_code ON courses(course_code);

-- Filter courses by teacher (teacher dashboard)
CREATE INDEX idx_courses_teacher_id ON courses(teacher_id);

-- Filter active courses (homepage, student browsing)
CREATE INDEX idx_courses_status ON courses(status);

-- Filter by department/semester for catalog browsing
CREATE INDEX idx_courses_department ON courses(department);
CREATE INDEX idx_courses_semester ON courses(semester);

-- The two most common enrollment queries:
--   1. All courses for a student
--   2. All students in a course
-- Composite index covers both with column order consideration
CREATE INDEX idx_enrollments_student_id ON enrollments(student_id);
CREATE INDEX idx_enrollments_course_id ON enrollments(course_id);

-- Filter enrollments by status (active students in a course)
CREATE INDEX idx_enrollments_status ON enrollments(status);

-- Announcements by course (most common fetch pattern)
CREATE INDEX idx_announcements_course_id ON announcements(course_id);
CREATE INDEX idx_announcements_created_at ON announcements(course_id, created_at DESC);

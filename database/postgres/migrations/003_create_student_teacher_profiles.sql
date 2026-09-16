-- =============================================================================
-- Migration 003: Student and Teacher Profiles
-- =============================================================================
-- Student and teacher information is separated from the generic users table
-- to follow 3NF (Third Normal Form).
--
-- If we stored department, semester, employee_id, etc. directly in users,
-- we would have many NULL columns for users of other roles — a violation
-- of good normalization. Each profile table has a 1:1 relationship with users.
-- =============================================================================

-- Student-specific profile data
CREATE TABLE students (
    student_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    registration_number VARCHAR(50) NOT NULL,
    department          VARCHAR(100) NOT NULL,
    semester            SMALLINT NOT NULL,
    section             VARCHAR(10),
    admission_year      SMALLINT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One user can only have one student profile
    CONSTRAINT students_user_id_unique UNIQUE (user_id),

    -- Registration number uniquely identifies a student in the institution
    CONSTRAINT students_registration_number_unique UNIQUE (registration_number),

    -- Semester must be between 1 and 8 for a standard B.Tech program
    CONSTRAINT students_semester_range CHECK (semester BETWEEN 1 AND 12),

    -- Admission year must be a realistic 4-digit year
    CONSTRAINT students_admission_year_range CHECK (admission_year BETWEEN 1990 AND 2100)
);

-- Teacher-specific profile data
CREATE TABLE teachers (
    teacher_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    employee_id     VARCHAR(50) NOT NULL,
    department      VARCHAR(100) NOT NULL,
    designation     VARCHAR(100) NOT NULL DEFAULT 'Assistant Professor',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One user can only have one teacher profile
    CONSTRAINT teachers_user_id_unique UNIQUE (user_id),

    -- Employee ID must be unique within the institution
    CONSTRAINT teachers_employee_id_unique UNIQUE (employee_id)
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Frequently looked up when building student profile from JWT user_id
CREATE INDEX idx_students_user_id ON students(user_id);

-- Used in admin searches and reporting
CREATE INDEX idx_students_registration_number ON students(registration_number);

-- Used when filtering students by department/semester in reports
CREATE INDEX idx_students_department ON students(department);
CREATE INDEX idx_students_semester ON students(semester);

-- Teacher lookups from user context
CREATE INDEX idx_teachers_user_id ON teachers(user_id);
CREATE INDEX idx_teachers_employee_id ON teachers(employee_id);
CREATE INDEX idx_teachers_department ON teachers(department);

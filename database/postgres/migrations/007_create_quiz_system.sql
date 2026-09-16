-- =============================================================================
-- Migration 007: Quiz System
-- =============================================================================
-- Quizzes are attached to courses (not assignments) for flexibility.
-- Students can attempt quizzes within a time window.
--
-- Security note: correct answer IDs are never exposed via student-facing
-- endpoints. The application service filters correct_option_id from
-- response payloads until after the quiz window closes.
-- =============================================================================

CREATE TYPE quiz_status AS ENUM ('DRAFT', 'PUBLISHED', 'CLOSED');
CREATE TYPE question_type AS ENUM ('SINGLE_CHOICE', 'MULTIPLE_CHOICE', 'TRUE_FALSE');
CREATE TYPE attempt_status AS ENUM ('IN_PROGRESS', 'SUBMITTED', 'GRADED');

-- Quiz configuration
CREATE TABLE quizzes (
    quiz_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    total_marks     DECIMAL(6,2) NOT NULL,
    duration_minutes SMALLINT NOT NULL,         -- Time limit in minutes
    start_time      TIMESTAMPTZ,                -- NULL = available immediately
    end_time        TIMESTAMPTZ,                -- NULL = no deadline
    status          quiz_status NOT NULL DEFAULT 'DRAFT',
    created_by      UUID NOT NULL REFERENCES teachers(teacher_id) ON DELETE RESTRICT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT quizzes_total_marks_positive CHECK (total_marks > 0),
    CONSTRAINT quizzes_duration_positive CHECK (duration_minutes > 0),
    CONSTRAINT quizzes_time_range CHECK (
        start_time IS NULL OR end_time IS NULL OR end_time > start_time
    )
);

CREATE TRIGGER trg_quizzes_updated_at
    BEFORE UPDATE ON quizzes
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

-- Individual questions in a quiz
CREATE TABLE quiz_questions (
    question_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id         UUID NOT NULL REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    question_text   TEXT NOT NULL,
    question_type   question_type NOT NULL DEFAULT 'SINGLE_CHOICE',
    marks           DECIMAL(5,2) NOT NULL,
    question_order  SMALLINT NOT NULL DEFAULT 1,  -- Display order
    explanation     TEXT,                          -- Shown after submission
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT quiz_questions_marks_positive CHECK (marks > 0),
    CONSTRAINT quiz_questions_order_positive CHECK (question_order >= 1)
);

-- Answer options for a question
CREATE TABLE quiz_options (
    option_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id         UUID NOT NULL REFERENCES quiz_questions(question_id) ON DELETE CASCADE,
    option_text         TEXT NOT NULL,
    is_correct          BOOLEAN NOT NULL DEFAULT FALSE,
    option_order        SMALLINT NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT quiz_options_order_positive CHECK (option_order >= 1)
);

-- Records each time a student attempts a quiz
CREATE TABLE quiz_attempts (
    attempt_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id         UUID NOT NULL REFERENCES quizzes(quiz_id) ON DELETE CASCADE,
    student_id      UUID NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at    TIMESTAMPTZ,
    score           DECIMAL(6,2),               -- Calculated on submission
    status          attempt_status NOT NULL DEFAULT 'IN_PROGRESS',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One active attempt per student per quiz at a time.
    -- If retakes are allowed, add a attempt_number column similar to submissions.
    CONSTRAINT quiz_attempts_student_quiz_unique UNIQUE (quiz_id, student_id),

    CONSTRAINT quiz_attempts_score_non_negative CHECK (score IS NULL OR score >= 0)
);

-- Individual answers selected by a student during an attempt
CREATE TABLE quiz_answers (
    answer_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id      UUID NOT NULL REFERENCES quiz_attempts(attempt_id) ON DELETE CASCADE,
    question_id     UUID NOT NULL REFERENCES quiz_questions(question_id) ON DELETE CASCADE,
    selected_option_id UUID REFERENCES quiz_options(option_id) ON DELETE SET NULL,
    is_correct      BOOLEAN,                    -- Set when attempt is graded
    marks_awarded   DECIMAL(5,2),               -- Set when attempt is graded
    answered_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One answer per question per attempt
    CONSTRAINT quiz_answers_attempt_question_unique UNIQUE (attempt_id, question_id)
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX idx_quizzes_course_id ON quizzes(course_id);
CREATE INDEX idx_quizzes_status ON quizzes(status);
CREATE INDEX idx_quiz_questions_quiz_id ON quiz_questions(quiz_id);
CREATE INDEX idx_quiz_options_question_id ON quiz_options(question_id);
CREATE INDEX idx_quiz_attempts_student_id ON quiz_attempts(student_id);
CREATE INDEX idx_quiz_attempts_quiz_id ON quiz_attempts(quiz_id);
CREATE INDEX idx_quiz_answers_attempt_id ON quiz_answers(attempt_id);

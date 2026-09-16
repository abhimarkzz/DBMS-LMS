-- =============================================================================
-- Database Triggers
-- =============================================================================
-- Triggers automate actions that should happen atomically with data changes,
-- without requiring the application to make multiple API calls.
--
-- Each trigger here solves a real consistency problem — not just demonstrating
-- that triggers exist.
-- =============================================================================


-- =============================================================================
-- Trigger 1: trg_after_grade_inserted
-- Purpose: When a submission is graded, automatically:
--   1. Update the submission status to 'GRADED'
--   2. Recalculate the student's course result
--   3. Update enrollment completion percentage
--
-- Why a trigger and not application code?
-- The grading and result update must be atomic. If the result update fails,
-- the grade insert should also roll back. A trigger runs in the same
-- transaction, ensuring this atomicity without distributed coordination.
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_after_grade_inserted()
RETURNS TRIGGER AS $$
DECLARE
    v_student_id UUID;
    v_course_id  UUID;
BEGIN
    -- Get the student and course from the submission
    SELECT sub.student_id, a.course_id
    INTO v_student_id, v_course_id
    FROM submissions sub
    JOIN assignments a ON a.assignment_id = sub.assignment_id
    WHERE sub.submission_id = NEW.submission_id;

    -- Mark the submission as graded
    UPDATE submissions
    SET status = 'GRADED', updated_at = NOW()
    WHERE submission_id = NEW.submission_id;

    -- Recalculate course result for this student
    PERFORM generate_student_course_result(v_student_id, v_course_id);

    -- Update enrollment completion percentage
    PERFORM update_enrollment_completion(v_student_id, v_course_id);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_after_grade_inserted
    AFTER INSERT ON submission_grades
    FOR EACH ROW
    EXECUTE FUNCTION fn_after_grade_inserted();


-- =============================================================================
-- Trigger 2: trg_after_grade_updated
-- Purpose: When a grade is updated (teacher revises marks), recalculate
-- the course result to reflect the new marks.
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_after_grade_updated()
RETURNS TRIGGER AS $$
DECLARE
    v_student_id UUID;
    v_course_id  UUID;
BEGIN
    -- Only recalculate if the marks actually changed
    IF OLD.marks_obtained = NEW.marks_obtained THEN
        RETURN NEW;
    END IF;

    SELECT sub.student_id, a.course_id
    INTO v_student_id, v_course_id
    FROM submissions sub
    JOIN assignments a ON a.assignment_id = sub.assignment_id
    WHERE sub.submission_id = NEW.submission_id;

    -- Recalculate result with updated marks
    PERFORM generate_student_course_result(v_student_id, v_course_id);
    PERFORM update_enrollment_completion(v_student_id, v_course_id);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_after_grade_updated
    AFTER UPDATE ON submission_grades
    FOR EACH ROW
    EXECUTE FUNCTION fn_after_grade_updated();


-- =============================================================================
-- Trigger 3: trg_validate_grade_marks
-- Purpose: Enforce that marks_obtained does not exceed assignment's total_marks.
-- This is a cross-table constraint that cannot be expressed as a CHECK constraint.
--
-- Runs BEFORE INSERT and UPDATE to reject invalid data before it reaches disk.
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_validate_grade_marks()
RETURNS TRIGGER AS $$
DECLARE
    v_total_marks DECIMAL(6,2);
BEGIN
    -- Get the total marks for the assignment this submission belongs to
    SELECT a.total_marks INTO v_total_marks
    FROM submissions sub
    JOIN assignments a ON a.assignment_id = sub.assignment_id
    WHERE sub.submission_id = NEW.submission_id;

    IF v_total_marks IS NULL THEN
        RAISE EXCEPTION 'Submission % not found or assignment has no total_marks',
            NEW.submission_id;
    END IF;

    IF NEW.marks_obtained > v_total_marks THEN
        RAISE EXCEPTION 'marks_obtained (%) cannot exceed assignment total_marks (%)',
            NEW.marks_obtained, v_total_marks;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_grade_marks
    BEFORE INSERT OR UPDATE ON submission_grades
    FOR EACH ROW
    EXECUTE FUNCTION fn_validate_grade_marks();


-- =============================================================================
-- Trigger 4: trg_prevent_late_submission_change
-- Purpose: Once an assignment is CLOSED, prevent new submissions.
-- This runs BEFORE INSERT on submissions.
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_check_assignment_open_for_submission()
RETURNS TRIGGER AS $$
DECLARE
    v_status    assignment_status;
    v_due_date  TIMESTAMPTZ;
BEGIN
    SELECT status, due_date
    INTO v_status, v_due_date
    FROM assignments
    WHERE assignment_id = NEW.assignment_id;

    -- Reject submissions to closed or archived assignments
    IF v_status IN ('CLOSED', 'ARCHIVED', 'DRAFT') THEN
        RAISE EXCEPTION 'Assignment is not accepting submissions (status: %)', v_status;
    END IF;

    -- Mark as LATE if past the due date but assignment is still PUBLISHED
    IF NOW() > v_due_date AND v_status = 'PUBLISHED' THEN
        NEW.status = 'LATE';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_assignment_open
    BEFORE INSERT ON submissions
    FOR EACH ROW
    EXECUTE FUNCTION fn_check_assignment_open_for_submission();


-- =============================================================================
-- Trigger 5: trg_audit_user_login
-- Purpose: Record a login event in activity_events when last_login_at is updated.
-- Avoids requiring the application to explicitly insert an activity event.
-- Note: IP and request_id cannot be captured in a trigger — the application
-- still logs the full event. This trigger is a backup log.
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_audit_user_login()
RETURNS TRIGGER AS $$
BEGIN
    -- Only fire when last_login_at changes (i.e., a new login occurred)
    IF OLD.last_login_at IS DISTINCT FROM NEW.last_login_at AND NEW.last_login_at IS NOT NULL THEN
        INSERT INTO activity_events (actor_id, event_type, entity_type, entity_id, metadata)
        VALUES (
            NEW.user_id,
            'USER_LOGIN',
            'users',
            NEW.user_id,
            jsonb_build_object('role', NEW.role::TEXT)
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_user_login
    AFTER UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION fn_audit_user_login();

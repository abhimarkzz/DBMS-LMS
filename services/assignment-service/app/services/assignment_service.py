from datetime import datetime, timezone
from uuid import UUID
from typing import Tuple, Sequence

from app.core.exceptions import (
    AssignmentNotFoundError,
    PermissionDeniedError,
    SubmissionNotFoundError,
    ValidationError,
    ConflictError
)
from app.models.assignment import Assignment, Submission, AssignmentStatus
from app.repositories.assignment_repository import AssignmentRepository
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentUpdate,
    SubmissionCreate,
    GradeSubmissionRequest,
)

class AssignmentService:
    def __init__(self, repository: AssignmentRepository):
        self.repository = repository

    async def create_assignment(self, teacher_id: UUID, data: AssignmentCreate) -> Assignment:
        # In a real microservices architecture, we should verify that `course_id` exists
        # and that `teacher_id` actually teaches it.
        # Since course data is in another service, the API gateway or an internal HTTP client
        # could check that. For this project, we assume the teacher is authorized if they
        # provide the course_id (or rely on UI ensuring they only see their courses).
        return await self.repository.create_assignment(teacher_id, data)

    async def get_assignment(self, assignment_id: UUID) -> Assignment:
        assignment = await self.repository.get_assignment_by_id(assignment_id)
        if not assignment:
            raise AssignmentNotFoundError()
        return assignment

    async def update_assignment(
        self, assignment_id: UUID, teacher_id: UUID, data: AssignmentUpdate, is_admin: bool = False
    ) -> Assignment:
        assignment = await self.get_assignment(assignment_id)

        if not is_admin and assignment.created_by != teacher_id:
            raise PermissionDeniedError("You can only update assignments you created.")

        return await self.repository.update_assignment(assignment, data)

    async def get_course_assignments(self, course_id: UUID, page: int, size: int) -> Tuple[Sequence[Assignment], int]:
        skip = (page - 1) * size
        return await self.repository.list_assignments_by_course(course_id, skip, size)

    async def submit_assignment(self, assignment_id: UUID, student_id: UUID, data: SubmissionCreate) -> Submission:
        assignment = await self.get_assignment(assignment_id)

        if assignment.status != AssignmentStatus.PUBLISHED:
            raise ConflictError("Cannot submit to an assignment that is not published.")

        due_date_utc = assignment.due_date
        if due_date_utc.tzinfo is None:
            due_date_utc = due_date_utc.replace(tzinfo=timezone.utc)
            
        if due_date_utc < datetime.now(timezone.utc):
            # We could mark it LATE instead of throwing an error, but let's allow it as LATE
            # Business rule: check if they exceeded attempts
            pass

        attempts = await self.repository.get_student_attempts_count(assignment_id, student_id)
        if attempts >= assignment.max_attempts:
            raise ConflictError(f"Maximum attempts ({assignment.max_attempts}) reached.")

        if not data.submission_text and not data.file_url:
            raise ValidationError("Must provide either text or a file url.")

        attempt_number = attempts + 1
        return await self.repository.create_submission(assignment_id, student_id, attempt_number, data)

    async def get_student_submission(self, assignment_id: UUID, student_id: UUID) -> Submission:
        submission = await self.repository.get_student_latest_submission(assignment_id, student_id)
        if not submission:
            raise SubmissionNotFoundError("No submission found for this student.")
        return submission

    async def get_submissions_for_assignment(
        self, assignment_id: UUID, teacher_id: UUID, page: int, size: int, is_admin: bool = False
    ) -> Tuple[Sequence[Submission], int]:
        assignment = await self.get_assignment(assignment_id)
        if not is_admin and assignment.created_by != teacher_id:
            raise PermissionDeniedError("You can only view submissions for your own assignments.")

        skip = (page - 1) * size
        return await self.repository.list_submissions_for_assignment(assignment_id, skip, size)

    async def grade_submission(
        self, submission_id: UUID, teacher_id: UUID, data: GradeSubmissionRequest, is_admin: bool = False
    ) -> Submission:
        submission = await self.repository.get_submission_by_id(submission_id)
        if not submission:
            raise SubmissionNotFoundError()

        assignment = await self.get_assignment(submission.assignment_id)
        if not is_admin and assignment.created_by != teacher_id:
            raise PermissionDeniedError("You can only grade submissions for your own assignments.")

        if data.marks_awarded > assignment.total_marks:
            raise ValidationError(f"Marks awarded cannot exceed total marks ({assignment.total_marks}).")

        submission.marks_awarded = data.marks_awarded
        submission.teacher_feedback = data.teacher_feedback
        submission.status = data.status
        submission.graded_by = teacher_id
        submission.graded_at = datetime.now(timezone.utc)

        # Trigger update explicitly not needed because object is tracked by session
        # but we can call a flush if we wanted to
        return submission

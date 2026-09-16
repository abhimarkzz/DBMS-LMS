from uuid import UUID
from typing import Sequence, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment, Submission, SubmissionStatus
from app.schemas.assignment import AssignmentCreate, AssignmentUpdate, SubmissionCreate


class AssignmentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ==========================
    # Assignments
    # ==========================

    async def create_assignment(self, teacher_id: UUID, data: AssignmentCreate) -> Assignment:
        assignment = Assignment(
            course_id=data.course_id,
            title=data.title,
            description=data.description,
            instructions=data.instructions,
            total_marks=data.total_marks,
            due_date=data.due_date,
            status=data.status,
            max_attempts=data.max_attempts,
            created_by=teacher_id
        )
        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def get_assignment_by_id(self, assignment_id: UUID) -> Optional[Assignment]:
        stmt = select(Assignment).where(Assignment.assignment_id == assignment_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_assignments_by_course(self, course_id: UUID, skip: int, limit: int) -> Tuple[Sequence[Assignment], int]:
        # Count
        count_stmt = select(func.count()).where(Assignment.course_id == course_id)
        total = await self.session.scalar(count_stmt) or 0

        # Fetch
        stmt = (
            select(Assignment)
            .where(Assignment.course_id == course_id)
            .order_by(Assignment.due_date.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def update_assignment(self, assignment: Assignment, data: AssignmentUpdate) -> Assignment:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(assignment, key, value)
        await self.session.flush()
        return assignment

    async def delete_assignment(self, assignment: Assignment) -> None:
        await self.session.delete(assignment)
        await self.session.flush()

    # ==========================
    # Submissions
    # ==========================

    async def get_student_attempts_count(self, assignment_id: UUID, student_id: UUID) -> int:
        stmt = select(func.count()).where(
            and_(
                Submission.assignment_id == assignment_id,
                Submission.student_id == student_id
            )
        )
        return await self.session.scalar(stmt) or 0

    async def create_submission(
        self, assignment_id: UUID, student_id: UUID, attempt_number: int, data: SubmissionCreate
    ) -> Submission:
        submission = Submission(
            assignment_id=assignment_id,
            student_id=student_id,
            submission_text=data.submission_text,
            file_url=data.file_url,
            attempt_number=attempt_number,
            status=SubmissionStatus.SUBMITTED
        )
        self.session.add(submission)
        await self.session.flush()
        return submission

    async def get_submission_by_id(self, submission_id: UUID) -> Optional[Submission]:
        stmt = select(Submission).where(Submission.submission_id == submission_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_student_latest_submission(self, assignment_id: UUID, student_id: UUID) -> Optional[Submission]:
        stmt = (
            select(Submission)
            .where(and_(Submission.assignment_id == assignment_id, Submission.student_id == student_id))
            .order_by(Submission.attempt_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_submissions_for_assignment(self, assignment_id: UUID, skip: int, limit: int) -> Tuple[Sequence[Submission], int]:
        # Count
        count_stmt = select(func.count()).where(Submission.assignment_id == assignment_id)
        total = await self.session.scalar(count_stmt) or 0

        # Fetch
        stmt = (
            select(Submission)
            .where(Submission.assignment_id == assignment_id)
            .order_by(Submission.submitted_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

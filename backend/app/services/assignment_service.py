from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.sql_models import Assignment, Submission
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.course_repo import CourseRepository
from app.services.notification_service import NotificationService


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.assignment_repo = AssignmentRepository(db)
        self.course_repo = CourseRepository(db)

    def create_assignment(
        self, 
        course_id: int, 
        title: str, 
        description: str, 
        max_score: float, 
        due_date: Optional[datetime],
        teacher_id: int
    ) -> Assignment:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        if course.teacher_id != teacher_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only course instructor can create assignments")

        if max_score <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="max_score must be positive")

        return self.assignment_repo.create_assignment(
            course_id=course_id,
            title=title,
            description=description,
            max_score=max_score,
            due_date=due_date
        )

    def list_assignments(self, course_id: Optional[int] = None, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if course_id:
            return self.assignment_repo.list_assignments_for_course(course_id, student_id=student_id)
        return self.assignment_repo.list_all_assignments(student_id=student_id)

    async def submit_assignment(
        self, 
        assignment_id: int, 
        student_id: int, 
        content: str, 
        file_url: Optional[str] = None
    ) -> Submission:
        assignment = self.assignment_repo.get_assignment_by_id(assignment_id)
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

        # Verify student enrollment
        if not self.course_repo.is_student_enrolled(student_id, assignment.course_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in the course to submit assignments"
            )

        submission = self.assignment_repo.create_or_update_submission(
            assignment_id=assignment_id,
            student_id=student_id,
            content=content,
            file_url=file_url
        )

        # Notify instructor in MongoDB & Redis
        if assignment.course and assignment.course.teacher_id:
            await NotificationService.create_notification(
                user_id=assignment.course.teacher_id,
                title="New Assignment Submission",
                message=f"A student submitted assignment: '{assignment.title}' in {assignment.course.code}.",
                notif_type="SUBMISSION",
                metadata={"assignment_id": assignment.id, "submission_id": submission.id}
            )

        return submission

    async def grade_submission(
        self, 
        submission_id: int, 
        score: float, 
        feedback: Optional[str],
        teacher_id: int
    ) -> Submission:
        submission = self.assignment_repo.get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

        course = submission.assignment.course if submission.assignment else None
        if not course or course.teacher_id != teacher_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the course instructor can grade this submission"
            )

        if score < 0 or score > float(submission.assignment.max_score):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Score must be between 0 and {submission.assignment.max_score}"
            )

        graded_sub = self.assignment_repo.grade_submission(submission_id, score, feedback)

        # Notify student in MongoDB & Redis
        await NotificationService.create_notification(
            user_id=graded_sub.student_id,
            title="Assignment Graded",
            message=f"Your submission for '{submission.assignment.title}' has been graded: {score}/{submission.assignment.max_score}.",
            notif_type="GRADE",
            metadata={"assignment_id": submission.assignment_id, "score": score}
        )

        return graded_sub

    def list_submissions_for_assignment(self, assignment_id: int, teacher_id: int) -> List[Dict[str, Any]]:
        assignment = self.assignment_repo.get_assignment_by_id(assignment_id)
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

        if assignment.course and assignment.course.teacher_id != teacher_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        submissions = self.assignment_repo.list_submissions_for_assignment(assignment_id)
        return [
            {
                "id": s.id,
                "assignment_id": s.assignment_id,
                "assignment_title": assignment.title,
                "max_score": float(assignment.max_score),
                "student_id": s.student_id,
                "student_name": s.student.full_name if s.student else None,
                "student_email": s.student.email if s.student else None,
                "content": s.content,
                "file_url": s.file_url,
                "submitted_at": s.submitted_at,
                "status": s.status,
                "score": float(s.score) if s.score is not None else None,
                "feedback": s.feedback,
                "graded_at": s.graded_at
            }
            for s in submissions
        ]

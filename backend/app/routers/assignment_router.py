from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.assignment_schema import (
    AssignmentCreate, AssignmentResponse, 
    SubmissionCreate, SubmissionGrade, SubmissionResponse
)
from app.services.assignment_service import AssignmentService
from app.services.auth_service import get_current_user, require_roles
from app.services.notification_service import NotificationService
from app.models.sql_models import User

router = APIRouter(prefix="/api/assignments", tags=["Assignments"])


@router.get("", response_model=List[AssignmentResponse])
def list_assignments(
    course_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    student_id = current_user.id if current_user.role and current_user.role.name == "STUDENT" else None
    return service.list_assignments(course_id=course_id, student_id=student_id)


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: AssignmentCreate,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    assignment = service.create_assignment(
        course_id=payload.course_id,
        title=payload.title,
        description=payload.description,
        max_score=payload.max_score,
        due_date=payload.due_date,
        teacher_id=current_user.id
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ASSIGNMENT_CREATED",
        details=f"Created assignment '{assignment.title}'"
    )
    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "course_title": assignment.course.title if assignment.course else None,
        "course_code": assignment.course.code if assignment.course else None,
        "title": assignment.title,
        "description": assignment.description,
        "max_score": float(assignment.max_score),
        "due_date": assignment.due_date,
        "created_at": assignment.created_at,
        "has_submitted": False
    }


@router.post("/{assignment_id}/submit", response_model=SubmissionResponse)
async def submit_assignment(
    assignment_id: int,
    payload: SubmissionCreate,
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    submission = await service.submit_assignment(
        assignment_id=assignment_id,
        student_id=current_user.id,
        content=payload.content,
        file_url=payload.file_url
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ASSIGNMENT_SUBMITTED",
        details=f"Submitted assignment ID {assignment_id}"
    )
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": submission.assignment.title if submission.assignment else None,
        "max_score": float(submission.assignment.max_score) if submission.assignment else None,
        "student_id": submission.student_id,
        "student_name": current_user.full_name,
        "student_email": current_user.email,
        "content": submission.content,
        "file_url": submission.file_url,
        "submitted_at": submission.submitted_at,
        "status": submission.status,
        "score": float(submission.score) if submission.score is not None else None,
        "feedback": submission.feedback,
        "graded_at": submission.graded_at
    }


@router.get("/{assignment_id}/submissions", response_model=List[SubmissionResponse])
def get_assignment_submissions(
    assignment_id: int,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    return service.list_submissions_for_assignment(assignment_id, teacher_id=current_user.id)


@router.post("/submissions/{submission_id}/grade", response_model=SubmissionResponse)
async def grade_submission(
    submission_id: int,
    payload: SubmissionGrade,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    submission = await service.grade_submission(
        submission_id=submission_id,
        score=payload.score,
        feedback=payload.feedback,
        teacher_id=current_user.id
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="SUBMISSION_GRADED",
        details=f"Graded submission ID {submission_id} with score {payload.score}"
    )
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": submission.assignment.title if submission.assignment else None,
        "max_score": float(submission.assignment.max_score) if submission.assignment else None,
        "student_id": submission.student_id,
        "student_name": submission.student.full_name if submission.student else None,
        "student_email": submission.student.email if submission.student else None,
        "content": submission.content,
        "file_url": submission.file_url,
        "submitted_at": submission.submitted_at,
        "status": submission.status,
        "score": float(submission.score) if submission.score is not None else None,
        "feedback": submission.feedback,
        "graded_at": submission.graded_at
    }

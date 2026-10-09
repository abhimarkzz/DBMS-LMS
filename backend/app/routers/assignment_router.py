from typing import List, Optional
from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Response, HTTPException
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.assignment_schema import (
    AssignmentCreate, AssignmentResponse, 
    SubmissionCreate, SubmissionGrade, SubmissionResponse
)
from app.services.assignment_service import AssignmentService
from app.services.file_storage_service import FileStorageService
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
        teacher_id=current_user.id,
        instructions=payload.instructions,
        assessment_type=payload.assessment_type or "DESCRIPTIVE",
        start_date=payload.start_date,
        due_time=payload.due_time,
        attempt_limit=payload.attempt_limit or 1,
        late_allowed=payload.late_allowed if payload.late_allowed is not None else True,
        status_val=payload.status or "PUBLISHED",
        attachment_url=payload.attachment_url,
        assessment_config=payload.assessment_config
    )
    # If published, broadcast notification to enrolled students
    if assignment.status == "PUBLISHED":
        due_str = assignment.due_date.strftime("%b %d, %H:%M UTC") if assignment.due_date else "No deadline"
        course_code = assignment.course.code if assignment.course else f"Course #{assignment.course_id}"
        await NotificationService.notify_enrolled_students(
            db=db,
            course_id=assignment.course_id,
            title=f"New Assignment: {assignment.title}",
            message=f"New {assignment.assessment_type.lower()} assignment published in {course_code}. Due: {due_str}.",
            notif_type="ASSIGNMENT_PUBLISHED",
            metadata={
                "course_id": assignment.course_id,
                "assignment_id": assignment.id,
                "assessment_type": assignment.assessment_type,
                "target_tab": "assignments"
            }
        )

    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ASSIGNMENT_CREATED",
        details=f"Created {assignment.assessment_type} assessment '{assignment.title}'"
    )
    return {
        "id": assignment.id,
        "course_id": assignment.course_id,
        "course_title": assignment.course.title if assignment.course else None,
        "course_code": assignment.course.code if assignment.course else None,
        "title": assignment.title,
        "description": assignment.description,
        "instructions": assignment.instructions,
        "max_score": float(assignment.max_score),
        "assessment_type": assignment.assessment_type,
        "due_date": assignment.due_date,
        "start_date": assignment.start_date,
        "due_time": assignment.due_time,
        "attempt_limit": assignment.attempt_limit,
        "late_allowed": assignment.late_allowed,
        "status": assignment.status,
        "attachment_url": assignment.attachment_url,
        "assessment_config": assignment.assessment_config,
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
        content=payload.content or "",
        file_url=payload.file_url,
        mcq_answers=payload.mcq_answers,
        submission_type=payload.submission_type or "TEXT"
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ASSIGNMENT_SUBMITTED",
        details=f"Submitted assessment ID {assignment_id} ({submission.submission_type})"
    )
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": submission.assignment.title if submission.assignment else None,
        "course_code": submission.assignment.course.code if (submission.assignment and submission.assignment.course) else None,
        "course_title": submission.assignment.course.title if (submission.assignment and submission.assignment.course) else None,
        "max_score": float(submission.assignment.max_score) if submission.assignment else None,
        "student_id": submission.student_id,
        "student_name": current_user.full_name,
        "student_email": current_user.email,
        "content": submission.content,
        "file_url": submission.file_url,
        "submission_type": submission.submission_type,
        "file_storage_id": submission.file_storage_id,
        "file_name": submission.file_name,
        "file_size": submission.file_size,
        "mcq_answers": submission.mcq_answers,
        "rubric_evaluation": submission.rubric_evaluation,
        "attempt_number": submission.attempt_number or 1,
        "is_late": submission.is_late or False,
        "submitted_at": submission.submitted_at,
        "status": submission.status,
        "grade_status": submission.grade_status,
        "score": float(submission.score) if submission.score is not None else None,
        "feedback": submission.feedback,
        "graded_at": submission.graded_at
    }


@router.post("/{assignment_id}/submit-file", response_model=SubmissionResponse)
async def submit_file_assignment(
    assignment_id: int,
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    submission = await service.submit_file_submission(
        assignment_id=assignment_id,
        student_id=current_user.id,
        file=file,
        notes=notes
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="FILE_SUBMITTED",
        details=f"Uploaded {submission.submission_type} file '{file.filename}' for assessment ID {assignment_id}"
    )
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": submission.assignment.title if submission.assignment else None,
        "course_code": submission.assignment.course.code if (submission.assignment and submission.assignment.course) else None,
        "course_title": submission.assignment.course.title if (submission.assignment and submission.assignment.course) else None,
        "max_score": float(submission.assignment.max_score) if submission.assignment else None,
        "student_id": submission.student_id,
        "student_name": current_user.full_name,
        "student_email": current_user.email,
        "content": submission.content,
        "file_url": submission.file_url,
        "submission_type": submission.submission_type,
        "file_storage_id": submission.file_storage_id,
        "file_name": submission.file_name,
        "file_size": submission.file_size,
        "mcq_answers": submission.mcq_answers,
        "rubric_evaluation": submission.rubric_evaluation,
        "attempt_number": submission.attempt_number or 1,
        "is_late": submission.is_late or False,
        "submitted_at": submission.submitted_at,
        "status": submission.status,
        "grade_status": submission.grade_status,
        "score": float(submission.score) if submission.score is not None else None,
        "feedback": submission.feedback,
        "graded_at": submission.graded_at,
        "assessment_type": submission.assignment.assessment_type if submission.assignment else "DESCRIPTIVE",
        "assessment_config": submission.assignment.assessment_config if submission.assignment else None,
        "instructions": submission.assignment.instructions if submission.assignment else None
    }


@router.get("/submissions/{submission_id}/file")
async def get_submission_file(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    submission = service.assignment_repo.get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    user_role = current_user.role.name if current_user.role else "STUDENT"
    is_owner = submission.student_id == current_user.id
    is_teacher = submission.assignment and submission.assignment.course and submission.assignment.course.teacher_id == current_user.id
    if user_role != "ADMIN" and not is_owner and not is_teacher:
        raise HTTPException(status_code=403, detail="Access denied")

    if not submission.file_storage_id:
        raise HTTPException(status_code=404, detail="No attached file in this submission")

    file_doc = FileStorageService.get_file(submission.file_storage_id)
    if not file_doc:
        raise HTTPException(status_code=404, detail="File data not found in storage")

    filename = file_doc.get("filename", "submission_file")
    content_type = file_doc.get("content_type", "application/octet-stream")
    return Response(
        content=file_doc["data"],
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'}
    )


@router.get("/submissions/pending", response_model=List[SubmissionResponse])
def get_pending_submissions(
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    teacher_id = current_user.id if current_user.role and current_user.role.name == "TEACHER" else None
    return service.list_pending_submissions(teacher_id=teacher_id)


@router.get("/{assignment_id}/submissions", response_model=List[SubmissionResponse])
def get_assignment_submissions(
    assignment_id: int,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    user_role = current_user.role.name if current_user.role else "TEACHER"
    return service.list_submissions_for_assignment(assignment_id, teacher_id=current_user.id, user_role=user_role)


@router.post("/submissions/{submission_id}/grade", response_model=SubmissionResponse)
async def grade_submission(
    submission_id: int,
    payload: SubmissionGrade,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    user_role = current_user.role.name if current_user.role else "TEACHER"
    publish = True if payload.publish is None else payload.publish
    submission = await service.grade_submission(
        submission_id=submission_id,
        score=payload.score,
        feedback=payload.feedback,
        teacher_id=current_user.id,
        user_role=user_role,
        rubric_evaluation=payload.rubric_evaluation,
        publish=publish
    )
    action_text = "PUBLISHED" if publish else "DRAFT_SAVED"
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action=f"SUBMISSION_{action_text}",
        details=f"Evaluated submission ID {submission_id} with score {payload.score} (publish={publish})"
    )
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": submission.assignment.title if submission.assignment else None,
        "course_code": submission.assignment.course.code if (submission.assignment and submission.assignment.course) else None,
        "course_title": submission.assignment.course.title if (submission.assignment and submission.assignment.course) else None,
        "max_score": float(submission.assignment.max_score) if submission.assignment else None,
        "student_id": submission.student_id,
        "student_name": submission.student.full_name if submission.student else None,
        "student_email": submission.student.email if submission.student else None,
        "content": submission.content,
        "file_url": submission.file_url,
        "submission_type": submission.submission_type or "TEXT",
        "file_storage_id": submission.file_storage_id,
        "file_name": submission.file_name,
        "file_size": submission.file_size,
        "mcq_answers": submission.mcq_answers,
        "rubric_evaluation": submission.rubric_evaluation,
        "attempt_number": submission.attempt_number or 1,
        "is_late": submission.is_late or False,
        "submitted_at": submission.submitted_at,
        "status": submission.status,
        "grade_status": submission.grade_status,
        "score": float(submission.score) if submission.score is not None else None,
        "feedback": submission.feedback,
        "graded_at": submission.graded_at,
        "assessment_type": submission.assignment.assessment_type if submission.assignment else "DESCRIPTIVE",
        "assessment_config": submission.assignment.assessment_config if submission.assignment else None,
        "instructions": submission.assignment.instructions if submission.assignment else None
    }


@router.post("/submissions/{submission_id}/publish", response_model=SubmissionResponse)
async def publish_submission(
    submission_id: int,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = AssignmentService(db)
    user_role = current_user.role.name if current_user.role else "TEACHER"
    submission = await service.publish_grade(
        submission_id=submission_id,
        teacher_id=current_user.id,
        user_role=user_role
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="GRADE_PUBLISHED",
        details=f"Published official grade for submission ID {submission_id}"
    )
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "assignment_title": submission.assignment.title if submission.assignment else None,
        "course_code": submission.assignment.course.code if (submission.assignment and submission.assignment.course) else None,
        "course_title": submission.assignment.course.title if (submission.assignment and submission.assignment.course) else None,
        "max_score": float(submission.assignment.max_score) if submission.assignment else None,
        "student_id": submission.student_id,
        "student_name": submission.student.full_name if submission.student else None,
        "student_email": submission.student.email if submission.student else None,
        "content": submission.content,
        "file_url": submission.file_url,
        "submission_type": submission.submission_type or "TEXT",
        "file_storage_id": submission.file_storage_id,
        "file_name": submission.file_name,
        "file_size": submission.file_size,
        "mcq_answers": submission.mcq_answers,
        "rubric_evaluation": submission.rubric_evaluation,
        "attempt_number": submission.attempt_number or 1,
        "is_late": submission.is_late or False,
        "submitted_at": submission.submitted_at,
        "status": submission.status,
        "grade_status": submission.grade_status,
        "score": float(submission.score) if submission.score is not None else None,
        "feedback": submission.feedback,
        "graded_at": submission.graded_at,
        "assessment_type": submission.assignment.assessment_type if submission.assignment else "DESCRIPTIVE",
        "assessment_config": submission.assignment.assessment_config if submission.assignment else None,
        "instructions": submission.assignment.instructions if submission.assignment else None
    }

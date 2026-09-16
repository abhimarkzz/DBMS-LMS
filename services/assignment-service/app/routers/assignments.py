from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    AuthenticatedUser,
    get_current_user,
    get_db,
    require_student,
    require_teacher_or_admin,
)
from app.repositories.assignment_repository import AssignmentRepository
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    GradeSubmissionRequest,
    PaginatedAssignments,
    SubmissionCreate,
    SubmissionResponse,
)
from app.services.assignment_service import AssignmentService

router = APIRouter()

def get_assignment_service(session: AsyncSession = Depends(get_db)) -> AssignmentService:
    repository = AssignmentRepository(session)
    return AssignmentService(repository)

@router.post("", response_model=AssignmentResponse, status_code=201)
async def create_assignment(
    data: AssignmentCreate,
    user: Annotated[AuthenticatedUser, Depends(require_teacher_or_admin)],
    service: Annotated[AssignmentService, Depends(get_assignment_service)],
):
    """Create a new assignment for a course."""
    teacher_id = UUID(user.user_id)
    return await service.create_assignment(teacher_id, data)

@router.get("/course/{course_id}", response_model=PaginatedAssignments)
async def get_course_assignments(
    course_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[AssignmentService, Depends(get_assignment_service)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List all assignments for a specific course."""
    items, total = await service.get_course_assignments(course_id, page, size)
    return PaginatedAssignments(items=items, total=total, page=page, size=size)

@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    service: Annotated[AssignmentService, Depends(get_assignment_service)],
):
    """Get assignment details."""
    return await service.get_assignment(assignment_id)

@router.patch("/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: UUID,
    data: AssignmentUpdate,
    user: Annotated[AuthenticatedUser, Depends(require_teacher_or_admin)],
    service: Annotated[AssignmentService, Depends(get_assignment_service)],
):
    """Update an assignment (teacher or admin)."""
    return await service.update_assignment(
        assignment_id, UUID(user.user_id), data, is_admin=user.is_admin
    )

# ==========================================
# Submissions
# ==========================================

@router.post("/{assignment_id}/submissions", response_model=SubmissionResponse, status_code=201)
async def submit_assignment(
    assignment_id: UUID,
    data: SubmissionCreate,
    user: Annotated[AuthenticatedUser, Depends(require_student)],
    service: Annotated[AssignmentService, Depends(get_assignment_service)],
):
    """Student submits an assignment."""
    student_id = UUID(user.user_id)
    return await service.submit_assignment(assignment_id, student_id, data)

@router.get("/{assignment_id}/submissions/my", response_model=SubmissionResponse)
async def get_my_submission(
    assignment_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_student)],
    service: Annotated[AssignmentService, Depends(get_assignment_service)],
):
    """Get the current student's latest submission for an assignment."""
    student_id = UUID(user.user_id)
    return await service.get_student_submission(assignment_id, student_id)

@router.get("/{assignment_id}/submissions", response_model=list[SubmissionResponse])
async def list_assignment_submissions(
    assignment_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_teacher_or_admin)],
    service: Annotated[AssignmentService, Depends(get_assignment_service)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """List all submissions for an assignment (teacher or admin only)."""
    items, _ = await service.get_submissions_for_assignment(
        assignment_id, UUID(user.user_id), page, size, is_admin=user.is_admin
    )
    return items

@router.patch("/submissions/{submission_id}/grade", response_model=SubmissionResponse)
async def grade_submission(
    submission_id: UUID,
    data: GradeSubmissionRequest,
    user: Annotated[AuthenticatedUser, Depends(require_teacher_or_admin)],
    service: Annotated[AssignmentService, Depends(get_assignment_service)],
):
    """Grade a submission (teacher or admin only)."""
    return await service.grade_submission(
        submission_id, UUID(user.user_id), data, is_admin=user.is_admin
    )

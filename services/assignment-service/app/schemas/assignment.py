from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.assignment import AssignmentStatus, SubmissionStatus

# ==========================================
# Assignments
# ==========================================

class AssignmentBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    total_marks: Decimal = Field(..., gt=0)
    due_date: datetime
    max_attempts: int = Field(1, ge=1)
    status: AssignmentStatus = AssignmentStatus.DRAFT

class AssignmentCreate(AssignmentBase):
    course_id: UUID

class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    total_marks: Optional[Decimal] = Field(None, gt=0)
    due_date: Optional[datetime] = None
    max_attempts: Optional[int] = Field(None, ge=1)
    status: Optional[AssignmentStatus] = None

class AssignmentResponse(AssignmentBase):
    assignment_id: UUID
    course_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedAssignments(BaseModel):
    items: list[AssignmentResponse]
    total: int
    page: int
    size: int


# ==========================================
# Submissions
# ==========================================

class SubmissionBase(BaseModel):
    submission_text: Optional[str] = None
    file_url: Optional[str] = Field(None, max_length=500)

class SubmissionCreate(SubmissionBase):
    pass

class GradeSubmissionRequest(BaseModel):
    marks_awarded: Decimal = Field(..., ge=0)
    teacher_feedback: Optional[str] = None
    status: SubmissionStatus = SubmissionStatus.GRADED

class SubmissionResponse(SubmissionBase):
    submission_id: UUID
    assignment_id: UUID
    student_id: UUID
    submitted_at: datetime
    status: SubmissionStatus
    attempt_number: int
    marks_awarded: Optional[Decimal] = None
    teacher_feedback: Optional[str] = None
    graded_by: Optional[UUID] = None
    graded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

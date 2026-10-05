from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    course_id: int
    title: str = Field(..., min_length=2, max_length=255)
    description: str
    max_score: float = 100.0
    due_date: Optional[datetime] = None


class AssignmentResponse(BaseModel):
    id: int
    course_id: int
    course_title: Optional[str] = None
    course_code: Optional[str] = None
    title: str
    description: str
    max_score: float
    due_date: Optional[datetime] = None
    created_at: datetime
    has_submitted: Optional[bool] = False
    submission_id: Optional[int] = None
    submission_status: Optional[str] = None
    submission_score: Optional[float] = None

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    content: str = Field(..., min_length=5)
    file_url: Optional[str] = None


class SubmissionGrade(BaseModel):
    score: float = Field(..., ge=0)
    feedback: Optional[str] = None


class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    assignment_title: Optional[str] = None
    max_score: Optional[float] = None
    student_id: int
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    content: str
    file_url: Optional[str] = None
    submitted_at: datetime
    status: str
    score: Optional[float] = None
    feedback: Optional[str] = None
    graded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

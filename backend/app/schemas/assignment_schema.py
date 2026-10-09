from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    course_id: int
    title: str = Field(..., min_length=2, max_length=255)
    description: str
    instructions: Optional[str] = None
    max_score: float = 100.0
    assessment_type: Optional[str] = "DESCRIPTIVE"  # DESCRIPTIVE, MCQ, FILE, AUDIO
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    due_time: Optional[str] = None
    attempt_limit: Optional[int] = 1
    late_allowed: Optional[bool] = True
    status: Optional[str] = "PUBLISHED"  # DRAFT, PUBLISHED, ARCHIVED
    attachment_url: Optional[str] = None
    assessment_config: Optional[str] = None  # JSON string containing rubric or mcq questions or file/audio rules


class AssignmentResponse(BaseModel):
    id: int
    course_id: int
    course_title: Optional[str] = None
    course_code: Optional[str] = None
    title: str
    description: str
    instructions: Optional[str] = None
    max_score: float
    assessment_type: Optional[str] = "DESCRIPTIVE"
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    due_time: Optional[str] = None
    attempt_limit: Optional[int] = 1
    late_allowed: Optional[bool] = True
    status: Optional[str] = "PUBLISHED"
    attachment_url: Optional[str] = None
    assessment_config: Optional[str] = None
    created_at: datetime
    has_submitted: Optional[bool] = False
    submission_id: Optional[int] = None
    submission_status: Optional[str] = None
    submission_score: Optional[float] = None
    submission_grade_status: Optional[str] = None
    submission_is_late: Optional[bool] = None

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    content: Optional[str] = ""
    file_url: Optional[str] = None
    submission_type: Optional[str] = "TEXT"
    file_storage_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = 0
    mcq_answers: Optional[str] = None  # JSON string of answers: {"q1": "B"}


class SubmissionGrade(BaseModel):
    score: float = Field(..., ge=0)
    feedback: Optional[str] = None
    rubric_evaluation: Optional[str] = None  # JSON string of criteria scores & comments
    publish: Optional[bool] = True  # If False, saved as DRAFT; if True, PUBLISHED & calculates course grade


class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    assignment_title: Optional[str] = None
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    max_score: Optional[float] = None
    student_id: int
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    content: str
    file_url: Optional[str] = None
    submission_type: Optional[str] = "TEXT"
    file_storage_id: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = 0
    mcq_answers: Optional[str] = None
    rubric_evaluation: Optional[str] = None
    attempt_number: Optional[int] = 1
    is_late: Optional[bool] = False
    submitted_at: datetime
    status: str
    grade_status: Optional[str] = "PUBLISHED"
    score: Optional[float] = None
    feedback: Optional[str] = None
    graded_at: Optional[datetime] = None
    assessment_type: Optional[str] = "DESCRIPTIVE"
    assessment_config: Optional[str] = None
    instructions: Optional[str] = None

    class Config:
        from_attributes = True

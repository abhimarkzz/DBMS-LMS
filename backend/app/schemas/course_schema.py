from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class StudyMaterialCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=10)
    material_type: str = "NOTES"
    file_url: Optional[str] = None


class StudyMaterialResponse(BaseModel):
    id: int
    course_id: int
    title: str
    content: Optional[str] = ""
    material_type: str = "NOTES"
    original_filename: Optional[str] = None
    file_type: Optional[str] = "NOTES"
    file_size: Optional[int] = 0
    file_storage_id: Optional[str] = None
    file_url: Optional[str] = None
    uploaded_by: Optional[int] = None
    uploader_name: Optional[str] = None
    status: str = "INDEXED"
    chunk_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=5)


class AnnouncementResponse(BaseModel):
    id: int
    course_id: int
    author_id: int
    author_name: Optional[str] = None
    title: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class QuizCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    duration_minutes: int = 30
    total_points: int = 100


class QuizResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    duration_minutes: int
    total_points: int
    created_at: datetime

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=3, max_length=255)
    short_description: Optional[str] = None
    description: Optional[str] = None
    department: str = "Computer Science & Engineering"
    level: str = "Graduate"
    academic_session: str = "Spring 2026"
    semester: str = "Term 2"
    credits: int = 4
    prerequisites: Optional[str] = None
    learning_outcomes: Optional[str] = None
    syllabus: Optional[str] = None
    modules_outline: Optional[str] = None
    start_date: str = "2026-01-15"
    end_date: str = "2026-05-30"
    capacity: int = 50
    status: str = "PUBLISHED"
    is_published: bool = True
    teacher_id: Optional[int] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    level: Optional[str] = None
    academic_session: Optional[str] = None
    semester: Optional[str] = None
    credits: Optional[int] = None
    prerequisites: Optional[str] = None
    learning_outcomes: Optional[str] = None
    syllabus: Optional[str] = None
    modules_outline: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    is_published: Optional[bool] = None
    teacher_id: Optional[int] = None


class CourseResponse(BaseModel):
    id: int
    code: str
    title: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = "Computer Science & Engineering"
    level: Optional[str] = "Graduate"
    academic_session: Optional[str] = "Spring 2026"
    semester: Optional[str] = "Term 2"
    credits: Optional[int] = 4
    prerequisites: Optional[str] = None
    learning_outcomes: Optional[str] = None
    syllabus: Optional[str] = None
    modules_outline: Optional[str] = None
    start_date: Optional[str] = "2026-01-15"
    end_date: Optional[str] = "2026-05-30"
    capacity: Optional[int] = 50
    status: Optional[str] = "PUBLISHED"
    teacher_id: int
    teacher_name: Optional[str] = None
    is_published: bool
    created_at: datetime
    enrolled_count: Optional[int] = 0
    is_enrolled: Optional[bool] = False

    class Config:
        from_attributes = True


class CourseDetailResponse(CourseResponse):
    materials: List[StudyMaterialResponse] = []
    announcements: List[AnnouncementResponse] = []
    quizzes: List[QuizResponse] = []
    assignments: List[dict] = []
    enrolled_students: List[dict] = []


class EnrollmentResponse(BaseModel):
    id: int
    student_id: int
    course_id: int
    enrolled_at: datetime
    status: str
    course_title: Optional[str] = None
    course_code: Optional[str] = None

    class Config:
        from_attributes = True

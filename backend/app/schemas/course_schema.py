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
    content: str
    material_type: str
    file_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CourseCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    syllabus: Optional[str] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    syllabus: Optional[str] = None
    is_published: Optional[bool] = None


class CourseResponse(BaseModel):
    id: int
    code: str
    title: str
    description: Optional[str] = None
    syllabus: Optional[str] = None
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

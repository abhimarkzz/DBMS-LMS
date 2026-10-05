from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ResultResponse(BaseModel):
    id: int
    student_id: int
    student_name: Optional[str] = None
    course_id: int
    course_code: Optional[str] = None
    course_title: Optional[str] = None
    total_score: float
    max_possible: float
    percentage: float
    grade: str
    status: str
    published_at: datetime

    class Config:
        from_attributes = True


class StudentProgressViewResponse(BaseModel):
    student_id: int
    student_name: str
    student_email: str
    course_id: int
    course_code: str
    course_title: str
    total_assignments: int
    submitted_assignments: int
    total_obtained_score: float
    total_possible_score: float
    completion_rate: float
    published_grade: Optional[str] = None
    overall_percentage: Optional[float] = None


class CourseResultSummaryResponse(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    instructor_name: str
    enrolled_students: int
    total_assignments: int
    total_submissions_graded: int
    average_assignment_score: float
    max_assignment_score: float
    min_assignment_score: float
    course_average_percentage: float


class LeaderboardItem(BaseModel):
    rank: int
    student_id: int
    student_name: str
    course_id: int
    course_title: str
    total_score: float
    percentage: float
    grade: str

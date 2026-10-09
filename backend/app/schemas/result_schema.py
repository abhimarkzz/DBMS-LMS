from datetime import datetime
from typing import Optional, List, Dict, Any
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
    published_at: Optional[datetime] = None

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


# ========================================================
# Phase 5: Comprehensive Gradebook & Detailed Academic Views
# ========================================================

class StudentAssignmentScore(BaseModel):
    assignment_id: int
    title: str
    assessment_type: str
    max_score: float
    score: Optional[float] = None
    percentage: Optional[float] = None
    grade: Optional[str] = None
    feedback: Optional[str] = None
    submission_status: str  # GRADED, SUBMITTED, NOT_SUBMITTED, PENDING
    grade_status: Optional[str] = None  # PUBLISHED, DRAFT
    submitted_at: Optional[datetime] = None
    is_late: bool = False


class StudentCourseBreakdown(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    instructor_name: str
    total_assignments: int
    completed_assignments: int
    pending_assignments: int
    completion_percentage: float
    total_obtained_score: float
    total_possible_score: float
    course_percentage: Optional[float] = None
    course_grade: Optional[str] = None
    status: str  # PUBLISHED, UNPUBLISHED, IN_PROGRESS
    published_at: Optional[datetime] = None
    class_rank: Optional[int] = None
    total_enrolled: int
    assignments: List[StudentAssignmentScore] = []


class StudentAcademicOverview(BaseModel):
    student_id: int
    student_name: str
    student_email: str
    overall_percentage: float
    overall_grade: str
    total_courses: int
    total_assignments: int
    total_completed: int
    total_pending: int
    overall_completion_percentage: float
    courses: List[StudentCourseBreakdown]


class GradebookAssignmentInfo(BaseModel):
    id: int
    title: str
    assessment_type: str
    max_score: float
    due_date: Optional[datetime] = None


class GradebookCell(BaseModel):
    assignment_id: int
    submission_id: Optional[int] = None
    score: Optional[float] = None
    max_score: float
    percentage: Optional[float] = None
    letter_grade: Optional[str] = None
    status: str  # GRADED, SUBMITTED, NOT_SUBMITTED
    grade_status: Optional[str] = None  # PUBLISHED, DRAFT
    is_late: bool = False
    feedback: Optional[str] = None


class GradebookStudentRow(BaseModel):
    student_id: int
    student_name: str
    student_email: str
    grades: Dict[int, GradebookCell]  # assignment_id -> GradebookCell
    total_score: float
    max_possible: float
    percentage: float
    grade: str
    status: str
    rank: Optional[int] = None


class CourseGradebookStats(BaseModel):
    class_average: float
    highest_percentage: float
    lowest_percentage: float
    pending_grading: int
    completed_grading: int
    total_enrolled: int


class CourseGradebookResponse(BaseModel):
    course_id: int
    course_code: str
    course_title: str
    instructor_name: str
    assignments: List[GradebookAssignmentInfo]
    students: List[GradebookStudentRow]
    stats: CourseGradebookStats
    leaderboard: List[LeaderboardItem]


class AdminAcademicStats(BaseModel):
    total_students: int
    total_teachers: int
    total_courses: int
    total_results_published: int
    platform_average_percentage: float
    total_assignments: int
    total_submissions: int
    pending_grading_count: int
    completed_grading_count: int
    grade_distribution: Dict[str, int]
    course_summaries: List[CourseResultSummaryResponse]

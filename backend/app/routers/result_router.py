from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.result_schema import (
    ResultResponse, StudentProgressViewResponse, 
    CourseResultSummaryResponse, LeaderboardItem
)
from app.services.result_service import ResultService
from app.services.auth_service import get_current_user, require_roles
from app.models.sql_models import User

router = APIRouter(prefix="/api/results", tags=["Results & Academic Views"])


@router.get("/my", response_model=List[ResultResponse])
def get_my_results(
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: Session = Depends(get_db)
):
    service = ResultService(db)
    return service.get_student_results(current_user.id)


@router.get("/progress-view", response_model=List[StudentProgressViewResponse])
def get_student_progress_view(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Demonstrates SQL View: student_progress_view
    Aggregates student assignments, submissions, completion rates, and published grades.
    """
    service = ResultService(db)
    return service.get_student_progress_view(current_user.id)


@router.get("/course-summary-view", response_model=List[CourseResultSummaryResponse])
def get_course_summary_view(
    course_id: Optional[int] = None,
    _: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Demonstrates SQL View: course_result_summary_view
    Provides instructor-level course analytics, enrollment counts, average, min, and max scores.
    """
    service = ResultService(db)
    return service.get_course_summary_view(course_id=course_id)


@router.get("/course/{course_id}/leaderboard", response_model=List[LeaderboardItem])
def get_course_leaderboard(
    course_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Demonstrates SQL Window Function:
    RANK() OVER (PARTITION BY course_id ORDER BY percentage DESC)
    """
    service = ResultService(db)
    return service.get_course_leaderboard(course_id)


@router.get("/course/{course_id}/above-average")
def get_above_average_students(
    course_id: int,
    _: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Demonstrates SQL Subquery:
    Finds all students with percentage greater than (SELECT AVG(percentage) FROM results WHERE course_id = :id)
    """
    service = ResultService(db)
    return service.get_above_average_students(course_id)


@router.post("/calculate")
def execute_grade_calculation_procedure(
    student_id: int,
    course_id: int,
    _: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Demonstrates PostgreSQL Stored Function / Procedure:
    SELECT calculate_course_grade(:student_id, :course_id)
    """
    service = ResultService(db)
    grade = service.recalculate_course_grade(student_id, course_id)
    return {
        "status": "SUCCESS",
        "student_id": student_id,
        "course_id": course_id,
        "computed_grade": grade,
        "procedure_used": "calculate_course_grade(p_student_id, p_course_id)"
    }

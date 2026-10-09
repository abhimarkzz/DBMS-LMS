from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.result_schema import (
    ResultResponse, StudentProgressViewResponse, 
    CourseResultSummaryResponse, LeaderboardItem,
    StudentAcademicOverview, StudentCourseBreakdown,
    CourseGradebookResponse, AdminAcademicStats
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
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Demonstrates SQL View: course_result_summary_view
    Provides instructor-level course analytics, enrollment counts, average, min, and max scores.
    """
    service = ResultService(db)
    if course_id and current_user.role.name != "ADMIN":
        course = service.course_repo.get_course_by_id(course_id)
        if course and course.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied: You can only view summary for courses you instruct")
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
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Demonstrates SQL Subquery:
    Finds all students with percentage greater than (SELECT AVG(percentage) FROM results WHERE course_id = :id)
    """
    service = ResultService(db)
    course = service.course_repo.get_course_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role.name != "ADMIN" and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: You can only view analytics for courses you instruct")
    return service.get_above_average_students(course_id)


@router.post("/calculate")
def execute_grade_calculation_procedure(
    student_id: int,
    course_id: int,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Demonstrates PostgreSQL Stored Function / Procedure:
    SELECT calculate_course_grade(:student_id, :course_id)
    """
    service = ResultService(db)
    course = service.course_repo.get_course_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role.name != "ADMIN" and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: You can only calculate grades for courses you instruct")
    grade = service.recalculate_course_grade(student_id, course_id)
    return {
        "status": "SUCCESS",
        "student_id": student_id,
        "course_id": course_id,
        "computed_grade": grade,
        "procedure_used": "calculate_course_grade(p_student_id, p_course_id)"
    }


# ========================================================
# Phase 5 Real Gradebook & Academic Report Endpoints
# ========================================================

@router.get("/my/overview", response_model=StudentAcademicOverview)
def get_student_academic_overview(
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: Session = Depends(get_db)
):
    """
    Student Result Page Overview:
    - Overall percentage & GPA letter grade
    - Total courses, completed assignments, pending assignments, overall completion rate
    - Course-wise breakdowns with individual assignment marks & class ranks
    """
    service = ResultService(db)
    overview = service.get_student_academic_overview(current_user.id)
    if not overview:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return overview


@router.get("/my/course/{course_id}/breakdown", response_model=StudentCourseBreakdown)
def get_student_course_breakdown(
    course_id: int,
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: Session = Depends(get_db)
):
    """
    Course Result Detail for Student:
    - Assignment title, score, max marks, percentage, grade, feedback, status
    - Class rank using SQL window function RANK() OVER
    """
    service = ResultService(db)
    breakdown = service.get_student_course_breakdown(current_user.id, course_id)
    if not breakdown:
        raise HTTPException(status_code=404, detail="Course breakdown not found")
    return breakdown


@router.get("/course/{course_id}/gradebook", response_model=CourseGradebookResponse)
def get_course_gradebook(
    course_id: int,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Teacher Gradebook Matrix:
    - Table of Student rows x Assignment/Quiz columns
    - Total points, percentage, letter grade, status
    - Course stats: class average, highest, lowest, pending grading, completed grading, leaderboard
    """
    service = ResultService(db)
    course = service.course_repo.get_course_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if current_user.role.name != "ADMIN" and course.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied: You can only view the gradebook for courses you instruct")
    gradebook = service.get_course_gradebook(course_id)
    if not gradebook:
        raise HTTPException(status_code=404, detail="Gradebook data not found")
    return gradebook


@router.get("/admin/academic-stats", response_model=AdminAcademicStats)
def get_admin_academic_stats(
    _: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Admin Platform-wide Academic Analytics:
    - Overall platform average, grade distribution (A+, A, B, C, D, F)
    - Submissions pending vs completed
    - Course-by-course performance comparison
    """
    service = ResultService(db)
    return service.get_admin_academic_stats()


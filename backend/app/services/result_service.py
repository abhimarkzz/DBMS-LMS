from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.repositories.result_repo import ResultRepository
from app.repositories.course_repo import CourseRepository


class ResultService:
    def __init__(self, db: Session):
        self.db = db
        self.result_repo = ResultRepository(db)
        self.course_repo = CourseRepository(db)

    def get_student_results(self, student_id: int) -> List[Dict[str, Any]]:
        return self.result_repo.get_student_results(student_id)

    def get_course_results(self, course_id: int) -> List[Dict[str, Any]]:
        return self.result_repo.get_course_results(course_id)

    def get_student_progress_view(self, student_id: int) -> List[Dict[str, Any]]:
        """Queries relational view: student_progress_view."""
        return self.result_repo.get_student_progress_from_view(student_id)

    def get_course_summary_view(self, course_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Queries relational view: course_result_summary_view."""
        return self.result_repo.get_course_summary_from_view(course_id)

    def get_course_leaderboard(self, course_id: int) -> List[Dict[str, Any]]:
        """Queries SQL window function: RANK() OVER (PARTITION BY course_id ORDER BY percentage DESC)."""
        return self.result_repo.get_course_leaderboard_window_function(course_id)

    def get_above_average_students(self, course_id: int) -> List[Dict[str, Any]]:
        """Queries SQL subquery: students above class average."""
        return self.result_repo.get_above_average_students_subquery(course_id)

    def recalculate_course_grade(self, student_id: int, course_id: int) -> str:
        """Executes PostgreSQL Stored Function: calculate_course_grade."""
        return self.result_repo.execute_stored_procedure_calculate_grade(student_id, course_id)

    def get_student_course_breakdown(self, student_id: int, course_id: int) -> Dict[str, Any]:
        """Detailed course breakdown with individual assignment scores, feedback, and class rank."""
        return self.result_repo.get_student_course_breakdown(student_id, course_id)

    def get_student_academic_overview(self, student_id: int) -> Dict[str, Any]:
        """Overall student academic standing, course-by-course results, completed/pending tasks."""
        return self.result_repo.get_student_academic_overview(student_id)

    def get_course_gradebook(self, course_id: int) -> Dict[str, Any]:
        """Teacher gradebook matrix with student rows, assignment columns, class stats, and leaderboard."""
        return self.result_repo.get_course_gradebook(course_id)

    def get_admin_academic_stats(self) -> Dict[str, Any]:
        """Admin platform-wide academic statistics from database views and tables."""
        return self.result_repo.get_admin_academic_stats()


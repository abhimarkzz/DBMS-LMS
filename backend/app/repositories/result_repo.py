from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from app.models.sql_models import Result, Course, User


class ResultRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_student_results(self, student_id: int) -> List[Dict[str, Any]]:
        results = self.db.query(Result).options(
            joinedload(Result.course),
            joinedload(Result.student)
        ).filter(Result.student_id == student_id).all()

        output = []
        for r in results:
            output.append({
                "id": r.id,
                "student_id": r.student_id,
                "student_name": r.student.full_name if r.student else None,
                "course_id": r.course_id,
                "course_code": r.course.code if r.course else None,
                "course_title": r.course.title if r.course else None,
                "total_score": float(r.total_score),
                "max_possible": float(r.max_possible),
                "percentage": float(r.percentage),
                "grade": r.grade,
                "status": r.status,
                "published_at": r.published_at
            })
        return output

    def get_course_results(self, course_id: int) -> List[Dict[str, Any]]:
        results = self.db.query(Result).options(
            joinedload(Result.course),
            joinedload(Result.student)
        ).filter(Result.course_id == course_id).order_by(Result.percentage.desc()).all()

        output = []
        for r in results:
            output.append({
                "id": r.id,
                "student_id": r.student_id,
                "student_name": r.student.full_name if r.student else None,
                "course_id": r.course_id,
                "course_code": r.course.code if r.course else None,
                "course_title": r.course.title if r.course else None,
                "total_score": float(r.total_score),
                "max_possible": float(r.max_possible),
                "percentage": float(r.percentage),
                "grade": r.grade,
                "status": r.status,
                "published_at": r.published_at
            })
        return output

    def get_student_progress_from_view(self, student_id: int) -> List[Dict[str, Any]]:
        """Query relational view: student_progress_view."""
        sql = text("""
            SELECT 
                student_id, student_name, student_email,
                course_id, course_code, course_title,
                total_assignments, submitted_assignments,
                total_obtained_score, total_possible_score,
                completion_rate, published_grade, overall_percentage
            FROM student_progress_view
            WHERE student_id = :student_id
            ORDER BY course_code;
        """)
        rows = self.db.execute(sql, {"student_id": student_id}).mappings().all()
        return [dict(r) for r in rows]

    def get_course_summary_from_view(self, course_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query relational view: course_result_summary_view."""
        if course_id:
            sql = text("""
                SELECT 
                    course_id, course_code, course_title, instructor_name,
                    enrolled_students, total_assignments, total_submissions_graded,
                    average_assignment_score, max_assignment_score, min_assignment_score,
                    course_average_percentage
                FROM course_result_summary_view
                WHERE course_id = :course_id;
            """)
            rows = self.db.execute(sql, {"course_id": course_id}).mappings().all()
        else:
            sql = text("""
                SELECT 
                    course_id, course_code, course_title, instructor_name,
                    enrolled_students, total_assignments, total_submissions_graded,
                    average_assignment_score, max_assignment_score, min_assignment_score,
                    course_average_percentage
                FROM course_result_summary_view
                ORDER BY course_code;
            """)
            rows = self.db.execute(sql).mappings().all()
        return [dict(r) for r in rows]

    def get_course_leaderboard_window_function(self, course_id: int) -> List[Dict[str, Any]]:
        """Demonstrate SQL Window Function: RANK() OVER (PARTITION BY course_id ORDER BY percentage DESC)."""
        sql = text("""
            SELECT 
                RANK() OVER (PARTITION BY r.course_id ORDER BY r.percentage DESC) AS rank,
                u.id AS student_id,
                u.full_name AS student_name,
                c.id AS course_id,
                c.title AS course_title,
                r.total_score,
                r.percentage,
                r.grade
            FROM results r
            JOIN users u ON r.student_id = u.id
            JOIN courses c ON r.course_id = c.id
            WHERE r.course_id = :course_id
            ORDER BY rank ASC;
        """)
        rows = self.db.execute(sql, {"course_id": course_id}).mappings().all()
        return [dict(r) for r in rows]

    def get_above_average_students_subquery(self, course_id: int) -> List[Dict[str, Any]]:
        """Demonstrate SQL Subquery: Find students with score strictly above the course average."""
        sql = text("""
            SELECT 
                u.id AS student_id,
                u.full_name AS student_name,
                r.percentage,
                r.grade
            FROM results r
            JOIN users u ON r.student_id = u.id
            WHERE r.course_id = :course_id
              AND r.percentage > (
                  SELECT AVG(percentage) 
                  FROM results 
                  WHERE course_id = :course_id
              )
            ORDER BY r.percentage DESC;
        """)
        rows = self.db.execute(sql, {"course_id": course_id}).mappings().all()
        return [dict(r) for r in rows]

    def execute_stored_procedure_calculate_grade(self, student_id: int, course_id: int) -> str:
        """Call PostgreSQL Stored Function: calculate_course_grade(student_id, course_id)."""
        sql = text("SELECT calculate_course_grade(:s_id, :c_id) AS computed_grade;")
        result = self.db.execute(sql, {"s_id": student_id, "c_id": course_id}).scalar()
        self.db.commit()
        return result or "N/A"

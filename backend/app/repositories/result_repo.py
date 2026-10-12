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

    def get_student_course_breakdown(self, student_id: int, course_id: int) -> Dict[str, Any]:
        """
        Retrieves detailed course breakdown for a student including:
        - Course info
        - All assignments with max score, score, percentage, grade, feedback, status
        - Class rank using SQL Window Function RANK() OVER
        - Progress metrics (completed vs pending)
        """
        # 1. Course Details & Instructor
        course = self.db.query(Course).options(joinedload(Course.teacher)).filter(Course.id == course_id).first()
        if not course:
            return None

        # 2. Total enrolled students
        total_enrolled = self.db.execute(
            text("SELECT COUNT(*) FROM enrollments WHERE course_id = :c_id"),
            {"c_id": course_id}
        ).scalar() or 0

        # 3. Class Rank via Window Function
        rank_sql = text("""
            WITH ranked_results AS (
                SELECT 
                    r.student_id,
                    RANK() OVER (PARTITION BY r.course_id ORDER BY r.percentage DESC) AS rank
                FROM results r
                WHERE r.course_id = :c_id AND r.status = 'PUBLISHED'
            )
            SELECT rank FROM ranked_results WHERE student_id = :s_id;
        """)
        student_rank = self.db.execute(rank_sql, {"c_id": course_id, "s_id": student_id}).scalar()

        # 4. Official Result Record
        result_record = self.db.query(Result).filter(
            Result.student_id == student_id,
            Result.course_id == course_id
        ).first()

        # 5. Assignments and Submissions for this student
        assignments_sql = text("""
            SELECT 
                a.id AS assignment_id,
                a.title,
                a.assessment_type,
                a.max_score,
                a.due_date,
                s.id AS submission_id,
                s.score,
                s.status AS submission_status,
                s.grade_status,
                s.feedback,
                s.submitted_at,
                s.is_late
            FROM assignments a
            LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = :s_id
            WHERE a.course_id = :c_id
            ORDER BY a.created_at ASC, a.id ASC;
        """)
        asg_rows = self.db.execute(assignments_sql, {"c_id": course_id, "s_id": student_id}).mappings().all()

        assignment_scores = []
        completed_count = 0
        total_obtained = 0.0
        total_possible = 0.0

        for row in asg_rows:
            max_sc = float(row["max_score"] or 100.0)
            total_possible += max_sc
            raw_score = float(row["score"]) if row["score"] is not None else None
            is_graded = row["submission_status"] == "GRADED" and (row["grade_status"] is None or row["grade_status"] == "PUBLISHED")
            is_draft = row["grade_status"] == "DRAFT"

            # Compute percentage and letter grade per assignment if published
            if raw_score is not None and is_graded:
                completed_count += 1
                total_obtained += raw_score
                pct = round((raw_score / max_sc) * 100, 2) if max_sc > 0 else 0.0
                if pct >= 90: let_grade = "A+"
                elif pct >= 80: let_grade = "A"
                elif pct >= 70: let_grade = "B"
                elif pct >= 60: let_grade = "C"
                elif pct >= 50: let_grade = "D"
                else: let_grade = "F"
                sub_status = "GRADED"
                display_score = raw_score
                display_feedback = row["feedback"]
            elif is_draft:
                # Draft grade is withheld from student view
                sub_status = "PENDING_GRADING"
                display_score = None
                pct = None
                let_grade = None
                display_feedback = None
            elif row["submission_status"] == "SUBMITTED":
                sub_status = "SUBMITTED"
                display_score = None
                pct = None
                let_grade = None
                display_feedback = None
            else:
                sub_status = "NOT_SUBMITTED"
                display_score = None
                pct = None
                let_grade = None
                display_feedback = None

            assignment_scores.append({
                "assignment_id": row["assignment_id"],
                "title": row["title"],
                "assessment_type": row["assessment_type"] or "Descriptive",
                "max_score": max_sc,
                "score": display_score,
                "percentage": pct,
                "grade": let_grade,
                "feedback": display_feedback,
                "submission_status": sub_status,
                "grade_status": row["grade_status"] if is_graded else None,
                "submitted_at": row["submitted_at"],
                "is_late": bool(row["is_late"])
            })

        total_asgs = len(asg_rows)
        pending_count = total_asgs - completed_count
        completion_pct = round((completed_count / total_asgs) * 100, 2) if total_asgs > 0 else 0.0

        is_published = result_record and result_record.status == "PUBLISHED"
        c_pct = float(result_record.percentage) if is_published else None
        c_grade = result_record.grade if is_published else None
        pub_date = result_record.published_at if is_published else None

        return {
            "course_id": course.id,
            "course_code": course.code,
            "course_title": course.title,
            "instructor_name": course.teacher.full_name if course.teacher else "Instructor",
            "total_assignments": total_asgs,
            "completed_assignments": completed_count,
            "pending_assignments": pending_count,
            "completion_percentage": completion_pct,
            "total_obtained_score": round(total_obtained, 2),
            "total_possible_score": round(total_possible, 2),
            "course_percentage": c_pct,
            "course_grade": c_grade,
            "status": "PUBLISHED" if is_published else "IN_PROGRESS",
            "published_at": pub_date,
            "class_rank": student_rank,
            "total_enrolled": total_enrolled,
            "assignments": assignment_scores
        }

    def get_student_academic_overview(self, student_id: int) -> Dict[str, Any]:
        """
        Combines student_progress_view data and individual course breakdowns
        into a unified, database-driven academic report.
        """
        user = self.db.query(User).filter(User.id == student_id).first()
        if not user:
            return None

        # Fetch enrolled course IDs
        enrollment_sql = text("""
            SELECT e.course_id 
            FROM enrollments e 
            JOIN courses c ON e.course_id = c.id
            WHERE e.student_id = :s_id 
            ORDER BY c.code ASC;
        """)
        course_ids = [r[0] for r in self.db.execute(enrollment_sql, {"s_id": student_id}).fetchall()]

        breakdowns = []
        total_assignments = 0
        total_completed = 0
        published_percentages = []

        for cid in course_ids:
            bd = self.get_student_course_breakdown(student_id, cid)
            if bd:
                breakdowns.append(bd)
                total_assignments += bd["total_assignments"]
                total_completed += bd["completed_assignments"]
                if bd["course_percentage"] is not None:
                    published_percentages.append(bd["course_percentage"])

        overall_pct = round(sum(published_percentages) / len(published_percentages), 2) if published_percentages else 0.0

        if overall_pct >= 90: overall_grade = "A+"
        elif overall_pct >= 80: overall_grade = "A"
        elif overall_pct >= 70: overall_grade = "B"
        elif overall_pct >= 60: overall_grade = "C"
        elif overall_pct >= 50: overall_grade = "D"
        elif len(published_percentages) == 0: overall_grade = "In Progress"
        else: overall_grade = "F"

        total_pending = total_assignments - total_completed
        overall_comp_pct = round((total_completed / total_assignments) * 100, 2) if total_assignments > 0 else 0.0

        return {
            "student_id": user.id,
            "student_name": user.full_name,
            "student_email": user.email,
            "overall_percentage": overall_pct,
            "overall_grade": overall_grade,
            "total_courses": len(course_ids),
            "total_assignments": total_assignments,
            "total_completed": total_completed,
            "total_pending": total_pending,
            "overall_completion_percentage": overall_comp_pct,
            "courses": breakdowns
        }

    def get_course_gradebook(self, course_id: int) -> Dict[str, Any]:
        """
        Generates full teacher gradebook matrix:
        Columns: Student Name | Assignment 1 | Assignment 2 | ... | Total | Percentage | Grade | Status
        Course Analytics: Class Average, Highest, Lowest, Pending/Completed Grading, Leaderboard.
        """
        course = self.db.query(Course).options(joinedload(Course.teacher)).filter(Course.id == course_id).first()
        if not course:
            return None

        # 1. Course Assignments
        assignments_sql = text("""
            SELECT id, title, assessment_type, max_score, due_date
            FROM assignments
            WHERE course_id = :c_id
            ORDER BY created_at ASC, id ASC;
        """)
        assignments = [dict(r) for r in self.db.execute(assignments_sql, {"c_id": course_id}).mappings().all()]
        for a in assignments:
            a["max_score"] = float(a["max_score"] or 100.0)

        # 2. Enrolled Students
        students_sql = text("""
            SELECT u.id AS student_id, u.full_name AS student_name, u.email AS student_email
            FROM enrollments e
            JOIN users u ON e.student_id = u.id
            WHERE e.course_id = :c_id
            ORDER BY u.full_name ASC;
        """)
        students = [dict(r) for r in self.db.execute(students_sql, {"c_id": course_id}).mappings().all()]

        # 3. All Submissions for this course
        subs_sql = text("""
            SELECT 
                s.id AS submission_id,
                s.assignment_id,
                s.student_id,
                s.score,
                s.status,
                s.grade_status,
                s.is_late,
                s.feedback
            FROM submissions s
            JOIN assignments a ON s.assignment_id = a.id
            WHERE a.course_id = :c_id;
        """)
        subs = self.db.execute(subs_sql, {"c_id": course_id}).mappings().all()
        # Map: (student_id, assignment_id) -> submission dict
        subs_map = {(s["student_id"], s["assignment_id"]): dict(s) for s in subs}

        # 4. Results with Window Function Rank
        results_sql = text("""
            SELECT 
                r.student_id,
                r.total_score,
                r.max_possible,
                r.percentage,
                r.grade,
                r.status,
                RANK() OVER (PARTITION BY r.course_id ORDER BY r.percentage DESC) AS rank
            FROM results r
            WHERE r.course_id = :c_id;
        """)
        res_rows = self.db.execute(results_sql, {"c_id": course_id}).mappings().all()
        results_map = {r["student_id"]: dict(r) for r in res_rows}

        # 5. Build Student Rows Matrix
        student_rows = []
        for s in students:
            s_id = s["student_id"]
            grades_dict = {}
            for a in assignments:
                a_id = a["id"]
                sub = subs_map.get((s_id, a_id))
                if sub:
                    sc = float(sub["score"]) if sub["score"] is not None else None
                    max_sc = a["max_score"]
                    pct = round((sc / max_sc) * 100, 2) if (sc is not None and max_sc > 0) else None
                    if pct is not None:
                        if pct >= 90: lg = "A+"
                        elif pct >= 80: lg = "A"
                        elif pct >= 70: lg = "B"
                        elif pct >= 60: lg = "C"
                        elif pct >= 50: lg = "D"
                        else: lg = "F"
                    else:
                        lg = None

                    grades_dict[a_id] = {
                        "assignment_id": a_id,
                        "submission_id": sub["submission_id"],
                        "score": sc,
                        "max_score": max_sc,
                        "percentage": pct,
                        "letter_grade": lg,
                        "status": sub["status"],
                        "grade_status": sub["grade_status"] or "PUBLISHED",
                        "is_late": bool(sub["is_late"]),
                        "feedback": sub["feedback"]
                    }
                else:
                    grades_dict[a_id] = {
                        "assignment_id": a_id,
                        "submission_id": None,
                        "score": None,
                        "max_score": a["max_score"],
                        "percentage": None,
                        "letter_grade": None,
                        "status": "NOT_SUBMITTED",
                        "grade_status": None,
                        "is_late": False,
                        "feedback": None
                    }

            res = results_map.get(s_id)
            if res:
                s_tot = float(res["total_score"])
                s_max = float(res["max_possible"])
                s_pct = float(res["percentage"])
                s_grd = res["grade"]
                s_stat = res["status"]
                s_rnk = res["rank"]
            else:
                s_tot = 0.0
                s_max = sum(a["max_score"] for a in assignments)
                s_pct = 0.0
                s_grd = "N/A"
                s_stat = "UNPUBLISHED"
                s_rnk = None

            student_rows.append({
                "student_id": s_id,
                "student_name": s["student_name"],
                "student_email": s["student_email"],
                "grades": grades_dict,
                "total_score": s_tot,
                "max_possible": s_max,
                "percentage": s_pct,
                "grade": s_grd,
                "status": s_stat,
                "rank": s_rnk
            })

        # 6. Aggregated Course Stats from course_result_summary_view & Submissions
        summary_rows = self.get_course_summary_from_view(course_id)
        if summary_rows:
            class_avg = float(summary_rows[0].get("course_average_percentage") or 0.0)
        else:
            class_avg = 0.0

        # Highest and lowest percentages among published results
        published_percentages = [r["percentage"] for r in student_rows if r["status"] == "PUBLISHED"]
        highest_pct = max(published_percentages) if published_percentages else 0.0
        lowest_pct = min(published_percentages) if published_percentages else 0.0

        # Pending grading (submitted or draft) vs Completed grading (graded & published)
        pending_grading_count = self.db.execute(text("""
            SELECT COUNT(*) FROM submissions s 
            JOIN assignments a ON s.assignment_id = a.id 
            WHERE a.course_id = :c_id AND (s.status = 'SUBMITTED' OR s.grade_status = 'DRAFT');
        """), {"c_id": course_id}).scalar() or 0

        completed_grading_count = self.db.execute(text("""
            SELECT COUNT(*) FROM submissions s 
            JOIN assignments a ON s.assignment_id = a.id 
            WHERE a.course_id = :c_id AND s.status = 'GRADED' AND (s.grade_status IS NULL OR s.grade_status = 'PUBLISHED');
        """), {"c_id": course_id}).scalar() or 0

        stats = {
            "class_average": class_avg,
            "highest_percentage": highest_pct,
            "lowest_percentage": lowest_pct,
            "pending_grading": pending_grading_count,
            "completed_grading": completed_grading_count,
            "total_enrolled": len(students)
        }

        # 7. Leaderboard
        leaderboard = self.get_course_leaderboard_window_function(course_id)

        return {
            "course_id": course.id,
            "course_code": course.code,
            "course_title": course.title,
            "instructor_name": course.teacher.full_name if course.teacher else "Instructor",
            "assignments": assignments,
            "students": student_rows,
            "stats": stats,
            "leaderboard": leaderboard
        }

    def get_admin_academic_stats(self) -> Dict[str, Any]:
        """
        Aggregate platform-wide academic statistics from database views and tables.
        """
        total_students = self.db.execute(text("""
            SELECT COUNT(*) FROM users u 
            JOIN roles r ON u.role_id = r.id 
            WHERE r.name = 'STUDENT'
        """)).scalar() or 0

        total_teachers = self.db.execute(text("""
            SELECT COUNT(*) FROM users u 
            JOIN roles r ON u.role_id = r.id 
            WHERE r.name = 'TEACHER'
        """)).scalar() or 0

        total_courses = self.db.execute(text("SELECT COUNT(*) FROM courses")).scalar() or 0

        total_results_published = self.db.execute(text("""
            SELECT COUNT(*) FROM results WHERE status = 'PUBLISHED'
        """)).scalar() or 0

        platform_avg_pct = self.db.execute(text("""
            SELECT COALESCE(ROUND(AVG(percentage)::numeric, 2), 0) 
            FROM results 
            WHERE status = 'PUBLISHED'
        """)).scalar() or 0.0

        total_assignments = self.db.execute(text("SELECT COUNT(*) FROM assignments")).scalar() or 0
        total_submissions = self.db.execute(text("SELECT COUNT(*) FROM submissions")).scalar() or 0

        pending_grading_count = self.db.execute(text("""
            SELECT COUNT(*) FROM submissions WHERE status = 'SUBMITTED' OR grade_status = 'DRAFT'
        """)).scalar() or 0

        completed_grading_count = self.db.execute(text("""
            SELECT COUNT(*) FROM submissions WHERE status = 'GRADED' AND (grade_status IS NULL OR grade_status = 'PUBLISHED')
        """)).scalar() or 0

        # Grade distribution breakdown
        dist_rows = self.db.execute(text("""
            SELECT grade, COUNT(*) AS count 
            FROM results 
            WHERE status = 'PUBLISHED' 
            GROUP BY grade 
            ORDER BY grade;
        """)).mappings().all()

        grade_distribution = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for dr in dist_rows:
            g = dr["grade"]
            if g in grade_distribution:
                grade_distribution[g] = int(dr["count"])

        # Course summaries from view
        course_summaries = self.get_course_summary_from_view()

        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_courses": total_courses,
            "total_results_published": total_results_published,
            "platform_average_percentage": float(platform_avg_pct),
            "total_assignments": total_assignments,
            "total_submissions": total_submissions,
            "pending_grading_count": pending_grading_count,
            "completed_grading_count": completed_grading_count,
            "grade_distribution": grade_distribution,
            "course_summaries": course_summaries
        }


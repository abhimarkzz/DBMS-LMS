from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from app.models.sql_models import Assignment, Submission, Course, User


class AssignmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_assignment_by_id(self, assignment_id: int) -> Optional[Assignment]:
        return self.db.query(Assignment).options(
            joinedload(Assignment.course)
        ).filter(Assignment.id == assignment_id).first()

    def create_assignment(self, course_id: int, title: str, description: str, max_score: float, due_date: Optional[datetime]) -> Assignment:
        assignment = Assignment(
            course_id=course_id,
            title=title.strip(),
            description=description.strip(),
            max_score=max_score,
            due_date=due_date
        )
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def list_assignments_for_course(self, course_id: int, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        assignments = self.db.query(Assignment).options(
            joinedload(Assignment.course)
        ).filter(Assignment.course_id == course_id).order_by(Assignment.created_at.desc()).all()

        output = []
        for a in assignments:
            item = {
                "id": a.id,
                "course_id": a.course_id,
                "course_title": a.course.title if a.course else None,
                "course_code": a.course.code if a.course else None,
                "title": a.title,
                "description": a.description,
                "max_score": float(a.max_score),
                "due_date": a.due_date,
                "created_at": a.created_at,
                "has_submitted": False,
                "submission_id": None,
                "submission_status": None,
                "submission_score": None
            }
            if student_id:
                sub = self.db.query(Submission).filter(
                    Submission.assignment_id == a.id,
                    Submission.student_id == student_id
                ).first()
                if sub:
                    item["has_submitted"] = True
                    item["submission_id"] = sub.id
                    item["submission_status"] = sub.status
                    item["submission_score"] = float(sub.score) if sub.score is not None else None
            output.append(item)
        return output

    def list_all_assignments(self, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        assignments = self.db.query(Assignment).options(
            joinedload(Assignment.course)
        ).order_by(Assignment.created_at.desc()).all()

        output = []
        for a in assignments:
            item = {
                "id": a.id,
                "course_id": a.course_id,
                "course_title": a.course.title if a.course else None,
                "course_code": a.course.code if a.course else None,
                "title": a.title,
                "description": a.description,
                "max_score": float(a.max_score),
                "due_date": a.due_date,
                "created_at": a.created_at,
                "has_submitted": False,
                "submission_id": None,
                "submission_status": None,
                "submission_score": None
            }
            if student_id:
                sub = self.db.query(Submission).filter(
                    Submission.assignment_id == a.id,
                    Submission.student_id == student_id
                ).first()
                if sub:
                    item["has_submitted"] = True
                    item["submission_id"] = sub.id
                    item["submission_status"] = sub.status
                    item["submission_score"] = float(sub.score) if sub.score is not None else None
            output.append(item)
        return output

    def get_submission_by_id(self, submission_id: int) -> Optional[Submission]:
        return self.db.query(Submission).options(
            joinedload(Submission.assignment),
            joinedload(Submission.student)
        ).filter(Submission.id == submission_id).first()

    def get_submission_by_assignment_and_student(self, assignment_id: int, student_id: int) -> Optional[Submission]:
        return self.db.query(Submission).filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id == student_id
        ).first()

    def create_or_update_submission(self, assignment_id: int, student_id: int, content: str, file_url: Optional[str] = None) -> Submission:
        submission = self.get_submission_by_assignment_and_student(assignment_id, student_id)
        if submission:
            submission.content = content.strip()
            submission.file_url = file_url
            submission.submitted_at = datetime.utcnow()
            submission.status = "SUBMITTED"
            self.db.commit()
            self.db.refresh(submission)
            return submission

        submission = Submission(
            assignment_id=assignment_id,
            student_id=student_id,
            content=content.strip(),
            file_url=file_url,
            status="SUBMITTED"
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def grade_submission(self, submission_id: int, score: float, feedback: Optional[str]) -> Submission:
        submission = self.db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            raise ValueError("Submission not found")
        
        submission.score = score
        submission.feedback = feedback
        # Note: the PostgreSQL trigger 'trigger_auto_grade_submission' automatically sets status='GRADED',
        # sets graded_at=NOW(), and triggers calculate_course_grade!
        submission.status = "GRADED"
        submission.graded_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def list_submissions_for_assignment(self, assignment_id: int) -> List[Submission]:
        return self.db.query(Submission).options(
            joinedload(Submission.student),
            joinedload(Submission.assignment)
        ).filter(Submission.assignment_id == assignment_id).order_by(Submission.submitted_at.desc()).all()

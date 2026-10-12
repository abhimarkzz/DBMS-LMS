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

    def create_assignment(
        self, 
        course_id: int, 
        title: str, 
        description: str, 
        max_score: float, 
        due_date: Optional[datetime],
        instructions: Optional[str] = None,
        assessment_type: str = "DESCRIPTIVE",
        start_date: Optional[datetime] = None,
        due_time: Optional[str] = None,
        attempt_limit: int = 1,
        late_allowed: bool = True,
        status: str = "PUBLISHED",
        attachment_url: Optional[str] = None,
        assessment_config: Optional[str] = None
    ) -> Assignment:
        assignment = Assignment(
            course_id=course_id,
            title=title.strip(),
            description=description.strip(),
            instructions=instructions.strip() if instructions else None,
            max_score=max_score,
            assessment_type=assessment_type,
            due_date=due_date,
            start_date=start_date,
            due_time=due_time,
            attempt_limit=attempt_limit,
            late_allowed=late_allowed,
            status=status,
            attachment_url=attachment_url,
            assessment_config=assessment_config
        )
        self.db.add(assignment)
        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def list_assignments_for_course(self, course_id: int, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = self.db.query(Assignment).options(
            joinedload(Assignment.course)
        ).filter(Assignment.course_id == course_id)
        if student_id:
            query = query.filter(Assignment.status == "PUBLISHED")
        assignments = query.order_by(Assignment.created_at.desc()).all()

        output = []
        for a in assignments:
            item = {
                "id": a.id,
                "course_id": a.course_id,
                "course_title": a.course.title if a.course else None,
                "course_code": a.course.code if a.course else None,
                "title": a.title,
                "description": a.description,
                "instructions": a.instructions,
                "max_score": float(a.max_score),
                "assessment_type": a.assessment_type or "DESCRIPTIVE",
                "due_date": a.due_date,
                "start_date": a.start_date,
                "due_time": a.due_time,
                "attempt_limit": a.attempt_limit,
                "late_allowed": a.late_allowed,
                "status": a.status,
                "attachment_url": a.attachment_url,
                "assessment_config": a.assessment_config,
                "created_at": a.created_at,
                "has_submitted": False,
                "submission_id": None,
                "submission_status": None,
                "submission_score": None,
                "submission_grade_status": None,
                "submission_is_late": None
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
                    item["submission_grade_status"] = sub.grade_status
                    item["submission_is_late"] = sub.is_late
            output.append(item)
        return output

    def list_all_assignments(self, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = self.db.query(Assignment).options(
            joinedload(Assignment.course)
        )
        if student_id:
            from app.models.sql_models import Enrollment
            query = query.join(Enrollment, Enrollment.course_id == Assignment.course_id).filter(
                Enrollment.student_id == student_id,
                Enrollment.status == "ACTIVE",
                Assignment.status == "PUBLISHED"
            )
        assignments = query.order_by(Assignment.created_at.desc()).all()

        output = []
        for a in assignments:
            item = {
                "id": a.id,
                "course_id": a.course_id,
                "course_title": a.course.title if a.course else None,
                "course_code": a.course.code if a.course else None,
                "title": a.title,
                "description": a.description,
                "instructions": a.instructions,
                "max_score": float(a.max_score),
                "assessment_type": a.assessment_type or "DESCRIPTIVE",
                "due_date": a.due_date,
                "start_date": a.start_date,
                "due_time": a.due_time,
                "attempt_limit": a.attempt_limit,
                "late_allowed": a.late_allowed,
                "status": a.status,
                "attachment_url": a.attachment_url,
                "assessment_config": a.assessment_config,
                "created_at": a.created_at,
                "has_submitted": False,
                "submission_id": None,
                "submission_status": None,
                "submission_score": None,
                "submission_grade_status": None,
                "submission_is_late": None
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
                    item["submission_grade_status"] = sub.grade_status
                    item["submission_is_late"] = sub.is_late
            output.append(item)
        return output

    def get_submission_by_id(self, submission_id: int) -> Optional[Submission]:
        return self.db.query(Submission).options(
            joinedload(Submission.assignment).joinedload(Assignment.course),
            joinedload(Submission.student)
        ).filter(Submission.id == submission_id).first()

    def get_submission_by_assignment_and_student(self, assignment_id: int, student_id: int) -> Optional[Submission]:
        return self.db.query(Submission).filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id == student_id
        ).first()

    def create_or_update_submission(
        self, 
        assignment_id: int, 
        student_id: int, 
        content: str, 
        file_url: Optional[str] = None,
        submission_type: str = "TEXT",
        file_storage_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: int = 0,
        mcq_answers: Optional[str] = None,
        rubric_evaluation: Optional[str] = None,
        score: Optional[float] = None,
        feedback: Optional[str] = None,
        status: str = "SUBMITTED",
        grade_status: str = "PUBLISHED",
        is_late: bool = False
    ) -> Submission:
        submission = self.get_submission_by_assignment_and_student(assignment_id, student_id)
        if submission:
            submission.content = content.strip() if content else ""
            submission.file_url = file_url
            submission.submission_type = submission_type
            if file_storage_id:
                submission.file_storage_id = file_storage_id
            if file_name:
                submission.file_name = file_name
            if file_size:
                submission.file_size = file_size
            if mcq_answers is not None:
                submission.mcq_answers = mcq_answers
            if rubric_evaluation is not None:
                submission.rubric_evaluation = rubric_evaluation
            if score is not None:
                submission.score = score
            if feedback is not None:
                submission.feedback = feedback
            submission.submitted_at = datetime.utcnow()
            submission.attempt_number = (submission.attempt_number or 1) + 1
            submission.is_late = is_late
            submission.status = status
            submission.grade_status = grade_status
            if status == "GRADED":
                submission.graded_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(submission)
            return submission

        submission = Submission(
            assignment_id=assignment_id,
            student_id=student_id,
            content=content.strip() if content else "",
            file_url=file_url,
            submission_type=submission_type,
            file_storage_id=file_storage_id,
            file_name=file_name,
            file_size=file_size,
            mcq_answers=mcq_answers,
            rubric_evaluation=rubric_evaluation,
            score=score,
            feedback=feedback,
            attempt_number=1,
            is_late=is_late,
            status=status,
            grade_status=grade_status,
            graded_at=datetime.utcnow() if status == "GRADED" else None
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def grade_submission(
        self, 
        submission_id: int, 
        score: float, 
        feedback: Optional[str],
        rubric_evaluation: Optional[str] = None,
        publish: bool = True
    ) -> Submission:
        submission = self.db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            raise ValueError("Submission not found")
        
        submission.score = score
        submission.feedback = feedback
        if rubric_evaluation is not None:
            submission.rubric_evaluation = rubric_evaluation

        if publish:
            submission.status = "GRADED"
            submission.grade_status = "PUBLISHED"
            submission.graded_at = datetime.utcnow()
        else:
            submission.status = "EVALUATED"
            submission.grade_status = "DRAFT"

        self.db.commit()
        self.db.refresh(submission)
        return submission

    def publish_submission_grade(self, submission_id: int) -> Submission:
        submission = self.db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            raise ValueError("Submission not found")

        submission.status = "GRADED"
        submission.grade_status = "PUBLISHED"
        submission.graded_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(submission)
        return submission

    def list_submissions_for_assignment(self, assignment_id: int) -> List[Submission]:
        return self.db.query(Submission).options(
            joinedload(Submission.student),
            joinedload(Submission.assignment)
        ).filter(Submission.assignment_id == assignment_id).order_by(Submission.submitted_at.desc()).all()

    def get_pending_submissions(self, teacher_id: Optional[int] = None) -> List[Submission]:
        query = self.db.query(Submission).join(
            Assignment, Submission.assignment_id == Assignment.id
        ).join(
            Course, Assignment.course_id == Course.id
        ).options(
            joinedload(Submission.student),
            joinedload(Submission.assignment).joinedload(Assignment.course)
        ).filter(Submission.status.in_(["SUBMITTED", "EVALUATED", "LATE"]))

        if teacher_id is not None:
            query = query.filter(Course.teacher_id == teacher_id)

        return query.order_by(Submission.submitted_at.desc()).all()

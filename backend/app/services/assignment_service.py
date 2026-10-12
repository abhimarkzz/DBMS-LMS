import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.sql_models import Assignment, Submission
from app.repositories.assignment_repo import AssignmentRepository
from app.repositories.course_repo import CourseRepository
from app.services.notification_service import NotificationService
from app.services.file_storage_service import FileStorageService

logger = logging.getLogger(__name__)


class AssignmentService:
    def __init__(self, db: Session):
        self.db = db
        self.assignment_repo = AssignmentRepository(db)
        self.course_repo = CourseRepository(db)

    def create_assignment(
        self, 
        course_id: int, 
        title: str, 
        description: str, 
        max_score: float, 
        due_date: Optional[datetime],
        teacher_id: int,
        instructions: Optional[str] = None,
        assessment_type: str = "DESCRIPTIVE",
        start_date: Optional[datetime] = None,
        due_time: Optional[str] = None,
        attempt_limit: int = 1,
        late_allowed: bool = True,
        status_val: str = "PUBLISHED",
        attachment_url: Optional[str] = None,
        assessment_config: Optional[str] = None
    ) -> Assignment:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        if course.teacher_id != teacher_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only course instructor can create assignments")

        if max_score <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="max_score must be positive")

        return self.assignment_repo.create_assignment(
            course_id=course_id,
            title=title,
            description=description,
            max_score=max_score,
            due_date=due_date,
            instructions=instructions,
            assessment_type=assessment_type,
            start_date=start_date,
            due_time=due_time,
            attempt_limit=attempt_limit,
            late_allowed=late_allowed,
            status=status_val,
            attachment_url=attachment_url,
            assessment_config=assessment_config
        )

    def list_assignments(self, course_id: Optional[int] = None, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if course_id:
            return self.assignment_repo.list_assignments_for_course(course_id, student_id=student_id)
        return self.assignment_repo.list_all_assignments(student_id=student_id)

    async def submit_assignment(
        self, 
        assignment_id: int, 
        student_id: int, 
        content: str = "", 
        file_url: Optional[str] = None,
        mcq_answers: Optional[str] = None,
        submission_type: str = "TEXT"
    ) -> Submission:
        assignment = self.assignment_repo.get_assignment_by_id(assignment_id)
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

        # Verify student enrollment
        if not self.course_repo.is_student_enrolled(student_id, assignment.course_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in the course to submit assignments"
            )

        # Check existing submission and attempt limit
        existing = self.assignment_repo.get_submission_by_assignment_and_student(assignment_id, student_id)
        attempt_limit = assignment.attempt_limit or 1
        if existing and existing.status == "GRADED" and (existing.attempt_number or 1) >= attempt_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum attempt limit ({attempt_limit}) reached for this assessment."
            )

        now = datetime.utcnow()
        is_late = bool(assignment.due_date and now > assignment.due_date)
        late_allowed = True if assignment.late_allowed is None else assignment.late_allowed
        if is_late and not late_allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Late submissions are not accepted for this assignment."
            )

        # Handle MCQ Automated Grading
        if assignment.assessment_type == "MCQ" or submission_type == "MCQ":
            total_earned = 0.0
            breakdown = []
            questions = []
            if assignment.assessment_config:
                try:
                    cfg = json.loads(assignment.assessment_config)
                    questions = cfg.get("questions", [])
                except Exception as ex:
                    logger.warning(f"Failed to parse MCQ config: {ex}")

            student_choices = {}
            if mcq_answers:
                try:
                    student_choices = json.loads(mcq_answers)
                except Exception as ex:
                    logger.warning(f"Failed to parse student MCQ answers: {ex}")

            correct_count = 0
            for idx, q in enumerate(questions):
                q_id = str(q.get("id", idx))
                correct_ans = str(q.get("correct_answer", "")).strip().upper()
                student_ans = str(student_choices.get(q_id, student_choices.get(str(idx), ""))).strip().upper()
                q_marks = float(q.get("marks", 1.0))

                if student_ans == correct_ans and correct_ans:
                    total_earned += q_marks
                    correct_count += 1
                    breakdown.append(f"Q{idx+1}: Correct (+{q_marks} pts)")
                else:
                    breakdown.append(f"Q{idx+1}: Incorrect (Selected: '{student_ans or 'None'}', Correct: '{correct_ans}')")

            feedback_summary = (
                f"Automated Quiz Evaluation: {correct_count}/{len(questions)} correct. "
                f"Score: {total_earned}/{float(assignment.max_score)}.\n" + "\n".join(breakdown)
            )

            submission = self.assignment_repo.create_or_update_submission(
                assignment_id=assignment_id,
                student_id=student_id,
                content=content or f"MCQ Quiz Submission ({correct_count}/{len(questions)} correct)",
                submission_type="MCQ",
                mcq_answers=mcq_answers,
                score=total_earned,
                feedback=feedback_summary,
                status="GRADED",
                grade_status="PUBLISHED",
                is_late=is_late
            )

            # Recalculate student course grade
            try:
                self.db.execute(
                    text("SELECT calculate_course_grade(:student_id, :course_id)"),
                    {"student_id": student_id, "course_id": assignment.course_id}
                )
                self.db.commit()
            except Exception as e:
                logger.warning(f"Grade calculation notice: {e}")

            # Notify student: Submission successful and Grade Published
            course_code = assignment.course.code if assignment.course else "Course"
            await NotificationService.create_notification(
                user_id=student_id,
                title="Submission Successful",
                message=f"Your quiz answers for '{assignment.title}' ({course_code}) have been submitted and evaluated.",
                notif_type="SUBMISSION_SUCCESS",
                metadata={"assignment_id": assignment.id, "submission_id": submission.id, "course_id": assignment.course_id, "target_tab": "assignments"}
            )
            await NotificationService.create_notification(
                user_id=student_id,
                title=f"Grade Published: {assignment.title}",
                message=f"Your automated score for '{assignment.title}' is {total_earned}/{float(assignment.max_score)}.",
                notif_type="GRADE_PUBLISHED",
                metadata={"assignment_id": assignment.id, "score": total_earned, "course_id": assignment.course_id, "target_tab": "results"}
            )

            # Notify instructor
            if assignment.course and assignment.course.teacher_id:
                await NotificationService.create_notification(
                    user_id=assignment.course.teacher_id,
                    title=f"New Quiz Submission: {assignment.title}",
                    message=f"Student completed quiz '{assignment.title}' in {course_code} (Score: {total_earned}/{float(assignment.max_score)}).",
                    notif_type="NEW_SUBMISSION",
                    metadata={"assignment_id": assignment.id, "submission_id": submission.id, "course_id": assignment.course_id, "target_tab": "assignments"}
                )

            return submission

        # Descriptive / Standard Text Submission
        is_resub = existing is not None
        submission = self.assignment_repo.create_or_update_submission(
            assignment_id=assignment_id,
            student_id=student_id,
            content=content,
            file_url=file_url,
            submission_type="TEXT",
            status="LATE" if is_late else "SUBMITTED",
            grade_status="DRAFT",
            is_late=is_late
        )

        course_code = assignment.course.code if assignment.course else "Course"

        # 1. Notify Student
        await NotificationService.create_notification(
            user_id=student_id,
            title="Submission Successful",
            message=f"Your submission for '{assignment.title}' in {course_code} was recorded successfully.",
            notif_type="SUBMISSION_SUCCESS",
            metadata={"assignment_id": assignment.id, "submission_id": submission.id, "course_id": assignment.course_id, "target_tab": "assignments"}
        )

        # 2. Notify instructor in MongoDB & Redis
        if assignment.course and assignment.course.teacher_id:
            teacher_type = "ASSIGNMENT_RESUBMITTED" if is_resub else "NEW_SUBMISSION"
            title_prefix = "Assignment Resubmitted" if is_resub else "New Assignment Submission"
            await NotificationService.create_notification(
                user_id=assignment.course.teacher_id,
                title=f"{title_prefix}: {assignment.title}",
                message=f"Student submitted text for '{assignment.title}' in {course_code}{' (LATE)' if is_late else ''}.",
                notif_type=teacher_type,
                metadata={"assignment_id": assignment.id, "submission_id": submission.id, "course_id": assignment.course_id, "target_tab": "assignments"}
            )
            await NotificationService.create_notification(
                user_id=assignment.course.teacher_id,
                title="Student Submission Ready for Grading",
                message=f"Assessment '{assignment.title}' ({course_code}) is awaiting your evaluation and rubric grading.",
                notif_type="SUBMISSION_READY_FOR_GRADING",
                metadata={"assignment_id": assignment.id, "submission_id": submission.id, "course_id": assignment.course_id, "target_tab": "assignments"}
            )

        return submission

    async def submit_file_submission(
        self,
        assignment_id: int,
        student_id: int,
        file: UploadFile,
        notes: Optional[str] = None
    ) -> Submission:
        assignment = self.assignment_repo.get_assignment_by_id(assignment_id)
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

        if not self.course_repo.is_student_enrolled(student_id, assignment.course_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be enrolled in course to submit")

        existing = self.assignment_repo.get_submission_by_assignment_and_student(assignment_id, student_id)
        attempt_limit = assignment.attempt_limit or 1
        if existing and existing.status == "GRADED" and (existing.attempt_number or 1) >= attempt_limit:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum attempt limit ({attempt_limit}) reached for this assessment.")

        now = datetime.utcnow()
        is_late = bool(assignment.due_date and now > assignment.due_date)
        late_allowed = True if assignment.late_allowed is None else assignment.late_allowed
        if is_late and not late_allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Late submissions are not accepted for this assignment.")

        data = await file.read()
        file_size = len(data)

        # Parse config for allowed extensions and size limits
        submission_type = "FILE"
        if assignment.assessment_type == "AUDIO" or (file.content_type and "audio" in file.content_type):
            submission_type = "AUDIO"

        if assignment.assessment_config:
            try:
                cfg = json.loads(assignment.assessment_config)
                if submission_type == "FILE":
                    allowed_exts = cfg.get("allowed_extensions", [])
                    if allowed_exts:
                        filename_lower = (file.filename or "").lower()
                        if not any(filename_lower.endswith(ext.lower().strip()) for ext in allowed_exts):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"File extension not allowed. Accepted: {', '.join(allowed_exts)}"
                            )
                    max_mb = cfg.get("max_file_size_mb", 50)
                    if file_size > (max_mb * 1024 * 1024):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"File size exceeds maximum allowed ({max_mb} MB)"
                        )
                elif submission_type == "AUDIO":
                    allowed_fmts = cfg.get("allowed_audio_formats", [".mp3", ".wav", ".m4a", ".ogg", ".webm"])
                    if allowed_fmts:
                        filename_lower = (file.filename or "").lower()
                        if not any(filename_lower.endswith(fmt.lower().strip()) for fmt in allowed_fmts):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Audio format not allowed. Accepted: {', '.join(allowed_fmts)}"
                            )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Config validation error: {e}")

        storage_id = FileStorageService.store_file(
            course_id=assignment.course_id,
            filename=file.filename or "submission",
            content_type=file.content_type or "application/octet-stream",
            data=data,
            uploaded_by=student_id
        )

        submission = self.assignment_repo.create_or_update_submission(
            assignment_id=assignment_id,
            student_id=student_id,
            content=notes or f"Submitted file: {file.filename} ({round(file_size / 1024, 1)} KB)",
            submission_type=submission_type,
            file_storage_id=storage_id,
            file_name=file.filename,
            file_size=file_size,
            status="LATE" if is_late else "SUBMITTED",
            grade_status="DRAFT",
            is_late=is_late
        )

        course_code = assignment.course.code if assignment.course else "Course"

        # 1. Notify Student
        await NotificationService.create_notification(
            user_id=student_id,
            title="Submission Successful",
            message=f"Your {submission_type.lower()} submission for '{assignment.title}' ({file.filename or 'file'}) was received.",
            notif_type="SUBMISSION_SUCCESS",
            metadata={"assignment_id": assignment.id, "submission_id": submission.id, "course_id": assignment.course_id, "target_tab": "assignments"}
        )

        # 2. Notify Instructor
        if assignment.course and assignment.course.teacher_id:
            is_resub = existing is not None
            teacher_type = "ASSIGNMENT_RESUBMITTED" if is_resub else "NEW_SUBMISSION"
            title_prefix = "Assignment Resubmitted" if is_resub else "New Assessment Submission"
            await NotificationService.create_notification(
                user_id=assignment.course.teacher_id,
                title=f"{title_prefix}: {assignment.title}",
                message=f"Student submitted {submission_type.lower()} for '{assignment.title}' in {course_code}{' (LATE)' if is_late else ''}.",
                notif_type=teacher_type,
                metadata={"assignment_id": assignment.id, "submission_id": submission.id, "course_id": assignment.course_id, "target_tab": "assignments"}
            )
            await NotificationService.create_notification(
                user_id=assignment.course.teacher_id,
                title="Student Submission Ready for Grading",
                message=f"Assessment '{assignment.title}' ({course_code}) has a new student submission pending grading.",
                notif_type="SUBMISSION_READY_FOR_GRADING",
                metadata={"assignment_id": assignment.id, "submission_id": submission.id, "course_id": assignment.course_id, "target_tab": "assignments"}
            )

        return submission

    async def grade_submission(
        self, 
        submission_id: int, 
        score: float, 
        feedback: Optional[str],
        teacher_id: int,
        user_role: str = "TEACHER",
        rubric_evaluation: Optional[str] = None,
        publish: bool = True
    ) -> Submission:
        submission = self.assignment_repo.get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

        assignment = submission.assignment
        course = assignment.course if assignment else None
        if user_role != "ADMIN" and (not course or course.teacher_id != teacher_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the course instructor or an administrator can grade this submission"
            )

        if score < 0 or score > float(assignment.max_score):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Score must be between 0 and {assignment.max_score}"
            )

        # Validate rubric if defined in assignment
        if assignment.assessment_config:
            try:
                cfg = json.loads(assignment.assessment_config)
                rubric = cfg.get("rubric", [])
                if rubric:
                    if not rubric_evaluation:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Missing rubric marks: all rubric criteria must be evaluated."
                        )
                    rub_data = json.loads(rubric_evaluation) if isinstance(rubric_evaluation, str) else rubric_evaluation
                    criteria_scores = rub_data.get("criteria_scores", {})
                    for crit in rubric:
                        crit_id = str(crit.get("id"))
                        if crit_id not in criteria_scores:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Missing score for rubric criterion: {crit.get('name', crit_id)}"
                            )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Rubric evaluation parse error: {e}")

        graded_sub = self.assignment_repo.grade_submission(
            submission_id=submission_id,
            score=score,
            feedback=feedback,
            rubric_evaluation=rubric_evaluation,
            publish=publish
        )

        if publish:
            # PostgreSQL trigger or procedure recalculates results
            try:
                self.db.execute(
                    text("SELECT calculate_course_grade(:student_id, :course_id)"),
                    {"student_id": graded_sub.student_id, "course_id": assignment.course_id}
                )
                self.db.commit()
            except Exception as ex:
                logger.warning(f"Auto grade calculation notice: {ex}")

            # Notify student in MongoDB & Redis
            await NotificationService.create_notification(
                user_id=graded_sub.student_id,
                title=f"Grade Published: {assignment.title}",
                message=f"Your grade for '{assignment.title}' has been published: {score}/{assignment.max_score}.",
                notif_type="GRADE_PUBLISHED",
                metadata={"assignment_id": assignment.id, "submission_id": graded_sub.id, "score": score, "course_id": assignment.course_id, "target_tab": "results"}
            )

        return graded_sub

    async def publish_grade(self, submission_id: int, teacher_id: int, user_role: str = "TEACHER") -> Submission:
        submission = self.assignment_repo.get_submission_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

        assignment = submission.assignment
        course = assignment.course if assignment else None
        if user_role != "ADMIN" and (not course or course.teacher_id != teacher_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if submission.score is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot publish a submission without an evaluation score")

        pub_sub = self.assignment_repo.publish_submission_grade(submission_id)

        try:
            self.db.execute(
                text("SELECT calculate_course_grade(:student_id, :course_id)"),
                {"student_id": pub_sub.student_id, "course_id": assignment.course_id}
            )
            self.db.commit()
        except Exception as ex:
            logger.warning(f"Publish grade calc notice: {ex}")

        await NotificationService.create_notification(
            user_id=pub_sub.student_id,
            title=f"Grade Published: {assignment.title}",
            message=f"Official grade for '{assignment.title}' published: {pub_sub.score}/{assignment.max_score}.",
            notif_type="GRADE_PUBLISHED",
            metadata={"assignment_id": assignment.id, "submission_id": pub_sub.id, "score": float(pub_sub.score), "course_id": assignment.course_id, "target_tab": "results"}
        )

        return pub_sub

    def list_submissions_for_assignment(self, assignment_id: int, teacher_id: int, user_role: str = "TEACHER") -> List[Dict[str, Any]]:
        assignment = self.assignment_repo.get_assignment_by_id(assignment_id)
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

        if user_role != "ADMIN" and assignment.course and assignment.course.teacher_id != teacher_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        submissions = self.assignment_repo.list_submissions_for_assignment(assignment_id)
        return [
            {
                "id": s.id,
                "assignment_id": s.assignment_id,
                "assignment_title": assignment.title,
                "course_code": assignment.course.code if assignment.course else None,
                "course_title": assignment.course.title if assignment.course else None,
                "max_score": float(assignment.max_score),
                "student_id": s.student_id,
                "student_name": s.student.full_name if s.student else None,
                "student_email": s.student.email if s.student else None,
                "content": s.content,
                "file_url": s.file_url,
                "submission_type": s.submission_type or "TEXT",
                "file_storage_id": s.file_storage_id,
                "file_name": s.file_name,
                "file_size": s.file_size,
                "mcq_answers": s.mcq_answers,
                "rubric_evaluation": s.rubric_evaluation,
                "attempt_number": s.attempt_number or 1,
                "is_late": s.is_late or False,
                "submitted_at": s.submitted_at,
                "status": s.status,
                "grade_status": s.grade_status or "PUBLISHED",
                "score": float(s.score) if s.score is not None else None,
                "feedback": s.feedback,
                "graded_at": s.graded_at,
                "assessment_type": s.assignment.assessment_type if s.assignment else "DESCRIPTIVE",
                "assessment_config": s.assignment.assessment_config if s.assignment else None,
                "instructions": s.assignment.instructions if s.assignment else None
            }
            for s in submissions
        ]

    def list_pending_submissions(self, teacher_id: Optional[int] = None) -> List[Dict[str, Any]]:
        submissions = self.assignment_repo.get_pending_submissions(teacher_id)
        return [
            {
                "id": s.id,
                "assignment_id": s.assignment_id,
                "assignment_title": s.assignment.title if s.assignment else None,
                "course_code": s.assignment.course.code if (s.assignment and s.assignment.course) else None,
                "course_title": s.assignment.course.title if (s.assignment and s.assignment.course) else None,
                "max_score": float(s.assignment.max_score) if s.assignment else 100.0,
                "student_id": s.student_id,
                "student_name": s.student.full_name if s.student else "Student",
                "student_email": s.student.email if s.student else "",
                "content": s.content,
                "file_url": s.file_url,
                "submission_type": s.submission_type or "TEXT",
                "file_storage_id": s.file_storage_id,
                "file_name": s.file_name,
                "file_size": s.file_size,
                "mcq_answers": s.mcq_answers,
                "rubric_evaluation": s.rubric_evaluation,
                "attempt_number": s.attempt_number or 1,
                "is_late": s.is_late or False,
                "submitted_at": s.submitted_at,
                "status": s.status,
                "grade_status": s.grade_status or "PUBLISHED",
                "score": float(s.score) if s.score is not None else None,
                "feedback": s.feedback,
                "graded_at": s.graded_at,
                "assessment_type": s.assignment.assessment_type if s.assignment else "DESCRIPTIVE",
                "assessment_config": s.assignment.assessment_config if s.assignment else None,
                "instructions": s.assignment.instructions if s.assignment else None
            }
            for s in submissions
        ]


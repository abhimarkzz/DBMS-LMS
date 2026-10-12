from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.sql_models import Course, Enrollment, StudyMaterial
from app.repositories.course_repo import CourseRepository
from app.services.ai_search_service import AISearchService
from app.services.notification_service import NotificationService
from app.database.redis_client import cache_get, cache_set, cache_delete


class CourseService:
    def __init__(self, db: Session):
        self.db = db
        self.course_repo = CourseRepository(db)
        self.ai_service = AISearchService(db)

    def create_course(
        self,
        code: str,
        title: str,
        short_description: Optional[str] = None,
        description: Optional[str] = None,
        department: str = "Computer Science & Engineering",
        level: str = "Graduate",
        academic_session: str = "Spring 2026",
        semester: str = "Term 2",
        credits: int = 4,
        prerequisites: Optional[str] = None,
        learning_outcomes: Optional[str] = None,
        syllabus: Optional[str] = None,
        modules_outline: Optional[str] = None,
        start_date: str = "2026-01-15",
        end_date: str = "2026-05-30",
        capacity: int = 50,
        status_val: str = "PUBLISHED",
        is_published: bool = True,
        teacher_id: int = 1
    ) -> Course:
        existing = self.course_repo.get_course_by_code(code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course with code '{code}' already exists"
            )
        course = self.course_repo.create_course(
            code=code,
            title=title,
            short_description=short_description,
            description=description,
            department=department,
            level=level,
            academic_session=academic_session,
            semester=semester,
            credits=credits,
            prerequisites=prerequisites,
            learning_outcomes=learning_outcomes,
            syllabus=syllabus,
            modules_outline=modules_outline,
            start_date=start_date,
            end_date=end_date,
            capacity=capacity,
            status=status_val,
            is_published=is_published,
            teacher_id=teacher_id
        )
        return course

    def update_course(self, course_id: int, user: Any, **kwargs) -> Course:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if user.role.name != "ADMIN" and course.teacher_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit a course you do not instruct")
        updated = self.course_repo.update_course(course_id, **kwargs)
        return updated

    def update_course_status(self, course_id: int, status_str: str, user: Any) -> Course:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if user.role.name != "ADMIN" and course.teacher_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot alter status of a course you do not instruct")
        updated = self.course_repo.update_course_status(course_id, status_str)
        return updated

    def delete_course(self, course_id: int, user: Any) -> bool:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if user.role.name != "ADMIN" and course.teacher_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete a course you do not instruct")
        return self.course_repo.delete_course(course_id)

    def list_courses(self, student_id: Optional[int] = None, teacher_id: Optional[int] = None, include_all: bool = False) -> List[Dict[str, Any]]:
        return self.course_repo.list_courses(student_id=student_id, teacher_id=teacher_id, include_all=include_all)

    def get_course_detail(self, course_id: int, student_id: Optional[int] = None) -> Dict[str, Any]:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        materials = self.course_repo.get_study_materials(course_id)
        is_enrolled = False
        if student_id:
            is_enrolled = self.course_repo.is_student_enrolled(student_id, course_id)

        announcements = self.course_repo.get_announcements(course_id)
        quizzes = self.course_repo.get_quizzes(course_id)

        return {
            "id": course.id,
            "code": course.code,
            "title": course.title,
            "short_description": course.short_description,
            "description": course.description,
            "department": course.department,
            "level": course.level,
            "academic_session": course.academic_session,
            "semester": course.semester,
            "credits": course.credits,
            "prerequisites": course.prerequisites,
            "learning_outcomes": course.learning_outcomes,
            "syllabus": course.syllabus,
            "modules_outline": course.modules_outline,
            "start_date": course.start_date,
            "end_date": course.end_date,
            "capacity": course.capacity,
            "status": course.status,
            "teacher_id": course.teacher_id,
            "teacher_name": course.teacher.full_name if course.teacher else None,
            "is_published": course.is_published,
            "created_at": course.created_at,
            "enrolled_count": len(course.enrollments),
            "is_enrolled": is_enrolled,
            "materials": [
                {
                    "id": m.id,
                    "course_id": m.course_id,
                    "title": m.title,
                    "content": m.content,
                    "material_type": m.material_type,
                    "original_filename": m.original_filename,
                    "file_type": m.file_type or m.material_type,
                    "file_size": m.file_size,
                    "status": m.status,
                    "chunk_count": m.chunk_count,
                    "error_message": m.error_message,
                    "file_storage_id": m.file_storage_id,
                    "file_url": m.file_url,
                    "uploaded_by": m.uploaded_by,
                    "uploader_name": m.uploader.full_name if m.uploader else "Faculty Instructor",
                    "created_at": m.created_at
                }
                for m in materials
            ],
            "announcements": [
                {
                    "id": a.id,
                    "course_id": a.course_id,
                    "author_id": a.author_id,
                    "author_name": a.author.full_name if a.author else None,
                    "title": a.title,
                    "content": a.content,
                    "created_at": a.created_at
                }
                for a in announcements
            ],
            "quizzes": [
                {
                    "id": q.id,
                    "course_id": q.course_id,
                    "title": q.title,
                    "description": q.description,
                    "due_date": q.due_date,
                    "duration_minutes": q.duration_minutes,
                    "total_points": q.total_points,
                    "created_at": q.created_at
                }
                for q in quizzes
            ],
            "assignments": [
                {
                    "id": assign.id,
                    "course_id": assign.course_id,
                    "title": assign.title,
                    "description": assign.description,
                    "max_score": float(assign.max_score) if assign.max_score else 100.0,
                    "due_date": assign.due_date,
                    "created_at": assign.created_at
                }
                for assign in (course.assignments or [])
            ],
            "enrolled_students": [
                {
                    "id": e.student.id,
                    "full_name": e.student.full_name,
                    "email": e.student.email,
                    "enrolled_at": e.enrolled_at,
                    "status": e.status
                }
                for e in (course.enrollments or [])
                if e.student
            ]
        }

    async def enroll_student(self, student_id: int, course_id: int) -> Enrollment:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        enrollment = self.course_repo.enroll_student(student_id, course_id)

        # Create MongoDB notification for the student
        await NotificationService.create_notification(
            user_id=student_id,
            title=f"Enrolled in {course.code}",
            message=f"You have been successfully enrolled in {course.code} - {course.title}.",
            notif_type="COURSE_ENROLLMENT",
            metadata={"course_id": course.id, "course_code": course.code, "target_tab": "courses"}
        )

        # Notify instructor
        if course.teacher_id:
            await NotificationService.create_notification(
                user_id=course.teacher_id,
                title=f"New Enrollment: {course.code}",
                message=f"A student has enrolled in your course {course.code} - {course.title}.",
                notif_type="COURSE_ENROLLMENT",
                metadata={"course_id": course.id, "student_id": student_id, "target_tab": "courses"}
            )

        return enrollment

    def get_student_enrollments(self, student_id: int) -> List[Dict[str, Any]]:
        enrollments = self.course_repo.get_student_enrollments(student_id)
        return [
            {
                "id": e.id,
                "student_id": e.student_id,
                "course_id": e.course_id,
                "course_title": e.course.title if e.course else None,
                "course_code": e.course.code if e.course else None,
                "enrolled_at": e.enrolled_at,
                "status": e.status
            }
            for e in enrollments
        ]

    async def add_study_material(
        self, 
        course_id: int, 
        title: str, 
        content: str, 
        material_type: str = "NOTES", 
        file_url: Optional[str] = None
    ) -> StudyMaterial:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        material = self.course_repo.add_study_material(
            course_id=course_id,
            title=title,
            content=content,
            material_type=material_type,
            file_url=file_url
        )

        # Chunk, embed, and store in pgvector note_chunks
        await self.ai_service.index_study_material(
            material_id=material.id,
            course_id=course_id,
            content=content
        )

        # Notify enrolled students that study material was indexed
        await NotificationService.notify_enrolled_students(
            db=self.db,
            course_id=course_id,
            title=f"Study Material Indexed: {material.title}",
            message=f"'{material.title}' is now indexed and available in {course.code} for AI Smart Search.",
            notif_type="STUDY_MATERIAL_INDEXED",
            metadata={"course_id": course_id, "material_id": material.id, "target_tab": "materials"}
        )

        return material

    async def add_announcement(self, course_id: int, author_id: int, title: str, content: str) -> Any:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        ann = self.course_repo.add_announcement(course_id, author_id, title, content)
        # Broadcast notification to enrolled students
        for enrollment in (course.enrollments or []):
            await NotificationService.create_notification(
                user_id=enrollment.student_id,
                title=f"Announcement: {course.code}",
                message=f"[{course.code}] {title}",
                notif_type="COURSE_ANNOUNCEMENT",
                metadata={"course_id": course_id, "announcement_id": ann.id, "target_tab": "courses"}
            )
        # Notify teacher
        await NotificationService.create_notification(
            user_id=author_id,
            title="Announcement Published",
            message=f"Your announcement '{title}' was published to {course.code}.",
            notif_type="ANNOUNCEMENT_CONFIRMATION",
            metadata={"course_id": course_id, "announcement_id": ann.id, "target_tab": "courses"}
        )
        return ann

    def add_quiz(self, course_id: int, title: str, description: Optional[str] = None, due_date: Optional[Any] = None, duration_minutes: int = 30, total_points: int = 100) -> Any:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return self.course_repo.add_quiz(
            course_id=course_id,
            title=title,
            description=description,
            due_date=due_date,
            duration_minutes=duration_minutes,
            total_points=total_points
        )

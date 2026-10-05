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

    def create_course(self, code: str, title: str, description: Optional[str], syllabus: Optional[str], teacher_id: int) -> Course:
        existing = self.course_repo.get_course_by_code(code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Course with code '{code}' already exists"
            )
        course = self.course_repo.create_course(code, title, description, syllabus, teacher_id)
        return course

    def list_courses(self, student_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.course_repo.list_courses(student_id=student_id)

    def get_course_detail(self, course_id: int, student_id: Optional[int] = None) -> Dict[str, Any]:
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        materials = self.course_repo.get_study_materials(course_id)
        is_enrolled = False
        if student_id:
            is_enrolled = self.course_repo.is_student_enrolled(student_id, course_id)

        return {
            "id": course.id,
            "code": course.code,
            "title": course.title,
            "description": course.description,
            "syllabus": course.syllabus,
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
                    "file_url": m.file_url,
                    "created_at": m.created_at
                }
                for m in materials
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
            title="Course Enrollment Successful",
            message=f"You have been successfully enrolled in {course.code} - {course.title}.",
            notif_type="ENROLLMENT",
            metadata={"course_id": course.id, "course_code": course.code}
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

        return material

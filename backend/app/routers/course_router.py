from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.course_schema import (
    CourseCreate, CourseResponse, CourseDetailResponse, 
    EnrollmentResponse, StudyMaterialCreate, StudyMaterialResponse
)
from app.services.course_service import CourseService
from app.services.auth_service import get_current_user, require_roles
from app.services.notification_service import NotificationService
from app.models.sql_models import User

router = APIRouter(prefix="/api/courses", tags=["Courses"])


@router.get("", response_model=List[CourseResponse])
def get_courses(
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    student_id = current_user.id if current_user and current_user.role and current_user.role.name == "STUDENT" else None
    return service.list_courses(student_id=student_id)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    course = service.create_course(
        code=payload.code,
        title=payload.title,
        description=payload.description,
        syllabus=payload.syllabus,
        teacher_id=current_user.id
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="COURSE_CREATED",
        details=f"Created course {course.code} - {course.title}"
    )
    return {
        "id": course.id,
        "code": course.code,
        "title": course.title,
        "description": course.description,
        "syllabus": course.syllabus,
        "teacher_id": course.teacher_id,
        "teacher_name": current_user.full_name,
        "is_published": course.is_published,
        "created_at": course.created_at,
        "enrolled_count": 0,
        "is_enrolled": False
    }


@router.get("/my/enrollments", response_model=List[EnrollmentResponse])
def get_my_enrollments(
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    return service.get_student_enrollments(current_user.id)


@router.get("/{course_id}", response_model=CourseDetailResponse)
def get_course_detail(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    student_id = current_user.id if current_user.role and current_user.role.name == "STUDENT" else None
    return service.get_course_detail(course_id, student_id=student_id)


@router.post("/{course_id}/enroll", response_model=EnrollmentResponse)
async def enroll_in_course(
    course_id: int,
    current_user: User = Depends(require_roles(["STUDENT"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    enrollment = await service.enroll_student(current_user.id, course_id)
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ENROLLED_IN_COURSE",
        details=f"Enrolled in course ID {course_id}"
    )
    return {
        "id": enrollment.id,
        "student_id": enrollment.student_id,
        "course_id": enrollment.course_id,
        "enrolled_at": enrollment.enrolled_at,
        "status": enrollment.status,
        "course_title": enrollment.course.title if enrollment.course else None,
        "course_code": enrollment.course.code if enrollment.course else None
    }


@router.post("/{course_id}/materials", response_model=StudyMaterialResponse, status_code=status.HTTP_201_CREATED)
async def add_course_material(
    course_id: int,
    payload: StudyMaterialCreate,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    material = await service.add_study_material(
        course_id=course_id,
        title=payload.title,
        content=payload.content,
        material_type=payload.material_type,
        file_url=payload.file_url
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="STUDY_MATERIAL_ADDED",
        details=f"Added material '{material.title}' in course ID {course_id}"
    )
    return material

from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, Form, Response, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.postgres import get_db
from app.schemas.course_schema import (
    CourseCreate, CourseUpdate, CourseResponse, CourseDetailResponse, 
    EnrollmentResponse, StudyMaterialCreate, StudyMaterialResponse,
    AnnouncementCreate, AnnouncementResponse, QuizCreate, QuizResponse
)
from app.services.course_service import CourseService
from app.services.study_material_service import StudyMaterialService
from app.services.auth_service import get_current_user, require_roles
from app.services.notification_service import NotificationService
from app.models.sql_models import User, Course

router = APIRouter(prefix="/api/courses", tags=["Courses"])


class StatusUpdatePayload(BaseModel):
    status: str


@router.get("", response_model=List[CourseResponse])
def get_courses(
    include_all: bool = Query(False),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    student_id = current_user.id if current_user and current_user.role and current_user.role.name == "STUDENT" else None
    is_privileged = current_user and current_user.role and current_user.role.name in ["TEACHER", "ADMIN"]
    return service.list_courses(
        student_id=student_id,
        include_all=(include_all and is_privileged)
    )


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
        short_description=payload.short_description,
        description=payload.description,
        department=payload.department,
        level=payload.level,
        academic_session=payload.academic_session,
        semester=payload.semester,
        credits=payload.credits,
        prerequisites=payload.prerequisites,
        learning_outcomes=payload.learning_outcomes,
        syllabus=payload.syllabus,
        modules_outline=payload.modules_outline,
        start_date=payload.start_date,
        end_date=payload.end_date,
        capacity=payload.capacity,
        status_val=payload.status,
        is_published=payload.is_published,
        teacher_id=payload.teacher_id if (current_user.role.name == "ADMIN" and payload.teacher_id) else current_user.id
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="COURSE_CREATED",
        details=f"Created course {course.code} - {course.title} ({course.department})"
    )
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
        "teacher_name": course.teacher.full_name if course.teacher else current_user.full_name,
        "is_published": course.is_published,
        "created_at": course.created_at,
        "enrolled_count": 0,
        "is_enrolled": False
    }


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    course = service.update_course(
        course_id=course_id,
        user=current_user,
        **payload.model_dump(exclude_unset=True)
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="COURSE_UPDATED",
        details=f"Updated details for course {course.code} - {course.title}"
    )
    return service.get_course_detail(course_id)


@router.patch("/{course_id}/status", response_model=CourseResponse)
async def update_course_status(
    course_id: int,
    payload: StatusUpdatePayload,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    course = service.update_course_status(
        course_id=course_id,
        status_str=payload.status,
        user=current_user
    )
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="COURSE_STATUS_CHANGED",
        details=f"Changed course {course.code} status to {course.status}"
    )
    return service.get_course_detail(course_id)


@router.delete("/{course_id}", status_code=status.HTTP_200_OK)
async def delete_course(
    course_id: int,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    success = service.delete_course(course_id, current_user)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course could not be deleted")
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="COURSE_DELETED",
        details=f"Deleted course ID {course_id}"
    )
    return {"message": "Course deleted successfully", "id": course_id}


@router.post("/{course_id}/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def add_announcement(
    course_id: int,
    payload: AnnouncementCreate,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    ann = await service.add_announcement(
        course_id=course_id,
        author_id=current_user.id,
        title=payload.title,
        content=payload.content
    )
    return {
        "id": ann.id,
        "course_id": ann.course_id,
        "author_id": ann.author_id,
        "author_name": current_user.full_name,
        "title": ann.title,
        "content": ann.content,
        "created_at": ann.created_at
    }


@router.post("/{course_id}/quizzes", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
async def add_quiz(
    course_id: int,
    payload: QuizCreate,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    quiz = service.add_quiz(
        course_id=course_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        duration_minutes=payload.duration_minutes,
        total_points=payload.total_points
    )
    return quiz


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


@router.get("/{course_id}/materials", response_model=List[StudyMaterialResponse])
def list_course_materials(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = CourseService(db)
    materials = service.course_repo.get_study_materials(course_id)
    return materials


@router.post("/{course_id}/materials/upload", response_model=List[StudyMaterialResponse], status_code=status.HTTP_201_CREATED)
async def upload_course_materials(
    course_id: int,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = StudyMaterialService(db)
    results = []

    for file in files:
        file_bytes = await file.read()
        material = await service.upload_file_material(
            course_id=course_id,
            filename=file.filename or "uploaded_file",
            file_bytes=file_bytes,
            user=current_user
        )
        results.append(material)

        if material.status == "INDEXED":
            course = db.query(Course).filter(Course.id == course_id).first()
            course_code = course.code if course else f"Course #{course_id}"
            await NotificationService.notify_enrolled_students(
                db=db,
                course_id=course_id,
                title=f"Study Material Indexed: {material.title}",
                message=f"'{material.title}' was uploaded and indexed in {course_code} ({material.chunk_count} chunks ready for AI Search).",
                notif_type="STUDY_MATERIAL_INDEXED",
                metadata={"course_id": course_id, "material_id": material.id, "target_tab": "materials"}
            )

        await NotificationService.log_activity(
            user_id=current_user.id,
            user_name=current_user.full_name,
            action="STUDY_MATERIAL_FILE_UPLOADED",
            details=f"Uploaded file '{file.filename}' (status: {material.status}, chunks: {material.chunk_count}) for course {course_id}"
        )

    return results


@router.post("/{course_id}/materials", response_model=StudyMaterialResponse, status_code=status.HTTP_201_CREATED)
async def add_course_material(
    course_id: int,
    payload: StudyMaterialCreate,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = StudyMaterialService(db)
    material = await service.add_manual_note(
        course_id=course_id,
        title=payload.title,
        content=payload.content,
        user=current_user,
        material_type=payload.material_type or "NOTES"
    )
    if material.status == "INDEXED":
        course = db.query(Course).filter(Course.id == course_id).first()
        course_code = course.code if course else f"Course #{course_id}"
        await NotificationService.notify_enrolled_students(
            db=db,
            course_id=course_id,
            title=f"Study Material Indexed: {material.title}",
            message=f"'{material.title}' was added and indexed in {course_code} ({material.chunk_count} chunks ready for AI Search).",
            notif_type="STUDY_MATERIAL_INDEXED",
            metadata={"course_id": course_id, "material_id": material.id, "target_tab": "materials"}
        )

    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="STUDY_MATERIAL_ADDED",
        details=f"Added text note '{material.title}' in course ID {course_id}"
    )
    return material


@router.get("/{course_id}/materials/{material_id}/download")
def download_course_material(
    course_id: int,
    material_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import urllib.parse
    service = StudyMaterialService(db)
    filename, content_type, data = service.get_material_file(course_id, material_id, current_user)
    ascii_filename = filename.encode("ascii", "replace").decode("ascii").replace('"', '')
    encoded_filename = urllib.parse.quote(filename)
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        }
    )


@router.post("/{course_id}/materials/{material_id}/reindex", response_model=StudyMaterialResponse)
async def reindex_course_material(
    course_id: int,
    material_id: int,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = StudyMaterialService(db)
    material = await service.reindex_material(course_id, material_id, current_user)
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="STUDY_MATERIAL_REINDEXED",
        details=f"Reindexed material '{material.title}' (chunks: {material.chunk_count}) in course ID {course_id}"
    )
    return material


@router.delete("/{course_id}/materials/{material_id}")
async def delete_course_material(
    course_id: int,
    material_id: int,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    service = StudyMaterialService(db)
    success = service.delete_material(course_id, material_id, current_user)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material could not be deleted")

    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="STUDY_MATERIAL_DELETED",
        details=f"Deleted study material ID {material_id} from course ID {course_id}"
    )
    return {"message": "Study material deleted successfully", "id": material_id}

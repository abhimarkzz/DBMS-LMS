from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.notification_schema import (
    NotificationResponse, AnnouncementCreate, 
    AnnouncementResponse, ActivityLogResponse
)
from app.services.notification_service import NotificationService
from app.services.auth_service import get_current_user, require_roles
from app.models.sql_models import User, Course

router = APIRouter(prefix="/api/notifications", tags=["Notifications & Announcements"])


@router.get("", response_model=List[NotificationResponse])
async def get_my_notifications(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    return await NotificationService.get_user_notifications(current_user.id, limit=limit)


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    success = await NotificationService.mark_as_read(notification_id, current_user.id)
    return {"success": success}


@router.get("/announcements/{course_id}", response_model=List[AnnouncementResponse])
async def get_course_announcements(
    course_id: int,
    _: User = Depends(get_current_user)
):
    return await NotificationService.get_course_announcements(course_id)


@router.post("/announcements", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
async def create_course_announcement(
    payload: AnnouncementCreate,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    course = db.query(Course).filter(Course.id == payload.course_id).first()
    course_title = course.title if course else "Course"

    announcement = await NotificationService.create_announcement(
        course_id=payload.course_id,
        title=payload.title,
        content=payload.content,
        author_name=current_user.full_name,
        course_title=course_title
    )
    return announcement


@router.get("/activities", response_model=List[ActivityLogResponse])
async def get_activity_logs(
    _: User = Depends(require_roles(["ADMIN"]))
):
    return await NotificationService.get_recent_activities(limit=30)

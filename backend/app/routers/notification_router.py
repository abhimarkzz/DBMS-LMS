import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.notification_schema import (
    NotificationResponse, AnnouncementCreate, 
    AnnouncementResponse, ActivityLogResponse,
    UnreadCountResponse, MarkAllReadResponse
)
from app.services.notification_service import NotificationService
from app.services.auth_service import get_current_user, require_roles, decode_access_token
from app.repositories.user_repo import UserRepository
from app.models.sql_models import User, Course

router = APIRouter(prefix="/api/notifications", tags=["Notifications & Announcements"])


def get_user_from_token_str(token: str, db: Session) -> User:
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
        user = UserRepository(db).get_user_by_id(int(user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed: {str(e)}")


@router.get("", response_model=List[NotificationResponse])
async def get_my_notifications(
    limit: int = 50,
    unread_only: bool = False,
    notif_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Fetch notifications from MongoDB with optional filter."""
    return await NotificationService.get_user_notifications(
        user_id=current_user.id,
        limit=limit,
        unread_only=unread_only,
        notif_type=notif_type
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    current_user: User = Depends(get_current_user)
):
    """Get accurate live count of unread notifications directly from MongoDB."""
    count = await NotificationService.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark single notification as read in MongoDB."""
    success = await NotificationService.mark_as_read(notification_id, current_user.id)
    return {"success": success}


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user)
):
    """Mark all unread notifications for current user as read in MongoDB."""
    marked_count = await NotificationService.mark_all_as_read(current_user.id)
    return {"success": True, "marked_count": marked_count}


@router.get("/stream")
async def stream_notifications(
    request: Request,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Server-Sent Events (SSE) endpoint for real-time notification streaming.
    No full page refresh needed. Fallback to keepalive pings every 15 seconds.
    """
    auth_header = request.headers.get("Authorization")
    tok = None
    if auth_header and auth_header.startswith("Bearer "):
        tok = auth_header.split(" ")[1]
    elif token:
        tok = token

    if not tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required for SSE stream"
        )

    user = get_user_from_token_str(tok, db)

    async def event_generator():
        queue = NotificationService.subscribe_user(user.id)
        try:
            # Yield initial connection message with current unread count
            unread_count = await NotificationService.get_unread_count(user.id)
            init_data = json.dumps({"event": "CONNECTED", "unread_count": unread_count})
            yield f"data: {init_data}\n\n"

            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(item, default=str)}\n\n"
                except asyncio.TimeoutError:
                    # SSE keepalive comment
                    yield ": ping\n\n"
        finally:
            NotificationService.unsubscribe_user(user.id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/check-due-soon")
async def trigger_due_soon_check(
    hours: int = 24,
    _: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """Trigger due soon notifications for pending student assignments."""
    count = await NotificationService.check_assignments_due_soon(db, hours_ahead=hours)
    return {"status": "ok", "notifications_sent": count}


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
    course_code = course.code if course else f"Course #{payload.course_id}"

    announcement = await NotificationService.create_announcement(
        course_id=payload.course_id,
        title=payload.title,
        content=payload.content,
        author_name=current_user.full_name,
        course_title=course_title
    )

    # 1. Notify enrolled students
    await NotificationService.notify_enrolled_students(
        db=db,
        course_id=payload.course_id,
        title=f"Announcement: {payload.title}",
        message=f"[{course_code}] {payload.content[:120]}{'...' if len(payload.content) > 120 else ''}",
        notif_type="COURSE_ANNOUNCEMENT",
        metadata={
            "course_id": payload.course_id,
            "announcement_id": announcement.get("id"),
            "target_tab": "courses"
        }
    )

    # 2. Confirm to teacher
    await NotificationService.create_notification(
        user_id=current_user.id,
        title="Announcement Published",
        message=f"Your announcement '{payload.title}' was sent to students in {course_code}.",
        notif_type="ANNOUNCEMENT_CONFIRMATION",
        metadata={"course_id": payload.course_id, "target_tab": "courses"}
    )

    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="ANNOUNCEMENT_POSTED",
        details=f"Posted announcement '{payload.title}' in {course_code}"
    )

    return announcement


@router.get("/activities", response_model=List[ActivityLogResponse])
async def get_activity_logs(
    _: User = Depends(require_roles(["ADMIN"]))
):
    return await NotificationService.get_recent_activities(limit=30)

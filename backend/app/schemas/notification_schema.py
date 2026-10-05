from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class NotificationResponse(BaseModel):
    id: str
    user_id: int
    title: str
    message: str
    type: str  # SYSTEM, GRADE, ENROLLMENT, ANNOUNCEMENT
    is_read: bool = False
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class AnnouncementCreate(BaseModel):
    course_id: int
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=5)


class AnnouncementResponse(BaseModel):
    id: str
    course_id: int
    course_title: Optional[str] = None
    title: str
    content: str
    author_name: str
    created_at: datetime


class ActivityLogResponse(BaseModel):
    id: str
    user_id: int
    user_name: str
    action: str
    details: Optional[str] = None
    timestamp: datetime

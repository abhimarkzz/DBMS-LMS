import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from bson import ObjectId
from sqlalchemy.orm import Session
from app.database.mongo import get_mongo_db
from app.database.redis_client import publish_event

logger = logging.getLogger(__name__)


class NotificationService:
    # In-memory subscriber registry for SSE real-time events: user_id -> set of asyncio.Queue
    _sse_subscribers: Dict[int, Set[asyncio.Queue]] = {}
    _lock = asyncio.Lock()

    @classmethod
    def subscribe_user(cls, user_id: int) -> asyncio.Queue:
        """Register an asyncio queue for real-time SSE stream delivery to user."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        if user_id not in cls._sse_subscribers:
            cls._sse_subscribers[user_id] = set()
        cls._sse_subscribers[user_id].add(queue)
        logger.info(f"SSE subscribed: user_id={user_id} (active connections: {len(cls._sse_subscribers[user_id])})")
        return queue

    @classmethod
    def unsubscribe_user(cls, user_id: int, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue when client disconnects."""
        if user_id in cls._sse_subscribers:
            cls._sse_subscribers[user_id].discard(queue)
            if not cls._sse_subscribers[user_id]:
                del cls._sse_subscribers[user_id]
        logger.info(f"SSE unsubscribed: user_id={user_id}")

    @classmethod
    async def broadcast_to_user(cls, user_id: int, event_data: dict) -> None:
        """Push real-time payload directly to active SSE listeners for user."""
        if user_id in cls._sse_subscribers:
            for q in list(cls._sse_subscribers[user_id]):
                try:
                    q.put_nowait(event_data)
                except asyncio.QueueFull:
                    try:
                        q.get_nowait()
                        q.put_nowait(event_data)
                    except Exception:
                        pass
                except Exception as e:
                    logger.debug(f"Error putting to SSE queue for user {user_id}: {e}")

    @classmethod
    async def create_notification(
        cls,
        user_id: int, 
        title: str, 
        message: str, 
        notif_type: str = "SYSTEM", 
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Create notification in MongoDB, publish to Redis pub/sub,
        and dispatch in real-time to active SSE streams.
        """
        doc = {
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notif_type,
            "is_read": False,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        
        try:
            db = get_mongo_db()
            if db is not None:
                res = await db.notifications.insert_one(doc)
                doc["id"] = str(res.inserted_id)
                if "_id" in doc:
                    del doc["_id"]
            else:
                doc["id"] = f"fb_{int(datetime.utcnow().timestamp())}"
        except Exception as e:
            logger.warning(f"Failed to persist notification in MongoDB: {e}")
            doc["id"] = f"fallback_{int(datetime.utcnow().timestamp())}"

        # Current unread count from MongoDB
        unread_count = await cls.get_unread_count(user_id)

        # Standard event envelope
        event_payload = {
            "event": "NEW_NOTIFICATION",
            "user_id": user_id,
            "unread_count": unread_count,
            "notification": {
                "id": str(doc.get("id")),
                "user_id": user_id,
                "title": title,
                "message": message,
                "type": notif_type,
                "is_read": False,
                "metadata": doc.get("metadata", {}),
                "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at"))
            }
        }

        # 1. Publish to Redis channel (graceful fallback handled internally)
        await publish_event("lms_notifications", event_payload)

        # 2. Dispatch directly to user's connected SSE browser streams
        await cls.broadcast_to_user(user_id, event_payload)
        
        return doc

    @classmethod
    async def notify_users(
        cls,
        user_ids: List[int],
        title: str,
        message: str,
        notif_type: str,
        metadata: Optional[dict] = None
    ) -> List[dict]:
        """Bulk notify a list of users."""
        results = []
        for uid in set(user_ids):
            try:
                res = await cls.create_notification(
                    user_id=uid,
                    title=title,
                    message=message,
                    notif_type=notif_type,
                    metadata=metadata
                )
                results.append(res)
            except Exception as e:
                logger.warning(f"Failed to create notification for user {uid}: {e}")
        return results

    @classmethod
    async def notify_enrolled_students(
        cls,
        db: Session,
        course_id: int,
        title: str,
        message: str,
        notif_type: str,
        metadata: Optional[dict] = None
    ) -> List[dict]:
        """Notify all actively enrolled students in a course."""
        from app.models.sql_models import Enrollment
        meta = metadata.copy() if metadata else {}
        meta["course_id"] = course_id

        enrollments = db.query(Enrollment.student_id).filter(
            Enrollment.course_id == course_id,
            Enrollment.status == "ACTIVE"
        ).all()
        student_ids = [e[0] for e in enrollments]
        return await cls.notify_users(student_ids, title, message, notif_type, meta)

    @classmethod
    async def notify_admins(
        cls,
        db: Session,
        title: str,
        message: str,
        notif_type: str,
        metadata: Optional[dict] = None
    ) -> List[dict]:
        """Notify all system administrators."""
        from app.models.sql_models import User, Role
        admins = db.query(User.id).join(Role, User.role_id == Role.id).filter(
            Role.name == "ADMIN",
            User.is_active == True
        ).all()
        admin_ids = [a[0] for a in admins]
        return await cls.notify_users(admin_ids, title, message, notif_type, metadata)

    @staticmethod
    async def get_user_notifications(
        user_id: int, 
        limit: int = 50, 
        unread_only: bool = False,
        notif_type: Optional[str] = None
    ) -> List[dict]:
        """Fetch user notifications from MongoDB with optional filtering."""
        try:
            db = get_mongo_db()
            if db is not None:
                query: Dict[str, Any] = {"user_id": user_id}
                if unread_only:
                    query["is_read"] = False
                if notif_type and notif_type.strip():
                    query["type"] = notif_type.strip()

                cursor = db.notifications.find(query).sort("created_at", -1).limit(limit)
                results = []
                async for item in cursor:
                    item["id"] = str(item["_id"])
                    del item["_id"]
                    results.append(item)
                return results
        except Exception as e:
            logger.warning(f"Error reading notifications from MongoDB: {e}")
        return []

    @staticmethod
    async def get_unread_count(user_id: int) -> int:
        """Get count of unread notifications from MongoDB."""
        try:
            db = get_mongo_db()
            if db is not None:
                return await db.notifications.count_documents({"user_id": user_id, "is_read": False})
        except Exception as e:
            logger.warning(f"Error counting unread notifications: {e}")
        return 0

    @classmethod
    async def mark_as_read(cls, notification_id: str, user_id: int) -> bool:
        """Mark single notification as read in MongoDB and broadcast updated count."""
        modified = False
        try:
            db = get_mongo_db()
            if db is not None and ObjectId.is_valid(notification_id):
                res = await db.notifications.update_one(
                    {"_id": ObjectId(notification_id), "user_id": user_id},
                    {"$set": {"is_read": True}}
                )
                modified = res.modified_count > 0
        except Exception as e:
            logger.warning(f"Failed to mark notification read: {e}")

        unread_count = await cls.get_unread_count(user_id)
        event_payload = {
            "event": "NOTIFICATION_READ",
            "user_id": user_id,
            "notification_id": notification_id,
            "unread_count": unread_count
        }
        await publish_event("lms_notifications", event_payload)
        await cls.broadcast_to_user(user_id, event_payload)
        return modified

    @classmethod
    async def mark_all_as_read(cls, user_id: int) -> int:
        """Mark all unread notifications as read for user in MongoDB."""
        count = 0
        try:
            db = get_mongo_db()
            if db is not None:
                res = await db.notifications.update_many(
                    {"user_id": user_id, "is_read": False},
                    {"$set": {"is_read": True}}
                )
                count = res.modified_count
        except Exception as e:
            logger.warning(f"Failed to mark all notifications read: {e}")

        event_payload = {
            "event": "ALL_NOTIFICATIONS_READ",
            "user_id": user_id,
            "unread_count": 0,
            "marked_count": count
        }
        await publish_event("lms_notifications", event_payload)
        await cls.broadcast_to_user(user_id, event_payload)
        return count

    @classmethod
    async def check_assignments_due_soon(cls, db: Session, hours_ahead: int = 24) -> int:
        """Find published assignments due within `hours_ahead` and notify enrolled students who haven't submitted."""
        from app.models.sql_models import Assignment, Enrollment, Submission
        now = datetime.utcnow()
        due_threshold = now + timedelta(hours=hours_ahead)

        assignments = db.query(Assignment).filter(
            Assignment.status == "PUBLISHED",
            Assignment.due_date.isnot(None),
            Assignment.due_date > now,
            Assignment.due_date <= due_threshold
        ).all()

        notifications_sent = 0
        for a in assignments:
            # Get enrolled students
            enrollments = db.query(Enrollment.student_id).filter(
                Enrollment.course_id == a.course_id,
                Enrollment.status == "ACTIVE"
            ).all()

            for (student_id,) in enrollments:
                # Check if already submitted
                has_submitted = db.query(Submission.id).filter(
                    Submission.assignment_id == a.id,
                    Submission.student_id == student_id
                ).first() is not None

                if not has_submitted:
                    due_str = a.due_date.strftime("%b %d, %H:%M UTC") if a.due_date else "soon"
                    await cls.create_notification(
                        user_id=student_id,
                        title=f"Due Soon: {a.title}",
                        message=f"'{a.title}' in {a.course.code if a.course else 'your course'} is due {due_str}. Please submit before the deadline.",
                        notif_type="ASSIGNMENT_DUE_SOON",
                        metadata={
                            "assignment_id": a.id,
                            "course_id": a.course_id,
                            "due_date": a.due_date.isoformat() if a.due_date else None,
                            "target_tab": "assignments"
                        }
                    )
                    notifications_sent += 1

        return notifications_sent

    @staticmethod
    async def create_announcement(course_id: int, title: str, content: str, author_name: str, course_title: Optional[str] = None) -> dict:
        """Create announcement in MongoDB and notify students via Redis."""
        doc = {
            "course_id": course_id,
            "course_title": course_title,
            "title": title,
            "content": content,
            "author_name": author_name,
            "created_at": datetime.utcnow()
        }
        try:
            db = get_mongo_db()
            if db is not None:
                res = await db.announcements.insert_one(doc)
                doc["id"] = str(res.inserted_id)
                if "_id" in doc:
                    del doc["_id"]
        except Exception as e:
            logger.warning(f"MongoDB announcement error: {e}")
            doc["id"] = "announcement_fallback_id"

        await publish_event("lms_announcements", {
            "event": "NEW_ANNOUNCEMENT",
            "course_id": course_id,
            "title": title,
            "author": author_name
        })
        return doc

    @staticmethod
    async def get_course_announcements(course_id: int, limit: int = 10) -> List[dict]:
        try:
            db = get_mongo_db()
            if db is not None:
                cursor = db.announcements.find({"course_id": course_id}).sort("created_at", -1).limit(limit)
                results = []
                async for item in cursor:
                    item["id"] = str(item["_id"])
                    del item["_id"]
                    results.append(item)
                return results
        except Exception as e:
            logger.warning(f"Error fetching announcements: {e}")
        return []

    @staticmethod
    async def log_activity(user_id: int, user_name: str, action: str, details: Optional[str] = None) -> None:
        """Log user activity to MongoDB."""
        try:
            db = get_mongo_db()
            if db is not None:
                await db.activity_logs.insert_one({
                    "user_id": user_id,
                    "user_name": user_name,
                    "action": action,
                    "details": details,
                    "timestamp": datetime.utcnow()
                })
        except Exception as e:
            logger.debug(f"Activity logging skipped: {e}")

    @staticmethod
    async def get_recent_activities(limit: int = 25) -> List[dict]:
        try:
            db = get_mongo_db()
            if db is not None:
                cursor = db.activity_logs.find().sort("timestamp", -1).limit(limit)
                results = []
                async for item in cursor:
                    item["id"] = str(item["_id"])
                    del item["_id"]
                    results.append(item)
                return results
        except Exception as e:
            logger.warning(f"Failed to fetch activity logs: {e}")
        return []

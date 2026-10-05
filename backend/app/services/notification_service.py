import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from app.database.mongo import get_mongo_db
from app.database.redis_client import publish_event

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    async def create_notification(
        user_id: int, 
        title: str, 
        message: str, 
        notif_type: str = "SYSTEM", 
        metadata: Optional[dict] = None
    ) -> dict:
        """Create notification in MongoDB and publish event to Redis."""
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
        except Exception as e:
            logger.warning(f"Failed to persist notification in MongoDB: {e}")
            doc["id"] = "temp_fallback_id"

        # Publish to Redis channel
        await publish_event("lms_notifications", {
            "event": "NEW_NOTIFICATION",
            "user_id": user_id,
            "title": title,
            "message": message,
            "type": notif_type
        })
        
        return doc

    @staticmethod
    async def get_user_notifications(user_id: int, limit: int = 20) -> List[dict]:
        """Fetch user notifications from MongoDB."""
        try:
            db = get_mongo_db()
            if db is not None:
                cursor = db.notifications.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
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
    async def mark_as_read(notification_id: str, user_id: int) -> bool:
        """Mark notification as read in MongoDB."""
        try:
            db = get_mongo_db()
            if db is not None and ObjectId.is_valid(notification_id):
                res = await db.notifications.update_one(
                    {"_id": ObjectId(notification_id), "user_id": user_id},
                    {"$set": {"is_read": True}}
                )
                return res.modified_count > 0
        except Exception as e:
            logger.warning(f"Failed to mark notification read: {e}")
        return False

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

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from app.config import settings

logger = logging.getLogger(__name__)

mongo_client: AsyncIOMotorClient = None
mongo_db = None
sync_mongo_client: MongoClient = None


def get_mongo_db():
    global mongo_client, mongo_db
    if mongo_db is None:
        try:
            mongo_client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
            mongo_db = mongo_client[settings.MONGODB_DB_NAME]
            logger.info("MongoDB Async connection established")
        except Exception as e:
            logger.warning(f"MongoDB connection error: {e}")
    return mongo_db


def get_sync_mongo():
    global sync_mongo_client
    if sync_mongo_client is None:
        try:
            sync_mongo_client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
        except Exception as e:
            logger.warning(f"MongoDB Sync connection error: {e}")
    return sync_mongo_client[settings.MONGODB_DB_NAME] if sync_mongo_client else None


async def init_mongo_indexes():
    """Create indexes for notifications, announcements, and activity logs."""
    try:
        db = get_mongo_db()
        if db is not None:
            await db.notifications.create_index([("user_id", 1), ("created_at", -1)])
            await db.notifications.create_index("is_read")
            await db.announcements.create_index([("course_id", 1), ("created_at", -1)])
            await db.activity_logs.create_index([("timestamp", -1)])
            await db.activity_logs.create_index("user_id")
            logger.info("MongoDB indexes successfully created")
    except Exception as e:
        logger.warning(f"Could not create MongoDB indexes: {e}")

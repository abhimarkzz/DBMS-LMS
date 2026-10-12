import logging
from typing import Optional, Dict, Any
from bson import ObjectId
from bson.binary import Binary
from app.database.mongo import get_sync_mongo

logger = logging.getLogger(__name__)


class FileStorageService:
    """
    Manages raw binary study material files in MongoDB.
    Keeps binary blobs completely decoupled from PostgreSQL relational rows.
    """

    @classmethod
    def store_file(
        cls,
        course_id: int,
        filename: str,
        content_type: str,
        data: bytes,
        uploaded_by: Optional[int] = None
    ) -> str:
        """Store binary file data in MongoDB and return the storage document ID."""
        mongo = get_sync_mongo()
        if mongo is None:
            logger.warning("MongoDB not connected for file storage. Generating local reference ID.")
            import uuid
            return f"local_{uuid.uuid4().hex}"

        doc = {
            "course_id": course_id,
            "filename": filename,
            "content_type": content_type,
            "file_size": len(data),
            "binary_data": Binary(data),
            "uploaded_by": uploaded_by
        }
        res = mongo.study_material_files.insert_one(doc)
        return str(res.inserted_id)

    @classmethod
    def get_file(cls, storage_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored file binary data and metadata from MongoDB."""
        mongo = get_sync_mongo()
        if mongo is None:
            return None

        try:
            doc = mongo.study_material_files.find_one({"_id": ObjectId(storage_id)})
            if not doc:
                return None
            return {
                "filename": doc.get("filename", "material"),
                "content_type": doc.get("content_type", "application/octet-stream"),
                "file_size": doc.get("file_size", 0),
                "data": bytes(doc.get("binary_data", b""))
            }
        except Exception as e:
            logger.error(f"Error fetching file with storage_id {storage_id}: {e}")
            return None

    @classmethod
    def delete_file(cls, storage_id: str) -> bool:
        """Delete stored file from MongoDB."""
        mongo = get_sync_mongo()
        if mongo is None:
            return False

        try:
            res = mongo.study_material_files.delete_one({"_id": ObjectId(storage_id)})
            return res.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting file with storage_id {storage_id}: {e}")
            return False

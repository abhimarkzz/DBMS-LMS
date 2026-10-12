from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.postgres import get_db
from app.database.mongo import get_mongo_db
from app.database.redis_client import get_redis_client
from app.services.auth_service import require_roles
from app.services.notification_service import NotificationService
from app.models.sql_models import User, Course, Assignment, Submission, NoteChunk

router = APIRouter(prefix="/api/admin", tags=["Admin & System Health"])


@router.get("/overview")
async def get_admin_platform_overview(
    _: User = Depends(require_roles(["ADMIN"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    total_users = db.query(User).count()
    total_courses = db.query(Course).count()
    total_assignments = db.query(Assignment).count()
    total_submissions = db.query(Submission).count()
    total_vector_chunks = db.query(NoteChunk).count()

    activities = await NotificationService.get_recent_activities(limit=15)

    return {
        "metrics": {
            "total_users": total_users,
            "total_courses": total_courses,
            "total_assignments": total_assignments,
            "total_submissions": total_submissions,
            "total_vector_chunks": total_vector_chunks
        },
        "recent_activities": activities
    }


@router.get("/health")
async def get_system_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Check health of all polyglot persistence components."""
    health_status: Dict[str, Any] = {
        "status": "HEALTHY",
        "components": {}
    }

    # 1. PostgreSQL check
    try:
        db.execute(text("SELECT 1;"))
        health_status["components"]["postgresql"] = {"status": "UP", "message": "Relational DB responding"}
    except Exception as e:
        health_status["components"]["postgresql"] = {"status": "DOWN", "error": str(e)}
        health_status["status"] = "DEGRADED"

    # 2. pgvector check
    try:
        row = db.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")).fetchone()
        if row:
            health_status["components"]["pgvector"] = {"status": "UP", "version": row[0]}
        else:
            health_status["components"]["pgvector"] = {"status": "NOT_INSTALLED"}
    except Exception as e:
        health_status["components"]["pgvector"] = {"status": "DOWN", "error": str(e)}

    # 3. MongoDB check
    try:
        mongo = get_mongo_db()
        if mongo is not None:
            await mongo.command("ping")
            health_status["components"]["mongodb"] = {"status": "UP", "message": "Document DB responding"}
        else:
            health_status["components"]["mongodb"] = {"status": "DOWN", "message": "Client uninitialized"}
    except Exception as e:
        health_status["components"]["mongodb"] = {"status": "DOWN", "error": str(e)}

    # 4. Redis check
    try:
        redis = await get_redis_client()
        if redis:
            await redis.ping()
            health_status["components"]["redis"] = {"status": "UP", "message": "Cache / Pub-Sub responding"}
        else:
            health_status["components"]["redis"] = {"status": "FALLBACK", "message": "Operating in local in-memory fallback"}
    except Exception as e:
        health_status["components"]["redis"] = {"status": "FALLBACK", "error": str(e)}

    return health_status

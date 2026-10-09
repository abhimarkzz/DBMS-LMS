from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.ai_search_schema import (
    NoteUploadRequest,
    AISearchRequest,
    AISearchResponse,
    SearchMode,
    ResearchDepth,
    FreshnessPreference
)
from app.services.ai_search_service import AISearchService
from app.services.course_service import CourseService
from app.services.auth_service import get_current_user, require_roles
from app.services.notification_service import NotificationService
from app.models.sql_models import User

router = APIRouter(prefix="/api/search", tags=["AI Research Engine"])


@router.post("", response_model=AISearchResponse)
async def unified_ai_research_endpoint(
    payload: AISearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Multi-Mode AI Research Engine:
    - Mode A (COURSE_NOTES): pgvector HNSW semantic search + Course RAG synthesis
    - Mode B (WEB_RESEARCH): Live Groq Web Research (browser_search) with citations & freshness
    - Mode C (HYBRID): Synthesizes curriculum course notes with live web technical evidence
    """
    from app.models.sql_models import Enrollment

    norm_mode = SearchMode.normalize(payload.mode.value if hasattr(payload.mode, "value") else str(payload.mode))
    norm_depth = ResearchDepth.normalize(payload.depth.value if hasattr(payload.depth, "value") else str(payload.depth))
    norm_freshness = FreshnessPreference.normalize(payload.freshness.value if hasattr(payload.freshness, "value") else str(payload.freshness))

    allowed_course_ids = None
    if current_user.role.name == "STUDENT" and norm_mode in (SearchMode.COURSE_NOTES, SearchMode.HYBRID):
        enrolled = db.query(Enrollment.course_id).filter(
            Enrollment.student_id == current_user.id,
            Enrollment.status == "ACTIVE"
        ).all()
        enrolled_ids = [row[0] for row in enrolled]

        if payload.course_id:
            if payload.course_id not in enrolled_ids:
                if norm_mode == SearchMode.COURSE_NOTES:
                    return {
                        "query": payload.query,
                        "mode": norm_mode.value,
                        "depth": norm_depth.value,
                        "freshness": norm_freshness.value,
                        "answer": "No relevant material was found in your uploaded course content. (This topic is not available in the uploaded course content.)",
                        "direct_answer": "No relevant material found in enrolled courses.",
                        "key_findings": [],
                        "grounded": False,
                        "sources": [],
                        "course_sources": [],
                        "web_sources": [],
                        "citations": [],
                        "search_status": "NO_RESULTS",
                        "model_used": "permission-filter",
                        "latency_ms": 0.0
                    }
                allowed_course_ids = []
            else:
                allowed_course_ids = [payload.course_id]
        else:
            if not enrolled_ids and norm_mode == SearchMode.COURSE_NOTES:
                return {
                    "query": payload.query,
                    "mode": norm_mode.value,
                    "depth": norm_depth.value,
                    "freshness": norm_freshness.value,
                    "answer": "No relevant material was found in your uploaded course content. (This topic is not available in the uploaded course content.)",
                    "direct_answer": "No enrolled courses found for student.",
                    "key_findings": [],
                    "grounded": False,
                    "sources": [],
                    "course_sources": [],
                    "web_sources": [],
                    "citations": [],
                    "search_status": "NO_RESULTS",
                    "model_used": "permission-filter",
                    "latency_ms": 0.0
                }
            allowed_course_ids = enrolled_ids

    ai_service = AISearchService(db)
    result = await ai_service.execute_research(
        query=payload.query,
        mode=norm_mode.value,
        depth=norm_depth.value,
        freshness=norm_freshness.value,
        course_id=payload.course_id,
        top_k=payload.top_k,
        allowed_course_ids=allowed_course_ids
    )

    req_mode_str = payload.mode.value if hasattr(payload.mode, "value") else str(payload.mode)
    result["mode"] = req_mode_str

    # Log user research activity to MongoDB
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action=f"AI_RESEARCH_{norm_mode.value.upper()}",
        details=f"Query: '{payload.query[:60]}' | Mode: {norm_mode.value} | Status: {result.get('search_status')}"
    )

    return result


@router.post("/notes/upload", status_code=status.HTTP_201_CREATED)
async def upload_and_index_note(
    payload: NoteUploadRequest,
    current_user: User = Depends(require_roles(["TEACHER", "ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Teacher uploads course notes:
    1. Stored in relational study_materials table
    2. Automatically chunked into overlapping passages
    3. 768-dimensional embeddings generated
    4. Stored in note_chunks table indexed with pgvector HNSW
    """
    course_service = CourseService(db)
    material = await course_service.add_study_material(
        course_id=payload.course_id,
        title=payload.title,
        content=payload.content,
        material_type=payload.material_type
    )

    # Notify students enrolled in this course
    await NotificationService.create_announcement(
        course_id=payload.course_id,
        title=f"New Study Material: {payload.title}",
        content=f"Instructor {current_user.full_name} added new study material available for AI Smart Notes Search.",
        author_name=current_user.full_name
    )

    return {
        "status": "SUCCESS",
        "material_id": material.id,
        "course_id": material.course_id,
        "title": material.title,
        "message": "Study material successfully saved, chunked, embedded, and indexed into pgvector."
    }

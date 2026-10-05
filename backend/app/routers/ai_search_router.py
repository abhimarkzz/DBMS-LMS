from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.postgres import get_db
from app.schemas.ai_search_schema import NoteUploadRequest, AISearchRequest, AISearchResponse
from app.services.ai_search_service import AISearchService
from app.services.course_service import CourseService
from app.services.auth_service import get_current_user, require_roles
from app.services.notification_service import NotificationService
from app.models.sql_models import User

router = APIRouter(prefix="/api/search", tags=["AI Smart Notes Search"])


@router.post("", response_model=AISearchResponse)
async def semantic_search_and_grounded_rag(
    payload: AISearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    RAG Semantic Vector Search:
    1. Query embedding generated via Gemini or semantic fallback
    2. Vector cosine distance similarity search executed in PostgreSQL via pgvector
    3. Top-k relevant note chunks retrieved
    4. Grounded answer synthesized using Gemini with strict course note constraints
    5. Returns grounded response and matched citations
    """
    ai_service = AISearchService(db)
    result = await ai_service.search_and_generate(
        query=payload.query,
        course_id=payload.course_id,
        top_k=payload.top_k
    )

    # Log student question activity
    await NotificationService.log_activity(
        user_id=current_user.id,
        user_name=current_user.full_name,
        action="AI_NOTES_SEARCH",
        details=f"Query: '{payload.query[:60]}' - Grounded: {result['grounded']}"
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

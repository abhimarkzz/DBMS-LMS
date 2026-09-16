from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from uuid import UUID
import uuid

from app.db.database import get_db
from app.db.models import CourseMaterial, MaterialChunk, MaterialType, MaterialStatus
from app.schemas.search import SearchRequest, SearchResponse, SearchResultChunk, MaterialUploadResponse
from app.services.pdf_processor import extract_text_from_pdf, chunk_text
from app.services.embedding_service import embedding_provider

router = APIRouter(prefix="/api/v1", tags=["AI Search"])

@router.post("/courses/{course_id}/materials", response_model=MaterialUploadResponse)
async def upload_material(
    course_id: UUID,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Uploads a PDF material, extracts text, chunks it, generates embeddings, 
    and stores it in pgvector.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # 1. Read file
    content = await file.read()
    file_size = len(content)
    
    # 2. Create Material record
    material = CourseMaterial(
        course_id=course_id,
        uploaded_by=uuid.uuid4(),  # Mocked user ID; normally extracted from JWT
        title=title,
        material_type=MaterialType.PDF,
        file_name=file.filename,
        storage_name=f"{uuid.uuid4()}.pdf",
        file_url="mock/url",
        file_size_bytes=file_size,
        mime_type=file.content_type,
        description=description,
        status=MaterialStatus.PROCESSING
    )
    db.add(material)
    db.flush() # get material_id

    try:
        # 3. Extract and chunk
        pages = extract_text_from_pdf(content)
        chunks = chunk_text(pages)
        
        # 4. Generate embeddings and store
        for i, chunk_data in enumerate(chunks):
            embedding = embedding_provider.embed_text(chunk_data["content"])
            
            chunk_record = MaterialChunk(
                material_id=material.material_id,
                chunk_number=i + 1,
                content=chunk_data["content"],
                page_number=chunk_data["page_number"],
                token_count=chunk_data["token_count"],
                embedding=embedding,
                embedding_model=embedding_provider.model,
                embedding_provider=embedding_provider.provider,
                embedding_dimension=embedding_provider.dimension
            )
            db.add(chunk_record)
        
        material.status = MaterialStatus.READY
        material.total_chunks = len(chunks)
        db.commit()
        
    except Exception as e:
        db.rollback()
        material.status = MaterialStatus.FAILED
        db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    return MaterialUploadResponse(
        material_id=material.material_id,
        course_id=course_id,
        file_name=file.filename,
        status=material.status.value,
        message="Upload and processing complete."
    )


@router.post("/search", response_model=SearchResponse)
def semantic_search(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Performs vector similarity search on the user's question, 
    but strictly filters by the provided course_ids (Authorization).
    """
    # 1. Embed the query
    query_embedding = embedding_provider.embed_text(request.query)
    
    # 2. Query pgvector (cosine similarity: <=>)
    #    We restrict the search to ONLY materials belonging to the specified course_ids
    results = db.query(
        MaterialChunk,
        CourseMaterial,
        MaterialChunk.embedding.cosine_distance(query_embedding).label("distance")
    ).join(CourseMaterial, MaterialChunk.material_id == CourseMaterial.material_id) \
     .filter(CourseMaterial.course_id.in_(request.course_ids)) \
     .order_by("distance") \
     .limit(request.top_k) \
     .all()

    # 3. Format response
    response_chunks = []
    for chunk, material, distance in results:
        # Convert distance to similarity score
        similarity = 1.0 - distance
        
        response_chunks.append(SearchResultChunk(
            chunk_id=chunk.chunk_id,
            material_id=chunk.material_id,
            course_id=material.course_id,
            title=material.title,
            content=chunk.content,
            page_number=chunk.page_number,
            similarity_score=similarity
        ))
        
    return SearchResponse(
        results=response_chunks,
        query_text=request.query
    )

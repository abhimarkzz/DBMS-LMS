from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID

class SearchRequest(BaseModel):
    query: str
    course_ids: List[UUID]
    top_k: int = 5

class SearchResultChunk(BaseModel):
    chunk_id: UUID
    material_id: UUID
    course_id: UUID
    title: str
    content: str
    page_number: Optional[int] = None
    similarity_score: float

class SearchResponse(BaseModel):
    results: List[SearchResultChunk]
    query_text: str

class MaterialUploadResponse(BaseModel):
    material_id: UUID
    course_id: UUID
    file_name: str
    status: str
    message: str

class IndexRequest(BaseModel):
    pass

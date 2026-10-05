from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NoteUploadRequest(BaseModel):
    course_id: int
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=20)
    material_type: str = "NOTES"


class ChunkResult(BaseModel):
    chunk_id: int
    material_id: int
    material_title: str
    course_id: int
    course_title: str
    chunk_index: int
    chunk_text: str
    similarity_score: float


class AISearchRequest(BaseModel):
    course_id: Optional[int] = None
    query: str = Field(default="", max_length=1000)
    top_k: int = Field(default=3, ge=1, le=10)


class AISearchResponse(BaseModel):
    query: str
    answer: str
    grounded: bool
    sources: List[ChunkResult] = []
    model_used: str
    latency_ms: Optional[float] = None

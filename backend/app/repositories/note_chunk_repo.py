from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.sql_models import NoteChunk, StudyMaterial, Course


class NoteChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_chunk(self, material_id: int, course_id: int, chunk_index: int, chunk_text: str, embedding: Optional[List[float]]) -> NoteChunk:
        chunk = NoteChunk(
            material_id=material_id,
            course_id=course_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text.strip(),
            embedding=embedding
        )
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def search_similar_chunks(
        self, 
        query_vector: List[float], 
        course_id: Optional[int] = None, 
        top_k: int = 3,
        keyword_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector cosine similarity search in PostgreSQL using pgvector <=> operator.
        Cosine distance ranges from 0 (identical) to 2 (opposite).
        Cosine similarity = 1 - cosine_distance.
        """
        # Vector format for pgvector literal: '[0.1, 0.2, ...]'
        vector_str = "[" + ",".join(str(float(x)) for x in query_vector) + "]"
        
        where_clauses = ["nc.embedding IS NOT NULL"]
        params: Dict[str, Any] = {"vec": vector_str, "top_k": top_k}

        if course_id:
            where_clauses.append("nc.course_id = :course_id")
            params["course_id"] = course_id

        where_sql = " AND ".join(where_clauses)

        # Pure vector cosine similarity is the primary retrieval mechanism
        sql = text(f"""
            SELECT 
                nc.id AS chunk_id,
                nc.material_id,
                sm.title AS material_title,
                nc.course_id,
                c.title AS course_title,
                nc.chunk_index,
                nc.chunk_text,
                ROUND(CAST(1 - (nc.embedding <=> CAST(:vec AS vector)) AS numeric), 4) AS similarity_score
            FROM note_chunks nc
            JOIN study_materials sm ON nc.material_id = sm.id
            JOIN courses c ON nc.course_id = c.id
            WHERE {where_sql}
            ORDER BY nc.embedding <=> CAST(:vec AS vector) ASC
            LIMIT :top_k;
        """)

        try:
            rows = self.db.execute(sql, params).mappings().all()
            return [dict(r) for r in rows]
        except Exception as e:
            self.db.rollback()
            return []

    def count_chunks_for_course(self, course_id: int) -> int:
        return self.db.query(NoteChunk).filter(NoteChunk.course_id == course_id).count()

    def get_all_chunks(self, limit: int = 50) -> List[NoteChunk]:
        return self.db.query(NoteChunk).limit(limit).all()

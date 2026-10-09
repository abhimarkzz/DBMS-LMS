from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.sql_models import NoteChunk, StudyMaterial, Course


class NoteChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_chunk(
        self,
        material_id: int,
        course_id: int,
        chunk_index: int,
        chunk_text: str,
        embedding: Optional[List[float]],
        chunk_metadata: Optional[str] = None
    ) -> NoteChunk:
        chunk = NoteChunk(
            material_id=material_id,
            course_id=course_id,
            chunk_index=chunk_index,
            chunk_text=chunk_text.strip(),
            embedding=embedding,
            chunk_metadata=chunk_metadata
        )
        self.db.add(chunk)
        self.db.commit()
        self.db.refresh(chunk)
        return chunk

    def delete_chunks_by_material(self, material_id: int) -> int:
        deleted = self.db.query(NoteChunk).filter(NoteChunk.material_id == material_id).delete()
        self.db.commit()
        return deleted

    def search_similar_chunks(
        self, 
        query_vector: List[float], 
        course_id: Optional[int] = None, 
        top_k: int = 3,
        keyword_filter: Optional[str] = None,
        allowed_course_ids: Optional[List[int]] = None
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
        elif allowed_course_ids is not None:
            if not allowed_course_ids:
                return []
            where_clauses.append("nc.course_id = ANY(:allowed_course_ids)")
            params["allowed_course_ids"] = allowed_course_ids

        where_sql = " AND ".join(where_clauses)

        # Calibrated hybrid ranking: semantic cosine distance with subtle keyword boost
        order_sql = "(nc.embedding <=> CAST(:vec AS vector))"
        score_sql = "ROUND(CAST(1 - (nc.embedding <=> CAST(:vec AS vector)) AS numeric), 4)"
        if keyword_filter:
            import re
            stopwords = {
                "what", "where", "when", "which", "who", "whom", "this", "that", "these", "those",
                "have", "has", "had", "does", "doing", "would", "should", "could", "about", "into",
                "through", "during", "before", "after", "above", "below", "from", "down", "with",
                "explain", "describe", "tell", "please", "for", "the", "and", "can", "are", "were",
                "was", "been", "being", "how", "why", "any", "some", "all", "its", "their", "more", "give"
            }
            # Only use specific content terms (length >= 4)
            tokens = [w for w in re.findall(r'\b[a-zA-Z]{4,}\b', keyword_filter.lower()) if w not in stopwords]
            if tokens:
                boost_terms = []
                for idx, t in enumerate(tokens[:4]):
                    p_name = f"kw_{idx}"
                    params[p_name] = f"%{t}%"
                    # Gentle boost of 0.08 per specific keyword match
                    boost_terms.append(f"(CASE WHEN nc.chunk_text ILIKE :{p_name} OR sm.title ILIKE :{p_name} THEN 0.08 ELSE 0 END)")
                combined_boost = " + ".join(boost_terms)
                order_sql = f"(nc.embedding <=> CAST(:vec AS vector)) - ({combined_boost})"
                score_sql = f"ROUND(CAST(LEAST(0.9999, 1 - (nc.embedding <=> CAST(:vec AS vector)) + ({combined_boost})) AS numeric), 4)"

        sql = text(f"""
            SELECT 
                nc.id AS chunk_id,
                nc.material_id,
                sm.title AS material_title,
                nc.course_id,
                c.title AS course_title,
                nc.chunk_index,
                nc.chunk_text,
                {score_sql} AS similarity_score
            FROM note_chunks nc
            JOIN study_materials sm ON nc.material_id = sm.id
            JOIN courses c ON nc.course_id = c.id
            WHERE {where_sql}
            ORDER BY {order_sql} ASC
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

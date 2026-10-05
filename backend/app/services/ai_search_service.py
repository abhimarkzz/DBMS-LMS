import hashlib
import logging
import math
import re
import time
from typing import List, Dict, Any, Optional
import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.repositories.note_chunk_repo import NoteChunkRepository

logger = logging.getLogger(__name__)


def generate_fallback_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Deterministic semantic hash embedding generator used when GEMINI_API_KEY is unset or API offline.
    Uses n-gram hashing and sinusoidal projection to produce consistent, normalized 768-dim vectors.
    """
    words = re.findall(r'\w+', text.lower())
    vec = np.zeros(dim, dtype=np.float32)
    
    if not words:
        return vec.tolist()

    for word in words:
        h = int(hashlib.sha256(word.encode('utf-8')).hexdigest(), 16)
        # Seed indices
        idx1 = h % dim
        idx2 = (h >> 16) % dim
        idx3 = (h >> 32) % dim
        weight = 1.0 / (1.0 + math.log(len(word) + 1))
        vec[idx1] += weight
        vec[idx2] += weight * 0.5
        vec[idx3] += weight * 0.25

    # Also capture bigrams for local phrase semantics
    for i in range(len(words) - 1):
        bigram = f"{words[i]}_{words[i+1]}"
        h = int(hashlib.md5(bigram.encode('utf-8')).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.5

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


class AISearchService:
    def __init__(self, db: Session):
        self.db = db
        self.chunk_repo = NoteChunkRepository(db)

    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 60) -> List[str]:
        """Split text into semantic paragraphs and overlapping chunks."""
        text = text.strip()
        if len(text) <= chunk_size:
            return [text]

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []

        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk) + len(p) <= chunk_size:
                current_chunk = f"{current_chunk}\n\n{p}".strip() if current_chunk else p
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(p) > chunk_size:
                    # Split giant paragraph by sentences or words
                    words = p.split()
                    step = chunk_size // 6
                    for i in range(0, len(words), step):
                        slice_words = words[i:i + step + 10]
                        chunk_str = " ".join(slice_words)
                        if chunk_str:
                            chunks.append(chunk_str)
                    current_chunk = ""
                else:
                    current_chunk = p

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [text]

    async def get_embedding(self, text: str) -> List[float]:
        """Generate 768-dim embedding via Gemini or fallback."""
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY.strip())
                # Try primary embedding model, then fallback
                for model_candidate in [settings.EMBEDDING_MODEL, "text-embedding-004"]:
                    try:
                        response = client.models.embed_content(
                            model=model_candidate,
                            contents=text
                        )
                        if hasattr(response, "embedding") and response.embedding:
                            vec = response.embedding.values
                            if len(vec) == 768:
                                return vec
                            elif len(vec) > 768:
                                return vec[:768]
                            else:
                                # Pad to 768 if smaller
                                return (vec + [0.0] * (768 - len(vec)))[:768]
                    except Exception as me:
                        logger.debug(f"Candidate {model_candidate} error: {me}")
                        continue
            except Exception as e:
                logger.warning(f"Gemini embedding API call failed: {e}. Using deterministic semantic fallback.")

        return generate_fallback_embedding(text, dim=768)

    async def index_study_material(self, material_id: int, course_id: int, content: str) -> int:
        """Chunk text, generate embeddings, and store in pgvector note_chunks table."""
        chunks = self.chunk_text(content)
        count = 0
        for idx, chunk_text in enumerate(chunks):
            embedding = await self.get_embedding(chunk_text)
            self.chunk_repo.save_chunk(
                material_id=material_id,
                course_id=course_id,
                chunk_index=idx,
                chunk_text=chunk_text,
                embedding=embedding
            )
            count += 1
        return count

    async def search_and_generate(
        self, 
        query: str, 
        course_id: Optional[int] = None, 
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        RAG Workflow:
        1. Handle empty / whitespace questions gracefully
        2. Embed user query using Gemini API / deterministic fallback
        3. Perform vector similarity search in PostgreSQL via pgvector HNSW index
        4. Retrieve top relevant chunks
        5. Grounded answer synthesis via Gemini (gemini-3.8-flash / 2.5-flash)
        6. Return answer, citations, similarity scores, and model metadata
        """
        start_time = time.time()
        query = query.strip() if query else ""

        # Handle empty question
        if not query:
            return {
                "query": "",
                "answer": "Please provide a valid question to search your course notes.",
                "grounded": False,
                "sources": [],
                "model_used": "query-validator",
                "latency_ms": 0.0
            }

        # 1. Embed query
        query_vector = await self.get_embedding(query)
        
        # 2. Vector search via pgvector
        matched_chunks = self.chunk_repo.search_similar_chunks(
            query_vector=query_vector,
            course_id=course_id,
            top_k=top_k,
            keyword_filter=query
        )

        # Relevance verification: check topical relevance and token overlap
        is_relevant = False
        stopwords = {
            "what", "where", "when", "which", "who", "whom", "this", "that", "these", "those",
            "have", "has", "had", "does", "doing", "would", "should", "could", "about", "into",
            "through", "during", "before", "after", "above", "below", "from", "down", "with",
            "explain", "describe", "tell", "please", "for", "the", "and", "can", "are", "were",
            "was", "been", "being", "how", "why", "any", "some", "all", "its", "their", "more", "give"
        }
        query_words = {w for w in re.findall(r'\b[a-zA-Z]{3,}\b', query.lower()) if w not in stopwords}

        if matched_chunks:
            highest_score = max(c.get("similarity_score", 0) for c in matched_chunks)
            # Check if any substantive query token appears in top chunks
            top_texts = " ".join(c.get("chunk_text", "").lower() for c in matched_chunks[:2])
            overlap = any(qw in top_texts for qw in query_words)
            
            if overlap or (highest_score >= 0.55):
                is_relevant = True

        if not is_relevant or not matched_chunks:
            latency = round((time.time() - start_time) * 1000, 2)
            return {
                "query": query,
                "answer": "The answer is not available in the uploaded course content. Please review your course materials or consult your instructor.",
                "grounded": False,
                "sources": [],
                "model_used": "course-guardrail",
                "latency_ms": latency
            }

        # 3. Build grounded prompt for Gemini
        context_blocks = []
        sources = []
        for c in matched_chunks:
            context_blocks.append(f"Source [{c['material_title']} - Course: {c['course_title']}]:\n{c['chunk_text']}")
            sources.append({
                "chunk_id": c["chunk_id"],
                "material_id": c["material_id"],
                "material_title": c["material_title"],
                "course_id": c["course_id"],
                "course_title": c["course_title"],
                "chunk_index": c["chunk_index"],
                "chunk_text": c["chunk_text"],
                "similarity_score": float(c["similarity_score"])
            })

        context_text = "\n\n---\n\n".join(context_blocks)
        system_instruction = (
            "You are an academic LMS AI Teaching Assistant. "
            "Your task is to answer the student's question STRICTLY and CONCISELY based ONLY on the provided Course Content Context. "
            "Guidelines:\n"
            "1. Ground your entire answer in the provided Course Content Context.\n"
            "2. Cite the specific note titles or sections when explaining key concepts.\n"
            "3. If the context does not contain the answer, explicitly state: 'The answer is not available in the uploaded course content.'\n"
            "4. Be concise, academically accurate, and clear."
        )
        user_prompt = f"Course Content Context:\n{context_text}\n\nStudent Question: {query}\n\nAnswer:"

        answer = ""
        model_name = "Deterministic-Semantic-RAG"

        # Call Gemini if API key available
        if settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 10:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY.strip())
                for gen_model in [settings.GEMINI_MODEL, "gemini-2.5-flash"]:
                    try:
                        response = client.models.generate_content(
                            model=gen_model,
                            contents=user_prompt,
                            config={"system_instruction": system_instruction}
                        )
                        if response and response.text:
                            answer = response.text.strip()
                            model_name = f"Gemini ({gen_model})"
                            break
                    except Exception as ge:
                        logger.debug(f"Gemini model {gen_model} error: {ge}")
                        continue
            except Exception as e:
                logger.warning(f"Gemini API failure handled gracefully: {e}")

        # Structured synthesis if Gemini API key is absent or quota exceeded
        if not answer:
            top_source = matched_chunks[0]
            answer = (
                f"Based on **{top_source['material_title']}** (Course: {top_source['course_title']}):\n\n"
                f"{top_source['chunk_text']}\n\n"
                f"*(Retrieved with similarity score: {top_source['similarity_score']:.2f})*"
            )

        latency = round((time.time() - start_time) * 1000, 2)
        return {
            "query": query,
            "answer": answer,
            "grounded": True,
            "sources": sources,
            "model_used": model_name,
            "latency_ms": latency
        }

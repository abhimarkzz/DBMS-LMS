import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
import numpy as np
import httpx

from app.main import app
from app.database.postgres import SessionLocal
from app.models.sql_models import NoteChunk, Course
from app.services.embedding_service import embedding_engine, reindex_all_database_chunks
from app.services.groq_client import groq_client, GroqClient, classify_domain_credibility
from app.config import settings


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def get_token(client: TestClient, email: str = "alex@student.univ.edu", password: str = "Password123!"):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ============================================================================
# 1. VECTOR DIMENSION, NORMALIZATION, AND RE-INDEXING (768-DIM LOCAL EMBEDDING)
# ============================================================================

def test_vector_dimension_and_normalization():
    """[UNIT] Verifies that local embedding engine strictly generates 768-dim normalized vectors."""
    text = "Shortest path graph algorithms and Dijkstra priority queue"
    vec = embedding_engine.embed_text(text)
    assert isinstance(vec, list)
    assert len(vec) == 768
    # All elements must be floats
    assert all(isinstance(x, float) for x in vec)
    # Unit normalization check (L2 norm == 1.0)
    norm = np.linalg.norm(np.array(vec, dtype=np.float32))
    assert pytest.approx(norm, rel=1e-3) == 1.0


def test_local_embedding_consistency_and_determinism():
    """[UNIT] Verifies deterministic reproducibility: identical inputs produce identical 768-dim vectors."""
    text = "Operating system virtual memory paging and translation lookaside buffer"
    vec1 = embedding_engine.embed_text(text)
    vec2 = embedding_engine.embed_text(text)
    assert vec1 == vec2


def test_reindex_all_database_chunks():
    """[INTEGRATION] Verifies safe repeatable re-indexing of all existing chunks in PostgreSQL."""
    db = SessionLocal()
    try:
        res = reindex_all_database_chunks(db)
        assert res["status"] == "COMPLETED"
        assert res["total_chunks"] >= 10
        assert res["migrated_chunks"] == res["total_chunks"]
        assert res["dimension"] == 768
        assert res["hnsw_reindexed"] is True

        # Check in DB that all chunks have 768-dim vectors
        chunks = db.query(NoteChunk).all()
        for ch in chunks:
            assert ch.embedding is not None
            assert len(ch.embedding) == 768
    finally:
        db.close()


# ============================================================================
# 2. GROQ ANSWER GENERATION WITH RETRIEVED COURSE CONTEXT
# ============================================================================

@pytest.mark.asyncio
async def test_groq_generation_with_retrieved_course_context(client, monkeypatch):
    """[INTEGRATION] Verifies Groq chat completion generates educational grounded answer with citations."""
    token = get_token(client, "alex@student.univ.edu")

    # Mock groq_client.chat_completion to return simulated Groq response
    mock_resp = {
        "success": True,
        "content": (
            "Dijkstra's algorithm finds the shortest path from a single source vertex to all other vertices "
            "in a weighted graph with strictly non-negative edge weights.\n\n"
            "Key Points:\n"
            "- Maintains tentative distances in a priority queue.\n"
            "- Greedily settles the unvisited vertex with the minimum distance.\n"
            "- Runs in O((V + E) log V) with a binary min-heap."
        ),
        "model": "openai/gpt-oss-120b",
        "usage": {"prompt_tokens": 120, "completion_tokens": 85},
        "status_code": 200
    }

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "chat_completion", AsyncMock(return_value=mock_resp))

    res = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "How does Dijkstra algorithm find the shortest path in a weighted graph?",
            "mode": "COURSE_NOTES"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert "Dijkstra" in data["answer"]
    assert "Groq (openai/gpt-oss-120b)" in data["model_used"]
    assert len(data["course_sources"]) > 0
    assert len(data["citations"]) > 0


def test_course_note_exact_and_paraphrased_queries(client):
    """[INTEGRATION] Verifies both exact and paraphrased queries successfully retrieve course notes."""
    token = get_token(client, "alex@student.univ.edu")

    # Exact query
    res1 = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "How does Dijkstra algorithm find the shortest path in a weighted graph?",
            "mode": "COURSE_NOTES"
        }
    )
    assert res1.status_code == 200
    assert res1.json()["grounded"] is True
    assert len(res1.json()["course_sources"]) > 0

    # Paraphrased query
    res2 = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "Single source minimum cost path with non-negative edge weights and priority queue",
            "mode": "COURSE_NOTES"
        }
    )
    assert res2.status_code == 200
    assert res2.json()["grounded"] is True
    assert len(res2.json()["course_sources"]) > 0


def test_irrelevant_query_guardrail(client):
    """[INTEGRATION] Verifies irrelevant query triggers honest guardrail with grounded=False."""
    token = get_token(client, "alex@student.univ.edu")
    res = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "What is the secret recipe for baking artisanal sourdough bread with natural yeast starter?",
            "mode": "COURSE_NOTES"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "not available in the uploaded course content" in data["answer"].lower()
    assert len(data["course_sources"]) == 0


def test_empty_and_whitespace_questions(client):
    """[INTEGRATION] Verifies empty and whitespace queries return validation response."""
    token = get_token(client, "alex@student.univ.edu")
    res = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "    ", "mode": "COURSE_NOTES"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "valid question" in data["answer"].lower()


def test_unauthorized_course_access(client):
    """[SECURITY] Verifies student cannot search notes in a course they are not enrolled in."""
    token = get_token(client, "alex@student.univ.edu")
    res = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "Explain operating system deadlock detection algorithms",
            "course_id": 999999,  # Non-enrolled course ID
            "mode": "COURSE_NOTES"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert "no relevant material" in data["answer"].lower()


# ============================================================================
# 3. GROQ LIVE WEB RESEARCH & CITATIONS
# ============================================================================

def test_missing_groq_api_key_honest_degradation(client, monkeypatch):
    """[UNIT/INTEGRATION] Verifies honest notification when GROQ_API_KEY is not configured."""
    token = get_token(client, "alex@student.univ.edu")

    # Simulate unconfigured GROQ_API_KEY
    monkeypatch.setattr(groq_client, "is_configured", lambda: False)

    res = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "What are the latest developments in PostgreSQL 17 query optimizer?",
            "mode": "WEB_RESEARCH"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is False
    assert data["search_status"] == "UNAVAILABLE"
    assert "groq_api_key is not configured" in data["answer"].lower() or "unavailable" in data["answer"].lower()
    assert len(data["web_sources"]) == 0  # Does NOT invent fake citations!


def test_groq_web_research_with_browser_search_and_citations(client, monkeypatch):
    """[MOCKED] Verifies Groq web research returns genuine URLs, citations, and credibility categorization."""
    token = get_token(client, "alex@student.univ.edu")

    mock_web_result = {
        "status": "SUCCESS",
        "answer": (
            "PostgreSQL 17 includes major enhancements to memory management and query execution [1]. "
            "According to official release notes at https://www.postgresql.org/about/news/postgresql-17-released-2722/, "
            "vacuuming now uses a new internal memory structure that reduces memory consumption up to 20x [2]."
        ),
        "direct_answer": "PostgreSQL 17 optimizes query planning and memory utilization.",
        "key_findings": [
            "Vacuuming memory consumption reduced up to 20x.",
            "JSON_TABLE capability added conforming to SQL/JSON standard."
        ],
        "grounded": True,
        "web_sources": [
            {
                "title": "PostgreSQL 17 Released",
                "url": "https://www.postgresql.org/about/news/postgresql-17-released-2722/",
                "domain": "postgresql.org",
                "publication_date": None,
                "retrieval_date": "2026-10-09T04:00:00Z",
                "snippet": "Official release notes for PostgreSQL 17.",
                "source_type": "OFFICIAL_DOC",
                "relevance_score": 1.0
            }
        ],
        "citations": [
            {
                "source_id": "web-1",
                "source_title": "PostgreSQL 17 Released",
                "source_url": "https://www.postgresql.org/about/news/postgresql-17-released-2722/",
                "citation_text": "Vacuuming memory consumption",
                "source_type": "WEB"
            }
        ],
        "search_queries": ["PostgreSQL 17 new features official"],
        "model_used": "Groq Grounded (openai/gpt-oss-120b)",
        "latency_ms": 350.0
    }

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "search_web_and_synthesize", AsyncMock(return_value=mock_web_result))

    res = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "What are the latest features in PostgreSQL 17?",
            "mode": "WEB_RESEARCH"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert data["mode"] == "WEB_RESEARCH"
    assert len(data["web_sources"]) == 1
    assert data["web_sources"][0]["domain"] == "postgresql.org"
    assert data["web_sources"][0]["source_type"] == "OFFICIAL_DOC"
    assert len(data["citations"]) == 1


def test_hybrid_research_with_separate_sources(client, monkeypatch):
    """[MOCKED] Verifies Hybrid mode separates Course Materials from Live Web Research."""
    token = get_token(client, "alex@student.univ.edu")

    mock_web_result = {
        "status": "SUCCESS",
        "answer": "Modern industry networks use Dijkstra in OSPF routing (RFC 2328).",
        "direct_answer": "Dijkstra is the basis of link-state routing.",
        "key_findings": ["Standardized in OSPF protocol."],
        "grounded": True,
        "web_sources": [
            {
                "title": "IETF RFC 2328 OSPF",
                "url": "https://datatracker.ietf.org/doc/html/rfc2328",
                "domain": "datatracker.ietf.org",
                "publication_date": None,
                "retrieval_date": "2026-10-09T04:00:00Z",
                "snippet": "OSPF link state protocol implementation.",
                "source_type": "OFFICIAL_DOC",
                "relevance_score": 1.0
            }
        ],
        "citations": [
            {
                "source_id": "web-1",
                "source_title": "IETF RFC 2328 OSPF",
                "source_url": "https://datatracker.ietf.org/doc/html/rfc2328",
                "citation_text": "OSPF implementation",
                "source_type": "WEB"
            }
        ],
        "search_queries": ["Dijkstra algorithm OSPF RFC"],
        "model_used": "Groq Grounded (openai/gpt-oss-120b)",
        "latency_ms": 290.0
    }

    monkeypatch.setattr(groq_client, "is_configured", lambda: True)
    monkeypatch.setattr(groq_client, "search_web_and_synthesize", AsyncMock(return_value=mock_web_result))

    res = client.post(
        "/api/search",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "query": "How does Dijkstra algorithm find the shortest path in a weighted graph?",
            "mode": "HYBRID"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["grounded"] is True
    assert data["mode"] == "HYBRID"
    assert len(data["course_sources"]) > 0
    assert len(data["web_sources"]) > 0
    assert "Course Material Evidence" in data["answer"]
    assert "Live Web Research" in data["answer"]


# ============================================================================
# 4. RATE LIMITING (HTTP 429), TIMEOUTS, AND MODEL CONFIGURATION
# ============================================================================

@pytest.mark.asyncio
async def test_groq_http_429_rate_limiting_handling():
    """[UNIT] Verifies that HTTP 429 rate limit is detected and parsed without crashing."""
    mock_client = GroqClient()
    mock_client.api_key = "test_key_abc123"

    mock_resp = httpx.Response(
        status_code=429,
        headers={"retry-after": "2"},
        text='{"error": {"message": "Rate limit exceeded. Try again in 2s.", "type": "tokens"}}'
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await mock_client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            max_retries=1
        )
        assert res["success"] is False
        assert res["status_code"] == 429
        assert res["error_type"] == "QUOTA_EXHAUSTED"
        assert "429" in res["error"]


@pytest.mark.asyncio
async def test_groq_timeout_handling():
    """[UNIT] Verifies that network timeouts return a structured TIMEOUT error."""
    mock_client = GroqClient()
    mock_client.api_key = "test_key_abc123"

    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Connection timed out")):
        res = await mock_client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            max_retries=0
        )
        assert res["success"] is False
        assert res["error_type"] == "TIMEOUT"
        assert res["status_code"] == 504


@pytest.mark.asyncio
async def test_groq_invalid_model_handling():
    """[UNIT] Verifies that an invalid model returns a structured INVALID_MODEL error."""
    mock_client = GroqClient()
    mock_client.api_key = "test_key_abc123"

    mock_resp = httpx.Response(
        status_code=400,
        text='{"error": {"message": "Model non-existent-model does not exist", "type": "invalid_request_error"}}'
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await mock_client.chat_completion(
            messages=[{"role": "user", "content": "Hello"}],
            model="non-existent-model",
            max_retries=0
        )
        assert res["success"] is False
        assert res["error_type"] == "INVALID_MODEL"
        assert res["status_code"] == 400


# ============================================================================
# 5. GEMINI ABSENT FROM NORMAL GENERATION AND SEARCH PATHS
# ============================================================================

def test_gemini_absent_from_normal_search_paths(client, monkeypatch):
    """
    [UNIT/SECURITY] Verifies that when LLM_PROVIDER=groq, Google Gemini SDK
    is NEVER called in the normal execution path for course notes or web research.
    """
    token = get_token(client, "alex@student.univ.edu")

    # Create a sentinel mock that asserts if Gemini Client is called
    with patch("google.genai.Client", side_effect=AssertionError("CRITICAL: Gemini Client was unexpectedly invoked!")):
        # 1. Course Notes search
        res1 = client.post(
            "/api/search",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "query": "How does Dijkstra algorithm find the shortest path in a weighted graph?",
                "mode": "COURSE_NOTES"
            }
        )
        assert res1.status_code == 200
        assert res1.json()["grounded"] is True

        # 2. Embedding calculation directly
        vec = embedding_engine.embed_text("Verify embedding does not call Gemini")
        assert len(vec) == 768

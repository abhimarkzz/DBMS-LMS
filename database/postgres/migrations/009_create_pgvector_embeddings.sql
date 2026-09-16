-- =============================================================================
-- Migration 009: pgvector Embedding Column and ANN Index
-- =============================================================================
-- Adds the embedding vector column to material_chunks.
-- Dimension: 384 — matching sentence-transformers/all-MiniLM-L6-v2.
--
-- This is separated from migration 008 intentionally:
--   - Allows testing the material schema without pgvector
--   - Makes the embedding dimension configurable in one place
--   - Clearly shows the AI/vector layer as a distinct concern
--
-- Index Choice: HNSW (Hierarchical Navigable Small World)
-- Chosen over IVFFlat because:
--   - HNSW does not require a training step (IVFFlat needs to know the
--     expected number of vectors upfront via lists parameter)
--   - HNSW provides better query-time recall at similar speeds
--   - Simpler to set up for an academic project without predefined data volumes
--   - HNSW supports incremental inserts naturally; IVFFlat degrades if
--     data distribution changes significantly after training
--
-- Trade-off: HNSW uses more memory than IVFFlat. At the scale of this
-- project (thousands of chunks, not billions), this is not a concern.
--
-- HNSW parameters:
--   m = 16           (number of connections per layer; 16 is the default, good balance)
--   ef_construction = 64  (search depth during index build; higher = better recall)
-- =============================================================================

-- Add embedding column to material_chunks
-- The dimension (384) must match EMBEDDING_DIMENSION in .env
ALTER TABLE material_chunks
    ADD COLUMN embedding vector(384);

-- HNSW index for approximate nearest-neighbor search using cosine distance.
-- Cosine similarity is preferred for text embeddings because it measures
-- directional similarity independent of vector magnitude.
CREATE INDEX idx_material_chunks_embedding_hnsw
    ON material_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Also create a table to track embedding jobs and their status.
-- This supports async processing: upload → queue → embed → ready.
CREATE TABLE embedding_jobs (
    job_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id     UUID NOT NULL REFERENCES course_materials(material_id) ON DELETE CASCADE,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, RUNNING, DONE, FAILED
    chunks_total    INTEGER DEFAULT 0,
    chunks_embedded INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT embedding_jobs_status_valid CHECK (
        status IN ('PENDING', 'RUNNING', 'DONE', 'FAILED')
    )
);

CREATE INDEX idx_embedding_jobs_material_id ON embedding_jobs(material_id);
CREATE INDEX idx_embedding_jobs_status ON embedding_jobs(status);

-- =============================================================================
-- Search cache table
-- Caches recent vector search results for identical queries.
-- Used by the AI Search service alongside Redis for persistence.
-- Redis is the primary cache; this table is a fallback/audit trail.
-- =============================================================================
CREATE TABLE search_cache (
    cache_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash      VARCHAR(64) NOT NULL,   -- SHA-256 of (user_query + course_ids)
    query_text      TEXT NOT NULL,
    result_payload  JSONB NOT NULL,         -- The returned chunk results
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL,   -- Typically NOW() + 1 hour

    CONSTRAINT search_cache_query_hash_unique UNIQUE (query_hash)
);

-- Periodically clean expired cache entries (can be run via pg_cron or app)
CREATE INDEX idx_search_cache_expires_at ON search_cache(expires_at);

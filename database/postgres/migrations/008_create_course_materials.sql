-- =============================================================================
-- Migration 008: Course Materials
-- =============================================================================
-- course_materials holds metadata about uploaded files (PDFs, notes, slides).
-- The actual files are stored in the filesystem or object storage.
--
-- material_chunks holds the extracted text chunks from processed materials.
-- These chunks are what get embedded into vectors for semantic search.
-- The embedding vector column is added in migration 009 (pgvector).
-- =============================================================================

CREATE TYPE material_type AS ENUM ('PDF', 'LECTURE_NOTES', 'PRESENTATION', 'VIDEO', 'DOCUMENT', 'OTHER');
CREATE TYPE material_status AS ENUM ('UPLOADING', 'PROCESSING', 'READY', 'FAILED');
CREATE TYPE content_type AS ENUM ('PDF', 'LECTURE', 'NOTE', 'STUDY_MATERIAL');

-- Metadata for uploaded course materials
CREATE TABLE course_materials (
    material_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id       UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    uploaded_by     UUID NOT NULL REFERENCES teachers(teacher_id) ON DELETE RESTRICT,
    title           VARCHAR(255) NOT NULL,
    material_type   material_type NOT NULL,
    content_type    content_type NOT NULL DEFAULT 'STUDY_MATERIAL',
    file_name       VARCHAR(255) NOT NULL,      -- Original filename
    storage_name    VARCHAR(255) NOT NULL,      -- Safe name used in storage (UUID-based)
    file_url        VARCHAR(500) NOT NULL,      -- Path or S3 key
    file_size_bytes BIGINT,
    mime_type       VARCHAR(100),
    checksum        VARCHAR(64),                -- SHA-256 of file content
    description     TEXT,
    -- Total chunks created during processing (NULL until processing completes)
    total_chunks    INTEGER,
    status          material_status NOT NULL DEFAULT 'UPLOADING',
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,               -- When embedding was completed

    CONSTRAINT course_materials_file_size_positive CHECK (
        file_size_bytes IS NULL OR file_size_bytes > 0
    )
);

-- Text chunks extracted from course materials.
-- embedding column is added in migration 009 after pgvector is confirmed enabled.
-- metadata JSONB stores additional info like page bounding boxes or extraction params.
CREATE TABLE material_chunks (
    chunk_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    material_id     UUID NOT NULL REFERENCES course_materials(material_id) ON DELETE CASCADE,
    chunk_number    INTEGER NOT NULL,           -- Sequential order within the material
    content         TEXT NOT NULL,              -- Extracted text for this chunk
    page_number     INTEGER,                    -- Source page (for PDFs)
    token_count     INTEGER,                    -- Approximate token count
    char_count      INTEGER GENERATED ALWAYS AS (LENGTH(content)) STORED,
    -- Stores embedding provider metadata alongside the chunk
    embedding_model     VARCHAR(100),
    embedding_provider  VARCHAR(50),
    embedding_dimension INTEGER,
    -- Additional extraction metadata (e.g., heading context, chunk strategy)
    chunk_metadata  JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Chunks must be in order within a material
    CONSTRAINT material_chunks_chunk_number_positive CHECK (chunk_number >= 1),

    -- Each chunk number is unique within its material
    CONSTRAINT material_chunks_number_unique UNIQUE (material_id, chunk_number)
);

-- =============================================================================
-- Indexes
-- =============================================================================

-- Find all materials for a course (course detail page)
CREATE INDEX idx_course_materials_course_id ON course_materials(course_id);

-- Teacher filters own uploaded materials
CREATE INDEX idx_course_materials_uploaded_by ON course_materials(uploaded_by);

-- Filter by processing status (background job monitoring)
CREATE INDEX idx_course_materials_status ON course_materials(status);

-- Find all chunks for a material (embedding pipeline)
CREATE INDEX idx_material_chunks_material_id ON material_chunks(material_id);

-- Full-text search index on chunk content (for keyword search in hybrid search)
-- Uses GIN index with tsvector for efficient full-text search
CREATE INDEX idx_material_chunks_content_fts
    ON material_chunks
    USING GIN (to_tsvector('english', content));

-- Trigram index for fuzzy keyword matching
CREATE INDEX idx_material_chunks_content_trigram
    ON material_chunks
    USING GIN (content gin_trgm_ops);

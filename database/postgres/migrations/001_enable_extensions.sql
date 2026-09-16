-- =============================================================================
-- Migration 001: Enable PostgreSQL Extensions
-- =============================================================================
-- Run this FIRST on a fresh database.
-- pgvector must be installed in the PostgreSQL image (ankane/pgvector or
-- official postgres with pgvector built in).
-- =============================================================================

-- UUID generation (built-in since PG 13, but pgcrypto adds gen_random_uuid)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- UUID type support (already in PG core, but explicit is better)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Vector similarity search extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Full-text search dictionaries (used in hybrid search)
-- This is a built-in extension, no install needed, just enabling unaccent
CREATE EXTENSION IF NOT EXISTS unaccent;

-- pg_trgm for trigram similarity (useful for keyword fuzzy search)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

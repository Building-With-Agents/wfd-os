-- =============================================================================
-- Job Board Agent — fix embeddings.embedding dimension (1024 -> 1536)
-- Run against: wfd_os database on local PostgreSQL 18
-- Date: 2026-04-17
-- =============================================================================
-- Adjusts the embeddings table to match the existing ecosystem convention:
-- Azure OpenAI text-embedding-3-small at 1536 dims (same model as
-- skills.embedding_vector). Migration 011 had declared VECTOR(1024) for
-- Voyage-3 but the design review decided to reuse the existing Azure OpenAI
-- wiring instead.
--
-- Safe because the embeddings table is currently empty (0 rows).
-- Re-running the ALTER on a populated table would truncate/reject vectors.
--
-- Steps:
--   1. Drop the HNSW index (tied to the VECTOR(1024) column)
--   2. ALTER the column type to VECTOR(1536)
--   3. Recreate the HNSW index with vector_cosine_ops
-- =============================================================================

BEGIN;

DROP INDEX IF EXISTS idx_embeddings_vector;

ALTER TABLE embeddings
    ALTER COLUMN embedding TYPE VECTOR(1536);

CREATE INDEX idx_embeddings_vector
    ON embeddings
    USING hnsw (embedding vector_cosine_ops);

COMMIT;


-- =============================================================================
-- Rollback
-- =============================================================================
-- BEGIN;
-- DROP INDEX IF EXISTS idx_embeddings_vector;
-- ALTER TABLE embeddings ALTER COLUMN embedding TYPE VECTOR(1024);
-- CREATE INDEX idx_embeddings_vector ON embeddings USING hnsw (embedding vector_cosine_ops);
-- COMMIT;

-- Phase 2D — add provenance metadata to embeddings table.
--
-- Motivation: we now write embeddings from multiple generators (job
-- backfill, student backfill, and whatever produced the initial 29
-- jobs_enriched rows pre-repo). Without metadata we cannot tell which
-- template produced which vector, when it was generated, or which
-- source fields were non-null at generation time. That makes it hard
-- to re-embed safely when a template changes.
--
-- Columns added:
--   text_template_version   — e.g. 'student_v1', 'job_v1'. Legacy
--                             rows (pre-Phase-2D) stay NULL.
--   embedding_generated_at  — distinct from created_at (row insert)
--                             and updated_at (row mutation). Marks
--                             the actual embedding API call time.
--   source_fields_present   — JSONB array of field names that were
--                             non-null when the template was rendered.
--                             Lets us debug why two similar records
--                             produced different vectors.

ALTER TABLE embeddings
  ADD COLUMN IF NOT EXISTS text_template_version VARCHAR(50),
  ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS source_fields_present JSONB;

CREATE INDEX IF NOT EXISTS idx_embeddings_template_version
  ON embeddings(text_template_version);

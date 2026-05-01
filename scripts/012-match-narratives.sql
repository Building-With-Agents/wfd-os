-- Phase 2G — cache table for LLM-generated match narratives.
--
-- Generation is ~4-6s per (student, job) pair at ~$0.01 cost; caching
-- so a recruiter flipping between candidates on the same job hits
-- warm results after the first open. Cache invalidates by input_hash
-- (sha256 over the student profile + job description + required
-- skills) so changes on either side regenerate automatically; a
-- 30-day staleness window in the endpoint catches prompt edits that
-- don't change the inputs.
--
-- Schema deviation from the Phase 2G spec: job_id is INTEGER, not
-- UUID. wfd-os jobs live in jobs_enriched(id INTEGER); the applications
-- table already uses this FK pattern.

CREATE TABLE IF NOT EXISTS match_narratives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id UUID NOT NULL REFERENCES students(id),
  job_id INTEGER NOT NULL REFERENCES jobs_enriched(id),
  verdict_line TEXT NOT NULL,
  narrative_text TEXT NOT NULL,
  match_strengths JSONB NOT NULL DEFAULT '[]'::jsonb,
  match_gaps JSONB NOT NULL DEFAULT '[]'::jsonb,
  match_partial JSONB NOT NULL DEFAULT '[]'::jsonb,
  calibration_label TEXT NOT NULL,
  cosine_similarity NUMERIC(5,4) NOT NULL,
  input_hash TEXT NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (student_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_match_narratives_lookup
  ON match_narratives(student_id, job_id);

CREATE INDEX IF NOT EXISTS idx_match_narratives_hash
  ON match_narratives(input_hash);

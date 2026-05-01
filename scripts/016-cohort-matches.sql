-- =============================================================================
-- Phase B — cohort_matches table (tenant-scoped match persistence)
-- Run against: wfd_os database on local PostgreSQL 18
-- Date: 2026-04-20
-- =============================================================================
-- Matches are real data (facts about apprentice/job compatibility), not
-- intermediate state. They deserve a proper home in the schema so Task 6
-- (placement report) and future analyses can query them independently of
-- the narrated subset in `match_narratives`.
--
-- Relationship to match_narratives:
--   cohort_matches    = broader set (top-N matches per apprentice; N=10
--                       currently for WSB Cohort 1 = 90 rows).
--   match_narratives  = narrated subset (top-3 narrated per apprentice).
--                       Each narrated (student_id, job_id) pair also lives
--                       in cohort_matches with the same cosine_similarity.
--
-- Tenancy pattern:
--   Follows Phase A migration 014: `tenant_id UUID NOT NULL REFERENCES
--   tenants(id)`. Unlike `embeddings` (which has no tenant_id and scopes
--   via JOIN-through-parent), cohort_matches is tenancy-native. This
--   matches the pattern used for other phase-A-scoped tables.
--
-- Safe to run: wraps everything in a single transaction. All-or-nothing.
-- =============================================================================

BEGIN;

CREATE TABLE cohort_matches (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES tenants(id),
    student_id         UUID NOT NULL REFERENCES students(id),
    job_id             INT  NOT NULL REFERENCES jobs_enriched(id),
    cosine_similarity  DOUBLE PRECISION NOT NULL,
    match_rank         INT  NOT NULL,
    generated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model_name         TEXT,                 -- e.g. 'text-embedding-3-small'
    template_version   TEXT,                 -- e.g. 'student_v2/job_v1'

    CONSTRAINT cohort_matches_rank_positive CHECK (match_rank >= 1),
    CONSTRAINT cohort_matches_cosine_range CHECK (cosine_similarity BETWEEN -1 AND 1),
    CONSTRAINT cohort_matches_student_job_tenant_unique UNIQUE (student_id, job_id, tenant_id)
);

COMMENT ON TABLE cohort_matches IS
    'Tenant-scoped top-N job matches per apprentice. Source of truth for '
    'matching facts; match_narratives stores LLM-generated narration on '
    'top of a subset of these rows.';

-- Query index: "matches for a given apprentice (ordered by rank)"
CREATE INDEX idx_cohort_matches_tenant_student
    ON cohort_matches(tenant_id, student_id, match_rank);

-- Query index: "which apprentices match this job"
CREATE INDEX idx_cohort_matches_tenant_job
    ON cohort_matches(tenant_id, job_id, match_rank);

COMMIT;


-- =============================================================================
-- Rollback
-- =============================================================================
-- BEGIN;
-- DROP INDEX IF EXISTS idx_cohort_matches_tenant_job;
-- DROP INDEX IF EXISTS idx_cohort_matches_tenant_student;
-- DROP TABLE IF EXISTS cohort_matches;
-- COMMIT;

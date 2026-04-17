-- =============================================================================
-- Job Board Agent — schema
-- Run against: wfd_os database on local PostgreSQL 18
-- Date: 2026-04-17
-- =============================================================================
-- Adds three new objects to wfd_os database:
--   1. v_jobs_active    — view over jobs_enriched (actionable jobs)
--   2. embeddings       — polymorphic vector table (students + jobs_enriched)
--   3. applications     — student applications with packaging + approval workflow
--
-- Plus updated_at triggers on the two mutable new tables.
--
-- Assumes:
--   - Postgres 15+ (gen_random_uuid())
--   - pgvector extension ('vector') already installed
--   - Existing tables: students (uuid PK), jobs_enriched (int PK), jobs_raw (int PK)
--
-- Pilot data source: jobs_enriched filtered to deployment_id='cfa-seattle-bd'.
-- Additional sources later plug in via new deployment_ids or new source tables.
--
-- Embedding model: default Voyage-3 (1024 dims). Change VECTOR(1024) to
-- VECTOR(1536) if switching to OpenAI text-embedding-3-small.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. v_jobs_active
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_jobs_active AS
SELECT
    je.id                                              AS job_id,
    je.deployment_id,
    je.region,
    je.title,
    je.company,
    je.company_domain,
    je.location,
    je.job_description                                 AS description,
    je.skills_required,
    je.seniority,
    je.is_ai_role,
    je.is_data_role,
    je.is_workforce_role,
    je.posted_at,
    COALESCE(
        jr.raw_data ->> 'job_apply_link',
        jr.raw_data ->> 'job_google_link'
    )                                                  AS apply_url,
    je.enriched_at
FROM jobs_enriched je
LEFT JOIN jobs_raw jr
    ON jr.deployment_id = je.deployment_id
   AND jr.job_id        = je.job_id
WHERE COALESCE(je.is_suppressed, FALSE) = FALSE;

COMMENT ON VIEW v_jobs_active IS
    'Candidate-facing view over jobs_enriched. Filters is_suppressed, joins '
    'jobs_raw to extract apply_url from the raw JSearch payload.';


-- -----------------------------------------------------------------------------
-- 2. embeddings
-- -----------------------------------------------------------------------------
CREATE TABLE embeddings (
    entity_type               VARCHAR(32)  NOT NULL,
    entity_id                 VARCHAR(64)  NOT NULL,
    model_name                VARCHAR(64)  NOT NULL,
    embedding                 VECTOR(1024) NOT NULL,
    content_hash              VARCHAR(64),
    created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    PRIMARY KEY (entity_type, entity_id, model_name),

    CONSTRAINT chk_embeddings_entity_type CHECK (
        entity_type IN ('student', 'jobs_enriched')
    )
);

CREATE INDEX idx_embeddings_vector ON embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_embeddings_entity ON embeddings (entity_type, entity_id);

COMMENT ON TABLE embeddings IS
    'Polymorphic vector store for students + jobs_enriched. entity_id stringified '
    'to accommodate uuid + int source keys. HNSW cosine index.';


-- -----------------------------------------------------------------------------
-- 3. applications
-- -----------------------------------------------------------------------------
CREATE TABLE applications (
    id                        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),

    student_id                UUID         NOT NULL REFERENCES students(id),
    job_id                    INT          NOT NULL REFERENCES jobs_enriched(id),
    owning_recruiter_id       UUID,

    status                    VARCHAR(32)  NOT NULL DEFAULT 'draft',
    initiated_by              VARCHAR(16)  NOT NULL,

    resume_version            VARCHAR(128),
    cover_letter              TEXT,
    custom_fields             JSONB,
    package_url               VARCHAR(1024),

    submitted_at              TIMESTAMPTZ,
    approved_at               TIMESTAMPTZ,
    sent_at                   TIMESTAMPTZ,
    employer_ack_at           TIMESTAMPTZ,
    last_status_change_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    notes                     TEXT,

    created_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_applications_initiated_by CHECK (
        initiated_by IN ('candidate', 'recruiter')
    ),
    CONSTRAINT chk_applications_status CHECK (
        status IN (
            'draft',
            'submitted_for_review',
            'approved',
            'rejected_by_recruiter',
            'packaged',
            'sent',
            'delivered',
            'employer_responded',
            'interview',
            'rejected_by_employer',
            'offer',
            'withdrawn'
        )
    ),
    CONSTRAINT uq_applications_student_job UNIQUE (student_id, job_id)
);

CREATE INDEX idx_applications_student   ON applications (student_id);
CREATE INDEX idx_applications_job       ON applications (job_id);
CREATE INDEX idx_applications_status    ON applications (status);
CREATE INDEX idx_applications_recruiter ON applications (owning_recruiter_id) WHERE owning_recruiter_id IS NOT NULL;

COMMENT ON TABLE applications IS
    'Student applications with packaging + recruiter approval workflow. '
    'Direct FK to jobs_enriched during pilot. UNIQUE (student_id, job_id) prevents '
    'duplicates; relax if re-application flow needs multiple rounds.';


-- -----------------------------------------------------------------------------
-- updated_at triggers
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION jba_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_embeddings_updated_at
    BEFORE UPDATE ON embeddings
    FOR EACH ROW EXECUTE FUNCTION jba_set_updated_at();

CREATE TRIGGER trg_applications_updated_at
    BEFORE UPDATE ON applications
    FOR EACH ROW EXECUTE FUNCTION jba_set_updated_at();

COMMIT;


-- =============================================================================
-- Rollback
-- =============================================================================
-- BEGIN;
-- DROP TRIGGER IF EXISTS trg_applications_updated_at ON applications;
-- DROP TRIGGER IF EXISTS trg_embeddings_updated_at   ON embeddings;
-- DROP FUNCTION IF EXISTS jba_set_updated_at();
-- DROP TABLE IF EXISTS applications;
-- DROP TABLE IF EXISTS embeddings;
-- DROP VIEW  IF EXISTS v_jobs_active;
-- COMMIT;

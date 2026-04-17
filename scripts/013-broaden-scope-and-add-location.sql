-- =============================================================================
-- Job Board Agent — broaden v_jobs_active + add structured location fields
-- Run against: wfd_os database on local PostgreSQL 18
-- Date: 2026-04-17
-- =============================================================================
-- Two changes:
--
--   1. jobs_enriched gets seven new structured columns, backfilled from the
--      JSearch payload in jobs_raw.raw_data:
--         city, state, country, is_remote, latitude, longitude, employment_type
--      These unlock filter params (city/state/is_remote/employment_type) that
--      the existing single VARCHAR `location` field can't cleanly support.
--
--   2. v_jobs_active drops the `is_suppressed = false` filter so it returns
--      the full population of ingested jobs (all 103 across both deployments),
--      not just the non-suppressed pilot set (58). Suppression is a caller
--      concern now, not a view concern — recruiting UIs should show the full
--      pipeline while matching / candidate-facing views filter themselves.
--
-- Safe casts are used throughout because JSearch payloads are inconsistent
-- across refreshes — fields that look like numbers or booleans can arrive
-- as strings, empty strings, or missing entirely. NULLIF(TRIM(...), '')
-- normalizes empties to NULL before casting.
--
-- employment_type is populated from the singular `job_employment_type`
-- string (e.g. "Full-time", "Contractor"). The plural job_employment_types
-- array is ignored for now — add a companion column later if multi-type
-- filtering is needed.
--
-- Assumes:
--   - Migrations 011 and 012 already applied
--   - jobs_raw has a `raw_data` JSONB column with JSearch-shaped keys
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Add structured location + employment columns to jobs_enriched
-- -----------------------------------------------------------------------------
ALTER TABLE jobs_enriched
    ADD COLUMN IF NOT EXISTS city            VARCHAR(100),
    ADD COLUMN IF NOT EXISTS state           VARCHAR(100),
    ADD COLUMN IF NOT EXISTS country         VARCHAR(100),
    ADD COLUMN IF NOT EXISTS is_remote       BOOLEAN,
    ADD COLUMN IF NOT EXISTS latitude        NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS longitude       NUMERIC(10, 7),
    ADD COLUMN IF NOT EXISTS employment_type VARCHAR(50);


-- -----------------------------------------------------------------------------
-- 2. Backfill from jobs_raw.raw_data with defensive casts
-- -----------------------------------------------------------------------------
UPDATE jobs_enriched je
SET
    city            = NULLIF(TRIM(jr.raw_data ->> 'job_city'),            ''),
    state           = NULLIF(TRIM(jr.raw_data ->> 'job_state'),           ''),
    country         = NULLIF(TRIM(jr.raw_data ->> 'job_country'),         ''),
    is_remote       = NULLIF(TRIM(jr.raw_data ->> 'job_is_remote'),       '')::boolean,
    latitude        = NULLIF(TRIM(jr.raw_data ->> 'job_latitude'),        '')::numeric,
    longitude       = NULLIF(TRIM(jr.raw_data ->> 'job_longitude'),       '')::numeric,
    employment_type = NULLIF(TRIM(jr.raw_data ->> 'job_employment_type'), '')
FROM jobs_raw jr
WHERE jr.deployment_id = je.deployment_id
  AND jr.job_id        = je.job_id;


-- -----------------------------------------------------------------------------
-- 3. Broaden v_jobs_active
--    - Drop the is_suppressed filter → returns all 103 ingested jobs
--    - Append the seven new columns at the end so CREATE OR REPLACE VIEW
--      accepts the change (existing columns keep their order + types)
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
    je.enriched_at,
    -- New columns (appended to preserve CREATE OR REPLACE VIEW compatibility)
    je.city,
    je.state,
    je.country,
    je.is_remote,
    je.latitude,
    je.longitude,
    je.employment_type
FROM jobs_enriched je
LEFT JOIN jobs_raw jr
    ON jr.deployment_id = je.deployment_id
   AND jr.job_id        = je.job_id;

COMMENT ON VIEW v_jobs_active IS
    'All ingested jobs joined with raw payload for apply_url extraction. '
    'No is_suppressed filter — suppression is a caller concern, not a view '
    'concern. Recruiting UIs see the full pipeline; candidate-facing views '
    'apply their own is_suppressed filter downstream.';

COMMIT;


-- =============================================================================
-- Rollback
-- =============================================================================
-- BEGIN;
-- CREATE OR REPLACE VIEW v_jobs_active AS
-- SELECT
--     je.id AS job_id,
--     je.deployment_id,
--     je.region,
--     je.title,
--     je.company,
--     je.company_domain,
--     je.location,
--     je.job_description AS description,
--     je.skills_required,
--     je.seniority,
--     je.is_ai_role,
--     je.is_data_role,
--     je.is_workforce_role,
--     je.posted_at,
--     COALESCE(jr.raw_data ->> 'job_apply_link', jr.raw_data ->> 'job_google_link') AS apply_url,
--     je.enriched_at
-- FROM jobs_enriched je
-- LEFT JOIN jobs_raw jr
--     ON jr.deployment_id = je.deployment_id
--    AND jr.job_id        = je.job_id
-- WHERE COALESCE(je.is_suppressed, FALSE) = FALSE;
-- ALTER TABLE jobs_enriched
--     DROP COLUMN IF EXISTS employment_type,
--     DROP COLUMN IF EXISTS longitude,
--     DROP COLUMN IF EXISTS latitude,
--     DROP COLUMN IF EXISTS is_remote,
--     DROP COLUMN IF EXISTS country,
--     DROP COLUMN IF EXISTS state,
--     DROP COLUMN IF EXISTS city;
-- COMMIT;

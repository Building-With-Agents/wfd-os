-- =============================================================================
-- Phase A — Tenants seed (lightest viable multi-tenancy scaffolding)
-- Run against: wfd_os database on local PostgreSQL 18
-- Date: 2026-04-20
-- =============================================================================
-- Creates a `tenants` table, seeds CFA + WSB, and adds tenant_id to the five
-- tables that hold tenant-specific data for the Cohort 1 setup:
--   students, jobs_enriched, applications, gap_analyses, match_narratives
--
-- Backfills all existing rows as CFA (the only tenant pre-Phase A), then
-- makes tenant_id NOT NULL so future inserts must specify a tenant.
--
-- This migration DOES NOT:
--   - Add tenant_id to any other tenant-adjacent tables (employers,
--     consulting_engagements, project_inquiries, wji_*, etc.). Those are
--     flagged in the Phase A report for Ritu to decide whether to tag
--     later.
--   - Enforce tenant filtering at the API layer. API code remains untouched.
--   - Add row-level security policies.
--
-- Safe to run: wraps everything in a single transaction. All-or-nothing.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. tenants table
-- -----------------------------------------------------------------------------
CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tenants IS
    'Customers of wfd-os. Seed: CFA (Computing for All, origin customer), '
    'WSB (Workforce Solutions Borderplex, Cohort 1 funder).';

-- -----------------------------------------------------------------------------
-- 2. Seed the two initial tenants
-- -----------------------------------------------------------------------------
INSERT INTO tenants (code, name) VALUES
    ('CFA', 'Computing for All'),
    ('WSB', 'Workforce Solutions Borderplex');

-- -----------------------------------------------------------------------------
-- 3. Add tenant_id columns (nullable initially so backfill can run)
-- -----------------------------------------------------------------------------
ALTER TABLE students         ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE jobs_enriched    ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE applications     ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE gap_analyses     ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE match_narratives ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- -----------------------------------------------------------------------------
-- 4. Backfill existing rows as CFA
-- Every row in these tables today was produced by/for CFA Coalition work.
-- -----------------------------------------------------------------------------
UPDATE students         SET tenant_id = (SELECT id FROM tenants WHERE code = 'CFA');
UPDATE jobs_enriched    SET tenant_id = (SELECT id FROM tenants WHERE code = 'CFA');
UPDATE applications     SET tenant_id = (SELECT id FROM tenants WHERE code = 'CFA');
UPDATE gap_analyses     SET tenant_id = (SELECT id FROM tenants WHERE code = 'CFA');
-- match_narratives has 0 rows; no backfill needed.

-- -----------------------------------------------------------------------------
-- 5. Enforce NOT NULL so future inserts must specify a tenant
-- -----------------------------------------------------------------------------
ALTER TABLE students         ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE jobs_enriched    ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE applications     ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE gap_analyses     ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE match_narratives ALTER COLUMN tenant_id SET NOT NULL;

-- -----------------------------------------------------------------------------
-- 6. Indexes for tenant-scoped queries
-- -----------------------------------------------------------------------------
CREATE INDEX idx_students_tenant         ON students(tenant_id);
CREATE INDEX idx_jobs_enriched_tenant    ON jobs_enriched(tenant_id);
CREATE INDEX idx_applications_tenant     ON applications(tenant_id);
CREATE INDEX idx_gap_analyses_tenant     ON gap_analyses(tenant_id);
CREATE INDEX idx_match_narratives_tenant ON match_narratives(tenant_id);

COMMIT;


-- =============================================================================
-- Rollback
-- =============================================================================
-- BEGIN;
-- DROP INDEX IF EXISTS idx_students_tenant;
-- DROP INDEX IF EXISTS idx_jobs_enriched_tenant;
-- DROP INDEX IF EXISTS idx_applications_tenant;
-- DROP INDEX IF EXISTS idx_gap_analyses_tenant;
-- DROP INDEX IF EXISTS idx_match_narratives_tenant;
-- ALTER TABLE students         DROP COLUMN IF EXISTS tenant_id;
-- ALTER TABLE jobs_enriched    DROP COLUMN IF EXISTS tenant_id;
-- ALTER TABLE applications     DROP COLUMN IF EXISTS tenant_id;
-- ALTER TABLE gap_analyses     DROP COLUMN IF EXISTS tenant_id;
-- ALTER TABLE match_narratives DROP COLUMN IF EXISTS tenant_id;
-- DROP TABLE IF EXISTS tenants;
-- COMMIT;

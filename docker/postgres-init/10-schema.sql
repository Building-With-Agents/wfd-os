-- wfd-os canonical schema — pass 1 (permissive; #22b).
--
-- Applies to the fresh Docker Postgres container from docker-compose.dev.yml
-- (PR #37) on first volume creation. Every table has a matching Pydantic
-- model in wfdos_common.models (#21) where applicable.
--
-- ## Design philosophy
--
-- - Permissive: most columns nullable, TEXT for ambiguous strings, JSONB
--   for flexible arrays/dicts, BIGSERIAL for primary keys. The goal is
--   to let every service boot against a real schema. Tightening is
--   iterative as the data-layer work matures.
-- - No FOREIGN KEY constraints yet. Commented `-- FK: ...` notes mark
--   every place a constraint should eventually land. Adding FKs before
--   the data shape is stable causes migration churn.
-- - `created_at` / `updated_at` on every mutable entity.
-- - Indexes only on obvious lookup columns (ids used in WHERE/JOIN).
-- - `CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` so init
--   is idempotent.
--
-- ## TODO markers
--
-- Every `-- TODO: ...` comment in this file identifies a place to tighten
-- once the real data shape is confirmed. Don't delete TODOs silently;
-- they're the punch list for schema hardening.
--
-- ## Provenance
--
-- Column set per table derived from observed SELECT/INSERT patterns in
-- agents/portal/*_api.py, agents/scoping/*, agents/career-services/,
-- agents/market-intelligence/, scripts/ and the domain models in
-- wfdos_common.models. See docs/database/wfdos-schema-inventory.md.

-- ===========================================================================
-- Reference data
-- ===========================================================================

CREATE TABLE IF NOT EXISTS cip_codes (
    -- Classification of Instructional Programs (CIP). Reference data,
    -- migrated from legacy SQL BACPAC via scripts/005*-migrate-bacpac-reference.
    code        TEXT PRIMARY KEY,
    title       TEXT NOT NULL,  -- TODO: confirm NOT NULL matches existing data
    version     TEXT,            -- CIP 2020 / 2010 etc.
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS soc_codes (
    -- Standard Occupational Classification (SOC). Reference data,
    -- migrated from legacy SQL BACPAC.
    code        TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    version     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cip_soc_crosswalk (
    -- Mapping between CIP and SOC. Used by college-pipeline to match
    -- programs (CIP) to jobs (SOC).
    id          BIGSERIAL PRIMARY KEY,
    cip_code    TEXT NOT NULL,  -- FK: cip_codes.code
    soc_code    TEXT NOT NULL,  -- FK: soc_codes.code
    match_type  TEXT,           -- direct / related / indirect
    source      TEXT            -- e.g. 'nces-2020'
);
CREATE INDEX IF NOT EXISTS ix_cip_soc_crosswalk_cip ON cip_soc_crosswalk(cip_code);
CREATE INDEX IF NOT EXISTS ix_cip_soc_crosswalk_soc ON cip_soc_crosswalk(soc_code);

-- ===========================================================================
-- Skills (taxonomy)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS skills (
    -- Normalized skill taxonomy. Referenced by 9+ files across agents/.
    -- `embedding_vector` is a pgvector column (1536-dim by convention;
    -- matches OpenAI-compatible embeddings used by agents/market-intelligence).
    -- TODO: once the real embedding model is locked, assert vector dim.
    skill_id          BIGSERIAL PRIMARY KEY,
    skill_name        TEXT NOT NULL,
    normalized_name   TEXT,                   -- lowercased / deduped form
    category          TEXT,                   -- digital / soft / domain
    source            TEXT,                   -- esco / lightcast / internal
    embedding_vector  vector(1536),           -- requires pgvector (enabled in 00-extensions.sql)
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_skills_name ON skills(skill_name);

-- ===========================================================================
-- Students + career services
-- ===========================================================================

CREATE TABLE IF NOT EXISTS students (
    -- Master student record. Written by Profile Agent (resume parse) +
    -- Dataverse migration (scripts/002-migrate-dataverse). Read by every
    -- portal + assistant.
    --
    -- Column set is the UNION of:
    --   - scripts/002-migrate-dataverse.py INSERT (migration columns)
    --   - showcase_api.py / student_api.py SELECTs (runtime reads)
    --   - profile/parse_resumes.py updates (parse metadata)
    --
    -- TODO: define the enum-valued columns (pipeline_status, track,
    --   availability_status, data_quality, engagement_level) as ENUM
    --   types or CHECK constraints once canonical values are locked.
    id                           BIGSERIAL PRIMARY KEY,
    full_name                    TEXT,
    email                        TEXT,
    phone                        TEXT,

    -- Demographics (migration + intake)
    gender                       TEXT,
    ethnicity                    TEXT,
    veteran_status               TEXT,

    -- Location
    city                         TEXT,
    state                        TEXT,
    zipcode                      TEXT,

    -- Latest education (denormalized; also in student_education for history)
    institution                  TEXT,
    degree                       TEXT,
    field_of_study               TEXT,
    graduation_year              INTEGER,

    -- Professional links
    linkedin_url                 TEXT,
    github_url                   TEXT,
    portfolio_url                TEXT,

    -- Intake / parse metadata
    resume_uploaded              BOOLEAN DEFAULT FALSE,
    resume_parsed                BOOLEAN DEFAULT FALSE,
    resume_blob_path             TEXT,
    parse_confidence_score       DOUBLE PRECISION,
    profile_completeness_score   DOUBLE PRECISION,
    missing_required             JSONB,       -- array of field names
    missing_preferred            JSONB,

    -- Journey
    pipeline_status              TEXT,        -- active / placed / alumni / dropped_out / unknown
    program_stage_reached        TEXT,
    track                        TEXT,        -- ojt / direct-placement / unknown
    availability_status          TEXT,        -- seeking / working / paused

    -- Showcase gate
    showcase_eligible            BOOLEAN DEFAULT FALSE,
    showcase_active              BOOLEAN DEFAULT FALSE,
    showcase_activated_at        TIMESTAMPTZ,

    -- Migration tags (Dynamics → Postgres)
    source_system                TEXT,        -- dynamics_cfadev / dynamics_cfahelpdesksandbox / intake
    original_record_id           TEXT,        -- Dataverse contactid
    migration_date               TIMESTAMPTZ,
    data_quality                 TEXT,        -- complete / partial / minimal
    engagement_level             TEXT,        -- high / medium / low / none
    last_active_date             DATE,
    re_engagement_eligible       BOOLEAN,
    re_engagement_status         TEXT,
    legacy_data                  JSONB,       -- raw Dynamics fields

    -- Audit
    created_at                   TIMESTAMPTZ DEFAULT NOW(),
    updated_at                   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_students_email ON students(email);
CREATE INDEX IF NOT EXISTS ix_students_showcase ON students(showcase_active) WHERE showcase_active = TRUE;
CREATE INDEX IF NOT EXISTS ix_students_original_id ON students(original_record_id);

CREATE TABLE IF NOT EXISTS student_skills (
    -- Junction: students → skills. Written by Profile Agent parse.
    -- Deduplicated SQL lives at showcase_api.py:322 and student_api.py:82 —
    -- both collapse to a single query in #22c (wfdos_common.db.queries).
    id              BIGSERIAL PRIMARY KEY,
    student_id      BIGINT NOT NULL,       -- FK: students.id
    skill_id        BIGINT NOT NULL,       -- FK: skills.skill_id
    proficiency     TEXT,                   -- beginner / intermediate / advanced / expert
    source          TEXT,                   -- resume_parse / assessment / self_reported
    confidence      DOUBLE PRECISION,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_student_skills_student ON student_skills(student_id);
CREATE INDEX IF NOT EXISTS ix_student_skills_skill ON student_skills(skill_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_student_skill ON student_skills(student_id, skill_id);

CREATE TABLE IF NOT EXISTS student_education (
    -- One row per school attended. Denormalized from students for multiple-
    -- education-history queries on showcase_api.py.
    id               BIGSERIAL PRIMARY KEY,
    student_id       BIGINT NOT NULL,
    institution      TEXT,
    degree           TEXT,
    field_of_study   TEXT,
    graduation_year  INTEGER,
    start_year       INTEGER,
    gpa              DOUBLE PRECISION,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_student_education_student ON student_education(student_id);

CREATE TABLE IF NOT EXISTS student_work_experience (
    -- One row per job in a student's resume. Written by Profile Agent
    -- (parse_resumes.py).
    id           BIGSERIAL PRIMARY KEY,
    student_id   BIGINT NOT NULL,
    employer     TEXT,
    title        TEXT,
    start_date   DATE,
    end_date     DATE,         -- null = current
    description  TEXT,
    skills_used  JSONB,         -- extracted skill names
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_student_work_student ON student_work_experience(student_id);

CREATE TABLE IF NOT EXISTS student_journeys (
    -- Stage-by-stage tracking per CLAUDE.md student-journey model:
    -- intake → assessment → training → ojt? → showcase → placed → post-placement.
    id                              BIGSERIAL PRIMARY KEY,
    student_id                      BIGINT NOT NULL,

    -- Stage 1: intake
    intake_date                     DATE,

    -- Stage 2: assessment
    assessment_date                 DATE,
    gap_score                       DOUBLE PRECISION,
    track_assigned                  TEXT,
    cohort_id                       TEXT,
    assessment_outcome              TEXT,

    -- Stage 3: training
    training_start_date             DATE,
    training_milestones_completed   JSONB,
    career_services_stage           TEXT,
    match_score_current             DOUBLE PRECISION,

    -- Stage 3b: OJT
    ojt_start_date                  DATE,
    ojt_end_date                    DATE,
    ojt_client_id                   TEXT,
    ojt_performance_rating          TEXT,
    ojt_skills_added                JSONB,

    -- Stage 4: job readiness
    job_ready_date                  DATE,
    final_gap_score                 DOUBLE PRECISION,
    resume_finalized                BOOLEAN DEFAULT FALSE,
    showcase_eligible               BOOLEAN DEFAULT FALSE,
    showcase_active                 BOOLEAN DEFAULT FALSE,
    showcase_activated_date         DATE,

    -- Stage 5: showcase
    showcase_views_count            INTEGER DEFAULT 0,
    showcase_shortlists_count       INTEGER DEFAULT 0,
    showcase_contact_requests_count INTEGER DEFAULT 0,
    employer_interest_signals       JSONB,

    -- Stage 6: placement
    placement_date                  DATE,
    placement_employer_id           BIGINT,       -- FK: employers.id
    placement_role                  TEXT,
    placement_salary                NUMERIC(12, 2),
    placement_type                  TEXT,          -- full_time / contract / apprentice
    placement_fee_applicable        BOOLEAN DEFAULT FALSE,

    -- Stage 7: post-placement
    checkin_30_day                  JSONB,
    checkin_90_day                  JSONB,
    checkin_180_day                 JSONB,
    employment_confirmed            BOOLEAN,
    alumni_status                   TEXT,

    created_at                      TIMESTAMPTZ DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_student_journeys_student ON student_journeys(student_id);
CREATE INDEX IF NOT EXISTS ix_student_journeys_placement_employer ON student_journeys(placement_employer_id);

CREATE TABLE IF NOT EXISTS gap_analyses (
    -- Output of career-services gap analysis. Column set from INSERT in
    -- agents/career-services/gap_analysis.py.
    id                    BIGSERIAL PRIMARY KEY,
    student_id            BIGINT NOT NULL,       -- FK: students.id
    target_role           TEXT,
    target_job_listing_id BIGINT,                 -- FK: job_listings.id
    gap_score             DOUBLE PRECISION,
    missing_skills        JSONB,                  -- array of skill names
    recommendations       JSONB,                  -- dict with match_similarity, matched_count, etc.
    analyzed_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_gap_analyses_student ON gap_analyses(student_id);
CREATE INDEX IF NOT EXISTS ix_gap_analyses_analyzed_at ON gap_analyses(student_id, analyzed_at DESC);
CREATE INDEX IF NOT EXISTS ix_gap_analyses_job ON gap_analyses(target_job_listing_id);

CREATE TABLE IF NOT EXISTS career_pathway_assessments (
    -- Migrated from legacy SQL BACPAC (scripts/005-migrate-bacpac-reference).
    -- TODO: column set is minimal; expand per real migration output.
    id                   BIGSERIAL PRIMARY KEY,
    student_id           BIGINT,
    assessment_date      DATE,
    source_system        TEXT,
    original_record_id   TEXT,
    attributes           JSONB,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS career_services_interactions (
    -- Career services interaction log. Used internally by career-services
    -- agent (CREATE TABLE observed in scan; columns not yet concrete).
    -- TODO: column set needs real data review.
    id             BIGSERIAL PRIMARY KEY,
    student_id     BIGINT,
    staff_id       TEXT,
    interaction_type TEXT,    -- coaching / resume_review / mock_interview / email
    notes          TEXT,
    occurred_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================================================
-- Colleges + programs
-- ===========================================================================

CREATE TABLE IF NOT EXISTS colleges (
    -- Institutions. Migrated from BACPAC (scripts/005-migrate-bacpac).
    id                  BIGSERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    short_name          TEXT,
    city                TEXT,
    state               TEXT,
    website             TEXT,
    source_system       TEXT,
    original_record_id  TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS college_partners (
    -- Subset of colleges that are active CFA partners. Separate table
    -- because partner metadata (contracts, contacts) doesn't apply to
    -- all colleges.
    id                    BIGSERIAL PRIMARY KEY,
    college_id            BIGINT,          -- FK: colleges.id
    partner_since         DATE,
    primary_contact_name  TEXT,
    primary_contact_email TEXT,
    active                BOOLEAN DEFAULT TRUE,
    notes                 TEXT,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_college_partners_college ON college_partners(college_id);

CREATE TABLE IF NOT EXISTS college_programs (
    -- Program offerings per college.
    id                BIGSERIAL PRIMARY KEY,
    college_id        BIGINT,
    name              TEXT NOT NULL,
    cip_code          TEXT,              -- FK: cip_codes.code
    degree_level      TEXT,              -- certificate / associate / bachelors / masters
    duration_months   INTEGER,
    description       TEXT,
    active            BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_college_programs_college ON college_programs(college_id);
CREATE INDEX IF NOT EXISTS ix_college_programs_cip ON college_programs(cip_code);

CREATE TABLE IF NOT EXISTS program_skills (
    -- Junction: college_programs → skills. Populated by
    -- agents/college-pipeline/map_programs_to_skills.py.
    id           BIGSERIAL PRIMARY KEY,
    program_id   BIGINT NOT NULL,       -- FK: college_programs.id
    skill_id     BIGINT NOT NULL,       -- FK: skills.skill_id
    source       TEXT,                   -- automatic_match / curator / survey
    confidence   DOUBLE PRECISION,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_program_skills_program ON program_skills(program_id);
CREATE INDEX IF NOT EXISTS ix_program_skills_skill ON program_skills(skill_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_program_skill ON program_skills(program_id, skill_id);

-- ===========================================================================
-- Employers + jobs
-- ===========================================================================

CREATE TABLE IF NOT EXISTS employers (
    -- Employer master record. Migrated from Dataverse + Lightcast.
    id                  BIGSERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    website_url         TEXT,
    industry            TEXT,
    city                TEXT,
    state               TEXT,
    employee_count      TEXT,          -- range bucket as string (from migration)
    hiring              BOOLEAN,
    source_system       TEXT,
    original_record_id  TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_employers_name ON employers(name);

CREATE TABLE IF NOT EXISTS job_listings (
    -- Job listings. Largest fan-in (11 files). Consumed heavily by JIE
    -- pipeline + wfd-os assistants.
    --
    -- TODO (#17): this is a shared-DB coupling. Per product-arch
    --   Decision 5 (locked 2026-04-14), wfd-os should read job_listings
    --   via JIE's HTTP API (JIE#160), not a direct DB read. This table
    --   stays for now to avoid breaking the 11 callers, but it should
    --   be read-only from wfd-os and populated by JIE ingest.
    id                      BIGSERIAL PRIMARY KEY,
    external_id             TEXT,           -- source-specific id (Lightcast, JSearch, etc.)
    source                  TEXT,           -- lightcast / jsearch / arbeitnow / usajobs
    title                   TEXT NOT NULL,
    employer_id             BIGINT,         -- FK: employers.id (optional — JIE may not resolve)
    employer_name           TEXT,
    location_city           TEXT,
    location_state          TEXT,
    remote                  BOOLEAN,
    salary_min              INTEGER,
    salary_max              INTEGER,
    description             TEXT,
    skills_text             TEXT,           -- comma-separated skill names (legacy; normalizing)
    is_digital              BOOLEAN,        -- digital-economy filter
    posted_date             DATE,
    url                     TEXT,
    raw_payload             JSONB,
    ingested_at             TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_job_listings_employer ON job_listings(employer_id);
CREATE INDEX IF NOT EXISTS ix_job_listings_source_ext ON job_listings(source, external_id);
CREATE INDEX IF NOT EXISTS ix_job_listings_posted ON job_listings(posted_date DESC);
CREATE INDEX IF NOT EXISTS ix_job_listings_digital ON job_listings(is_digital) WHERE is_digital = TRUE;

CREATE TABLE IF NOT EXISTS job_listing_skills (
    -- Junction: job_listings → skills. Populated from market-intel ingest.
    id              BIGSERIAL PRIMARY KEY,
    job_listing_id  BIGINT NOT NULL,
    skill_id        BIGINT NOT NULL,
    source          TEXT,            -- skill_mention / classifier / manual
    confidence      DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS ix_job_listing_skills_job ON job_listing_skills(job_listing_id);
CREATE INDEX IF NOT EXISTS ix_job_listing_skills_skill ON job_listing_skills(skill_id);

CREATE TABLE IF NOT EXISTS job_roles (
    -- Canonical roles (data-engineer, cloud-engineer, etc.). Used by
    -- market-intelligence for aggregation. TODO: align with JIE's
    -- canonical_roles table (JIE has dbo.canonical_roles).
    id          BIGSERIAL PRIMARY KEY,
    role_key    TEXT UNIQUE NOT NULL,   -- slug form
    display_name TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_role_skills (
    -- Junction: job_roles → skills. Expected-skill-set per role.
    id          BIGSERIAL PRIMARY KEY,
    role_id     BIGINT NOT NULL,
    skill_id    BIGINT NOT NULL,
    importance  DOUBLE PRECISION      -- 0..1 weight
);
CREATE INDEX IF NOT EXISTS ix_job_role_skills_role ON job_role_skills(role_id);
CREATE INDEX IF NOT EXISTS ix_job_role_skills_skill ON job_role_skills(skill_id);

-- ===========================================================================
-- Consulting pipeline (Waifinder)
-- ===========================================================================

CREATE TABLE IF NOT EXISTS project_inquiries (
    -- Inbound consulting prospects. Apollo CRM webhooks write; the
    -- consulting-api reads + updates through to conversion.
    --
    -- Column set matched to the real SELECT/INSERT statements in
    -- agents/portal/consulting_api.py and agents/apollo/api.py.
    id                          BIGSERIAL PRIMARY KEY,
    reference_number            TEXT UNIQUE,

    -- Organization
    organization_name           TEXT,

    -- Contact (names match what consulting_api + Apollo use — don't
    -- rename without updating both services)
    contact_name                TEXT,
    contact_role                TEXT,
    email                       TEXT,
    phone                       TEXT,
    is_coalition_member         BOOLEAN,

    -- Inquiry
    project_description         TEXT,
    problem_statement           TEXT,
    success_criteria            TEXT,
    project_area                TEXT,
    timeline                    TEXT,
    budget_range                TEXT,

    -- Status + notes
    status                      TEXT DEFAULT 'new',  -- new / contacted / scoping / qualified / proposal / won / lost / scoped / active
    notes                       TEXT,

    -- Apollo linkage
    apollo_contact_id           TEXT,
    apollo_sequence_suggested   BOOLEAN,

    -- Audit
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_project_inquiries_status ON project_inquiries(status);
CREATE INDEX IF NOT EXISTS ix_project_inquiries_email ON project_inquiries(email);
CREATE INDEX IF NOT EXISTS ix_project_inquiries_created ON project_inquiries(created_at DESC);

CREATE TABLE IF NOT EXISTS consulting_engagements (
    -- Converted project_inquiries → engagement.
    --
    -- PK is explicit INT (from inquiry.id conversion, not BIGSERIAL).
    -- Column set matches INSERT in agents/portal/consulting_api.py exactly.
    id                       BIGINT PRIMARY KEY,  -- set from converting inquiry.id
    organization_name        TEXT,
    contact_name             TEXT,
    contact_email            TEXT,
    project_name             TEXT,
    project_description      TEXT,
    status                   TEXT DEFAULT 'in_progress',   -- in_progress / wrap / closed / cancelled
    start_date               DATE DEFAULT CURRENT_DATE,
    expected_completion      DATE,
    budget                   NUMERIC(12, 2),
    invoiced_amount          NUMERIC(12, 2) DEFAULT 0,
    paid_amount              NUMERIC(12, 2) DEFAULT 0,
    next_milestone           TEXT,
    next_milestone_date      DATE,
    cfa_lead                 TEXT,
    cfa_lead_email           TEXT,
    tech_lead                TEXT,
    tech_lead_email          TEXT,
    client_access_token      TEXT,       -- magic-link style token (#24)
    sharepoint_workspace_url TEXT,
    created_at               TIMESTAMPTZ DEFAULT NOW(),
    updated_at               TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_consulting_engagements_status ON consulting_engagements(status);

CREATE TABLE IF NOT EXISTS engagement_team (
    -- Staff + apprentices assigned to an engagement.
    id              BIGSERIAL PRIMARY KEY,
    engagement_id   BIGINT NOT NULL,
    person_type     TEXT,            -- staff / apprentice
    person_id       TEXT,            -- email or student_id
    person_name     TEXT,
    role            TEXT,            -- lead / apprentice / advisor / client
    joined_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_engagement_team_engagement ON engagement_team(engagement_id);

CREATE TABLE IF NOT EXISTS engagement_milestones (
    id              BIGSERIAL PRIMARY KEY,
    engagement_id   BIGINT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    due_date        DATE,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_engagement_milestones_engagement ON engagement_milestones(engagement_id);

CREATE TABLE IF NOT EXISTS engagement_deliverables (
    id              BIGSERIAL PRIMARY KEY,
    engagement_id   BIGINT NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    url             TEXT,              -- SharePoint / link to artifact
    delivered_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_engagement_deliverables_engagement ON engagement_deliverables(engagement_id);

CREATE TABLE IF NOT EXISTS engagement_updates (
    -- Client-facing update log. Posted to SharePoint + Teams.
    -- Column set from INSERT in consulting_api.py.
    id                 BIGSERIAL PRIMARY KEY,
    engagement_id      BIGINT NOT NULL,       -- FK: consulting_engagements.id
    author             TEXT,
    author_email       TEXT,
    update_type        TEXT,                   -- progress / milestone / blocker / deliverable
    title              TEXT,
    body               TEXT,
    is_client_visible  BOOLEAN DEFAULT FALSE,
    update_date        TIMESTAMPTZ DEFAULT NOW(),
    created_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_engagement_updates_engagement ON engagement_updates(engagement_id, update_date DESC);

-- ===========================================================================
-- Marketing + Apollo
-- ===========================================================================

CREATE TABLE IF NOT EXISTS marketing_content (
    -- Content lifecycle (draft → reviewing → approved → published).
    -- Column set from INSERT in agents/marketing/api.py.
    id                  BIGSERIAL PRIMARY KEY,
    content_type        TEXT,                  -- blog / case_study / email / social / landing
    title               TEXT,
    slug                TEXT UNIQUE,
    content_body        TEXT,
    author              TEXT,
    audience_tag        TEXT,                  -- student / employer / college / prospect
    status              TEXT DEFAULT 'draft',  -- draft / reviewing / approved / published
    sharepoint_doc_url  TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_marketing_content_status ON marketing_content(status);

CREATE TABLE IF NOT EXISTS apollo_webhook_events (
    -- Inbound Apollo CRM webhook payloads.
    -- Column set from INSERT in agents/apollo/api.py.
    id               BIGSERIAL PRIMARY KEY,
    event_type       TEXT,             -- contact.created / sequence.started / stage.changed / etc.
    contact_email    TEXT,
    contact_name     TEXT,
    organization     TEXT,
    stage_name       TEXT,              -- "Ready to Scope" is the scoping-agent trigger
    raw_payload      JSONB,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_apollo_events_email ON apollo_webhook_events(contact_email);
CREATE INDEX IF NOT EXISTS ix_apollo_events_created ON apollo_webhook_events(created_at DESC);

-- ===========================================================================
-- WJI (Workforce Justice Initiative) grant reporting
-- ===========================================================================

CREATE TABLE IF NOT EXISTS wji_upload_batches (
    -- Upload-job tracking (SharePoint file ingestion). Each uploaded
    -- spreadsheet becomes a batch. Column set matches the SELECT + UPDATE
    -- statements in agents/portal/wji_api.py exactly.
    --
    -- Regression fix from Phase 2 exit gate: success_count + error_count +
    -- errors were missing; /api/wji/dashboard SELECTed them and crashed.
    id             BIGSERIAL PRIMARY KEY,
    upload_type    TEXT,              -- placements / payments
    filename       TEXT,
    uploaded_by    TEXT,
    status         TEXT,              -- processing / completed / error
    error_message  TEXT,
    row_count      INTEGER,
    success_count  INTEGER,
    error_count    INTEGER,
    errors         JSONB,             -- per-row error list for the UI
    uploaded_at    TIMESTAMPTZ DEFAULT NOW(),
    processed_at   TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_wji_upload_batches_type ON wji_upload_batches(upload_type, uploaded_at DESC);

CREATE TABLE IF NOT EXISTS wji_placements (
    -- WSAC placement reports. Column set from INSERT in wji_api.py.
    -- student_id is TEXT (not FK int) because it's the WSB participant
    -- identifier from the source spreadsheet, not our internal students.id.
    id                BIGSERIAL PRIMARY KEY,
    batch_id          BIGINT,            -- FK: wji_upload_batches.id
    source_row_num    INTEGER,           -- which row of the uploaded sheet
    student_name      TEXT,
    student_id        TEXT,              -- WSB participant id; TODO: join to our students table
    program           TEXT,
    placement_date    DATE,
    employer          TEXT,
    job_title         TEXT,
    wage              NUMERIC(10, 2),
    wage_basis        TEXT,              -- hourly / annual / weekly
    hours_per_week    INTEGER,
    retention_status  TEXT,              -- 30d / 90d / 180d / placed
    naics_code        TEXT,
    region            TEXT,
    raw_data          JSONB,             -- preserve full row for audit
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_wji_placements_batch ON wji_placements(batch_id);

CREATE TABLE IF NOT EXISTS wji_payments (
    -- QuickBooks payment reconciliation. Column set from INSERT in wji_api.py.
    id              BIGSERIAL PRIMARY KEY,
    batch_id        BIGINT,            -- FK: wji_upload_batches.id
    source_row_num  INTEGER,
    payment_date    DATE,
    vendor          TEXT,
    amount          NUMERIC(12, 2),
    category        TEXT,
    account         TEXT,
    memo            TEXT,
    check_number    TEXT,
    raw_data        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_wji_payments_batch ON wji_payments(batch_id);

-- ===========================================================================
-- Agent runtime
-- ===========================================================================

CREATE TABLE IF NOT EXISTS agent_conversations (
    -- Chat session persistence for the 6 assistants. Upserted via
    -- ON CONFLICT (session_id) DO UPDATE in agents/assistant/base.py.
    -- Column set from that INSERT exactly.
    --
    -- TODO(#26): migrate session persistence from agents/assistant/base.py
    --   into wfdos_common.db; add a tenant_id column then for #16 isolation.
    session_id   TEXT PRIMARY KEY,
    agent_type   TEXT,                              -- student / consulting / college / employer / staff / youth
    messages     JSONB NOT NULL DEFAULT '[]'::jsonb,-- ordered list of messages
    user_id      TEXT,
    user_role    TEXT,                              -- student / staff / admin
    outcome      TEXT,                              -- INTAKE_COMPLETE / HANDOFF_TO_HUMAN / ongoing
    metadata     JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_agent_conversations_user ON agent_conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_agent_conversations_updated ON agent_conversations(updated_at DESC);

CREATE TABLE IF NOT EXISTS audit_log (
    -- Pipeline audit entries. Matches wfdos_common.models.core.AuditEvent.
    -- Every service writes; nobody deletes (#23 CLAUDE.md rule:
    -- audit tables are permanent).
    id             BIGSERIAL PRIMARY KEY,
    event_type     TEXT NOT NULL,
    occurred_at    TIMESTAMPTZ DEFAULT NOW(),
    actor          TEXT,
    tenant_id      TEXT,
    request_id     TEXT,
    subject_type   TEXT,
    subject_id     TEXT,
    attributes     JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_audit_log_event ON audit_log(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_log_subject ON audit_log(subject_type, subject_id);
CREATE INDEX IF NOT EXISTS ix_audit_log_tenant ON audit_log(tenant_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS pipeline_metrics (
    -- Pipeline run metrics. Market-intelligence ingest writes per-run.
    id            BIGSERIAL PRIMARY KEY,
    pipeline      TEXT NOT NULL,         -- market_intelligence_ingest / scoping / etc.
    run_id        TEXT,                   -- uuid per run
    stage         TEXT,                   -- fetch / normalize / enrich / load
    metric_name   TEXT,                   -- rows_ingested / latency_ms / error_count
    metric_value  DOUBLE PRECISION,
    observed_at   TIMESTAMPTZ DEFAULT NOW(),
    attributes    JSONB
);
CREATE INDEX IF NOT EXISTS ix_pipeline_metrics_run ON pipeline_metrics(pipeline, run_id, observed_at);

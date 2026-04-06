-- WFD OS PostgreSQL Schema v1.0
-- Run against: wfd_os database on local PostgreSQL 18
-- Date: 2026-04-02

-- ============================================================
-- EXTENSIONS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- pgvector will be added in step 1 (skills upgrade)

-- ============================================================
-- PROFILE AGENT TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Identity
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    -- Demographics (optional, PII)
    gender VARCHAR(50),
    ethnicity VARCHAR(100),
    veteran_status BOOLEAN,
    disability_status BOOLEAN,
    -- Location
    city VARCHAR(100),
    state VARCHAR(50),
    zipcode VARCHAR(20),
    -- Education (denormalized from contact fields)
    institution VARCHAR(255),
    degree VARCHAR(100),
    field_of_study VARCHAR(255),
    graduation_year INTEGER,
    -- Social/Professional
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    portfolio_url VARCHAR(500),
    -- Resume
    resume_blob_path VARCHAR(500),
    resume_parsed BOOLEAN DEFAULT FALSE,
    parse_confidence_score NUMERIC(3,2),
    -- Pipeline tracking
    pipeline_status VARCHAR(50) DEFAULT 'unknown',
    pipeline_stage VARCHAR(50),
    track VARCHAR(50),
    cohort_id VARCHAR(100),
    -- Profile completeness (calculated)
    required_fields_complete NUMERIC(3,2) DEFAULT 0.0,
    preferred_fields_complete NUMERIC(3,2) DEFAULT 0.0,
    profile_completeness_score NUMERIC(3,2) DEFAULT 0.0,
    missing_required TEXT[],
    missing_preferred TEXT[],
    -- Showcase
    showcase_eligible BOOLEAN DEFAULT FALSE,
    showcase_active BOOLEAN DEFAULT FALSE,
    showcase_activated_date TIMESTAMPTZ,
    -- Availability
    availability_status VARCHAR(50),
    work_authorization VARCHAR(100),
    expected_salary_range VARCHAR(100),
    -- Migration tags (all 8 confirmed fields)
    source_system VARCHAR(50),
    original_record_id VARCHAR(255),
    migration_date TIMESTAMPTZ,
    data_quality VARCHAR(50),
    engagement_level VARCHAR(50),
    last_active_date TIMESTAMPTZ,
    program_stage_reached VARCHAR(100),
    re_engagement_eligible BOOLEAN,
    re_engagement_status VARCHAR(50),
    -- Overflow for low-population Dynamics fields
    legacy_data JSONB,
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS student_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    skill_id UUID REFERENCES skills(skill_id),
    proficiency_level VARCHAR(50),
    source VARCHAR(50),
    added_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS student_education (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    institution VARCHAR(255),
    degree VARCHAR(100),
    field_of_study VARCHAR(255),
    start_date DATE,
    end_date DATE,
    gpa NUMERIC(3,2)
);

CREATE TABLE IF NOT EXISTS student_work_experience (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    company VARCHAR(255),
    title VARCHAR(255),
    description TEXT,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS student_journeys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    stage VARCHAR(50) NOT NULL,
    entered_at TIMESTAMPTZ DEFAULT NOW(),
    exited_at TIMESTAMPTZ,
    notes TEXT,
    triggered_by VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS employers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    website VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(50),
    zipcode VARCHAR(20),
    company_size VARCHAR(50),
    description TEXT,
    logo_url VARCHAR(500),
    -- Contact
    primary_contact_name VARCHAR(255),
    primary_contact_email VARCHAR(255),
    primary_contact_phone VARCHAR(50),
    -- Migration
    source_system VARCHAR(50),
    original_record_id VARCHAR(255),
    migration_date TIMESTAMPTZ,
    legacy_data JSONB,
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MARKET INTELLIGENCE AGENT TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS job_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    employer_id UUID REFERENCES employers(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zipcode VARCHAR(20),
    remote_option VARCHAR(50),
    employment_type VARCHAR(50),
    salary_min NUMERIC(12,2),
    salary_max NUMERIC(12,2),
    salary_period VARCHAR(20),
    soc_code VARCHAR(20),
    posted_date DATE,
    expires_date DATE,
    status VARCHAR(50) DEFAULT 'active',
    -- Migration
    source_system VARCHAR(50),
    original_record_id VARCHAR(255),
    migration_date TIMESTAMPTZ,
    legacy_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_listing_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_listing_id UUID REFERENCES job_listings(id),
    skill_id UUID REFERENCES skills(skill_id),
    importance VARCHAR(50),
    extracted_by VARCHAR(50)
);

-- ============================================================
-- SKILLS & MATCHING AGENT TABLES
-- (skills table already exists — pgvector upgrade separate)
-- ============================================================

CREATE TABLE IF NOT EXISTS job_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    pathway_id UUID
);

CREATE TABLE IF NOT EXISTS job_role_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_role_id UUID REFERENCES job_roles(id),
    skill_id UUID REFERENCES skills(skill_id),
    importance_level VARCHAR(50)
);

-- ============================================================
-- CAREER SERVICES AGENT TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS gap_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    target_role VARCHAR(255),
    target_job_listing_id UUID REFERENCES job_listings(id),
    gap_score NUMERIC(5,2),
    missing_skills TEXT[],
    recommendations JSONB,
    analyzed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS career_services_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    interaction_type VARCHAR(50),
    notes TEXT,
    outcome VARCHAR(100),
    advisor VARCHAR(255),
    interaction_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS career_pathway_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    pathway VARCHAR(100),
    scores JSONB,
    overall_score NUMERIC(5,2),
    assessed_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COLLEGE PIPELINE AGENT TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS colleges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    website VARCHAR(500),
    city VARCHAR(100),
    state VARCHAR(50),
    type VARCHAR(50),
    source_system VARCHAR(50),
    original_record_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS college_programs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID REFERENCES colleges(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    credential_type VARCHAR(100),
    duration VARCHAR(100),
    delivery_mode VARCHAR(100),
    cip_code VARCHAR(20),
    source VARCHAR(50),
    source_system VARCHAR(50),
    original_record_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS program_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id UUID REFERENCES college_programs(id),
    skill_id UUID REFERENCES skills(skill_id),
    source VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS cip_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(500),
    definition TEXT
);

CREATE TABLE IF NOT EXISTS soc_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) NOT NULL,
    title VARCHAR(500),
    version VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS cip_soc_crosswalk (
    cip_id UUID REFERENCES cip_codes(id),
    soc_id UUID REFERENCES soc_codes(id),
    PRIMARY KEY (cip_id, soc_id)
);

-- ============================================================
-- SYSTEM / AUDIT TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    details JSONB,
    performed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pipeline_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100),
    metric_value NUMERIC(12,4),
    dimensions JSONB,
    measured_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_students_email ON students(email);
CREATE INDEX IF NOT EXISTS idx_students_pipeline_status ON students(pipeline_status);
CREATE INDEX IF NOT EXISTS idx_students_showcase_active ON students(showcase_active);
CREATE INDEX IF NOT EXISTS idx_students_original_record_id ON students(original_record_id);
CREATE INDEX IF NOT EXISTS idx_student_skills_student_id ON student_skills(student_id);
CREATE INDEX IF NOT EXISTS idx_student_skills_skill_id ON student_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_student_journeys_student_id ON student_journeys(student_id);
CREATE INDEX IF NOT EXISTS idx_employers_original_record_id ON employers(original_record_id);
CREATE INDEX IF NOT EXISTS idx_job_listings_source ON job_listings(source);
CREATE INDEX IF NOT EXISTS idx_job_listings_soc_code ON job_listings(soc_code);
CREATE INDEX IF NOT EXISTS idx_job_listings_status ON job_listings(status);
CREATE INDEX IF NOT EXISTS idx_job_listing_skills_job ON job_listing_skills(job_listing_id);
CREATE INDEX IF NOT EXISTS idx_job_listing_skills_skill ON job_listing_skills(skill_id);
CREATE INDEX IF NOT EXISTS idx_college_programs_college ON college_programs(college_id);
CREATE INDEX IF NOT EXISTS idx_college_programs_cip ON college_programs(cip_code);
CREATE INDEX IF NOT EXISTS idx_audit_log_agent ON audit_log(agent);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_time ON audit_log(performed_at);

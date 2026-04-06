# Phase 2: Schema Profiling + PostgreSQL Schema Design Recommendations
**Date:** 2026-04-02

---

## Executive Summary

This report profiles the data quality across all discovered sources and
recommends a target PostgreSQL schema organized by agent domain. The key
principle: **flat, purpose-built tables** — not a copy of Dynamics' 266
custom fields on a single contact entity.

---

## Field Population Analysis

### Dataverse Contacts (266 custom fields)

Without querying every field's population rate (which requires sampling
individual records), we can infer from the data patterns:

| Signal | Implication |
|--------|-------------|
| 2,139 student details vs 5,000+ contacts | ~43% have extended profiles |
| 8 education details vs 5,000+ contacts | <1% used dedicated education entity |
| 13 work experiences vs 5,000+ contacts | <1% used dedicated work entity |
| 314 portal users vs 5,000+ contacts | ~6% activated self-service portal |
| 1,515 resumes vs 5,000+ contacts | ~30% have resumes in Blob Storage |

**Prediction:** Many of the 266 custom fields on contacts have <5%
population rates. A full field-level population audit should be run
during migration (sample 500 contacts, check null rates per field).

### SQL/BACPAC Data

| Table | Data Size | Populated? |
|-------|----------|------------|
| skills | 259 MB (5,061 rows) | **Fully populated** including embeddings |
| job_postings | 1.5 MB | Populated |
| 6 rating tables | <10 KB combined | **Barely populated** — schemas exist, data minimal |
| CaseMgmt/Notes | <5 KB combined | **Barely populated** |
| CIP taxonomy | 2 MB | **Fully populated** (reference data) |
| SOC codes (3 versions) | 277 KB | **Fully populated** (reference data) |
| edu_providers/programs | ~450 KB | Populated |
| postal_geo_data | 2.8 MB | **Fully populated** (reference data) |

### Dead Fields (Predicted <5% Population)

These should NOT be migrated as dedicated columns:

| Source | Likely Dead Fields |
|--------|-------------------|
| Contact entity | Many of the 266 custom fields (exact TBD after sampling) |
| cfa_educationdetails | 8 records — entity barely used |
| cfa_studentworkexperiences | 13 records — entity barely used |
| Rating tables | Very few assessment records |
| CaseMgmt | Very few case records |

**Strategy:** During migration, check each contact field. If <5% populated,
store in a JSONB `legacy_data` column rather than creating a dedicated column.

---

## Recommended PostgreSQL Schema by Agent Domain

### Profile Agent Tables

```sql
-- Core student record (flat, not 266 fields)
CREATE TABLE students (
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
    -- Pipeline
    pipeline_status VARCHAR(50) DEFAULT 'unknown',
    pipeline_stage VARCHAR(50),
    track VARCHAR(50),
    cohort_id VARCHAR(100),
    -- Profile completeness
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
    -- Migration metadata
    source_system VARCHAR(50),
    original_record_id VARCHAR(255),
    migration_date TIMESTAMPTZ,
    data_quality VARCHAR(50),
    engagement_level VARCHAR(50),
    last_active_date TIMESTAMPTZ,
    legacy_data JSONB,
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Student skills (normalized)
CREATE TABLE student_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    skill_id UUID REFERENCES skills(skill_id),
    proficiency_level VARCHAR(50),
    source VARCHAR(50), -- 'resume_parse', 'self_reported', 'assessment', 'ojt'
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Student education history
CREATE TABLE student_education (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    institution VARCHAR(255),
    degree VARCHAR(100),
    field_of_study VARCHAR(255),
    start_date DATE,
    end_date DATE,
    gpa NUMERIC(3,2)
);

-- Student work experience
CREATE TABLE student_work_experience (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    company VARCHAR(255),
    title VARCHAR(255),
    description TEXT,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT FALSE
);

-- Student journey tracking
CREATE TABLE student_journeys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    stage VARCHAR(50) NOT NULL,
    entered_at TIMESTAMPTZ DEFAULT NOW(),
    exited_at TIMESTAMPTZ,
    notes TEXT,
    triggered_by VARCHAR(100)
);

-- Employers
CREATE TABLE employers (
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
```

### Market Intelligence Agent Tables

```sql
-- Job listings (from Lightcast + future ingestion)
CREATE TABLE job_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL, -- 'lightcast', 'jsearch', 'cfa_posted', 'scraped'
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

-- Job ↔ skill mapping
CREATE TABLE job_listing_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_listing_id UUID REFERENCES job_listings(id),
    skill_id UUID REFERENCES skills(skill_id),
    importance VARCHAR(50),
    extracted_by VARCHAR(50) -- 'manual', 'llm_extraction', 'taxonomy_match'
);
```

### Skills & Matching Agent Tables

```sql
-- Skills taxonomy (already migrated, needs pgvector upgrade)
-- ALTER TABLE skills ADD COLUMN embedding_vector vector(1536);
-- Convert existing text embeddings to vector format

-- Role definitions
CREATE TABLE job_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    pathway_id UUID
);

CREATE TABLE job_role_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_role_id UUID REFERENCES job_roles(id),
    skill_id UUID REFERENCES skills(skill_id),
    importance_level VARCHAR(50)
);
```

### Career Services Agent Tables

```sql
CREATE TABLE gap_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    target_role VARCHAR(255),
    target_job_listing_id UUID REFERENCES job_listings(id),
    gap_score NUMERIC(5,2),
    missing_skills TEXT[],
    recommendations JSONB,
    analyzed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE career_services_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    interaction_type VARCHAR(50), -- 'resume_review', 'interview_prep', 'coaching', 'gap_analysis'
    notes TEXT,
    outcome VARCHAR(100),
    advisor VARCHAR(255),
    interaction_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE career_pathway_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    pathway VARCHAR(100), -- matches the 6 rating schemas
    scores JSONB, -- all dimension scores
    overall_score NUMERIC(5,2),
    assessed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### College Pipeline Agent Tables

```sql
CREATE TABLE colleges (
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

CREATE TABLE college_programs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID REFERENCES colleges(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    credential_type VARCHAR(100),
    duration VARCHAR(100),
    delivery_mode VARCHAR(100),
    cip_code VARCHAR(20),
    source VARCHAR(50), -- 'cfa_college', 'career_bridge'
    source_system VARCHAR(50),
    original_record_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE program_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id UUID REFERENCES college_programs(id),
    skill_id UUID REFERENCES skills(skill_id),
    source VARCHAR(50) -- 'cip_soc_mapping', 'manual', 'llm_extraction'
);

-- Reference data
CREATE TABLE cip_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) UNIQUE NOT NULL,
    title VARCHAR(500),
    definition TEXT
);

CREATE TABLE soc_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(20) NOT NULL,
    title VARCHAR(500),
    version VARCHAR(10) -- '2010', '2018', 'current'
);

CREATE TABLE cip_soc_crosswalk (
    cip_id UUID REFERENCES cip_codes(id),
    soc_id UUID REFERENCES soc_codes(id),
    PRIMARY KEY (cip_id, soc_id)
);
```

### System / Audit Tables

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    details JSONB,
    performed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE pipeline_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100),
    metric_value NUMERIC(12,4),
    dimensions JSONB,
    measured_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Migration Order

| Step | Source | Target Table(s) | Records |
|------|--------|-----------------|---------|
| 1 | skills (already in PG) | Upgrade with pgvector | 5,061 |
| 2 | Dataverse contacts | students | 5,000+ |
| 3 | Dataverse accounts | employers | 1,619 |
| 4 | Dataverse cfa_studentdetails | students (merge) | 2,139 |
| 5 | Dataverse cfa_lightcastjobs | job_listings | 2,670 |
| 6 | Dataverse cfa_studentjourneies | student_journeys | 3,728 |
| 7 | Dataverse cfa_collegeprograms | college_programs | 729 |
| 8 | Dataverse cfa_careerprograms | college_programs | 3,940 |
| 9 | BACPAC cip/socc tables | cip_codes, soc_codes, crosswalk | ~10K+ |
| 10 | BACPAC edu_providers/programs | colleges, college_programs | hundreds |
| 11 | BACPAC rating tables | career_pathway_assessments | minimal |
| 12 | BACPAC jobseekers + related | students (merge/supplement) | hundreds |

---

*This schema is a recommendation. Review with Gary before implementation.*

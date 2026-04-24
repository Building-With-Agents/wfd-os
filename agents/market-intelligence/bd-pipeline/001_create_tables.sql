-- JSearch BD Pipeline Tables
-- Creates jobs_raw and jobs_enriched for multi-region job ingestion

CREATE TABLE IF NOT EXISTS jobs_raw (
    id SERIAL PRIMARY KEY,
    deployment_id VARCHAR(50) DEFAULT 'cfa-seattle-bd',
    region VARCHAR(100) DEFAULT 'Greater Seattle',
    source VARCHAR(50) DEFAULT 'jsearch',
    job_id VARCHAR(100) UNIQUE,
    raw_data JSONB,
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jobs_enriched (
    id SERIAL PRIMARY KEY,
    deployment_id VARCHAR(50),
    region VARCHAR(100),
    job_id VARCHAR(100) UNIQUE,
    title VARCHAR(255),
    company VARCHAR(255),
    company_domain VARCHAR(255),
    location VARCHAR(255),
    posted_at TIMESTAMP,
    repost_count INTEGER DEFAULT 0,
    is_ai_role BOOLEAN DEFAULT FALSE,
    is_data_role BOOLEAN DEFAULT FALSE,
    is_workforce_role BOOLEAN DEFAULT FALSE,
    skills_required TEXT[],
    seniority VARCHAR(50),
    job_description TEXT,
    job_highlights JSONB,
    enriched_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_raw_deployment ON jobs_raw(deployment_id);
CREATE INDEX IF NOT EXISTS idx_jobs_raw_region ON jobs_raw(region);
CREATE INDEX IF NOT EXISTS idx_jobs_enriched_deployment ON jobs_enriched(deployment_id);
CREATE INDEX IF NOT EXISTS idx_jobs_enriched_region ON jobs_enriched(region);
CREATE INDEX IF NOT EXISTS idx_jobs_enriched_ai ON jobs_enriched(is_ai_role) WHERE is_ai_role = TRUE;
CREATE INDEX IF NOT EXISTS idx_jobs_enriched_data ON jobs_enriched(is_data_role) WHERE is_data_role = TRUE;
CREATE INDEX IF NOT EXISTS idx_jobs_enriched_workforce ON jobs_enriched(is_workforce_role) WHERE is_workforce_role = TRUE;
CREATE INDEX IF NOT EXISTS idx_jobs_enriched_company_domain ON jobs_enriched(company_domain);

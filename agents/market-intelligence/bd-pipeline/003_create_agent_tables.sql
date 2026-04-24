-- Agent 12 + Agent 13 infrastructure tables
-- Migration 003: replaces 002_create_scoring_tables.sql

-- ICP definitions — read by Agent 12 before every scoring run
CREATE TABLE IF NOT EXISTS icp_definitions (
    id SERIAL PRIMARY KEY,
    deployment_id VARCHAR(50),
    version VARCHAR(20),
    definition TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- Outreach definitions — read by Agent 13 before every distribution run
CREATE TABLE IF NOT EXISTS outreach_definitions (
    id SERIAL PRIMARY KEY,
    deployment_id VARCHAR(50),
    version VARCHAR(20),
    definition TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- Prospect companies — master list of companies to score
CREATE TABLE IF NOT EXISTS prospect_companies (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    company_domain VARCHAR(255) UNIQUE,
    entry_source VARCHAR(50),
    entry_date TIMESTAMP DEFAULT NOW(),
    is_suppressed BOOLEAN DEFAULT FALSE,
    suppression_reason VARCHAR(255),
    deployment_id VARCHAR(50),
    region VARCHAR(100)
);

-- Company scores — unified scoring table (replaces company_scores_a and company_scores_b)
CREATE TABLE IF NOT EXISTS company_scores (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    company_domain VARCHAR(255),
    apollo_account_id VARCHAR(100),
    tier VARCHAR(20),
    confidence VARCHAR(20),
    confidence_rationale TEXT,
    scoring_rationale TEXT,
    key_signals TEXT[],
    disqualifying_signals TEXT[],
    recommended_buyer VARCHAR(255),
    recommended_content TEXT,
    sources_consulted TEXT[],
    research_gaps TEXT,
    tier_assigned_at TIMESTAMP DEFAULT NOW(),
    tier_expires_at TIMESTAMP,
    previous_tier VARCHAR(20),
    tier_changed BOOLEAN DEFAULT FALSE,
    gemini_tokens_used INTEGER,
    deployment_id VARCHAR(50) DEFAULT 'waifinder-national',
    region VARCHAR(100)
);

-- Scoring feedback — shared between Agent 12 and Agent 13
-- Drop old version if it has incompatible schema (approach column)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'scoring_feedback' AND column_name = 'approach'
    ) THEN
        DROP TABLE scoring_feedback CASCADE;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS scoring_feedback (
    id SERIAL PRIMARY KEY,
    company_domain VARCHAR(255),
    apollo_account_id VARCHAR(100),
    content_id INTEGER,
    engagement_type VARCHAR(50),
    engaged_at TIMESTAMP,
    tier_at_engagement VARCHAR(20),
    converted_to_conversation BOOLEAN DEFAULT FALSE,
    feedback_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Content submissions — content pieces submitted by Ritu and Jason
CREATE TABLE IF NOT EXISTS content_submissions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    url TEXT,
    content_text TEXT,
    author VARCHAR(50),
    vertical VARCHAR(50),
    topic_tags TEXT[],
    funnel_stage VARCHAR(50),
    format VARCHAR(50),
    distribution_timing TIMESTAMP,
    channels TEXT[],
    status VARCHAR(50) DEFAULT 'pending',
    submitted_at TIMESTAMP DEFAULT NOW(),
    distributed_at TIMESTAMP,
    deployment_id VARCHAR(50) DEFAULT 'waifinder-national',
    region VARCHAR(100)
);

-- Distribution log — Agent 13 logs every distribution event
CREATE TABLE IF NOT EXISTS distribution_log (
    id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES content_submissions(id),
    apollo_contact_id VARCHAR(100),
    apollo_account_id VARCHAR(100),
    company_domain VARCHAR(255),
    company_tier VARCHAR(20),
    channel VARCHAR(50),
    apollo_sequence_id VARCHAR(100),
    enrolled_at TIMESTAMP DEFAULT NOW(),
    deployment_id VARCHAR(50),
    region VARCHAR(100)
);

-- Warm signals — Agent 13 detects and logs engagement signals
CREATE TABLE IF NOT EXISTS warm_signals (
    id SERIAL PRIMARY KEY,
    content_id INTEGER REFERENCES content_submissions(id),
    apollo_contact_id VARCHAR(100),
    apollo_account_id VARCHAR(100),
    company_domain VARCHAR(255),
    contact_name VARCHAR(255),
    contact_title VARCHAR(255),
    company_name VARCHAR(255),
    signal_type VARCHAR(50),
    signal_detail TEXT,
    priority VARCHAR(20),
    company_tier_at_signal VARCHAR(20),
    alert_sent BOOLEAN DEFAULT FALSE,
    alert_sent_at TIMESTAMP,
    converted_to_conversation BOOLEAN DEFAULT FALSE,
    deployment_id VARCHAR(50),
    region VARCHAR(100),
    detected_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_icp_deployment ON icp_definitions(deployment_id);
CREATE INDEX IF NOT EXISTS idx_outreach_deployment ON outreach_definitions(deployment_id);
CREATE INDEX IF NOT EXISTS idx_prospects_domain ON prospect_companies(company_domain);
CREATE INDEX IF NOT EXISTS idx_prospects_deployment ON prospect_companies(deployment_id);
CREATE INDEX IF NOT EXISTS idx_prospects_suppressed ON prospect_companies(is_suppressed);
CREATE INDEX IF NOT EXISTS idx_scores_domain ON company_scores(company_domain);
CREATE INDEX IF NOT EXISTS idx_scores_tier ON company_scores(tier);
CREATE INDEX IF NOT EXISTS idx_scores_deployment ON company_scores(deployment_id);
CREATE INDEX IF NOT EXISTS idx_scores_changed ON company_scores(tier_changed) WHERE tier_changed = TRUE;
CREATE INDEX IF NOT EXISTS idx_feedback_domain ON scoring_feedback(company_domain);
CREATE INDEX IF NOT EXISTS idx_feedback_processed ON scoring_feedback(feedback_processed) WHERE feedback_processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_content_status ON content_submissions(status);
CREATE INDEX IF NOT EXISTS idx_content_deployment ON content_submissions(deployment_id);
CREATE INDEX IF NOT EXISTS idx_distlog_content ON distribution_log(content_id);
CREATE INDEX IF NOT EXISTS idx_distlog_domain ON distribution_log(company_domain);
CREATE INDEX IF NOT EXISTS idx_warm_domain ON warm_signals(company_domain);
CREATE INDEX IF NOT EXISTS idx_warm_priority ON warm_signals(priority);
CREATE INDEX IF NOT EXISTS idx_warm_alert ON warm_signals(alert_sent) WHERE alert_sent = FALSE;

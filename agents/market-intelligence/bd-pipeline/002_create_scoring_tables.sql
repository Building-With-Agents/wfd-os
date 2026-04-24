-- Agent 12: Lead Intelligence and Scoring Agent tables
-- Supports dual-approach scoring (Approach A: scripted, Approach B: Gemini)

-- Approach A — scripted 5-dimension scoring
CREATE TABLE IF NOT EXISTS company_scores_a (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    company_domain VARCHAR(255),
    apollo_account_id VARCHAR(100),
    dimension_1_score INTEGER,
    dimension_2_score INTEGER,
    dimension_3_score INTEGER,
    dimension_4_score INTEGER,
    dimension_5_score INTEGER,
    total_score INTEGER,
    tier VARCHAR(20),
    scoring_rationale TEXT,
    key_signals TEXT[],
    tier_assigned_at TIMESTAMP DEFAULT NOW(),
    tier_expires_at TIMESTAMP,
    previous_tier VARCHAR(20),
    tier_changed BOOLEAN DEFAULT FALSE,
    deployment_id VARCHAR(50) DEFAULT 'cfa-seattle-bd',
    region VARCHAR(100) DEFAULT 'Greater Seattle'
);

-- Approach B — Gemini orchestrated scoring
CREATE TABLE IF NOT EXISTS company_scores_b (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    company_domain VARCHAR(255),
    apollo_account_id VARCHAR(100),
    tier VARCHAR(20),
    confidence VARCHAR(20),
    confidence_rationale TEXT,
    scoring_rationale TEXT,
    key_signals TEXT[],
    tier_assigned_at TIMESTAMP DEFAULT NOW(),
    tier_expires_at TIMESTAMP,
    previous_tier VARCHAR(20),
    tier_changed BOOLEAN DEFAULT FALSE,
    gemini_tokens_used INTEGER,
    deployment_id VARCHAR(50) DEFAULT 'cfa-seattle-bd',
    region VARCHAR(100) DEFAULT 'Greater Seattle'
);

-- Scoring feedback for reinforcement learning
CREATE TABLE IF NOT EXISTS scoring_feedback (
    id SERIAL PRIMARY KEY,
    company_domain VARCHAR(255),
    apollo_account_id VARCHAR(100),
    content_id INTEGER,
    engagement_type VARCHAR(50),
    engaged_at TIMESTAMP,
    tier_at_engagement VARCHAR(20),
    approach VARCHAR(10),
    converted_to_conversation BOOLEAN DEFAULT FALSE,
    feedback_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_scores_a_domain ON company_scores_a(company_domain);
CREATE INDEX IF NOT EXISTS idx_scores_a_tier ON company_scores_a(tier);
CREATE INDEX IF NOT EXISTS idx_scores_a_deployment ON company_scores_a(deployment_id);
CREATE INDEX IF NOT EXISTS idx_scores_b_domain ON company_scores_b(company_domain);
CREATE INDEX IF NOT EXISTS idx_scores_b_tier ON company_scores_b(tier);
CREATE INDEX IF NOT EXISTS idx_scores_b_deployment ON company_scores_b(deployment_id);
CREATE INDEX IF NOT EXISTS idx_feedback_domain ON scoring_feedback(company_domain);
CREATE INDEX IF NOT EXISTS idx_feedback_approach ON scoring_feedback(approach);

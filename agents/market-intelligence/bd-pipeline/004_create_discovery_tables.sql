-- Agent 15: Market Discovery Agent tables
-- Adds discovery columns to prospect_companies and creates performance table

-- Add discovery columns to prospect_companies if not exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospect_companies' AND column_name = 'discovery_signal'
    ) THEN
        ALTER TABLE prospect_companies ADD COLUMN discovery_signal TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospect_companies' AND column_name = 'discovery_source_url'
    ) THEN
        ALTER TABLE prospect_companies ADD COLUMN discovery_source_url TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospect_companies' AND column_name = 'transformation_type'
    ) THEN
        ALTER TABLE prospect_companies ADD COLUMN transformation_type VARCHAR(50);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospect_companies' AND column_name = 'signal_strength'
    ) THEN
        ALTER TABLE prospect_companies ADD COLUMN signal_strength VARCHAR(20);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospect_companies' AND column_name = 'vertical'
    ) THEN
        ALTER TABLE prospect_companies ADD COLUMN vertical VARCHAR(50);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'prospect_companies' AND column_name = 'estimated_size'
    ) THEN
        ALTER TABLE prospect_companies ADD COLUMN estimated_size VARCHAR(20);
    END IF;
END $$;

-- Discovery performance table — weekly self-correction
CREATE TABLE IF NOT EXISTS discovery_performance (
    id SERIAL PRIMARY KEY,
    week_start DATE,
    week_end DATE,
    total_discovered INTEGER DEFAULT 0,
    scored_hot INTEGER DEFAULT 0,
    scored_warm INTEGER DEFAULT 0,
    scored_monitor INTEGER DEFAULT 0,
    scored_suppressed INTEGER DEFAULT 0,
    by_vertical JSONB,
    by_transformation_type JSONB,
    best_search_pattern TEXT,
    worst_search_pattern TEXT,
    adjustment_for_next_week TEXT,
    deployment_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discovery_perf_week ON discovery_performance(week_start);
CREATE INDEX IF NOT EXISTS idx_discovery_perf_deployment ON discovery_performance(deployment_id);

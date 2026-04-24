-- marketing_leads table — referenced by agents/marketing/api.py
-- Schema inferred from existing INSERT/UPDATE statements

CREATE TABLE IF NOT EXISTS marketing_leads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    content_id INTEGER,
    content_title VARCHAR(500),
    content_type VARCHAR(50),
    apollo_contact_id VARCHAR(100),
    captured_at TIMESTAMP DEFAULT NOW(),
    vertical VARCHAR(50),
    company_name VARCHAR(255),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_marketing_leads_email ON marketing_leads(email);
CREATE INDEX IF NOT EXISTS idx_marketing_leads_content ON marketing_leads(content_id);
CREATE INDEX IF NOT EXISTS idx_marketing_leads_captured ON marketing_leads(captured_at);

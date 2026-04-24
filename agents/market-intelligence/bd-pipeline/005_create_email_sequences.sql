-- Agent 13: Email sequences via Microsoft Graph API
-- Replaces Apollo sequence enrollment with direct email drafts/sends

CREATE TABLE IF NOT EXISTS email_sequences (
    id SERIAL PRIMARY KEY,
    contact_id INTEGER REFERENCES hot_warm_contacts(id),
    content_id INTEGER REFERENCES content_submissions(id),
    company_domain VARCHAR(255),
    company_name VARCHAR(255),
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    sender VARCHAR(50),
    sender_email VARCHAR(255),
    subject_line VARCHAR(255),
    touch_1_body TEXT,
    touch_1_sent_at TIMESTAMP,
    touch_1_message_id VARCHAR(255),
    touch_1_read BOOLEAN DEFAULT FALSE,
    touch_2_body TEXT,
    touch_2_sent_at TIMESTAMP,
    touch_2_message_id VARCHAR(255),
    touch_2_read BOOLEAN DEFAULT FALSE,
    touch_3_body TEXT,
    touch_3_sent_at TIMESTAMP,
    touch_3_message_id VARCHAR(255),
    touch_3_read BOOLEAN DEFAULT FALSE,
    reply_detected_at TIMESTAMP,
    reply_message_id VARCHAR(255),
    reply_body TEXT,
    sequence_status VARCHAR(50) DEFAULT 'pending_review',
    approved_by VARCHAR(50),
    approved_at TIMESTAMP,
    deployment_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_seq_status ON email_sequences(sequence_status);
CREATE INDEX IF NOT EXISTS idx_email_seq_domain ON email_sequences(company_domain);
CREATE INDEX IF NOT EXISTS idx_email_seq_sender ON email_sequences(sender_email);
CREATE INDEX IF NOT EXISTS idx_email_seq_contact ON email_sequences(contact_id);

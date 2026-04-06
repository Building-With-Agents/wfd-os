# TODO — Apollo, Scoping Agent, and Client Onboarding Setup

---

## Apollo Setup (Marketing Agent prerequisites)

- [ ] Add Apollo API key to .env file (get from Apollo Settings)
- [ ] Add Apollo webhook secret to .env file
- [ ] Review Jessica Mangold's email sequence document and approve before loading
- [ ] Load Jessica's three email sequences into Apollo:
  - Sequence 1: WA professional services firms/employers
  - Sequence 2: Texas professional services firms/employers
  - Sequence 3: Texas workforce boards/agencies
- [ ] Configure Apollo webhook for "Ready to Scope" trigger
  (Apollo Settings -> Webhooks -> fire when lead moves to "Ready to Scope")

## Scoping Agent Integration

- [ ] Integrate existing Scoping Agent codebase from
  C:\Users\ritub\projects\cfa-scoping-agent into WFD OS
- [ ] Verify Graph API permissions are still active
  (Calendars.ReadWrite, OnlineMeetings.ReadWrite,
  OnlineMeetingTranscripts.Read.All, Teams/Sites)
- [ ] Test SharePoint workspace creation at
  computinforall.sharepoint.com/sites/Waifinder/Clients/
- [ ] Add Apollo webhook endpoint to WFD OS agent server

## Client Onboarding Agent

- [ ] Confirm DocuSeal webhook endpoint and credentials
- [ ] Add DocuSeal webhook secret to .env file
- [ ] Create clients table in PostgreSQL schema
- [ ] Define standard Waifinder project folder structure
  for SharePoint workspace creation
- [ ] Set up ClickUp API access for project creation
- [ ] Define onboarding checklist template

## PostgreSQL Schema Addition Needed

```sql
CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    primary_contact_name VARCHAR(255),
    primary_contact_email VARCHAR(255),
    contract_signed_date DATE,
    engagement_type VARCHAR(50),  -- consulting, managed_services, both
    engagement_status VARCHAR(50), -- active, complete, paused
    sharepoint_workspace_url VARCHAR(500),
    teams_channel_id VARCHAR(255),
    clickup_project_id VARCHAR(255),
    assigned_apprentices TEXT[],
    gary_notified BOOLEAN DEFAULT FALSE,
    onboarding_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

*These TODOs are prerequisites for Agents 12-14. Complete before building.*

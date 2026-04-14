# WFD OS — Workforce Development Operating System
# CLAUDE.md v4

=============================================================
!! CRITICAL — DO NOT DISTURB EXISTING SYSTEMS !!
=============================================================

This rule applies at ALL times, in ALL phases, without exception.

DO NOT write to, modify, delete, or change anything in:
  - Dynamics / Dataverse (any instance)
  - Power Automate flows
  - Power Apps
  - The existing SQL database
  - Azure Blob Storage
  - The Azure Python endpoint
  - Any permissions, roles, settings, or configurations

All new data goes into the WFD OS PostgreSQL schema ONLY.
If any action would modify ANYTHING in an existing system:
STOP. Ask Ritu first.

=============================================================

## Project Overview

WFD OS is CFA's internal agent-first platform for managing the
education-to-work placement pipeline. It is a rebuild of CFA's
legacy SaaS platform (React app, SQL database, Dynamics CRM,
Power Apps) as an agent-first system using PostgreSQL as the
system of record.

Ritu Bahl (Executive Director, CFA) + Claude are building WFD OS v1.0.
Cohort 1 apprentices will build specific features and extensions
as their OJT, supervised by Gary, as Waifinder Client 0 delivery.

## About Waifinder

Waifinder is CFA's consulting business. It delivers real agentic
consulting services to clients — the true value is the consulting
work itself, building agentic data systems for client organizations.

Waifinder also doubles as the pre-placement stage in the talent
pipeline. Apprentices who are ready and qualified do their OJT by
delivering Waifinder client engagements under Gary's supervision.

CFA is Waifinder Client 0 — the first engagement. WFD OS is the
deliverable that Cohort 1 apprentices will extend during their OJT.

The flywheel:
Waifinder wins client → apprentices deliver via OJT → client gets
agentic system → CFA's engagement produces WFD OS → WFD OS manages
next cohort → next cohort delivers next engagement → repeat.

## Organization Context

- CFA = Computing for All, 501(c)(3) nonprofit in Bellevue, WA
- Ritu Bahl is Executive Director
- Gary is Technical Lead, supervises apprentice cohorts
- Cohort 1: Angel, Fabian, Bryan, Emilio, Juan, Enrique, Fatima, Nestor
- Key client: Workforce Solutions Borderplex (Alma is primary contact)
- JIE for Borderplex = Market Intelligence Agent Deployment 001

## What WFD OS Is and Is Not

WFD OS IS:
- Internal pipeline management tool for CFA staff and agents
- Operational backbone from student intake through placement
- Data layer powering all three external portal surfaces
- Platform deployed as Waifinder for paying clients

WFD OS IS NOT:
- A student-facing application (students use the Student Portal)
- An employer-facing application (employers use Employer Portal)
- A public job board
- A replacement for CFA's apprenticeship curriculum

External surfaces powered by WFD OS:
1. Student Portal — profile management and journey tracking
2. Employer Portal + Talent Showcase — talent discovery and hiring
3. College Partner Portal — program management and graduate tracking

## Full Data Ecosystem — All Known Sources

READ ONLY during discovery:
1. SQL Database — primary application data, source of truth
2. Microsoft Dataverse — Dynamics CRM (5,000+ student records)
3. Azure Blob Storage — resumes, documents, model files
4. Azure Python Endpoint — matching engine, embeddings, gap analysis
5. Power Automate Flows — legacy business logic (reference only)
6. Power Apps — legacy staff UX (reference only)
7. OneNote / SharePoint — employer notes and files

Write target:
- PostgreSQL — primary system of record
- pgvector — vector embeddings
- Azure Blob Storage — continued use for file storage

## Azure Credentials

- Tenant ID: [INSERT FROM EXISTING AGENTS]
- Client ID: 068d383c-673e-49f9-9784-6496074d4194 (WFD-OS app)
- Client Secret: [INSERT]
- SQL Server connection string: [INSERT]
- Dynamics URL: [INSERT]
- Azure Blob Storage connection string: [INSERT]
- Azure Python Endpoint URL: [INSERT]
- Azure Python Endpoint API key: [INSERT]

## Dynamics Instances

- cfadev: newer instance, likely less data
- cfahelpdesksandbox: older instance, likely has real WFD OS data
- WFD-OS app registered as System Administrator in both instances

## Strategic Decisions

PostgreSQL as System of Record:
All WFD OS data lives in PostgreSQL. Clean, flat, purpose-built
schemas. No hundreds of unused fields.

Dynamics CRM — Experiment, Don't Invest:
Keep running but stop investing. Build Profile Agent on PostgreSQL
in parallel. Run both through September 2026. Cancel Dynamics after
parallel run validation.

Agent-First Architecture:
Every workflow previously in Power Automate or Power Apps rebuilt
as an agent. No new flows or apps to be built.

Portals Built on Existing React App:
All three portals modernized from existing React app discovered
in WFD OS data. Connected to PostgreSQL via new API layer.
Tokenized link authentication replaces any existing login system.

Azure OpenAI as Default LLM Provider:
All WFD OS agents (Market Intelligence, Profile, Matching, Career
Services, College Pipeline, Orchestrator) route LLM calls through
the provider-agnostic adapter. Do not hardcode Anthropic model IDs
(`claude-haiku-4-5`, `claude-sonnet-4-6`, etc.) in agent code,
`.cursor/rules/*.mdc` contracts, runbooks, or docs. Deployment map:
Haiku-class → `chat-gpt41mini` via `LLM_DEFAULT`; Sonnet-class →
`chat-gpt41` via `LLM_SYNTHESIS`; embeddings →
`embeddings-te3small` via `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME`.
See `.cursor/rules/llm-provider.mdc` (repo-wide, `alwaysApply: true`)
for the full rule.

## The Two Student Tracks

Track 1 — OJT Track:
- 12 weeks technical training + 8 weeks paid OJT on Waifinder
  client engagement, supervised by Gary
- Capacity constrained by available client projects
- Premium path, strongest placement outcomes

Track 2 — Direct Placement Track:
- Training and career services leading directly to placement
- No OJT required
- Scales independently of client projects
- Primary path for majority of students

Both tracks converge at Talent Showcase and placement stage.

## Student Journey Stages and Tracking Fields

Stage 1: Intake
Resume uploaded. Career Services Agent parses. Profile Agent
creates record. Skills normalized. Gap analysis run. Completeness
score calculated.
Fields: intake_date, resume_uploaded, resume_parsed,
parse_confidence_score, profile_completeness_score,
missing_required_fields, missing_preferred_fields

Stage 2: Assessment
Gap score calculated. Upskilling pathway recommended. CFA staff
reviews. Track and cohort assigned.
Fields: assessment_date, gap_score, track_assigned, cohort_id,
assessment_outcome

Stage 3: Training
Cohort enrolled. Milestones tracked. Skills updated. Career
services engaged. Student Portal activated.
Fields: training_start_date, training_milestones_completed,
career_services_stage, match_score_current

Stage 3b: OJT (OJT Track only)
Deployed on Waifinder client engagement. Supervised by Gary.
Fields: ojt_start_date, ojt_end_date, ojt_client_id,
ojt_performance_rating, ojt_skills_added

Stage 4: Job Readiness
Final gap analysis. Resume finalized. Interview prep. Showcase
eligibility evaluated. CFA staff activates if eligible.
Fields: job_ready_date, final_gap_score, resume_finalized,
showcase_eligible, showcase_active, showcase_activated_date

Stage 5: Active in Talent Showcase
Visible to registered employers. Interest signals logged.
Fields: showcase_views_count, showcase_shortlists_count,
showcase_contact_requests_count, employer_interest_signals

Stage 6: Placement
Interview, offer, placement recorded. Showcase deactivated.
Fields: placement_date, placement_employer_id, placement_role,
placement_salary, placement_type, placement_fee_applicable

Stage 7: Post-Placement
30/90/180 day check-ins. Employment confirmed. Alumni created.
Fields: checkin_30_day, checkin_90_day, checkin_180_day,
employment_confirmed, alumni_status

## Talent Showcase Activation Trigger

Student becomes discoverable when ALL are true:
- All required profile fields populated (completeness = 100%)
- Gap score >= 50
- Resume parsed and finalized
- Career services stage = ready or active
- Training milestone baseline reached (NOT OJT completion)
- CFA staff explicitly sets showcase_active = true

NEVER fully automatic. Human confirmation always required.
Students CAN be discoverable while still in OJT.

Deactivation: placed, withdrawn, manually deactivated, skills stale

## Profile Completeness Model

Required fields (100% needed for showcase eligibility):
full_name, email, skills (min 3 normalized), education
(institution + degree), location, availability_status, resume_file

Preferred fields:
phone, linkedin_url, graduation_year, field_of_study,
project_highlights, career_objective, expected_salary_range,
work_authorization, certifications

Calculated fields:
- required_fields_complete (0.0-1.0)
- preferred_fields_complete (0.0-1.0)
- profile_completeness_score (required 70%, preferred 30%)
- missing_required (array of field names)
- missing_preferred (array of field names)
- showcase_eligible (boolean)

Recalculate automatically on every profile field update.

## Historical Data Migration (5,000+ Dynamics Records)

Migrate everyone. Tag every record. No deletions.

Migration tags:
source_system, migration_date, original_record_id,
pipeline_status (active/placed/alumni/dropped_out/unknown),
engagement_level (high/medium/low/none),
data_quality (complete/partial/minimal), last_active_date,
program_stage_reached, track, cohort_id, placement_count,
re_engagement_eligible, re_engagement_status, showcase_eligible

Resume Parsing Transformation:
For every migrated record with resume in Blob Storage but empty
profile fields:
1. Check Blob Storage for resume file linked to student ID
2. If found → send to Claude API for structured extraction
3. Extract: name, email, phone, education, work history, skills,
   projects, certifications
4. Normalize skills to taxonomy
5. Populate PostgreSQL fields
6. Calculate parse_confidence_score (0.0-1.0)
7. >0.8 → auto-populate
8. 0.5-0.8 → partial, flag for review
9. <0.5 → flag for re-engagement
10. No resume → resume_missing=true, trigger outreach

Post-migration segmentation:
- Good data + unknown/seeking → intake queue
- Trained but never placed → high priority re-engagement
- Minimal data + valid email → Student Portal link
- Confirmed placed → alumni archive
- Conflicting data → staff review queue

## AGENT ARCHITECTURE — v2.0

===============================================================
NORTH STAR
===============================================================
Employers and businesses are delighted.
Every build decision is filtered through:
"Does this make the employer experience
faster, clearer, more trustworthy,
or more impressive?"

===============================================================
THREE SYSTEMS
===============================================================

SYSTEM 1: WORKFORCE DEVELOPMENT OS
Manages the training flywheel
- Cohort management and OJT tracking
- Skills assessment and progress
- Placement tracking
- WDB outcome reporting (Alma/WSB)
- Student job matching

SYSTEM 2: PRODUCT INTELLIGENCE PLATFORM
Products built during each cohort
- JIE pipeline (current product)
- Labor market intelligence
- Skills demand analysis
- Regional employer signals
Future products TBD per cohort

SYSTEM 3: AI CONSULTING PLATFORM (Waifinder)
- Client intake and scoping
- Project delivery tracking
- Consulting revenue

===============================================================
ARCHITECTURAL DISTINCTION
===============================================================

Following Anthropic's guidance:

WORKFLOWS (existing — do not change):
LLMs orchestrated through predefined code paths.
These are NOT agents.
- JIE Pipeline (6 agents, sequential)
- Scoping Workflow (agents/scoping/)
- Grant Workflow (agents/grant/)
- Marketing Workflow
- Profile Workflow
- Career Services Workflow

CONVERSATIONAL AGENTS (new layer):
Augmented LLMs that dynamically decide what to do based on context.
Each = Gemini Flash + system prompt + tools + session memory
Tools = existing APIs wrapped for LLM function calling

===============================================================
THE SIX CONVERSATIONAL AGENTS
===============================================================

All powered by Gemini Flash.
All saved to: agents/assistant/
All served by: agents/assistant/api.py
Port: 8009

AGENT 1: Student Agent
File: agents/assistant/student_agent.py
Lives on: /careers, student portal widget
Principle: VALUE BEFORE ASK
Goal: Get student to a job offer fast
Tools: search_jobs, get_job_matches,
       get_gap_analysis, find_training,
       create_profile

AGENT 2: Employer Agent
File: agents/assistant/employer_agent.py
Lives on: /showcase, /for-employers
Principle: TRUST BEFORE ACTION
Goal: Match to candidate OR qualify
      for consulting
Tools: search_candidates,
       get_candidate_profile,
       get_proof_of_work,
       submit_consulting_inquiry,
       get_case_study

AGENT 3: College Agent
File: agents/assistant/college_agent.py
Lives on: /college portal
Principle: DATA THAT CHANGES DECISIONS
Goal: One insight that changes
      curriculum or employer strategy
Tools: get_graduate_stats,
       get_curriculum_gaps,
       get_employer_demand,
       get_placement_rates,
       request_employer_intro

AGENT 4: Consulting Intake Agent
File: agents/assistant/consulting_agent.py
Lives on: /cfa/ai-consulting/chat
Principle: GUIDE DON'T PITCH
Goal: Guide prospect to clarity,
      trigger INTAKE_COMPLETE
Tools: get_case_study, get_blog_post,
       submit_inquiry, check_budget_fit

AGENT 5: Youth Agent
File: agents/assistant/youth_agent.py
Lives on: /youth
Principle: MAKE TECH FEEL ACCESSIBLE
Goal: Get application started
Tools: get_program_info,
       get_application_steps,
       get_career_paths,
       get_financial_assistance

AGENT 6: CFA Staff Agent
File: agents/assistant/staff_agent.py
Lives on: /internal chat interface
Principle: EVERYTHING IN 60 SECONDS
Goal: Answer any operational question
      immediately. Eliminate admin.
Users: Ritu, Gary, Krista, Bethany,
       Leslie, Jason, Jessica
Role-aware: different opening briefing
       per user based on ?user= param
Full access to all APIs and tables
Tools: get_ceo_briefing,
       get_grant_status,
       get_cohort_status,
       get_consulting_pipeline,
       get_placement_status,
       get_payroll_status,
       draft_communication,
       get_student_progress,
       flag_issue

===============================================================
ROUTING (rule-based, not LLM)
===============================================================
/careers            -> Student Agent
/showcase           -> Employer Agent
/for-employers      -> Employer Agent
/college            -> College Agent
/cfa/ai-consulting/chat -> Consulting Agent
/internal           -> Staff Agent (?user=ritu etc)
/youth              -> Youth Agent
/ (homepage)        -> ask user who they are

===============================================================
USER PROFILES
===============================================================

Students:
- Don't want forms, just want jobs
- Show value before asking anything
- One question at a time maximum
- Connect everything to salary

Employers (hiring):
- Need verified job-readiness signals
- Show proof of work not just profiles
- Make contacting CFA frictionless

Employers (consulting):
- All hesitations are real simultaneously
- De-risk at every step
- Fixed price, proof of work,
  try before hire

College partners:
- Need data that changes decisions
- Lead with curriculum gap signals
- Show specific employers hiring
  their graduate profile

Consulting prospects:
- Guide to clarity about their problem
- Never pitch — always ask and listen
- Reference Borderplex naturally

Alma/WSB (Workforce Funder):
- Employer of record, pays apprentice wages
- Needs participant outcomes for board
- Payroll accuracy
- Board-ready reporting on demand
- Funded residents can work anywhere

Ritu (CEO):
- Cross-system visibility on demand
- Tell me what matters in 60 seconds
- Full access to everything

Gary (Technical Lead):
- Admin elimination is the goal
- Surface who's stuck automatically
- Zero coordination overhead

Jason (BD):
- Consulting pipeline and BD focus
- Prospect status and follow-ups
- No access to student PII or
  grant financials

Jessica (Marketing):
- Content approval and campaign status
- Apollo sequence status
- No access to student PII or
  grant financials

===============================================================
VISIBILITY PRINCIPLE
===============================================================
Every user has the same underlying problem:
"I can't see what I need to see
fast enough to act on it."

WFD OS's core job:
Make the right information visible
to the right person at the right moment.

===============================================================
WAIFINDER AS A PRODUCT
===============================================================
Same four components per deployment:
1. Conversational agents
   (configured per client's audiences)
2. Tools layer
   (pointing to client's data)
3. Workflows
   (configured per client's industry)
4. Portals
   (branded per client)

Config-driven not code-driven.
Agents orchestrate reusable platform
services — not rebuilt per deployment.

===============================================================
EXISTING WORKFLOWS (reference)
===============================================================

Scoping Workflow (agents/scoping/)
Trigger: consulting_api.py when inquiry status -> 'scoping'
Pipeline: prospect research -> briefing doc -> SharePoint workspace
-> Teams channel -> online meeting -> post-call transcript analysis
-> proposal doc generation
Graph API credentials: GRAPH_* in .env (app 60a49f2a-...)

Grant Workflow (agents/grant/)
Location: agents/grant/
Powers: /wji dashboard
Pipeline: SharePoint file ingestion, reconciliation, grant reporting.
Uploads: POST /api/wji/upload/placements (WSAC Excel),
         POST /api/wji/upload/payments (QB CSV)

Shared Graph API Library (agents/graph/)
All workflows/agents that need Microsoft 365 access import from here:
- auth.py: ClientSecretCredential + GraphServiceClient (singleton)
- sharepoint.py: Site/workspace/page creation, file uploads, listing
- teams.py: Channel creation, calendar invites, online meetings
- transcript.py: Retrieve meeting transcripts after a call
- config.py: Loads GRAPH_* env vars from .env
- invitations.py: SharePoint folder sharing via drive invite API

Email (agents/portal/email.py)
Microsoft Graph sendMail API. Uses the same GRAPH_* app registration.
Sends branded HTML emails (templates in email_templates.py).
Never crashes the caller — returns status dict.

LLM Client (agents/llm/client.py)
Gemini Flash via google-generativeai SDK.
get_llm_response(messages, system_prompt) — chat completions
get_structured_output(text, instructions) — single-turn extraction

## The Two Pipelines

Pipeline 1: Student -> Placement
Resume upload -> Profile -> Training -> OJT ->
Showcase -> Match -> Placement

Pipeline 2: Prospect -> Waifinder Client
Apollo lead -> Marketing Agent outreach ->
Scoping Agent (Ready to Scope webhook) ->
Proposal -> DocuSeal contract signed ->
Client Onboarding Agent -> Client delivery ->
Reporting Agent -> Ongoing managed services

## The Three Portals

All portals:
- Modernized from existing React app
- Web + mobile responsive
- Tokenized link auth (no password)
- All actions logged to PostgreSQL audit table

Student Portal sections:
My Profile, My Journey, My Matches, My Gap Analysis,
Career Services, My Showcase, Messages

Employer Portal features:
Browse/filter Talent Showcase, favorite/shortlist candidates,
post jobs, manage talent pipeline per job, message candidates
(routed through CFA), hiring history, placement tracking,
request college talent pipeline

College Partner Portal features:
Manage program profile and skills mapping,
see graduates in WFD OS pipeline,
track graduate placement outcomes,
post upcoming cohort availability,
request employer partnerships,
view employer demand in program skill areas,
see graduates on Talent Showcase and employer interest,
receive notifications when employer requests match program,
view skills gap data,
see Waifinder apprenticeship opportunities for graduates

## Discovery Phases (Complete Before Building)

Phase 0: Instance Discovery
https://globaldisco.crm.dynamics.com/api/discovery/v2.0/Instances
Present as table. Proceed with cfahelpdesksandbox as primary.

Phase 1: SQL Database Discovery (PRIMARY)
All tables, columns, FKs, full ERD. Map each table to agent owner.
Generate: SQL Source of Truth Report

Phase 1b: Azure Python Endpoint (CRITICAL)
All source code. Find: embeddings, matching, gap analysis,
ingestion, skills taxonomy. Assess reuse vs. rebuild.
Generate: Python Codebase Report

Phase 1c: Blob Storage
All containers, counts, sizes. Find resumes and model files.
Generate: Blob Storage Report

Phase 1d: Dataverse Deep
All tables including custom. Business Process Flows, audit logs.
Generate: Dataverse Deep Report

Phase 1e-1l: Career Services, Job Listings, College Programs,
Talent Showcase, Matching Engine, React App, Power Flows, Apps
Generate individual reports for each.

Phase 2: Schema Profiling + PostgreSQL Schema Design
Field population rates. Dead fields (<5% = dead).
Design target schema per agent domain.

## Build Sequence

Phase 1 — v1.0 (Ritu Bahl + Claude):
1. Data Discovery -- COMPLETE
2. PostgreSQL Schema -- COMPLETE
3. Data Migration -- COMPLETE
4. Resume Parser Agent -- IN PROGRESS
5. Profile Agent
6. Market Intelligence Agent
7. Employer Matching Agent
8. Matching Agent
9. Career Services Agent
10. College Pipeline Agent
11. Marketing Agent (Apollo)
12. Scoping Agent (integrated from cfa-scoping-agent -- agents/scoping/)
13. Client Onboarding Agent
14. Re-engagement Agent (AFTER Student Portal)
15. Reporting Agent
16. Orchestrator Agent
17. Student Portal
18. Talent Showcase
19. Employer Portal
20. College Partner Portal
21. Grant Agent (migrated from cfa-grant-agent -- agents/grant/)
    Powers the /wji dashboard. File ingestion from SharePoint,
    reconciliation of grant partner submissions.
22. Placement Agent (last)

Phase 2 — Extensions (Cohort 1 apprentices):
Features built during OJT supervised by Gary
as Waifinder Client 0 delivery.

Waifinder Deployment 001: Workforce Solutions Borderplex

## Technical Approach

- PostgreSQL: TARGET system of record
- All existing systems: SOURCE — read only
- Auth: OAuth 2.0 client credentials
- LLM: Claude API (Sonnet most agents, Haiku high-volume extraction)
- Language: Python (agents), React (portals)
- Each agent in its own subfolder
- NO writes to existing systems during discovery

## Key Questions to Answer

1. Full platform across ALL data sources?
2. What Python code exists and what did it do?
3. Are trained embedding models in Blob Storage?
4. Clean PostgreSQL schema per agent domain?
5. Which agent owns which data?
6. What can be migrated now vs. rebuilt?
7. Can existing embeddings/code be reused?
8. What % of 5,000+ students have resumes in Blob Storage?
9. Which agent to build first after discovery?
10. Evidence for cancelling Dynamics?

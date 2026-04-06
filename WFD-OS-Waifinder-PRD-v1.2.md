# WFD OS + Waifinder
# Product Requirements Document
# Version 1.2 — April 2026
# Author: Ritu Bahl

---

## Document Purpose and Audience

This PRD defines requirements for WFD OS and Waifinder. Audience:
- Claude Code — technical spec and agent architecture
- Gary and apprentice delivery team — what we are building and why
- Internal CFA team — strategic context and success criteria

---

## 1. Executive Summary

WFD OS is CFA's internal agent-first platform for managing the
education-to-work placement pipeline. It is a rebuild of CFA's legacy
SaaS platform as an agent-first system using PostgreSQL as the system
of record.

Waifinder is CFA's consulting business. It delivers real agentic
consulting services to clients — building agentic data systems as the
primary value delivered. Waifinder also serves as the OJT stage for
qualified apprentices, who deliver Waifinder engagements under Gary.

CFA is Waifinder Client 0. Ritu Bahl + Claude build WFD OS v1.0.
Cohort 1 apprentices extend WFD OS as their OJT.

---

## 2. Problem Statement

CFA has been connecting students to employers for years but data is
fragmented across a dormant SQL database, Dynamics CRM, Azure Blob
Storage, a React app, Power Apps, and OneNote. Over 5,000 student
records exist with unknown status, incomplete profiles, and
unextracted resume data. Decisions are made without data.

Workforce organizations broadly cannot fill talent needs, connect
training programs to employers, or place job seekers effectively.
Legacy CRMs and spreadsheets were not designed for today's labor market.

AI agents can replace the manual coordination work that makes
workforce development slow and expensive. CFA is uniquely positioned
to build this because we already built a version of it.

---

## 3. Vision and Goals

Vision: An internal operating system where agents handle intelligence
work so CFA staff focus on relationships, coaching, and outcomes.

Goals:
1. Migrate CFA's dormant data into clean PostgreSQL database
2. Build six agents managing the education-to-work pipeline
3. Prove platform with CFA's 5,000+ student records
4. Deploy for one paying Waifinder client by end of 2026
5. Establish Waifinder as CFA's primary earned revenue stream

---

## 4. What WFD OS Is and Is Not

WFD OS is:
- Internal pipeline management tool for CFA staff and agents
- Operational backbone from intake through placement
- Data layer powering all three external portals
- Platform deployed as Waifinder for paying clients

WFD OS is not:
- A student-facing application
- An employer-facing application
- A public job board
- A replacement for CFA's apprenticeship curriculum

External surfaces:
1. Student Portal
2. Employer Portal + Talent Showcase
3. College Partner Portal

---

## 5. About Waifinder

Waifinder is CFA's consulting business delivering real agentic data
engineering services to clients. The true value is the consulting
work itself — not just a software deployment.

Waifinder also serves as the OJT stage. When Waifinder wins a client
engagement, apprentices deliver the work under Gary's supervision,
gaining real experience while the client gets a production system.

The flywheel: Waifinder wins client → apprentices deliver via OJT →
client gets agentic system → CFA's engagement produces WFD OS →
WFD OS manages next cohort → next cohort delivers next engagement.

CFA as Client 0:
- Ritu Bahl + Claude build WFD OS v1.0
- Cohort 1 apprentices extend WFD OS as their OJT under Gary
- WFD OS is the deliverable for CFA as first Waifinder client

---

## 6. Users and Personas

Internal:
- Ritu Bahl — Executive Director, strategic oversight
- Gary — Technical Lead, supervises apprentices
- CFA staff — manage intake, career services, employer relationships
- WFD OS agents — automate pipeline coordination

External:
- Students — interact via Student Portal
- Employers — interact via Employer Portal and Talent Showcase
- College program directors — interact via College Partner Portal

Waifinder clients:
- Workforce boards (e.g., Workforce Solutions Borderplex)
- Healthcare talent acquisition teams
- Professional services HR directors

---

## 7. Student Entry Point

Students upload a resume to signal interest in CFA's program.
This triggers automated intake — Career Services Agent parses the
resume, Profile Agent creates the student record in PostgreSQL,
Orchestrator routes to intake queue for CFA staff review.

Students do not interact with WFD OS directly. All student
interaction happens through the Student Portal.

---

## 8. The Two Student Tracks

Track 1 — OJT Track:
12 weeks technical training + 8 weeks paid OJT on a Waifinder client
engagement supervised by Gary. Capacity constrained by client
projects. Premium path, strongest placement outcomes.

Track 2 — Direct Placement Track:
Training and career services leading directly to placement. No OJT.
Scales independently of client projects. Primary path for most students.

Both tracks converge at Talent Showcase and placement stage.

---

## 9. Student Journey and Pipeline Tracking

Every student has pipeline_status and pipeline_stage tracked at all
times. Every stage transition logged to audit table with timestamp.

Stage 1: Intake
Student uploads resume. Career Services Agent parses. Profile Agent
creates record in PostgreSQL. Skills extracted and normalized.
Initial gap analysis run. Profile completeness score calculated.
Fields: intake_date, resume_uploaded, resume_parsed,
parse_confidence_score, profile_completeness_score,
missing_required_fields, missing_preferred_fields

Stage 2: Assessment
Gap score calculated vs. market demand. Upskilling pathway
recommended. CFA staff reviews. Track and cohort assigned.
Fields: assessment_date, gap_score, track_assigned, cohort_id,
assessment_outcome (accepted/deferred/declined)

Stage 3: Training
Cohort enrolled. Milestones tracked. Skills updated. Career
services engaged. Student Portal activated with tokenized link.
Fields: training_start_date, training_milestones_completed,
career_services_stage, match_score_current

Stage 3b: OJT (OJT Track only)
Deployed on Waifinder client engagement. Supervised by Gary.
Skills updated from real work.
Fields: ojt_start_date, ojt_end_date, ojt_client_id,
ojt_performance_rating, ojt_skills_added

Stage 4: Job Readiness
Final gap analysis. Resume finalized. Interview prep. Showcase
eligibility evaluated. CFA staff activates if eligible.
Fields: job_ready_date, final_gap_score, resume_finalized,
showcase_eligible, showcase_active, showcase_activated_date

Stage 5: Active in Talent Showcase
Visible to registered employers. Interest signals logged.
Matching Agent surfaces new matches.
Fields: showcase_views_count, showcase_shortlists_count,
showcase_contact_requests_count, employer_interest_signals

Stage 6: Placement
Interview arranged, offer accepted, placement recorded.
Showcase deactivated. Placement fee triggered if applicable.
Fields: placement_date, placement_employer_id, placement_role,
placement_salary, placement_type, placement_fee_applicable

Stage 7: Post-Placement
30/90/180 day check-ins. Employment confirmed. Alumni created.
Fields: checkin_30_day, checkin_90_day, checkin_180_day,
employment_confirmed, alumni_status

---

## 10. Talent Showcase

Filterable, searchable database of job-ready profiles embedded
in the Employer Portal. Powered by Profile Agent + Matching Agent.

Activation trigger — student discoverable when ALL true:
- All required fields populated (completeness = 100%)
- Gap score >= 50
- Resume parsed and finalized
- Career services stage = ready or active
- Training milestone baseline reached (NOT OJT completion)
- CFA staff explicitly sets showcase_active = true

Never fully automatic. Human confirmation always required.
Students CAN be discoverable while still in OJT.

Deactivation: placed, withdrawn, manually deactivated, skills stale

Employer filters: skills, education, location, availability,
experience level, track (OJT vs. direct placement)

Employer interaction tracking: views, shortlists, contact requests,
interview outcomes, placement outcomes — all logged with timestamps.

---

## 11. Profile Completeness Model

Required fields (100% needed for showcase eligibility):
full_name, email, skills (min 3 normalized), education
(institution + degree), location, availability_status, resume_file

Preferred fields:
phone, linkedin_url, graduation_year, field_of_study,
project_highlights, career_objective, expected_salary_range,
work_authorization, certifications

Calculated fields on every record:
- required_fields_complete (0.0-1.0)
- preferred_fields_complete (0.0-1.0)
- profile_completeness_score (required 70%, preferred 30%)
- missing_required (array of field names that are null)
- missing_preferred (array of field names that are null)
- showcase_eligible (boolean)

Recalculated automatically on every profile field update.

---

## 12. Historical Data Migration (5,000+ Records)

Migrate everyone from Dynamics. Tag every record. No deletions.

Migration tags:
source_system, migration_date, original_record_id,
pipeline_status (active/placed/alumni/dropped_out/unknown),
engagement_level (high/medium/low/none),
data_quality (complete/partial/minimal), last_active_date,
program_stage_reached, track, cohort_id, placement_count,
re_engagement_eligible, re_engagement_status, showcase_eligible

Resume parsing transformation:
For every migrated record with resume in Blob Storage but empty
profile fields:
1. Check Blob Storage for resume linked to student ID
2. If found → send to Claude API for structured extraction
3. Extract: name, email, phone, education, work history, skills,
   projects, certifications
4. Normalize skills to taxonomy
5. Populate PostgreSQL fields
6. Calculate parse_confidence_score (0.0-1.0)
7. >0.8 → auto-populate all extracted fields
8. 0.5-0.8 → partial population, flag for review
9. <0.5 → flag for re-engagement outreach
10. No resume → resume_missing=true, trigger outreach

Post-migration segmentation:
- Good data + seeking status → active intake queue
- Trained but never placed → high priority re-engagement
- Minimal data + valid email → Student Portal re-engagement
- Confirmed placed/employed → alumni archive
- Conflicting/low-confidence data → staff review queue

---

## 13. Platform Architecture

Target data architecture:
- PostgreSQL — primary system of record
- pgvector — vector embeddings for matching
- Azure Blob Storage — resume and document storage
- All agents read and write to PostgreSQL directly

Infrastructure:
- Azure Functions for agent compute
- WFD-OS App ID: 068d383c-673e-49f9-9784-6496074d4194
- Auth: OAuth 2.0 client credentials
- Language: Python (agents), React (portals)
- LLM: Claude API — Sonnet most agents, Haiku high-volume extraction

---

## 14. The Six Agents

Agent 1: Orchestrator Agent
Master coordinator. Routes tasks, sends portal links, alerts staff,
monitors stale records, daily pipeline summary.
Replaces: Power Automate flows, manual coordination

Agent 2: Profile Agent
Owns all student and employer records. Calculates completeness.
Runs resume parsing. Manages showcase activation. Syncs with Apollo.
Primary store: PostgreSQL — students, employers
Replaces: Dynamics CRM

Agent 3: Market Intelligence Agent (JIE)
Ingests job listings. Normalizes skills. Tracks demand trends.
Three-layer digital role filter. Market intelligence reports.
JIE for Workforce Solutions Borderplex = Deployment 001.
Primary store: PostgreSQL — job_listings, skills_taxonomy
Replaces: existing SQL ingestion pipeline

Agent 4: College Pipeline Agent
College program profiles with skills mapping. Matches employer
requests to pipelines. Cohort graduation alerts.
Primary store: PostgreSQL — colleges, programs, program_skills
Replaces: college profiling layer in SQL

Agent 5: Matching Agent
Vector embeddings via pgvector. Cosine similarity matching.
Ranked matches with explanations. Weekly ready-to-place report.
Assess existing Python code before rebuilding.
Primary store: PostgreSQL with pgvector
Replaces: existing vector engine + Azure Python endpoint

Agent 6: Career Services Agent
Resume parsing. Gap analysis. Upskilling pathways. Resume
optimization. Interview prep. Career coaching. Tracks completions.
CLTI (Nina Zhao / careerslaunch.org) potential integration.
Primary store: PostgreSQL — gap_analyses, upskilling_pathways,
career_services_interactions
Replaces: existing career services layer in SQL

---

## 15. The Three Portals

All portals: modernized from existing React app, web + mobile
responsive, tokenized link auth, all actions logged to PostgreSQL.

Student Portal sections:
My Profile, My Journey, My Matches, My Gap Analysis,
Career Services, My Showcase, Messages

Tokenized links sent at: initial intake, profile incomplete,
new match above threshold, gap analysis update, career services
milestone, showcase activation, employer interest signal,
staff manual send, student request.

Employer Portal features:
Browse/filter Talent Showcase, favorite/shortlist candidates,
post jobs, manage talent pipeline per job, message candidates
(routed through CFA), view hiring history, track placement
outcomes, request college talent pipeline.

College Partner Portal features:
Manage program profile and skills mapping,
see graduates in WFD OS pipeline,
track graduate placement outcomes,
post upcoming cohort availability for employers,
request employer partnerships,
view employer demand in program skill areas,
see graduates on Talent Showcase and employer interest,
receive notifications when employer requests match program,
view skills gap data,
see Waifinder apprenticeship opportunities for graduates.

---

## 16. Technical Requirements

Non-functional:
- All agents stateless and independently deployable
- All agent actions logged to PostgreSQL audit table
- No agent writes to legacy systems without human confirmation
- PII encrypted at rest
- Role-based access control
- Portal tokens expire after 30 days inactivity

Performance:
- Resume parser: each resume within 10 seconds
- Matching Agent: full re-run weekly
- Market Intelligence Agent: new listings within 24 hours
- Profile Agent: query response within 3 seconds
- Career Services Agent: gap analysis within 30 seconds

Tech stack:
- Compute: Azure Functions
- Database: PostgreSQL + pgvector
- Storage: Azure Blob Storage
- Auth: Microsoft Entra ID
- LLM: Claude API (Sonnet / Haiku)
- Language: Python (agents), React (portals)
- Version control: GitHub

---

## 17. Build Sequence

Phase 1 — v1.0 (Ritu Bahl + Claude, now to Q3 2026):
1. Data Discovery — all sources, all reports
2. PostgreSQL Schema Design — reviewed with Gary
3. Data Migration + Resume Parsing Transformation
4. Profile Agent
5. Market Intelligence Agent (JIE)
6. Matching Agent
7. Career Services Agent
8. Orchestrator Agent
9. College Pipeline Agent
10. Student Portal
11. Talent Showcase
12. Employer Portal
13. College Partner Portal

Phase 2 — Extensions (Cohort 1 apprentices, Q3 2026+):
Features built during OJT supervised by Gary as Client 0 delivery.
Waifinder Deployment 001: Workforce Solutions Borderplex.

---

## 18. Success Metrics

Platform health:
Active profiles by stage and track, completeness distribution,
parse success rate, showcase activation rate, employer engagement.

Outcomes:
Placement rate by track, time to placement, employer return rate,
career services vs. placement correlation, re-engagement rate.

Business (Waifinder):
Paying clients, revenue per engagement, placement fees
(15-20% first year salary), managed services revenue.

---

## 19. Out of Scope v1.0

LinkedIn Sales Navigator, Dynamics marketing automation,
automated email without human review, writes to legacy systems
during discovery, real-time video or chat.

---

## 20. Open Questions

1. Which SQL tables map to which agents?
2. Can existing vector embeddings be reused?
3. Is Azure Python endpoint code recoverable?
4. What custom Dataverse entities exist?
5. What is CLTI API capability?
6. JIE Deployment 001 go-live date with WSB?
7. What % of 5,000+ students have resumes in Blob Storage?
8. Minimum viable Student Portal for v1.0?

---

## 21. Glossary

WFD OS — CFA's internal agent-first pipeline management platform.
Waifinder — CFA's consulting business. WFD OS for paying clients.
JIE — Job Intelligence Engine. Market Intelligence Agent for WSB.
Student Portal — Student interface for profile and journey tracking.
Employer Portal — Employer interface for talent discovery and hiring.
College Partner Portal — College interface for program management.
Talent Showcase — Filterable student profiles in Employer Portal.
Skills taxonomy — Normalized vocabulary across students, jobs, programs.
Gap analysis — Student skills vs. target job requirements.
Profile completeness score — Weighted measure of profile completeness.
Parse confidence score — Resume parsing quality, 0.0-1.0.
pgvector — PostgreSQL extension for vector embeddings.
OJT Track — Students completing OJT on Waifinder client engagement.
Direct Placement Track — Students placed directly without OJT.
Client 0 — CFA itself, first Waifinder proof-of-concept.
CFA — Computing for All.
WSB — Workforce Solutions Borderplex.
Alma — Director at WSB, primary JIE end user.
Cohort — Group of apprentices going through program together.

---

## 22. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | April 2026 | Ritu Bahl | Initial draft |
| 1.1 | April 2026 | Ritu Bahl | Student journey, two tracks, showcase trigger, profile completeness, resume parsing, Student Portal |
| 1.2 | April 2026 | Ritu Bahl | Employer Portal, College Partner Portal, Waifinder as consulting business, CFA as Client 0, correct author name |

---

*Maintained in WFD OS project repository.
Update when significant architectural decisions change.*

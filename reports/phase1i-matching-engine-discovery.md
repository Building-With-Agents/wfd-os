# Phase 1i: Vector Embedding & Matching Engine Discovery
**Date:** 2026-03-30

---

## Executive Summary

The matching engine's core asset — **5,034 skills with 1536-dimensional vector embeddings** — is fully intact in the BACPAC backup. The embeddings were generated using an OpenAI model (ada-002 or text-embedding-3-small, both produce 1536 dimensions). Two Azure OpenAI resources with `text-embedding-3-small` and `GPT-4.1 Mini` are deployed and ready. The matching logic was built with Prisma ORM in a Next.js/React stack, with match results stored in `JobseekerJobPosting` including `totalMatchScore`, `gapAnalysis`, and `elevatorPitch` fields.

**Bottom line: The embeddings are reusable. The matching infrastructure is recoverable. The WFD OS Matching Agent has a running start.**

---

## 1. Skills Taxonomy

### Overview
- **5,034 unique skills** with vector embeddings
- **5,682 total embedding records** (some skills have multiple variants)
- **Source:** Lightcast Open Skills taxonomy (skills linked to `lightcast.io/open-skills` URLs)
- **Skill types:** Hard skills, Soft skills, Certifications

### Taxonomy Structure
```
Career Pathways (6)
  └── Skill Subcategories (45+)
       └── Skills (5,034 with embeddings)
```

### Career Pathways
1. **Cybersecurity** — Protecting systems, networks, data from breaches
2. **Profession Skills Training** — Cross-cutting professional skills
3. **Design and User Experience** — UX/UI design
4. **Data Analytics** — (implied from DataAnalyticsRating table)
5. **IT/Cloud** — (implied from ITCloudRating table)
6. **Software Development** — (implied from SoftwareDevRating table)

### Skill Subcategories (45+ discovered)
AI/ML, AR/VR, Blockchain, Cloud Solutions, Computer Science, Cybersecurity, Data Visualization, Distributed Computing, ETL, General Networking, Geospatial Technology, IDEs, iOS Development, IT Management, IoT, JavaScript/jQuery, Mainframe Technologies, Malware Protection, Microsoft Windows, Middleware, Network Protocols, Programming Languages, Query Languages, Scripting Languages, Search Engines, Software Development, Systems Administration, Technical Support, Telecommunications, Test Automation, Version Control, Video Conferencing, Virtualization, Web Conferencing, Wireless Technologies, XML/Extensible Languages, Business Operations, Relationship Building & Emotional Intelligence, Critical Thinking & Problem Solving, Team Collaboration

### Sample Skills (from 5,034)
API-based tools, Agile Coaching, Agile Leadership, Augmented Reality, AWS Backup, Blockchain, Circuit Diagrams, Client Onboarding, Cloud Security, CRM Systems, Cybersecurity, Data Visualization, Fabrication, Generative AI (LLMs), Hand Tools, Industrial Automation, JIRA, Kanban, Machine Operation, Materials Science, Metaverse, Network Protocols, Pair Programming, Physics, Prompt Engineering, Root Cause Analysis, Salesforce, Soldering, Sprint Planning, Test-Driven Development, Troubleshooting, User Experience, Virtual Reality, VMware, Writing...

---

## 2. Embedding Model

### Specifications
- **Dimensions:** 1536
- **Format:** Float array stored as SQL `vector(1536)` type
- **Sample values:** `[-2.6288984e-002, 1.3544795e-002, 1.4651086e-002, ...]`
- **Data size:** 260 MB (embeddings only)

### Which Model Generated These?
- **1536 dimensions** matches two OpenAI models:
  - `text-embedding-ada-002` (legacy, 1536 dims)
  - `text-embedding-3-small` (current, default 1536 dims)
- CFA has `text-embedding-3-small` deployed in Azure OpenAI (`embeddings-te3small`)
- Most likely generated with **text-embedding-3-small** given the deployment name

### Can These Embeddings Be Reused?
**YES — with caveats:**
- If generated with `text-embedding-3-small`: **Directly reusable** — same model is still deployed
- If generated with `text-embedding-ada-002`: **Partially reusable** — can still compute cosine similarity, but new embeddings should use the same model for consistency
- **Recommendation:** Re-embed with `text-embedding-3-small` to ensure consistency, but use existing embeddings as baseline while rebuilding

---

## 3. Matching Engine Architecture

### Data Flow (Recovered)
```
[Student Profile] → [Resume Upload] → [Skill Extraction]
                                            ↓
[Job Posting] → [Skill Requirements] → [Embedding Generation]
                                            ↓
                    [Cosine Similarity Matching]
                                            ↓
                    [JobseekerJobPosting Record]
                    ├── totalMatchScore
                    ├── gapAnalysis
                    ├── elevatorPitch
                    ├── generatedResume
                    └── linkedInProfileUpdate
```

### Match Result Schema (`JobseekerJobPosting` — 19 columns)
| Column | Purpose |
|--------|---------|
| jobPostId | Target job posting |
| jobseekerId | Student/jobseeker |
| jobStatus | Application status |
| totalMatchScore | Overall match percentage |
| gapAnalysis | AI-generated gap analysis text |
| elevatorPitch | AI-generated elevator pitch |
| generatedResume | AI-tailored resume version |
| linkedInProfileUpdate | AI LinkedIn suggestions |
| isBookmarked | Student saved this match |
| employerClickedConnect | Employer expressed interest |
| feedbackRating | Match quality feedback |
| feedbackText | Detailed feedback |
| analysisDate | When matching was run |

### Skill-Level Match Detail (`JobseekerJobPostingSkillMatch`)
| Column | Purpose |
|--------|---------|
| jobseekerJobPostingId | Parent match record |
| jobSkill | Required skill from job posting |
| jobseekerSkill | Matching skill from student |
| matchScore | Skill-level similarity score |

---

## 4. Supporting Tables

### Student Skills (`jobseeker_has_skills`)
- Links students to skills from the 5,034-skill taxonomy
- ~64 KB of data (hundreds of student-skill associations)

### Pathway-Specific Skill Ratings
Six detailed assessment tables with granular ratings:

| Table | Skills Rated | Rating Type |
|-------|-------------|-------------|
| CybersecurityRating | 13 skills | networking, cryptography, cloud security, incident response... |
| DataAnalyticsRating | 16 skills | SQL, Python, R, Tableau, ML, data viz, algorithms... |
| ITCloudRating | 16 skills | Active Directory, help desk, Windows servers, virtualization... |
| SoftwareDevRating | 16 skills | SDLC, languages, architecture, DevOps, cloud, debugging... |
| DurableSkillsRating | 20 skills | empathy, time management, communication, teamwork, leadership... |
| BrandingRating | 18 skills | personal brand, resume, interview, networking, mentorship... |

### Employer Feedback (`EmployerJobRoleFeedBack`)
- Likert ratings from employers on job role skills
- Closes the loop: employer signals → skill relevance → taxonomy refinement

---

## 5. Azure OpenAI Resources (Ready to Use)

### resumeJobMatch (Primary)
- **Endpoint:** https://resumejobmatch.openai.azure.com/
- **Deployments:**
  - `chat-gpt41mini` — GPT-4.1 Mini (reasoning, gap analysis, elevator pitches)
  - `embeddings-te3small` — text-embedding-3-small (vector embeddings)
- **API Key:** Retrieved and stored in .env

### myOAIResource508483 (Secondary/Backup)
- **Endpoint:** https://myoairesource508483.openai.azure.com/
- **Same deployments** as primary

---

## 6. What Was Built vs. What Was Used

| Component | Built? | Used? | Data Volume |
|-----------|--------|-------|-------------|
| Skills taxonomy | YES | YES | 5,034 skills with embeddings |
| Embedding generation | YES | YES | 260 MB of vectors |
| Skill subcategories | YES | YES | 45+ categories |
| Career pathways | YES | YES | 6 pathways |
| Job posting ingestion | YES | YES | 1,586 KB of postings |
| Student-skill mapping | YES | YES | 64 KB of associations |
| Resume-to-job matching | YES | **PARTIALLY** | 30 KB (limited matches) |
| Gap analysis generation | YES | **PARTIALLY** | Stored in match records |
| Elevator pitch generation | YES | **PARTIALLY** | Stored in match records |
| AI resume tailoring | YES | **BARELY** | generatedResume field exists |
| LinkedIn optimization | YES | **BARELY** | linkedInProfileUpdate field exists |
| Employer feedback loop | YES | **BARELY** | EmployerJobRoleFeedBack exists |
| RAG pipeline | YES | **NEVER** | RAGRecordManager is empty |

---

## 7. Assessment: Reuse vs. Rebuild

### Reuse Immediately
- **5,034 skill embeddings** — load into WFD OS Matching Agent as baseline taxonomy
- **Lightcast skill IDs** — maintain compatibility with external labor market data
- **Skill subcategory taxonomy** — 45+ categories already organized
- **Career pathway definitions** — 6 pathways with descriptions
- **Azure OpenAI deployments** — GPT-4.1 Mini + text-embedding-3-small ready to go
- **Pathway rating schemas** — 99 granular skill ratings across 6 assessment tables

### Rebuild as Agent
- **Matching algorithm** — was in React app code (Prisma/Next.js), rebuild as Matching Agent tool
- **Gap analysis** — was likely GPT-generated (field exists), rebuild as Career Services Agent tool
- **Elevator pitch/resume generation** — fields exist but barely used, full build needed
- **RAG pipeline** — table exists but empty, build fresh for Career Services Agent
- **Employer feedback loop** — schema exists, needs agent-driven activation

### Key Insight
The **data layer is rich** (5,034 skills, embeddings, taxonomy, pathways, ratings). The **intelligence layer was barely activated** (matching ran but gap analysis, resume generation, and employer feedback were minimal). WFD OS agents don't need to rebuild the data — they need to **activate the intelligence** that was already designed but never fully turned on.

---

## Next Steps

1. **Load skill embeddings** into a working database for the Matching Agent
2. **Test embedding quality** — run sample cosine similarity queries
3. **Map student-to-skill associations** from both SQL and Dataverse
4. **Locate the React app source code** on WatechProd-v2 VM (Phase 1j) — this contains the matching logic
5. **Build Matching Agent prototype** using existing embeddings + Azure OpenAI

# Phase 1i: Vector Embedding & Matching Engine Discovery
**Date:** 2026-04-02

---

## Embedding Data

### Skills Embeddings (SQL → Local PostgreSQL)

| Metric | Value |
|--------|-------|
| Table | skills (migrated to wfd_os.public.skills) |
| Records | 5,061 |
| Embedding size | ~20,700 chars each (text field) |
| Total size | 259 MB (BACPAC) / 85 MB (PostgreSQL) |
| Model (likely) | text-embedding-3-small (1,536 dimensions) |
| Format | JSON-serialized float array stored as TEXT |
| Skill types | Hard skills (confirmed from sample data) |

**Sample skills:** Abend-AID, ABR Routers, Abstract Data Types,
Abstraction Layers, Abstractions

### Azure OpenAI Resources

| Resource | Model | Status |
|----------|-------|--------|
| resumejobmatch.openai.azure.com | GPT-4.1 Mini + text-embedding-3-small | Deployed, keys in .env |
| myoairesource508483.openai.azure.com | Unknown | Secondary resource |

## Matching Algorithm

**No matching code was found in any recovered codebase.**

The function app (cs-copilot-py-w2) is a stub. No cosine similarity,
no vector search, no ranking logic exists in recovered code.

### What the SQL schema tells us about matching design:

| Table | Purpose | Implication |
|-------|---------|-------------|
| skills (with embeddings) | Skill vectors for similarity | Cosine similarity was planned |
| jobseeker_has_skills | Student ↔ skill links | Direct skill matching possible |
| _JobPostingSkills | Job ↔ skill links | Job-skill matching possible |
| JobRoleSkill | Role ↔ skill + importance_level | Weighted skill matching |
| JobseekerJobPosting | Student ↔ job applications | Match history/outcomes |
| bookmarked_jobseekers | Employer interest signals | Implicit match validation |

### Likely intended matching flow:
1. Student skills → embeddings via text-embedding-3-small
2. Job posting skills → embeddings (same model)
3. Cosine similarity between student embedding vector and job embedding vector
4. Rank by similarity score
5. Return top-N matches with explanations

**This flow was designed but never automated.** Manual matching was
done by CFA staff (13 employer matching folders found in SharePoint).

## Blob Storage Model Files

**No model files found.** No .pkl, .bin, .pt, or .onnx files in any
Blob Storage container. This confirms embeddings were generated via
the Azure OpenAI API (not a locally-trained model) and stored
directly in the SQL skills table.

## Match History and Outcomes

| Data | Source | Status |
|------|--------|--------|
| JobseekerJobPosting | SQL | Applications/matches tracked |
| bookmarked_jobseekers | SQL | Employer bookmarks |
| Placement outcomes | None | Not tracked |
| Match scores | None | Not computed/stored |

## Can Existing Embeddings Be Reused?

**Yes, with caveats:**

| Factor | Assessment |
|--------|-----------|
| Model | text-embedding-3-small is current and supported |
| Dimensions | 1,536 (standard) |
| Coverage | 5,061 skills — comprehensive taxonomy |
| Format | JSON text → needs conversion to pgvector format |
| Freshness | Pre-2025-11-18 — skills taxonomy may need updates |
| Quality | Professional skill names → should embed well |

**Recommendation:**
1. Convert existing embeddings from JSON text to pgvector float arrays
2. Enable pgvector extension in PostgreSQL
3. Store in vector column for native similarity search
4. Re-embed any new skills added after migration
5. For student/job matching, generate new embeddings using
   composite text (not just skill names)

---

## Summary for Matching Agent Build

| Asset | Status | Action |
|-------|--------|--------|
| 5,061 skill embeddings | In local PG (text) | Convert to pgvector format |
| Azure OpenAI (embedding model) | Deployed, keys available | Use for new embeddings |
| Cosine similarity logic | Does not exist | Build as Matching Agent |
| Match ranking/explanation | Does not exist | Build with Claude reasoning |
| Student-skill links | In SQL BACPAC | Migrate to PostgreSQL |
| Job-skill links | In SQL BACPAC | Migrate to PostgreSQL |
| Match history | Minimal in SQL | Migrate what exists |
| pgvector extension | Not yet installed | Install in local PG |

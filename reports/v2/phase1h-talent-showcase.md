# Phase 1h: Talent Showcase Discovery
**Date:** 2026-04-02

---

## Showcase Data Sources

### SQL/BACPAC

| Table | Content | Relevance |
|-------|---------|-----------|
| jobseekers | Student profiles with is_featured, status | Showcase candidates |
| bookmarked_jobseekers | Employer ↔ student bookmarks | Employer interest signals |
| jobseeker_has_skills | Student ↔ skill mappings | Showcase skill filters |
| JobseekerJobPosting | Student ↔ job applications/matches | Match history |

### Dataverse

| Entity | Content | Relevance |
|--------|---------|-----------|
| contacts (266 custom fields) | Full student profiles | Showcase source data |
| cfa_studentdetails (2,139) | Extended profiles | Showcase eligibility |
| cfa_reactportalusers (314) | Portal activations | Who used self-service |

## Employer Filter Capabilities (from SQL schema)

Available filter dimensions based on existing data:
- **Skills** — via jobseeker_has_skills (linked to 5,061 skill taxonomy)
- **Location** — city, state, zipcode on jobseeker record
- **Education** — institution, degree, field_of_study
- **Experience** — years_experience, work_experiences
- **Status** — is_featured flag on jobseeker record
- **Industry** — via employer's industry_sector

**Missing filters needed for WFD OS Talent Showcase:**
- Availability status (not tracked)
- Track (OJT vs. Direct Placement — not in legacy data)
- Gap score / readiness level (not computed)
- Profile completeness score (not computed)

## Profile Completeness

No profile completeness scoring exists in any data source.
The WFD OS Profile Completeness Model defines:
- Required fields: full_name, email, skills (3+), education, location,
  availability_status, resume_file
- Preferred fields: phone, linkedin, graduation_year, etc.
- Weighted score: required 70%, preferred 30%

**This must be computed during migration** by checking which fields
are populated per student record.

## Employer Engagement

| Signal | Data Source | Found? |
|--------|-----------|--------|
| Showcase views | None | **No** |
| Shortlists/favorites | bookmarked_jobseekers (SQL) | **Yes** (very small) |
| Contact requests | None | **No** |
| Interview outcomes | None | **No** |
| Placement from showcase | None | **No** |

**Assessment:** Employer engagement tracking was minimal. The bookmark
feature existed but was barely used. No view tracking, no funnel analytics.

## Outcomes

No placement outcome data was found linked to the showcase.
The system tracked who was bookmarked but not what happened after.

---

## Summary for Talent Showcase Build

| Asset | Status | Action |
|-------|--------|--------|
| Student profiles (5,000+) | In Dataverse | Migrate, compute completeness |
| Skills per student | In SQL | Migrate jobseeker_has_skills |
| Employer bookmarks | In SQL (minimal) | Migrate as seed data |
| is_featured flag | In SQL | Use as initial showcase_active |
| View/engagement tracking | Does not exist | Build in Employer Portal |
| Completeness scoring | Does not exist | Compute during migration |
| Showcase activation rules | Defined in CLAUDE.md | Implement in Profile Agent |

# Phase 1e: Career Services Layer Discovery
**Date:** 2026-04-02

---

## Resume Data

| Source | Count | Format | Status |
|--------|-------|--------|--------|
| Blob Storage (resume-storage) | 1,515 PDFs | `{guid}/resume.pdf` | Unprocessed |
| Blob Storage (OCR experiments) | 15 JSONs | `{guid}/resume.pdf.ocr.json` | Incomplete experiment |
| SQL (jobseekers.resume_url) | Unknown | URL references | May point to Blob GUIDs |
| Dataverse (contact fields) | Unknown | resume_data custom field | May contain parsed text |

**Cross-reference:** 1,515 resumes / 2,139 student details = ~71% coverage.
The remaining 29% may have enrolled without submitting resumes or their
resumes may be linked via different IDs.

## Career Pathway Assessments (SQL)

Six rating schemas covering 99 skill dimensions:

| Schema | Table | Dimensions | Records | Coverage |
|--------|-------|-----------|---------|----------|
| Personal Branding | BrandingRating | ~18 | Very few | Barely used |
| Cybersecurity | CybersecurityRating | ~18 | Very few | Barely used |
| Data Analytics | DataAnalyticsRating | ~18 | Very few | Barely used |
| Durable/Soft Skills | DurableSkillsRating | ~18 | Very few | Barely used |
| IT/Cloud | ITCloudRating | ~18 | Very few | Barely used |
| Software Development | SoftwareDevRating | ~18 | Very few | Barely used |

**Assessment:** The assessment frameworks were designed but barely activated.
The schemas define a comprehensive 99-dimension rubric that the Career
Services Agent can operationalize at scale.

## Case Management (SQL)

| Table | Records | Content |
|-------|---------|---------|
| CaseMgmt | Very few | Student-advisor case records |
| CaseMgmtNotes | Very few | HTML-formatted notes with categories |

**Assessment:** Minimal usage. Case management was largely manual/offline.

## Gap Analysis

No computational gap analysis logic was found in any codebase.
The contact entity in Dataverse has gap_score and readiness_level fields,
but no code exists to calculate these. The Career Services Agent will
need to build gap analysis from scratch using:
- Student skills (from resume parsing + profile)
- Target job requirements (from Market Intelligence Agent)
- Career pathway rubrics (from the 6 rating schemas)

## Upskilling Pathways (SQL)

| Table | Records | Content |
|-------|---------|---------|
| pathways | Small | Career pathway definitions |
| PathwayTraining | Small | Pathway ↔ training links |
| Training | ~60+ | Training resources with providers, URLs, costs |
| JobRoleTraining | Small | Role ↔ training links |

**Assessment:** A basic training catalog exists linking pathways to
training resources to job roles. The Career Services Agent can use
this as the foundation for personalized upskilling recommendations.

## Correlation: Career Services → Placement

No placement tracking data was found in any system. The
Dataverse contact entity likely has placement-related fields, but
systematic outcome tracking was not implemented. This is a gap
the WFD OS Orchestrator Agent must address.

---

## Summary for Career Services Agent Build

| Asset | Status | Action |
|-------|--------|--------|
| 1,515 resumes in Blob Storage | Ready | Parse via Claude API |
| 6 career pathway schemas (99 dims) | Ready | Use as assessment framework |
| Case management data | Minimal | Rebuild in PostgreSQL |
| Gap analysis logic | Does not exist | Build from scratch |
| Training catalog | Basic | Expand and link to market data |
| Placement tracking | Does not exist | Build as Stage 6-7 tracking |

# Phase 1c: Azure Blob Storage Discovery — Blob Storage Report
**Date:** 2026-04-02
**Storage Account:** careerservicesstorage
**Location:** Azure (connection string in .env)
**Total containers:** 4
**Total blobs:** 1,637
**Total size:** ~272.8 MB

---

## Executive Summary

The Blob Storage account contains **1,531 student resumes** (198.6 MB,
nearly all PDF), a BACPAC database backup, and user avatar images.
No trained model files were found. A small set of OCR/labeling JSON
files suggests a resume parsing experiment was started but not completed.

---

## Container Inventory

### 1. resume-storage — PRIMARY ASSET

| Metric | Value |
|--------|-------|
| Total blobs | 1,531 |
| Total size | 198.6 MB |
| Date range | 2024-12-06 to 2025-11-17 |
| PDF files | **1,515** (197.1 MB) |
| JSON files | 15 (1.5 MB) |
| Other | 1 stray .bacpac (4 bytes, empty) |

**Storage pattern:** `{guid}/resume.pdf`
- Each resume stored under a UUID directory
- UUID likely corresponds to a jobseeker_id or contact record
- Consistent naming: always `resume.pdf`

**JSON files (OCR experiment):**
- Pattern: `{guid}/resume.pdf.ocr.json` and `{guid}/resume.pdf.labels.json`
- Only ~7-8 resumes had OCR processing attempted
- Suggests a Form Recognizer / Document Intelligence experiment
- Never scaled to full corpus

**Resume parsing status:**
- 1,515 PDF resumes available for Career Services Agent
- Zero have been systematically parsed and extracted
- This is the primary data enrichment opportunity

### 2. image-storage

| Metric | Value |
|--------|-------|
| Total blobs | 104 |
| Total size | 19.3 MB |
| Date range | 2024-08-31 to 2026-02-06 |
| File types | PNG, JPG, JPEG, SVG, WEBP |

User avatar / profile images uploaded through the React app.
Low priority for migration — images can be re-uploaded.

### 3. bacpac-backups

| Metric | Value |
|--------|-------|
| Total blobs | 1 |
| Total size | 54.9 MB |
| Date | 2025-11-18 |

Single BACPAC file — this is the same backup already recovered to
`recovered-code/bacpac/prod.bacpac` (57.6 MB local copy).

### 4. azure-webjobs-hosts

| Metric | Value |
|--------|-------|
| Total blobs | 1 |
| Total size | 0 B |
| Date | 2025-06-03 |

System container for Azure Functions host metadata. Empty/negligible.

---

## What Was NOT Found

| Expected Asset | Found? | Implication |
|----------------|--------|-------------|
| Trained model files (.pkl, .bin, .pt) | **No** | Embeddings were generated via Azure OpenAI API, not local models |
| Raw job listing CSVs/JSONs | **No** | Job ingestion wrote directly to SQL/Dataverse, not Blob Storage |
| Data exports | **No** | No bulk exports from SQL or Dynamics |
| DOCX resumes | **No** | All resumes are PDF only |
| Log files | **No** | No execution logs from the Python endpoint |

---

## Agent Ownership Mapping

| Container | Agent Owner | Priority |
|-----------|------------|----------|
| resume-storage (PDFs) | Career Services Agent | **HIGH** — 1,515 unprocessed resumes |
| resume-storage (OCR JSONs) | Career Services Agent | LOW — incomplete experiment |
| image-storage | Profile Agent | LOW — avatar images |
| bacpac-backups | N/A (already recovered) | DONE |
| azure-webjobs-hosts | N/A (system) | IGNORE |

---

## Resume-to-Student Linking Strategy

To connect the 1,515 resumes to student records:

1. **Extract GUIDs from blob paths** — each resume is stored as `{guid}/resume.pdf`
2. **Match GUIDs to Dataverse contact IDs** — the GUIDs likely correspond to
   `contactid` in the Dynamics contacts entity
3. **Cross-reference with cfa_studentdetails** — link to extended student profiles
4. **After migration to PostgreSQL** — store blob path reference in student record,
   trigger Career Services Agent resume parsing pipeline

**Estimated coverage:** 1,515 resumes / 2,139 student details = **~71%** of
students with known detail records have resumes. Some resumes may belong to
contacts not in cfa_studentdetails (e.g., applicants who never enrolled).

---

## Migration Recommendation

1. **Do NOT copy resumes to local storage for testing** — access via Blob SDK
2. **Keep resumes in Blob Storage permanently** — it's the right store for files
3. **Build resume parsing pipeline** that reads from Blob → parses via Claude API →
   writes structured data to PostgreSQL
4. **Track parsing status per student** — resume_parsed, parse_confidence_score,
   parse_date in PostgreSQL

---

*Source: Live query of careerservicesstorage via azure-storage-blob SDK*
*Script: scripts/blob_discovery.py*

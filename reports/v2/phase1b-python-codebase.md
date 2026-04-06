# Phase 1b: Azure Python Endpoint Discovery — Python Codebase Report
**Date:** 2026-04-02
**Source:** recovered-code/function-app/ (4 files + deployment zip)
**Deployment:** Azure Function App "cs-copilot-py-w2" (Python 3.11)
**Last deployed:** 2026-02-11

---

## Executive Summary

The recovered Azure Function App is a **stub/skeleton only**. It contains
a single HTTP endpoint (`POST /api/copilot`) designed as a backend for
Copilot Studio, but the actual AI logic was never implemented. There is
no matching engine, no embedding generation, no gap analysis, no job
ingestion code, and no database connectivity.

**Assessment: Nothing to reuse. Rebuild from scratch as WFD OS agents.**

---

## File Inventory

| File | Size | Purpose |
|------|------|---------|
| function_app.py | ~1 KB | Single HTTP-triggered function (stub) |
| requirements.txt | 33 B | Only dependency: azure-functions==1.20.0 |
| host.json | ~200 B | Standard Azure Functions host config |
| README.md | ~500 B | Setup documentation |
| function-app.zip | ~2 KB | Deployment artifact (identical contents) |

---

## function_app.py — Detailed Analysis

```python
# What it does:
# - Accepts POST /api/copilot with JSON body {"prompt": "..."}
# - Logs the prompt length
# - Returns {"ok": true, "result": "Received prompt of length X"}
# - Has a TODO: "Replace with your Python logic"

# What it does NOT do:
# - No LLM calls (no OpenAI, no Claude, no Azure OpenAI)
# - No database queries (no SQLAlchemy, no psycopg2, no pyodbc)
# - No embedding generation
# - No matching/similarity computation
# - No resume parsing
# - No skills extraction
# - No gap analysis
# - No job ingestion
```

**Trigger:** HTTP POST with Function-level key auth
**Dependencies:** azure-functions only (no AI/ML packages)
**Data access:** None — purely request/response echo

---

## What This Tells Us

1. **The intelligence layer was never deployed as Azure Functions.**
   The function app was a placeholder for connecting Copilot Studio
   to a Python backend. The actual business logic was never wired in.

2. **The real logic was in the React app + SQL database.**
   The Next.js app (running on the Ubuntu VM at WatechProd-v2) likely
   handled matching and profile logic directly via Prisma and the
   SQL database. The Python endpoint was planned but not executed.

3. **The embedding generation happened elsewhere.** The 5,061 skill
   embeddings in the SQL database were generated via Azure OpenAI
   (text-embedding-3-small), likely through a one-time script or
   notebook — not through this function app.

4. **Copilot Studio integration was attempted.** The README confirms
   this was meant to be a Copilot Studio connector, suggesting CFA
   was exploring conversational AI interfaces for the platform.

---

## Reuse Assessment

| Component | Reuse? | Recommendation |
|-----------|--------|----------------|
| function_app.py | **No** | Stub only. No logic to reuse. |
| Architecture pattern | **Partial** | Azure Functions + Python is valid for WFD OS agents |
| Copilot Studio approach | **No** | WFD OS uses direct agent interfaces, not Copilot Studio |
| requirements.txt | **No** | Empty of useful dependencies |

---

## Implications for WFD OS Build

- **No existing Python codebase to assess for reuse** — the agents are
  a greenfield build
- **The matching engine must be built from scratch** — but the skill
  embeddings (5,061 vectors) are available as training/seed data
- **Gap analysis logic does not exist in code** — the rating schemas
  (6 pathways, 99 dimensions) in SQL define the framework but no
  computational logic was recovered
- **Resume parsing was never automated** — 1,531 resumes sit unprocessed
  in Blob Storage

---

*Source: recovered-code/function-app/ (5 files)*
*Function App URL: https://cs-copilot-py-w2-26021101.azurewebsites.net/api/copilot*

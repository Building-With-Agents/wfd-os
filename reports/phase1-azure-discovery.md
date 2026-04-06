# Phase 1: Full Azure Infrastructure Discovery Report
**Date:** 2026-03-30
**Logged in as:** ritu@computingforall.org

---

## Azure Subscriptions

| Subscription | ID | Access |
|---|---|---|
| **CFA pay-as-you-go** | d6e226c1-c645-417e-90b9-34467c145353 | FULL ACCESS |
| **cfax** | e2326475-5424-4c44-998a-fd242d120c13 | FULL ACCESS |
| Azure Sponsorship - 1 | 9731a3f4-6e0b-4fdc-8dbb-a6d74b6fa806 | No access |
| Azure Sponsorship | e7603e19-3860-4d87-abd0-cb3bf2b62670 | No access |

---

## Complete Resource Inventory

### Databases

#### PostgreSQL Flexible Server — `pg-jobintel-cfa-dev`
- **Host:** pg-jobintel-cfa-dev.postgres.database.azure.com
- **Database:** `talent_finder`
- **Version:** PostgreSQL 16
- **SKU:** Standard_B1ms (Burstable)
- **Storage:** 32 GB
- **Admin:** azadmin
- **Location:** West US 2
- **Created:** 2026-03-11 (very recent — 19 days old)
- **Firewall:** Open to all (AllowAll rule)
- **Resource Group:** rg-job-inteligence-engine
- **WFD OS Agent:** Market Intelligence Agent / Matching Agent
- **Note:** This is the JIE (Job Intelligence Engine) database

#### Azure SQL Server — DECOMMISSIONED
- **Evidence:** Logic App connection "ReactPortalSqlProd" (status: Connected)
- **Evidence:** BACPAC backup in Blob Storage (prod-20251117-210037.bacpac, 57 MB)
- **No active Azure SQL server found in any accessible subscription**
- **WFD OS Agent:** Was likely the primary app database for React portal
- **Recovery:** BACPAC can be restored to discover full schema

### Blob Storage

#### `careerservicesstorage` (Primary — career services data)
- **Location:** East US
- **SKU:** Standard_RAGRS (geo-redundant)
- **Blob endpoint:** https://careerservicesstorage.blob.core.windows.net/

| Container | Contents | Count | Size |
|-----------|----------|-------|------|
| **resume-storage** | Student resume PDFs (organized by GUID/resume.pdf) | **1,531 resumes** | **198.6 MB** |
| **image-storage** | Student/user avatar images (GUID/avatar.jpg) | **104 images** | **19.3 MB** |
| **bacpac-backups** | SQL database backup (prod-20251117-210037.bacpac) | 1 file | 57 MB |
| azure-webjobs-hosts | System (webjobs runtime) | — | — |

#### `careerservicesreactb773` (React app storage)
- **Location:** East US
- **SKU:** Standard_LRS

#### `csfuncw226021101` (Function App storage)
- **Location:** West US 2
- **SKU:** Standard_LRS
- Contains function deployment packages

### Compute

#### Azure Function App — `cs-copilot-py-w2-26021101`
- **URL:** https://cs-copilot-py-w2-26021101.azurewebsites.net
- **Runtime:** Python 3.11 on Linux
- **State:** Running
- **Functions:** 1 function — `copilot` (POST /api/copilot)
- **Last Modified:** 2026-02-12
- **Source Code:** RECOVERED (saved to recovered-code/function-app/)
- **Status:** Skeleton/stub — the function accepts a prompt but returns a placeholder. The TODO says "Replace with your Python logic."
- **WFD OS Agent:** Was intended to be the Career Services copilot

#### Virtual Machine — `WatechProd-v2`
- **OS:** Ubuntu 22.04 (Canonical Jammy)
- **Size:** Standard_B2s
- **Location:** East US
- **Purpose:** Likely runs the Career Services React application
- **WFD OS Agent:** Replaced by agent interfaces

### AI / Cognitive Services

#### Azure OpenAI — `resumeJobMatch`
- **Endpoint:** https://resumejobmatch.openai.azure.com/
- **SKU:** S0
- **Deployments:**
  - `chat-gpt41mini` — GPT-4.1 Mini for chat/reasoning
  - `embeddings-te3small` — text-embedding-3-small for vector embeddings
- **WFD OS Agent:** Matching Agent + Career Services Agent

#### Azure OpenAI — `myOAIResource508483`
- **Endpoint:** https://myoairesource508483.openai.azure.com/
- **SKU:** S0
- **Deployments:**
  - `chat-gpt41mini` — GPT-4.1 Mini
  - `embeddings-te3small` — text-embedding-3-small
- **WFD OS Agent:** General purpose / backup

### Integration

#### Logic App — `SQLtoDynamics`
- **Location:** North Central US
- **Purpose:** Syncs data from SQL database to Dynamics CRM
- **SQL Connection:** "ReactPortalSqlProd" (status: Connected)
- **Office 365 Connection:** Active
- **WFD OS Agent:** Orchestrator Agent (replace with agent-to-agent sync)

### Identity (Azure AD B2C)

| B2C Directory | Purpose |
|---|---|
| computingforallusers.onmicrosoft.com | Production user auth |
| computingforallstage.onmicrosoft.com | Staging user auth |
| computingforall003.onmicrosoft.com | Dev/test user auth |

### Communication Services

#### Azure Communication Services — `acs-waifinder-shared`
- **Email service:** CFA-EmailCommunicationService
- **Custom domain:** thewaifinder.com
- **Azure managed domain:** Also configured

### Monitoring

- `wtwc-job-normalizer-sbx` — Application Insights (job normalizer monitoring)
- Failure anomaly detection configured
- Log Analytics workspaces in East US and West US 2

### cfax Subscription Resources

| Resource | Type | Purpose |
|---|---|---|
| CFA CAST | Lab Services | Computer science lab |
| CFAHelpDeskFlow | Power Platform Account | Dynamics CRM Power Platform |
| cfa-test-001-resource | Cognitive Services | AI testing resource |

---

## Data Flow Architecture (Discovered)

```
[React Portal (VM: WatechProd-v2)]
        |
        v
[Azure SQL Database] --BACPAC backup--> [Blob Storage]
        |                                    |
  [Logic App: SQLtoDynamics] -----> [Dynamics CRM (cfahelpdesksandbox)]
        |
        v
[Azure B2C Auth] <-- student/employer login
        |
[Blob Storage: resume-storage] <-- 1,531 resumes
[Blob Storage: image-storage] <-- 104 profile images
        |
[Azure OpenAI: resumeJobMatch]
  |- chat-gpt41mini (reasoning)
  |- embeddings-te3small (vector embeddings)
        |
[PostgreSQL: talent_finder] <-- JIE database (new, 19 days old)
        |
[Function App: cs-copilot-py-w2] <-- Career Services copilot (stub)
```

---

## Key Findings

1. **The original Azure SQL database has been decommissioned** — but a full BACPAC backup exists (Nov 2025). This can be restored to recover the complete schema and data.

2. **Two Azure OpenAI resources** with GPT-4.1 Mini and text-embedding-3-small deployed — these are the embedding models for the matching engine.

3. **1,531 student resumes** in Blob Storage (198.6 MB of PDFs) — this is the Career Services Agent's primary asset.

4. **The Python endpoint is a stub** — the Function App was scaffolded but contains only placeholder logic. The actual matching/embedding code was likely in the original system (possibly on the VM or in the decommissioned SQL database logic).

5. **The PostgreSQL "talent_finder" database is brand new** (created 2026-03-11) — this is likely being built as part of the JIE (Job Intelligence Engine) for Borderplex.

6. **Azure AD B2C** handles all user authentication (production, staging, dev directories).

7. **The SQLtoDynamics Logic App** was the bridge between the React portal's SQL database and Dynamics CRM.

---

## Credentials to Add to .env

```
# PostgreSQL (JIE / talent_finder)
PG_HOST=pg-jobintel-cfa-dev.postgres.database.azure.com
PG_DATABASE=talent_finder
PG_USER=azadmin
PG_PORT=5432
# PG_PASSWORD= [need to retrieve or reset]

# Azure Blob Storage (Career Services)
BLOB_CONNECTION_STRING=DefaultEndpointsProtocol=https;EndpointSuffix=core.windows.net;AccountName=careerservicesstorage;AccountKey=REDACTED

# Azure OpenAI (Resume/Job Matching)
AZURE_OPENAI_ENDPOINT=https://resumejobmatch.openai.azure.com/
# AZURE_OPENAI_KEY= [need to retrieve]

# Function App
FUNCTION_APP_URL=https://cs-copilot-py-w2-26021101.azurewebsites.net/api/copilot
```

---

## Next Steps

1. **Restore the BACPAC** to discover the original SQL schema (Phase 1 primary priority)
2. **Get PostgreSQL password** (reset or retrieve) to explore the talent_finder database
3. **Get Azure OpenAI keys** to test embedding models
4. **SSH into WatechProd-v2 VM** to find the React application source code
5. **Examine the Logic App definition** to understand the SQL-to-Dynamics sync logic

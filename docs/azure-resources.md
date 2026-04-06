# Azure Resources — WFD OS Project

Last updated: April 6, 2026

## Subscription

| Field | Value |
|---|---|
| Name | CFA pay-as-you-go |
| Subscription ID | d6e226c1-c645-417e-90b9-34467c145353 |
| Tenant ID | a3c7a257-40f2-43a9-9373-8bb5fc6862f7 |
| Offer | PayAsYouGo_2014-09-01 |
| Nonprofit credits | NOT YET APPLIED — apply at https://nonprofit.microsoft.com ($3,500/year) |

---

## App Registrations (Entra ID)

### 1. WFD-OS (068d383c-673e-49f9-9784-6496074d4194)

**Setup:** Azure Portal UI
**Purpose:** WFD OS application — Dataverse/Dynamics CRM access
**Used by:** Legacy data discovery, Dynamics API calls
**Permissions:** Dynamics CRM, Dataverse Web API
**Env vars:** `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`

### 2. CFA-Grant-Agent (60a49f2a-230a-4460-bd6d-c0e22bc32384)

**Setup:** Azure Portal UI (originally created for the Grant Agent project)
**Purpose:** Microsoft Graph API access — email, SharePoint, Teams, Calendar
**Used by:** ALL Graph API operations in WFD OS:
- Email sending via `sendMail` (agents/portal/email.py)
- SharePoint workspace creation and file management (agents/graph/sharepoint.py)
- SharePoint folder sharing/invitations (agents/graph/invitations.py)
- Teams channel listing and messaging (agents/graph/teams.py)
- Calendar/meeting scheduling (agents/graph/teams.py)
- Transcript retrieval (agents/graph/transcript.py)

**Permissions (Application):**
- Sites.ReadWrite.All
- Calendars.ReadWrite
- OnlineMeetings.ReadWrite.All
- OnlineMeetingTranscripts.Read.All
- Mail.Send
- ChannelMessage.Send *(added via CLI, pending admin consent)*
- Files.ReadWrite.All
- User.Read.All

**Env vars:** `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`

**Permission added via CLI (this project):**
```bash
az ad app permission add \
  --id 60a49f2a-230a-4460-bd6d-c0e22bc32384 \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions 5922d31f-46c8-4404-9eaf-2117e390a8a4=Role

# Admin consent URL (must be opened in browser by tenant admin):
# https://login.microsoftonline.com/a3c7a257-40f2-43a9-9373-8bb5fc6862f7/adminconsent?client_id=60a49f2a-230a-4460-bd6d-c0e22bc32384
```

---

## Resources Created/Modified via CLI (This Project)

These resources were created or modified using Azure CLI commands during WFD OS development.

| Resource | Type | Resource Group | CLI Command | Purpose |
|---|---|---|---|---|
| `ChannelMessage.Send` permission | App Permission | (Entra ID) | `az ad app permission add --id 60a49f2a-...` | Enable direct Teams channel posting via Graph API |
| `rg-wfdos` | Resource Group | — | `az group create --name rg-wfdos --location eastus` | *(Created but empty — Azure deployment deferred)* |

**CLI commands used for discovery (read-only):**
```bash
az account show                              # Verify subscription
az group list --output table                 # List all resource groups
az webapp list --output table                # List App Services (none found)
az postgres flexible-server list             # List PostgreSQL servers
az acr list                                  # List container registries (none)
az resource list                             # Full resource inventory
az ad app permission list --id 60a49f2a-...  # Check Graph permissions
az ad app show --id 60a49f2a-...             # App registration details
az ad app show --id 068d383c-...             # App registration details
```

---

## Resources Created via Azure Portal UI (Pre-existing)

These resources existed before the WFD OS project and were created through the Azure Portal UI by CFA staff.

### Resource Group: rg-job-inteligence-engine (West US 2)

| Resource | Type | Purpose | Used by WFD OS? |
|---|---|---|---|
| `pg-jobintel-cfa-dev` | PostgreSQL Flexible Server (v16, B1ms, 32GB) | Database server | **YES** — planned to host `wfdos` database for production |
| `waifinder-market-intelligence` | Bot Service | JIE bot registration | No (reference only) |

### Resource Group: CareerServicesReactApp (East US)

| Resource | Type | Purpose | Used by WFD OS? |
|---|---|---|---|
| `WatechProd-v2` | Virtual Machine | Legacy Career Services React app | **DO NOT TOUCH** |
| `careerservicesstorage` | Storage Account | Resume Blob Storage | **YES** — resume PDFs downloaded for parsing |
| `careerservicesreactb773` | Storage Account | Static web assets | No |
| `resumeJobMatch` | Cognitive Services (OpenAI) | Azure OpenAI for embeddings | Reference only |
| `myOAIResource508483` | Cognitive Services | Additional OpenAI resource | Reference only |
| `cs-copilot-py-w2-26021101` | Azure Function (Python) | Legacy matching/embedding endpoint | Reference only |
| `WestUS2LinuxDynamicPlan` | App Service Plan | Hosts the Azure Function | Reference only |
| `csfuncw226021101` | Storage Account | Function App storage | Reference only |
| `career-services-test-vnet` | Virtual Network | VM networking | Do not touch |
| `CareerServiceProd-nsg` | Network Security Group | VM security rules | Do not touch |
| `CareerServiceProd-ip` | Public IP Address | VM public IP | Do not touch |
| `wtwc-job-normalizer-sbx` | Application Insights | Monitoring | Reference only |

### Resource Group: CFADev2024 (East US)

| Resource | Type | Purpose | Used by WFD OS? |
|---|---|---|---|
| `computingforall003.onmicrosoft.com` | Azure AD B2C | Identity directory | No |
| `computingforallstage.onmicrosoft.com` | Azure AD B2C | Staging identity | No |
| `computingforallusers.onmicrosoft.com` | Azure AD B2C | User identity | No |
| `CFA-Grant-Bot` | Bot Service | Grant bot registration | Reference only |

### Resource Group: ACommunicationServices-RS (East US)

| Resource | Type | Purpose | Used by WFD OS? |
|---|---|---|---|
| `CFA-EmailCommunicationService` | Email Service | Azure Communication Services email | **Available** — has `thewaifinder.com` domain. Currently using Graph `sendMail` instead. |
| `thewaifinder.com` domain | Email Domain | Custom email domain | Available for future use |
| `AzureManagedDomain` | Email Domain | Default Azure domain | Not used |
| `acs-waifinder-shared` | Communication Services | Shared communication resource | Available |

### Resource Group: SQLtoDynamics (North Central US)

| Resource | Type | Purpose | Used by WFD OS? |
|---|---|---|---|
| `SQLtoDynamics` | Logic App | SQL-to-Dynamics sync workflow | **DO NOT TOUCH** |
| `sql` | API Connection | SQL connector for Logic App | Do not touch |
| `office365` | API Connection | Office 365 connector | Do not touch |

### Other Resource Groups

| Resource Group | Resources | Purpose |
|---|---|---|
| `DefaultResourceGroup-EUS` | Log Analytics Workspace | Azure monitoring (auto-created) |
| `DefaultResourceGroup-WUS2` | Log Analytics Workspace | Azure monitoring (auto-created) |
| `NetworkWatcherRG` | Network Watcher (Central US) | Network monitoring (auto-created) |
| `MCT-Resources` / `MCT-Managed-Resources` | Microsoft training resources | Microsoft Certified Trainer resources |
| `VisualStudioOnline-*` | Visual Studio account (CFA1) | Dev tools (South India) |

---

## Resources WFD OS Actively Uses

| Resource | How WFD OS Uses It |
|---|---|
| **CFA-Grant-Agent app registration** (60a49f2a-...) | ALL Graph API calls — email, SharePoint, Teams |
| **WFD-OS app registration** (068d383c-...) | Dataverse/Dynamics CRM access |
| **careerservicesstorage** (Blob Storage) | Downloads resume PDFs for Gemini parsing |
| **pg-jobintel-cfa-dev** (PostgreSQL) | Target for production database deployment |
| **SCOPING_WEBHOOK_URL** (Power Automate) | Teams channel posting for engagement updates |

---

## Resources NOT YET Created (Needed for Production Deployment)

| Resource | Type | Estimated Cost | Purpose |
|---|---|---|---|
| `wfdos` database | PostgreSQL Database (on existing server) | $0 | Production database |
| Container App Environment | Azure Container Apps | ~$15-25/month | Host 6 API services |
| Container Registry | Azure Container Registry | ~$5/month | Docker images |
| Static Web App or Container | Azure Static Web Apps / Container | $0-10/month | Next.js frontend |
| Custom domain + SSL | App Service Domain | ~$12/year | `wfdos.computingforall.org` or similar |

**Estimated total incremental cost:** ~$25-40/month (database is free on existing server)

---

## Third-Party Services (Not Azure)

| Service | Purpose | Auth | Env Var |
|---|---|---|---|
| **Google Gemini API** | LLM for all agents, resume parsing, career navigator | API key | `GEMINI_API_KEY` |
| **Apollo.io** | CRM — contact creation, sequences, webhook | API key | `APOLLO_API_KEY` |
| **ngrok** | Tunnel for Apollo webhook during development | Local binary | N/A |
| **GitHub** | Source code (Building-With-Agents/wfd-os, private) | `gh` CLI | Keyring token |
| **SharePoint** | Document storage (computinforall.sharepoint.com) | Graph API | `GRAPH_*` vars |
| **Microsoft Teams** | Channel messaging for engagement updates | Power Automate webhook | `SCOPING_WEBHOOK_URL` |

# Phase 0: Full Discovery Report
**Date:** 2026-03-30
**Status:** Partially complete — Dynamics Application User registration needed

---

## 1. Organization Identity (CONFIRMED)

| Field | Value |
|-------|-------|
| **Tenant ID** | a3c7a257-40f2-43a9-9373-8bb5fc6862f7 |
| **Display Name** | Computing For All |
| **Technical Contact** | HR@computingforall.org |

### Verified Domains
- computinforall.onmicrosoft.com
- computingforall.org
- cfacareer.computingforall.org
- services.computingforall.org
- WATechCoalition.org
- ess.watechcoalition.org
- **thewaifinder.com** ← The product domain already exists!

---

## 2. Dynamics CRM Instances Found

### Instance 1: cfadev (Production/Dev)
- **URL:** https://cfadev.crm.dynamics.com
- **Tenant:** a3c7a257-40f2-43a9-9373-8bb5fc6862f7 ✓ CFA
- **Access status:** Token acquired, but app not registered as Application User

### Instance 2: cfahelpdesksandbox (Sandbox)
- **URL:** https://cfahelpdesksandbox.crm.dynamics.com
- **Tenant:** a3c7a257-40f2-43a9-9373-8bb5fc6862f7 ✓ CFA
- **Access status:** Same — needs Application User registration
- **Note:** Referenced by Integration-SSIS app — likely used for data sync

### Instance 3: cfa (NOT CFA's)
- **URL:** https://cfa.crm.dynamics.com
- **Tenant:** e287fe40-2fd2-42fb-a268-a684b1d3780a ✗ Different organization

---

## 3. Full App Ecosystem (48+ apps discovered)

### Power Apps Portals (5 portals)
| Portal | URL | Purpose |
|--------|-----|---------|
| CFA Partner | cfapartner.powerappsportals.com | Employer/partner portal |
| Volunteer Engagement | CFAVolunteerEngagement.powerappsportals.com | Volunteer management |
| CFA Projects | cfaprojects.powerappsportals.com | Project tracking |
| CFA Educator | CFAEducator.powerappsportals.com | College/educator portal |
| PAP Student Analytics | papstudentalalytics.powerappsportals.com | Student analytics |
| CFA Test | cfatest1.powerappsportals.com | Test environment |

### Career Services Apps (React UX)
| App | App ID | Notes |
|-----|--------|-------|
| CFA1-Career Services (d6e226c1) | ee7b9987, 8106d580, 4cec2dd3 | Three instances — different environments |
| CFA1-Career Services (e2326475) | 98c99fd3 | Redirect: localhost:3000/ess — THIS IS THE REACT UX |
| CFA Career Services localhost | 60ced11c | Local dev instance |

### Copilot Studio / Power Virtual Agents Bots (15+ bots)
- **Talent Assistant** — talent matching bot
- **JobsPortal bot** — job search chatbot
- **CFA Students bot** — student-facing assistant
- **CFA Forms bot** — form automation
- **CFA Jobs 3/4 bots** — job listing bots
- **CFA Portal bot** — general portal bot
- **CFA Test bot** — test instance
- Multiple D365 Sales agents (research, email, competitor, stakeholder, etc.)
- Customer Service agents (case followup, onboarding, quality evaluation)

### Integration & Data Apps
| App | App ID | Notes |
|-----|--------|-------|
| Integration-SSIS | aa81e2d7 | SQL/Dynamics sync — has Dynamics CRM permission |
| Dataverse App | 2ae9faf2 | Direct Dataverse access |
| DataverseClientBots | 4b27bfaf | Bot data layer |
| CFA App - Dev-SharePoint Graph writer | 66dd8f0f | SharePoint integration |

### Google Cloud Resources (Found)
- cfa-test-001-resource (service principal in Azure AD)
- May indicate GCP cross-cloud integrations

---

## 4. What We CAN Already Do

### Azure AD / Graph API (WORKING)
- ✅ List all app registrations
- ✅ Query organization info
- ✅ Access SharePoint sites
- ✅ Access Teams channels
- ✅ Manage app permissions

### Power Automate Webhook (WORKING)
- ✅ Scoping webhook URL discovered and functional

---

## 5. What's BLOCKED and How to Fix

### Blocker: Dynamics CRM Application User
**Error:** "The user is not a member of the organization"
**Root cause:** App registration exists in Azure AD but not registered in Dynamics

**Fix — 2-minute manual step in Power Platform Admin Center:**
1. Go to https://admin.powerplatform.microsoft.com
2. Environments → select cfadev → Settings → Users + permissions → Application users
3. New app user → App ID: 60a49f2a-230a-4460-bd6d-c0e22bc32384
4. Select Business Unit (root)
5. Assign security role: System Administrator
6. Click Create

**Then repeat for cfahelpdesksandbox if desired.**

### Missing Credentials (Not Found on Local Machine)
- Azure SQL Server connection string
- Azure Blob Storage connection string
- Azure Python Endpoint URL and API key
- Azure subscription RBAC for this app (no subscription access)

These credentials are likely stored in:
- Azure Key Vault
- App Service configuration
- Function App settings
- Power Automate connection references

**To find them:** We need either Azure subscription access (RBAC role for the app) OR to log into the Azure Portal directly.

---

## 6. Recommended Next Steps

### Immediate (Ritu to do manually — 5 minutes):
1. Register app as Application User in Dynamics (steps above)
2. Check Azure Portal → Subscriptions → add Reader role for app 60a49f2a...
3. Locate SQL Server connection string (likely in App Service or Function App config)

### Once Dynamics access is granted:
- Full Dataverse table discovery (Phase 1d)
- Power Apps and Power Automate inventory
- Entity relationship mapping

### Once SQL credentials are found:
- Full SQL database discovery (Phase 1 — PRIMARY PRIORITY)
- Table inventory, row counts, schema mapping
- Agent ownership assignment

### Once Azure subscription access is granted:
- Discover all Azure resources (App Services, Functions, SQL, Storage, etc.)
- Pull Python endpoint code (Phase 1b)
- Blob Storage inventory (Phase 1c)

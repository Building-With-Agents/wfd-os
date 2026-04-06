# Phase 0: Instance Discovery — Status Report
**Date:** 2026-03-30

## What We Confirmed

### Organization Identity
- **Tenant ID:** a3c7a257-40f2-43a9-9373-8bb5fc6862f7
- **Display Name:** Computing For All
- **Verified Domains:**
  - computinforall.onmicrosoft.com
  - computingforall.org
  - cfacareer.computingforall.org
  - services.computingforall.org
  - WATechCoalition.org
  - ess.watechcoalition.org
  - thewaifinder.com
- **Technical Contact:** HR@computingforall.org

### Dynamics CRM Instance Found
- **URL:** https://cfadev.crm.dynamics.com
- **Tenant match:** CONFIRMED — belongs to CFA tenant a3c7a257-40f2-43a9-9373-8bb5fc6862f7
- **Status:** Instance exists and responds, but app is not authorized as a Dynamics user

### App Registration
- **App ID:** 60a49f2a-230a-4460-bd6d-c0e22bc32384
- **Object ID:** 0a8b2199-6bf1-48a6-8fc9-54c8f7f10291
- **Current permissions:** Microsoft Graph API (SharePoint, Teams) — WORKING
- **Missing permissions:** Dynamics CRM API, Power Platform admin API

## What's Blocked

### Issue: App not registered as Dynamics application user
The app registration can authenticate to Azure AD and get tokens scoped to
cfadev.crm.dynamics.com, but Dynamics returns:
> "The user is not a member of the organization."

### Fix Required (2 steps):
1. **Add Dynamics CRM API permission** to the app registration in Azure AD:
   - Azure Portal → App Registrations → 60a49f2a... → API Permissions
   - Add: Dynamics CRM → Application permissions → user_impersonation
   - Grant admin consent

2. **Register as Application User** in Dynamics Admin Center:
   - Power Platform Admin Center → Environments → cfadev → Settings → Users
   - Add Application User → App ID: 60a49f2a-230a-4460-bd6d-c0e22bc32384
   - Assign Security Role: System Administrator (for read-only discovery)

### Also blocked: Power Platform Admin API
Same app lacks permissions for the Business Application Platform API.
This prevents listing all environments programmatically.

## Other Dynamics Instances Probed
- cfa.crm.dynamics.com → EXISTS but belongs to DIFFERENT tenant (e287fe40-...) — NOT CFA's
- cfadev.crm.dynamics.com → CFA's instance ✓
- computingforall, computing4all, cfanonprofit, cfabellevue, cfawa, computeall,
  c4a, cfaops, cfatech, computingforallorg, cfaworkforce → Do not exist

# TODO — Consulting Pipeline Integrations
**Status:** Internal dashboard built. Integrations deferred.

## Deferred Items

1. **Apollo Integration**
   - Add APOLLO_API_KEY to .env
   - Add APOLLO_WEBHOOK_SECRET to .env
   - Load Jessica Mangold's email sequences (3 sequences: WA/TX professional services, TX workforce boards)
   - Auto-create Apollo contact when new inquiry arrives
   - Trigger outreach sequence based on project area
   - Webhook handler for "Ready to Scope" stage trigger

2. **Scoping Agent Integration**
   - Connect existing Scoping Agent Azure Function (from cfa-scoping-agent project)
   - Auto-fire when inquiry moves to "scoped" stage
   - Create SharePoint workspace automatically
   - Create Teams channel automatically
   - Schedule recorded Teams meeting via Graph API
   - Post-call: generate proposal draft from transcript

3. **Email Notifications**
   - Configure SMTP for real notifications
   - On new inquiry: email ritu@computingforall.org with inquiry details + link to /internal
   - On status change: email client if appropriate
   - On conversion to active: welcome email with client portal access

4. **Client Onboarding Agent**
   - Fire when DocuSeal contract is signed
   - Create full client workspace in SharePoint
   - Set up ClickUp project
   - Notify Gary to assign apprentices
   - Add to Apollo as active client account

5. **Pipeline Value Accuracy**
   - Current: estimates budget from dropdown ranges
   - Better: store actual negotiated budget after scoping call
   - Track placement fees separately

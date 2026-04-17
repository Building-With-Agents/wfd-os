# System summary

Plain-language snapshot as of commit 50f5c20. Written for me (ED + developer),
not for management, not for funders, not for onboarding.

## 1. What the system is

A layer on top of QuickBooks that turns raw QB transactions into grant-aware
accounting decisions. It pulls our bookkeeping data, proposes which
transactions charge to which grant, flags unallowable costs against 2 CFR 200,
drafts the monthly time & effort certifications federal grants require, and
produces SF-425 and foundation report drafts. Built for CFA specifically —
one org, multiple concurrent grants, a bookkeeper (Krista), an ED/developer
(me), and a federal grant closing September 2026. Every decision the system
proposes requires a human to approve it before it becomes final.

## 2. What's working today

As of commit 50f5c20, the system can:

- Connect to an Intuit sandbox via OAuth2, capture access + refresh tokens,
  persist them against a specific QB realm, refuse to use a sandbox token
  against production config or vice versa.
- Pull accounts, classes, bills, purchases, and journal entries from sandbox
  QB into the `grant_compliance.*` Postgres schema. Verified against realm
  9341456894726426: 89 accounts, 53 transactions, all field mappings correct
  on an end-to-end spot-check (raw QB JSON → normalized integer-cents row).
- Preserve the raw QB payload alongside every normalized transaction, so
  we can reprocess if our normalization logic changes without re-hitting
  Intuit.
- Write every consequential action (OAuth authorization, each sync phase)
  to an append-only `audit_log` table with actor, action, inputs, outputs,
  and timestamp.
- Refuse non-GET HTTP requests from the QB client at the transport layer.
  `_ReadOnlyHttpxClient` raises `NotImplementedError` rather than letting
  a write reach Intuit. A CI test additionally fails if any future
  `QbClient` method is named with a write-suggestive prefix.
- Refuse to initialize against `QB_ENVIRONMENT=production` unless
  `ENCRYPTION_KEY` is set. The guard is in `config.py` and fires during
  Settings construction.

Verified by 29 tests: audit log append-only behavior, compliance rule
matching, Classifier skeleton, MS Graph client construction, QB read-only
HTTP enforcement (including the introspection test for drift), and the
production startup guard.

## 3. Scaffolded but not yet functional end-to-end

**Transaction Classifier.** Two code paths exist: a deterministic shortcut
when a QB Class uniquely identifies a grant, and an LLM fallback when it
doesn't. Hasn't been run against real data. Can't be meaningfully exercised
on this sandbox either — Intuit's sample company has zero Classes, so only
the LLM path would fire, and we'd be calling Anthropic against synthetic
transactions.

**Compliance Monitor.** Rule engine runs, tests pass, but hasn't been run
across a real transaction set. The unallowable-costs rules cover a subset
of 2 CFR 200 Subpart E; gaps will become visible when a real transaction
surfaces something the rules don't catch.

**Time & Effort Agent.** Draft structures work. No employee data is
flowing (QB Payroll sync is deferred) and there's no UI for an employee
to actually sign a certification.

**Reporting Agent.** Draft generators exist for SF-425 and foundation
narratives. Snapshot-ID reproducibility — regenerating a Q3 2025 report
months later from the same DB state — is untested on real multi-month data.

**Microsoft Graph integration.** OAuth flow written, `EvidenceCollector`
written, zero calls made against a real Graph tenant.

**Review queue / human approval UI.** API routes exist to propose, approve,
and reject allocations. There is no interface Krista would actually use —
today she'd hit those routes via curl, which is not a workflow.

## 4. Deferred and why

None of these block Step 1a. Naming them so nothing is lost.

- **QuickBooks production keys.** Internal-app path at developer.intuit.com
  requires a questionnaire review. Sandbox works with current keys.
- **Fernet encryption for OAuth tokens.** Required for production; the
  startup guard blocks a production misstep until this is wired.
- **Void/delete/amend detection via QB's CDC endpoint (Step 1b).** Currently
  any re-sync of a previously-seen transaction returns 0 — voids are
  invisible.
- **Auto-refresh on 401 for expired access tokens (Step 1b).** Access
  tokens expire in ~1 hour; today the sync returns 401 and I re-authorize
  in the browser.
- **Teams integration, all four phases (2A webhook flags → 2D @-mention
  bot).** No `docs/PHASE_2_TEAMS_INTEGRATION.md` in the repo yet; deferred.
- **Automated sync cadence / scheduling.** `POST /qb/sync` is triggered
  manually.
- **BoA → QB bank feed verification.** Operational task, not code.
- **SEFA generator, audit sample documentation pull, gap analysis reports.**

## 5. What the system will not do

Architectural choices, not missing features. The distinction matters.

- **Will not write to QuickBooks.** HTTP client raises `NotImplementedError`
  on anything other than GET.
- **Will not auto-post to funder systems, funder portals, or federal
  reporting sites.**
- **Will not decide whether a cost is allowable under 2 CFR 200.** The LLM
  never makes that call. Deterministic code in
  `compliance/unallowable_costs.py` does.
- **Will not auto-approve allocations.** Every Classifier proposal requires
  an explicit human decision recorded in the audit log.
- **Will not finalize time & effort certifications** on behalf of employees.
  Drafts only; the employee signs.
- **Will not operate against production QB** without `ENCRYPTION_KEY`
  configured.

## 6. Who does what

**Krista (bookkeeper).** Today she tags transactions with grant Classes by
hand in QB — several hours a week. With the system running against real
data, she reviews Classifier proposals instead of starting from blank, and
reviews time & effort drafts before signing. Her reconciliation workflow
inside QB itself is unchanged; this layer sits above it. The Classifier is
expected to reduce her tagging time meaningfully, but actual performance
can only be measured against real data.

**Me (ED).** Day-to-day unchanged. I should be aware the scaffold has
read-only access to QB, and will have read-only access to Teams / SharePoint
once MS Graph is wired.

**The auditor (June).** Workflow for this audit is unchanged — they'll
pull their own samples from QB. For the FY26 audit, if the system has been
running against real data for several months by then, it could materially
shorten the documentation gather.

**Me (developer).** Maintain the system. Review rules in
`compliance/unallowable_costs.py` when 2 CFR 200 updates. Set up production
keys, Fernet encryption, and backups when we flip out of sandbox.

## 7. Honest limits

- Won't tell me whether the FY2025 Single Audit extension was filed. That's
  a phone call and a fac.gov login.
- Won't engage an audit firm.
- Won't reconstruct compliance documentation that was never created. It
  surfaces what's in QB, Teams, SharePoint, and email. It doesn't fabricate
  records.
- Won't make Single Audit findings go away if the underlying compliance is
  weak. Better documentation doesn't retroactively improve the transactions
  themselves.
- Won't replace the CPA's judgment on allowability edge cases, the
  auditor's sampling decisions, or the ED's governance choices.

The system is genuinely well-architected for its stage. It isn't done.

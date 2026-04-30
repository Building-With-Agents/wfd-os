# Feature Spec — Compliance Requirements Agent

**Audience:** Claude Code (implementation)
**Spec owner:** Ritu Bahl
**Target location:** Engine-side service in `agents/grant-compliance/src/grant_compliance/`, exposed via HTTP endpoints consumed by the cockpit's Monitoring tab and elsewhere
**Branch:** `feature/compliance-engine-extract` (engine-side feature; cockpit-side rendering changes will follow on `feature/finance-cockpit` as a separate companion task)
**Status:** Draft for implementation
**Date:** April 30, 2026

---

## Spec file placement

Place this spec at `agents/grant-compliance/docs/compliance_requirements_agent_spec.md`, alongside `audit_readiness_tab_spec.md`.

---

## Purpose

Produce structured, comprehensive documentation requirements derived from 2 CFR 200 (and related federal grant guidance) for CFA's K8341 grant. The agent's output answers the question: **"What documentation should exist if we are fully compliant?"**

This question is currently answered ad hoc, by institutional knowledge that has eroded through team attrition. The Compliance Requirements Agent makes the answer structured and complete, so Krista can hunt against a known-comprehensive list rather than an inferred one. The discovery process itself surfaces what CFA does and does not have.

The agent operates in two modes:

- **Mode A (one-time / scheduled generation):** Produces a comprehensive checklist for a defined scope (e.g., "all procurement-related documentation for K8341"). Output ingested into the cockpit as the rule corpus that the Monitoring Agent (separate, later feature) evaluates against.
- **Mode B (interactive Q&A):** Responds to specific questions about documentation requirements as edge cases arise. ("What documentation is required for an above-threshold sole-source procurement to a former contractor?")

Both modes ground responses in the actual regulatory text. Both modes refuse to provide legal opinions about CFA's actual compliance state — the agent specifies *what should exist*; counsel and auditors evaluate *whether what exists is compliant*.

---

## Why this matters

CFA's situation is a textbook case of the structural gap this agent addresses:

- A multi-year federal grant with substantial subrecipient and contractor activity
- Team attrition has cost institutional knowledge of what was documented when, by whom, in what form
- An active monitoring engagement (ESD-WMU procurement compliance review) requires producing comprehensive documentation, but no single person at CFA holds the full picture of what comprehensive looks like under the regulation
- An annual monitoring engagement (June 2026) is upcoming with broader scope
- A Single Audit will follow grant closeout, examining all of this against federal standards

In each case, the question that has to be answered is "does the documentation that should exist actually exist?" That question can't be answered without first answering "what should exist?" — and that answer requires regulatory expertise CFA can't fully assemble from internal sources today.

The Compliance Requirements Agent fills the structural gap. It reads the regulation, applies CFA's specific circumstances (K8341 grant terms, contract values, procurement methods, classifications), and produces the comprehensive structured checklist Krista hunts against.

---

## Scope: what the agent covers

The agent's regulatory corpus is bounded to make output reliable. For v1:

**In scope:**

- 2 CFR 200 Subpart D (Procurement Standards), §§200.317 through 200.327
- 2 CFR 200 Subpart E (Cost Principles), §200.404 (cost reasonableness) and the §200.420–.476 range of selected items of cost as they apply to procurement and personnel
- 2 CFR 200 Subpart D (Subrecipient Monitoring), §§200.331 through 200.333
- 2 CFR 200 Subpart D (Standards of Conduct, Conflicts of Interest), §200.318(c)
- Application to the Economic Development Cluster (Assistance Listing 11.307) per the 2025 OMB Compliance Supplement, Part 4-11.300
- ESD-specific pass-through requirements that supplement the federal floor, when documented (per K8341 contract terms and ESD policies, when those are available to the agent)

**Out of scope for v1:**

- Subpart F (Audit Requirements) — addressed separately by the Audit Readiness work; the agent doesn't generate audit requirements
- Subpart B (General Provisions) — covered indirectly through the relevant subparts
- Time and effort certifications under §200.430 — addressed by the v1.3.3 Time and Effort dimension; the agent may eventually extend here but doesn't initially
- Indirect cost rate methodology under §200.414 — out of scope; the cockpit handles indirect via the existing Allowable Costs dimension
- Subaward financial reporting requirements — addressed by the Reporting dimension; not duplicated here
- Other federal grant programs beyond Economic Development Cluster — the agent is K8341-specific in v1 (multi-grant generalization is a future capability)

The boundaries are deliberate. A narrower agent that does its narrower scope reliably is far more valuable than a broader agent that produces lower-quality output across more topics.

---

## Mode A: one-time / scheduled generation

### Purpose

Produce a comprehensive structured documentation requirements specification for CFA's K8341 grant. The output is a structured artifact that:

- Lists every documentation requirement implied by the in-scope regulations
- Organizes requirements by compliance area (procurement, classification, cost reasonableness, subrecipient monitoring, conflict of interest)
- Tailors requirements to CFA's specific circumstances (contract values, procurement methods, classifications) where the regulation conditions requirements on those circumstances
- Cites the specific regulatory text for each requirement so requirements are auditable

### Trigger

- **On demand:** Ritu or Krista invokes generation via the cockpit (button in the Monitoring tab or a separate "Compliance Requirements" admin view)
- **Scheduled:** Initially monthly during active grant operations, transitioning to quarterly once the grant is in closeout. Scheduled runs detect when CFA's circumstances have changed (new contracts added, classifications revised, monitoring engagements opened) and regenerate accordingly.
- **Triggered:** When a monitoring engagement is opened in the cockpit, the agent runs against the engagement's specific scope and produces an engagement-tailored checklist.

### Input

The agent reads CFA's K8341 grant context to tailor output:

- Grant identity and award information (from the engine's `grants` and `funders` tables)
- Budget structure (from `budget_lines`)
- Classifications of parties paid through the grant (from the cockpit's personnel feature data and from forthcoming contracts inventory data when available)
- Contract values and procurement methods per contractor (from contract data, when populated)
- Open monitoring engagements and their scopes (from the cockpit's Monitoring feature data, when populated)
- ESD pass-through contract terms (from K8341 contract documents, when available; for v1 the agent may operate on the regulatory corpus without pass-through specifics if those documents aren't yet structured)

### Output

A structured `ComplianceRequirementsSet` artifact with the following shape:

- `set_id` (string) — stable identifier for the generated set
- `generated_at` (datetime)
- `scope` (object) — what the set covers (which compliance areas, which contracts, which engagement if engagement-scoped)
- `regulatory_corpus_version` (string) — which version of the OMB Compliance Supplement and which 2 CFR 200 effective date the agent worked from. Important because regulations evolve; the corpus version provides traceability.
- `grant_context` (object) — snapshot of the CFA-specific facts the agent used to tailor output (contract counts, classifications, thresholds in play). Lets a future reader understand what assumptions drove the specifics.
- `requirements` (array of `Requirement` records) — the actual documentation requirements

Each `Requirement` record:

- `requirement_id` (string) — stable identifier
- `compliance_area` (enum) — `procurement_standards` | `full_and_open_competition` | `cost_reasonableness` | `classification_200_331` | `subrecipient_monitoring` | `conflict_of_interest` | `standards_of_conduct`
- `regulatory_citation` (string) — the specific CFR section (e.g., "2 CFR 200.318(i)")
- `regulatory_text_excerpt` (text) — the relevant excerpt from the regulation, verbatim, so the requirement is auditable against source
- `applicability` (object) — when this requirement applies, structured:
  - `applies_to` — `all_contracts` | `contracts_above_threshold` | `sole_source_only` | `contractors_only` | `subrecipients_only` | `specific_circumstance`
  - `threshold_value` (decimal, optional) — if applicability depends on a dollar threshold
  - `circumstance_description` (text, optional) — narrative for specific circumstances
- `requirement_summary` (text) — one-paragraph plain-English description of what should exist
- `documentation_artifacts_required` (array of strings) — specific documents or records that constitute compliance with this requirement (e.g., "Independent cost estimate documented before contract award", "§200.320(c) sole-source justification with specific basis cited")
- `documentation_form_guidance` (text) — how the documentation should be structured (signed by whom, dated when, retained where)
- `cfa_specific_application` (text) — where applicable, narrative explaining how this requirement applies to CFA's specific situation (e.g., "For AI Engage at $245K contract value, this requirement applies because... For Pete Vargo at [actual value], this requirement applies because...")
- `severity_if_missing` (enum) — `material` | `significant` | `minor` | `procedural`. Severity reflects how a federal auditor or pass-through monitor would likely characterize a finding if the documentation is absent. The agent provides a reasoned default; counsel can revise. The severity is informational, not authoritative.

### Generation methodology

The agent uses an LLM (Claude API, the cockpit's existing pattern) with a carefully constructed prompt that includes:

1. The regulatory corpus (text of the in-scope CFR sections, plus the relevant 2025 OMB Compliance Supplement Part 4-11.300 content)
2. CFA's grant-context snapshot (current state of contracts, classifications, thresholds)
3. A structured prompt asking the model to produce the `requirements` array per the schema above, with each requirement grounded in cited regulatory text

The prompt requires the model to produce *only* requirements that have direct regulatory grounding — no speculative or "best practice" additions that aren't in the regulation. Each requirement must cite a specific CFR section. Requirements without citation are rejected at validation.

The agent runs the prompt, parses the output, validates the schema, and persists the resulting `ComplianceRequirementsSet` to the engine's database.

### Storage

A new SQLAlchemy table `compliance_requirements_sets` with the structure above. A child table `compliance_requirements` for the individual requirement records, FK'd to the parent set. Migrations follow the existing engine pattern.

### Versioning and replacement

When a new generation run produces a new `ComplianceRequirementsSet`, the prior set is preserved (not deleted) but marked `superseded_by` the new set. This preserves audit trail of how requirements specifications evolved over time. The cockpit displays the current set by default; historical sets are accessible via a version history view.

---

## Mode B: interactive Q&A

### Purpose

Provide regulatory expertise on demand for specific questions that arise during day-to-day work. The agent acts as a 2-CFR-200-literate assistant Krista (or Ritu, or counsel-light queries) can ask narrowly-scoped questions of.

### Trigger

User-initiated through a dedicated interface:

- A "Ask the Compliance Agent" panel within the Monitoring tab
- A standalone admin route at `/internal/compliance-agent` for broader queries
- Optional: integration with the existing finance assistant's broad chat (via context routing — questions that match compliance-area patterns route to this agent's prompt instead of the general finance agent's)

### Input

Free-text questions from the user. Examples:

- "What documentation is required for an above-threshold sole-source procurement to a former contractor?"
- "If an existing employee starts performing partly-grant-funded work mid-grant, what documentation establishes the allocation?"
- "Does the cost reasonableness analysis for a $245K contract have to be contemporaneous, or can it be reconstructed?"

The agent has access to:

- The full in-scope regulatory corpus
- The current `ComplianceRequirementsSet` for CFA's K8341 grant (so Mode B can reference Mode A output coherently)
- CFA's grant context (so Mode B can tailor responses to CFA specifics where relevant)

### Output

A structured response with:

- `answer` (text, markdown) — direct response to the user's question, grounded in regulatory text
- `regulatory_citations` (array of strings) — specific CFR sections referenced
- `relevant_existing_requirements` (array of `requirement_id` references) — links back to relevant entries in the current `ComplianceRequirementsSet`. This connects Mode B answers back into the structured Mode A output.
- `caveats` (array of strings) — explicit limitations on the response (e.g., "This response addresses federal regulation only; ESD pass-through terms may impose additional requirements.", "This response is informational and not a legal opinion.")
- `out_of_scope_warning` (string, optional) — if the question is outside the agent's regulatory corpus, the agent surfaces this rather than guessing

### Honesty constraints in Mode B

The Mode B agent has a strict constraint on what it does and does not output:

**The agent provides:** documentation requirements implied by the regulation, regulatory text references, structured analysis of how a requirement might apply to a circumstance, identification of what's outside its corpus.

**The agent does NOT provide:**

- Legal opinions about whether CFA is compliant or not in any specific instance
- Predictions about how a specific auditor or monitor will respond to a specific situation
- Strategic advice about what to disclose, when, or how
- Advocacy framing — the agent provides facts and regulatory grounding, not arguments for positions
- Any output that could be construed as the practice of law

The system prompt for Mode B explicitly instructs the model to refuse these categories of questions and redirect the user to counsel. The refusal is structured (the agent says specifically "this question requires counsel review" rather than just declining), so the user knows what to do next.

---

## Implementation architecture

### Components

1. **`agents/grant-compliance/src/grant_compliance/compliance_requirements_agent/`** — new module
   - `agent.py` — the core agent logic (LLM client wrapper, prompt construction, response validation)
   - `corpus.py` — loads the regulatory corpus from a stored corpus file (the regulation text + OMB Compliance Supplement excerpts)
   - `prompts.py` — the structured prompts for Mode A (generation) and Mode B (Q&A)
   - `schemas.py` — Pydantic models for `ComplianceRequirementsSet`, `Requirement`, Q&A response
   - `tasks.py` — scheduled task entry points (for Mode A scheduled runs)

2. **`agents/grant-compliance/alembic/versions/<new>_add_compliance_requirements_tables.py`** — Alembic migration adding `compliance_requirements_sets` and `compliance_requirements` tables

3. **HTTP endpoints (`agents/grant-compliance/src/grant_compliance/api/`):**
   - `POST /compliance/requirements/generate` — triggers Mode A generation; returns set_id when complete
   - `GET /compliance/requirements/current` — returns the current `ComplianceRequirementsSet`
   - `GET /compliance/requirements/sets/{set_id}` — returns a specific historical set
   - `POST /compliance/requirements/qa` — Mode B Q&A endpoint; takes a question, returns a response

4. **Regulatory corpus storage:** the actual text of the in-scope regulations and OMB Compliance Supplement excerpts. Stored as structured text files in `agents/grant-compliance/data/regulatory_corpus/`. Versioned in the repo. This is the agent's source of truth for what the regulation says; not pulled from external services at runtime.

### LLM model selection

Use `claude-sonnet-4-5` or whichever Sonnet 4.5 alias the existing engine code uses for similar tasks (the verdict generator on Audit Readiness is a precedent). Sonnet is appropriate here — sufficient quality for structured analysis, lower cost than Opus for runs that may happen frequently in Mode B and on schedule in Mode A.

For Mode A initial generation runs (high stakes, comprehensive output), consider Opus once if the cost is justified — the initial corpus is the foundation everything else evaluates against, and Opus's higher quality on structured analysis at length is meaningful. For subsequent regenerations and for Mode B, Sonnet is the default.

### Determinism and reproducibility

LLM output is non-deterministic. For Mode A, this means two generation runs against the same input may produce slightly different `requirements` arrays. The spec acknowledges this and addresses it through:

- Validation against a strict schema (rejecting outputs that don't conform)
- Storing the prompt, model name, model version, and full response alongside the generated set, so any specific generation run is reproducible and auditable
- Treating the generated set as a draft that human review (Ritu or counsel) confirms before it becomes the active set used by the Monitoring Agent

This is the same pattern the engine's existing audit log enforces — every consequential agent action has its inputs, outputs, model name+version, prompt, and timestamp logged. Apply that pattern here.

---

## Honesty discipline (cross-mode)

Both modes share these requirements:

- **Cite or don't claim.** Every requirement in Mode A output and every assertion in Mode B output that purports to derive from regulation must cite the specific CFR section. Outputs without citation are rejected.
- **Surface scope limits.** Both modes know their corpus boundaries and explicitly say so when a question falls outside.
- **Distinguish should from is.** The agent describes what the regulation requires (should). It does not describe what CFA has or doesn't have (is). Mode A produces requirements; the Monitoring Agent (separate feature) evaluates state against requirements.
- **Distinguish from legal opinion.** Both modes carry caveat language: the output is informational, derived from regulatory text, and does not constitute legal advice or a determination of compliance.
- **Make uncertainty visible.** When the agent encounters edge cases where regulatory interpretation is ambiguous (e.g., "is participant support cost allowable for this specific activity"), it surfaces the ambiguity and suggests counsel review rather than picking a position.

---

## Acceptance criteria

The implementation is complete when:

1. New module `compliance_requirements_agent` exists in the engine at the specified location
2. Database migration applied; `compliance_requirements_sets` and `compliance_requirements` tables exist with correct schema
3. Regulatory corpus stored in `data/regulatory_corpus/` covering 2 CFR 200.317-.327, 200.331-.333, 200.318(c), 200.404, and 2025 OMB Compliance Supplement Part 4-11.300
4. Mode A generation endpoint produces a valid `ComplianceRequirementsSet` for CFA's K8341 grant; the set covers all in-scope compliance areas; every requirement has a regulatory citation; output validates against the schema
5. Generated set is persisted to the database with full audit trail (prompt, model, response, timestamp)
6. Mode A versioning works: a second generation run preserves the prior set as `superseded_by` rather than deleting it
7. Mode B Q&A endpoint responds to questions with structured output including answer, citations, relevant requirement references, caveats; refuses out-of-scope or legal-opinion questions with a structured refusal
8. Both modes honor the honesty constraints (no claims without citation, scope limits surfaced, should/is distinction maintained)
9. Sample run for Mode A produces output that Ritu manually reviews and confirms is structurally correct, comprehensive against the in-scope corpus, and free of speculative or non-cited claims
10. Sample queries for Mode B (3-5 queries covering procurement, classification, cost reasonableness) produce responses Ritu manually reviews and confirms are accurate, properly cited, and appropriately limited

---

## Out of scope (explicit — Claude Code, do not implement these)

- Multi-tenant operation — the agent is K8341-specific in v1; tenant isolation comes with v1.3.0 wfdos-common integration
- Cockpit-side rendering of the requirements (separate companion task on the cockpit branch — see "Companion cockpit work" below)
- Real-time evaluation of CFA's actual documentation state against requirements — that's the Monitoring Agent's job, separate feature
- Automated regulatory corpus updates from external sources — corpus is manually versioned in the repo for v1
- PDF parsing of source regulatory documents — corpus is stored as structured text, not extracted from PDFs at runtime
- Q&A response streaming — Mode B returns complete responses, not streamed chunks; streaming can be added later if response latency becomes an issue
- Authentication and authorization beyond what the existing engine API has
- Integration with the existing finance assistant's broad chat — that's a separate routing feature, can be added later

---

## Companion cockpit work (separate task on `feature/finance-cockpit`)

After this engine-side feature ships, the cockpit needs companion changes to consume it. Specified separately to keep this spec engine-focused. The companion work covers:

- A "Compliance Requirements" view in the cockpit (likely a sub-section of the Monitoring tab) that displays the current `ComplianceRequirementsSet`
- Per-requirement display: regulatory citation, summary, documentation artifacts required, CFA-specific application
- Filter and search across requirements by compliance area, applicability, severity
- Integration into the Monitoring engagement view: when displaying a contract under review, surface relevant requirements from the current set
- Mode B Q&A interface: a panel where users type questions and see responses
- Version history view for `ComplianceRequirementsSet` showing how requirements have evolved

The companion cockpit work depends on this engine-side feature. Do not start the companion work until this feature is shipped and stable.

---

## Forward seams

The Compliance Requirements Agent's output is consumed by other features:

- **Monitoring Agent (future):** Evaluates CFA's actual state against the current `ComplianceRequirementsSet`. Each `Requirement` becomes a check the Monitoring Agent performs.
- **Audit Readiness — Procurement dimension (v1.3.4):** Computes readiness by counting how many requirements in the procurement-area subset of the current set have corresponding documentation in CFA's records.
- **Audit Readiness — Subrecipient Monitoring dimension (v1.3.1):** Same pattern, scoped to the subrecipient-monitoring requirements.
- **Future Single Audit prep:** The set serves as the documentation expectation against which Single Audit prep is organized. Each requirement maps to evidence that should be assembled for the auditor.
- **Multi-tenant generalization (v1.3.0+):** When the cockpit becomes multi-tenant via wfdos-common, the agent's grant-context input becomes per-tenant; output is per-tenant; corpus stays shared.

---

## Deferred to v1.1+

Captured here so the ideas don't get lost.

### 1. Pass-through entity requirements

CFA's K8341 contract incorporates ESD-specific pass-through requirements that supplement the federal floor. v1 of the agent operates on the regulatory corpus alone; ingesting K8341 contract terms into the corpus is a v1.1 addition once those terms are structured.

### 2. ESD-WMU framework as part of corpus

If ESD-WMU's monitoring framework is documented in a form the agent can ingest, including it in the corpus would let the agent generate requirements that reflect ESD's specific monitoring practices, not just federal floor. v1.1 addition.

### 3. Multi-grant generalization

The agent is K8341-specific in v1. Generalizing to other grants (other Assistance Listings, other federal programs, other funding sources) requires a corpus selection mechanism per grant and grant-type-specific prompt variations. v1.1+.

### 4. Counsel review workflow

Mode A generated sets and Mode B responses sometimes warrant counsel review before being treated as authoritative. v1 has no structured counsel-review-of-agent-output workflow. v1.1 should add a "pending counsel review" status on requirements and Q&A responses, with explicit reviewer attribution when reviewed.

### 5. Streaming Mode B responses

Mode B currently returns complete responses. For longer answers, streaming would improve user experience. v1.1.

### 6. Continuous corpus update

The regulation evolves. v1 stores the corpus as static files. v1.1 should establish a process for tracking corpus updates (e.g., when a new OMB Compliance Supplement is published) and regenerating affected sets.

### 7. Tool use within Mode B

Mode B currently produces text responses. For complex queries, the agent could use tools — querying CFA's actual contract data to provide context-aware answers. v1.1.

### 8. Cross-grant requirement comparison

When CFA operates multiple grants (or when the practice serves multiple tenants), comparing requirements across grants surfaces patterns. v1.2+.

---

## Implementation order

1. Read the existing engine architecture (`agents/grant-compliance/src/grant_compliance/`) to understand conventions
2. Save this spec at `agents/grant-compliance/docs/compliance_requirements_agent_spec.md`
3. Curate the regulatory corpus: gather the text of in-scope CFR sections and 2025 OMB Compliance Supplement Part 4-11.300, store as structured text files in `data/regulatory_corpus/`
4. Define schemas (Pydantic models) for `ComplianceRequirementsSet`, `Requirement`, Q&A response
5. Implement Alembic migration for the new tables
6. Implement the agent module:
   a. `corpus.py` — corpus loading
   b. `prompts.py` — Mode A and Mode B prompts
   c. `agent.py` — core agent logic with LLM client, prompt construction, response validation
   d. `tasks.py` — scheduled task entry point for Mode A
7. Wire HTTP endpoints
8. Run Mode A end-to-end against CFA's grant context; validate output against acceptance criteria 4-6
9. Run Mode B end-to-end against 3-5 sample queries; validate output against acceptance criterion 7-8
10. Manual review (Ritu) of Mode A and Mode B sample outputs to confirm acceptance criteria 9-10
11. Commit with clear commit message describing the feature, the corpus version, and the model used

Stop after step 11 and report. Do not proceed to companion cockpit work or Monitoring Agent without explicit instruction.

---

## Open questions for Ritu

1. Is the regulatory corpus scope correct? The spec covers 2 CFR 200 procurement, classification, cost reasonableness, subrecipient monitoring, conflict of interest, and Compliance Supplement Part 4-11.300. Anything to add for K8341 specifically? Anything to remove?
2. Confirm the model selection: Sonnet 4.5 by default, optional Opus for the initial Mode A generation.
3. Should Mode B queries be retained (logged with the question, response, timestamp) for review or audit purposes? Recommendation: yes, with a `compliance_qa_log` table; confirm.
4. Should Mode A scheduled runs be automatic, or always require Ritu/Krista to invoke? Recommendation: invocation-based for v1, with the option to add scheduling later.
5. Is the deferred item list complete, or are there other ideas to capture before they're forgotten?

These should be resolved before step 8 (Mode A run). Steps 1-7 can proceed.

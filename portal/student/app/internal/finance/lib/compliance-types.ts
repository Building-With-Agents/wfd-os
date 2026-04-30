// TypeScript mirror of the engine's Pydantic schemas for the Compliance
// Requirements Agent. Source of truth:
//   agents/grant-compliance/src/grant_compliance/compliance_requirements_agent/schemas.py
// (engine commit 4c1a566 on feature/compliance-engine-extract).
//
// Update both sides when the engine schema changes. Cockpit-side rendering
// in components/compliance/* depends on these field names matching exactly.

// ---------- enums ----------

export type ComplianceArea =
  | "procurement_standards"
  | "full_and_open_competition"
  | "cost_reasonableness"
  | "classification_200_331"
  | "subrecipient_monitoring"
  | "conflict_of_interest"
  | "standards_of_conduct"

export const COMPLIANCE_AREA_LABELS: Record<ComplianceArea, string> = {
  procurement_standards: "Procurement standards",
  full_and_open_competition: "Full and open competition",
  cost_reasonableness: "Cost reasonableness",
  classification_200_331: "Subrecipient vs contractor (§200.331)",
  subrecipient_monitoring: "Subrecipient monitoring",
  conflict_of_interest: "Conflict of interest",
  standards_of_conduct: "Standards of conduct",
}

export type ApplicabilityScope =
  | "all_contracts"
  | "contracts_above_threshold"
  | "sole_source_only"
  | "contractors_only"
  | "subrecipients_only"
  | "specific_circumstance"

export const APPLICABILITY_LABELS: Record<ApplicabilityScope, string> = {
  all_contracts: "All contracts",
  contracts_above_threshold: "Contracts above threshold",
  sole_source_only: "Sole-source only",
  contractors_only: "Contractors only",
  subrecipients_only: "Subrecipients only",
  specific_circumstance: "Specific circumstance",
}

export type Severity = "material" | "significant" | "minor" | "procedural"

export const SEVERITY_RANK: Record<Severity, number> = {
  material: 0,
  significant: 1,
  minor: 2,
  procedural: 3,
}

// ---------- requirement record ----------

export interface Applicability {
  applies_to: ApplicabilityScope
  threshold_value: number | string | null
  circumstance_description: string | null
}

export interface Requirement {
  requirement_id: string
  compliance_area: ComplianceArea
  regulatory_citation: string
  regulatory_text_excerpt: string
  applicability: Applicability
  requirement_summary: string
  documentation_artifacts_required: string[]
  documentation_form_guidance: string | null
  cfa_specific_application: string | null
  severity_if_missing: Severity
}

export interface Scope {
  compliance_areas: ComplianceArea[]
  contract_ids: string[]
  engagement_id: string | null
  description: string | null
}

export interface GrantContext {
  grant_id: string
  grant_name: string
  funder_name: string | null
  funder_type: string | null
  period_start: string | null
  period_end: string | null
  total_award_cents: number | null
  contract_count: number | null
  classifications: Record<string, unknown>
  thresholds_in_play: Record<string, unknown>
  notes: string | null
}

// ---------- top-level set ----------
//
// Two shapes show up in practice:
//   - The route /compliance/requirements/current returns RequirementsSetOut
//     (id, grant_id, generated_at, scope, regulatory_corpus_version,
//      grant_context, model_name, is_current, superseded_by_id, reviewed_*,
//      requirements[]).
//   - The agent's internal schema uses set_id instead of id.
// The cockpit consumes the route shape, so we model that.

export interface RequirementsSet {
  id: string
  grant_id: string
  generated_at: string
  scope: Scope
  regulatory_corpus_version: string
  grant_context: GrantContext
  model_name: string
  is_current: boolean
  superseded_by_id: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
  requirements: Requirement[]
}

// ---------- Mode B Q&A ----------

export interface QARequest {
  question: string
  grant_id?: string
  asked_by?: string
  context_hints?: Record<string, unknown> | null
}

export interface QAResponse {
  answer: string
  regulatory_citations: string[]
  relevant_existing_requirements: string[]
  caveats: string[]
  out_of_scope_warning: string | null
  refused: boolean
}

// ---------- corpus verification status (mirror of corpus manifest) ----------
//
// The engine's corpus has each section file marked with a verification status
// indicating how the agent may use the text. The cockpit uses this to colour-
// code citations in the UI (the honesty discipline made visual). When the
// corpus changes verification status of a section (e.g., upgrade paraphrase
// → verbatim by transcribing from eCFR), update this map.
//
// Source of truth for this map:
//   agents/grant-compliance/data/regulatory_corpus/manifest.json
// (engine commit 4c1a566 on feature/compliance-engine-extract).

export type VerificationStatus =
  | "verbatim"
  | "mixed-verbatim-paraphrase"
  | "structured-paraphrase"
  | "skeleton"
  | "unknown"

export const VERIFICATION_LABELS: Record<VerificationStatus, string> = {
  verbatim: "Verbatim",
  "mixed-verbatim-paraphrase": "Mixed (¶ verbatim)",
  "structured-paraphrase": "Paraphrase — verify",
  skeleton: "Skeleton — not yet citable",
  unknown: "Unmapped",
}

// CFR section → verification status. Citation strings can be subsection-
// specific (e.g., "2 CFR 200.318(c)(1)"); the lookup matches by the section
// number prefix. Order matters: longer / more-specific keys first to avoid
// shadowing.
const VERIFICATION_BY_SECTION: Array<[RegExp, VerificationStatus]> = [
  // CFR Subpart D — procurement (§§200.317–200.327)
  [/^2 CFR 200\.317\b/, "structured-paraphrase"],
  [/^2 CFR 200\.318\b/, "mixed-verbatim-paraphrase"], // (c) is verbatim
  [/^2 CFR 200\.319\b/, "verbatim"],
  [/^2 CFR 200\.320\b/, "structured-paraphrase"],
  [/^2 CFR 200\.321\b/, "structured-paraphrase"],
  [/^2 CFR 200\.322\b/, "structured-paraphrase"],
  [/^2 CFR 200\.323\b/, "structured-paraphrase"],
  [/^2 CFR 200\.324\b/, "structured-paraphrase"],
  [/^2 CFR 200\.325\b/, "structured-paraphrase"],
  [/^2 CFR 200\.326\b/, "structured-paraphrase"],
  [/^2 CFR 200\.327\b/, "structured-paraphrase"],
  // CFR Subpart D — subrecipient (§§200.331–200.333)
  [/^2 CFR 200\.331\b/, "structured-paraphrase"],
  [/^2 CFR 200\.332\b/, "structured-paraphrase"],
  [/^2 CFR 200\.333\b/, "structured-paraphrase"],
  // CFR Subpart E — cost principles
  [/^2 CFR 200\.404\b/, "structured-paraphrase"],
  // OMB Compliance Supplement
  [/^OMB Compliance Supplement/i, "skeleton"],
  [/Compliance Supplement.*11\.300/i, "skeleton"],
]

// Special case: §200.318(c) and its sub-paragraphs ARE verbatim. The
// citation string ends with "(c)" or "(c)(<n>)". Detect this and override
// the section-level "mixed" classification with "verbatim".
const VERBATIM_SUBPARAGRAPH = /^2 CFR 200\.318\(c\)/

export function getCitationVerification(citation: string): VerificationStatus {
  const trimmed = citation.trim()
  if (VERBATIM_SUBPARAGRAPH.test(trimmed)) return "verbatim"
  for (const [pattern, status] of VERIFICATION_BY_SECTION) {
    if (pattern.test(trimmed)) return status
  }
  return "unknown"
}

// CSS color class for a verification status. Maps to existing cockpit tone
// custom properties (--cockpit-good, --cockpit-watch, --cockpit-critical,
// --cockpit-text-3 for neutral) so the indicators line up with the rest of
// the cockpit's tone language.
export const VERIFICATION_TONE: Record<VerificationStatus, "good" | "watch" | "critical" | "neutral"> = {
  verbatim: "good",
  "mixed-verbatim-paraphrase": "good",
  "structured-paraphrase": "watch",
  skeleton: "critical",
  unknown: "neutral",
}

// ---------- summary card data ----------

export interface ComplianceSummary {
  total_requirements: number
  compliance_areas_covered: number
  citations_verbatim: number
  citations_mixed_verbatim_paraphrase: number
  citations_structured_paraphrase: number
  citations_unknown: number
  // Skeleton corpus sources are tracked at the corpus level, not per-
  // requirement (the agent refuses to cite skeleton sources). This field
  // counts corpus documents whose verification status is "skeleton" —
  // i.e., domain coverage that is structurally incomplete and not yet
  // citable. v1.1 work is needed to populate the OMB Compliance
  // Supplement; until then, skeleton_sources stays at 1.
  skeleton_corpus_sources: number
  skeleton_areas_affected: ComplianceArea[]
}

export function computeSummary(set: RequirementsSet): ComplianceSummary {
  const reqs = set.requirements
  const areasCovered = new Set(reqs.map((r) => r.compliance_area)).size
  let verbatim = 0
  let mixed = 0
  let paraphrase = 0
  let unknown = 0
  for (const r of reqs) {
    const v = getCitationVerification(r.regulatory_citation)
    if (v === "verbatim") verbatim++
    else if (v === "mixed-verbatim-paraphrase") mixed++
    else if (v === "structured-paraphrase") paraphrase++
    else unknown++
  }
  return {
    total_requirements: reqs.length,
    compliance_areas_covered: areasCovered,
    citations_verbatim: verbatim,
    citations_mixed_verbatim_paraphrase: mixed,
    citations_structured_paraphrase: paraphrase,
    citations_unknown: unknown,
    // Hardcoded for v1: 1 skeleton source (OMB Compliance Supplement) covering
    // 3 compliance areas per the manifest. Updates when the corpus is
    // populated.
    skeleton_corpus_sources: 1,
    skeleton_areas_affected: [
      "procurement_standards",
      "subrecipient_monitoring",
      "classification_200_331",
    ],
  }
}

// ---------- tab payload (returned by /api/finance/cockpit/tabs/compliance) ----------

export interface ComplianceTabPayload {
  tab: "compliance"
  // The current requirements set, or null when the engine is unreachable
  // or no set has been generated yet.
  current_set: RequirementsSet | null
  // engine_status surfaces engine availability per the audit-tab pattern.
  engine_status: "ok" | "unreachable" | "no_set_yet"
  engine_error: string | null
}

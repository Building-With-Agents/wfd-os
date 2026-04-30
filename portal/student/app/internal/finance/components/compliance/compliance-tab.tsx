"use client"

// Compliance Requirements tab — Mode A read-only display + Mode B Q&A
// trigger. Spec: agents/finance/design/compliance_requirements_display_spec.md
//
// Top-level component layout:
//   1. Verdict banner (engine status + corpus version + generated timestamp)
//   2. Five summary stat cards
//   3. "Ask the Compliance Agent" toggle button → opens QA panel
//   4. Filter bar (compliance area · severity · verification · search)
//   5. Grouped requirements table
//   6. "What's not in this view" footer
//
// Q&A panel renders to the side as an overlay when toggled. Per-requirement
// drill panel renders to the side when a row is clicked.

import { useMemo, useState, useCallback } from "react"
import {
  COMPLIANCE_AREA_LABELS,
  computeSummary,
  getCitationVerification,
  SEVERITY_RANK,
  VERIFICATION_LABELS,
  VERIFICATION_TONE,
  type ComplianceArea,
  type ComplianceTabPayload,
  type Requirement,
  type Severity,
  type VerificationStatus,
} from "../../lib/compliance-types"
import { ComplianceRequirementsTable } from "./compliance-table"
import { ComplianceQAPanel } from "./compliance-qa-panel"

const ALL_AREAS: ComplianceArea[] = [
  "procurement_standards",
  "full_and_open_competition",
  "cost_reasonableness",
  "classification_200_331",
  "subrecipient_monitoring",
  "conflict_of_interest",
  "standards_of_conduct",
]
const ALL_SEVERITIES: Severity[] = ["material", "significant", "minor", "procedural"]
const ALL_VERIFICATIONS: VerificationStatus[] = [
  "verbatim",
  "mixed-verbatim-paraphrase",
  "structured-paraphrase",
  "skeleton",
  "unknown",
]

export function ComplianceTab({ payload }: { payload: ComplianceTabPayload }) {
  // Drill state — which requirement is currently expanded in the side panel.
  const [activeRequirementId, setActiveRequirementId] = useState<string | null>(null)
  // Q&A panel state — open / closed.
  const [qaOpen, setQaOpen] = useState(false)
  // Pre-loaded question (used when the user clicks "Ask the agent about this"
  // from a drill panel). Cleared once the panel reads it.
  const [qaSeedQuestion, setQaSeedQuestion] = useState<string | null>(null)

  // Filters
  const [areaFilter, setAreaFilter] = useState<Set<ComplianceArea>>(new Set(ALL_AREAS))
  const [severityFilter, setSeverityFilter] = useState<Set<Severity>>(new Set(ALL_SEVERITIES))
  const [verificationFilter, setVerificationFilter] = useState<Set<VerificationStatus>>(
    new Set(ALL_VERIFICATIONS),
  )
  const [searchQuery, setSearchQuery] = useState("")

  // Engine-unreachable / no-set-yet states.
  if (payload.engine_status !== "ok" || !payload.current_set) {
    return (
      <div className="cockpit-tab-pane">
        <DegradedState payload={payload} />
      </div>
    )
  }

  return <ComplianceTabReady
    payload={payload}
    areaFilter={areaFilter}
    severityFilter={severityFilter}
    verificationFilter={verificationFilter}
    searchQuery={searchQuery}
    activeRequirementId={activeRequirementId}
    qaOpen={qaOpen}
    qaSeedQuestion={qaSeedQuestion}
    setAreaFilter={setAreaFilter}
    setSeverityFilter={setSeverityFilter}
    setVerificationFilter={setVerificationFilter}
    setSearchQuery={setSearchQuery}
    setActiveRequirementId={setActiveRequirementId}
    setQaOpen={setQaOpen}
    setQaSeedQuestion={setQaSeedQuestion}
  />
}

function ComplianceTabReady({
  payload,
  areaFilter, severityFilter, verificationFilter, searchQuery,
  activeRequirementId, qaOpen, qaSeedQuestion,
  setAreaFilter, setSeverityFilter, setVerificationFilter, setSearchQuery,
  setActiveRequirementId, setQaOpen, setQaSeedQuestion,
}: {
  payload: ComplianceTabPayload
  areaFilter: Set<ComplianceArea>
  severityFilter: Set<Severity>
  verificationFilter: Set<VerificationStatus>
  searchQuery: string
  activeRequirementId: string | null
  qaOpen: boolean
  qaSeedQuestion: string | null
  setAreaFilter: (s: Set<ComplianceArea>) => void
  setSeverityFilter: (s: Set<Severity>) => void
  setVerificationFilter: (s: Set<VerificationStatus>) => void
  setSearchQuery: (s: string) => void
  setActiveRequirementId: (id: string | null) => void
  setQaOpen: (b: boolean) => void
  setQaSeedQuestion: (q: string | null) => void
}) {
  const set = payload.current_set!
  const summary = useMemo(() => computeSummary(set), [set])

  // Sort + filter the requirements list.
  const filtered = useMemo(() => {
    const lcQuery = searchQuery.trim().toLowerCase()
    return set.requirements
      .filter((r) => areaFilter.has(r.compliance_area))
      .filter((r) => severityFilter.has(r.severity_if_missing))
      .filter((r) => verificationFilter.has(getCitationVerification(r.regulatory_citation)))
      .filter((r) => {
        if (!lcQuery) return true
        const haystack = [
          r.requirement_summary,
          r.cfa_specific_application ?? "",
          r.regulatory_citation,
          r.requirement_id,
        ].join(" ").toLowerCase()
        return haystack.includes(lcQuery)
      })
      .sort((a, b) => {
        // Primary: by compliance area declared order
        const ai = ALL_AREAS.indexOf(a.compliance_area)
        const bi = ALL_AREAS.indexOf(b.compliance_area)
        if (ai !== bi) return ai - bi
        // Secondary: by severity
        const sd = SEVERITY_RANK[a.severity_if_missing] - SEVERITY_RANK[b.severity_if_missing]
        if (sd !== 0) return sd
        // Tertiary: by citation order (string compare)
        return a.regulatory_citation.localeCompare(b.regulatory_citation)
      })
  }, [set, areaFilter, severityFilter, verificationFilter, searchQuery])

  const activeRequirement: Requirement | null = useMemo(
    () => set.requirements.find((r) => r.requirement_id === activeRequirementId) ?? null,
    [set, activeRequirementId],
  )

  const askAboutRequirement = useCallback(
    (req: Requirement) => {
      const seed = `Tell me more about ${req.regulatory_citation}: ${req.requirement_summary}`
      setQaSeedQuestion(seed)
      setQaOpen(true)
    },
    [setQaSeedQuestion, setQaOpen],
  )

  return (
    <div className="cockpit-tab-pane">
      <SetMetadataBanner payload={payload} />

      <SummaryCards summary={summary} />

      <div className="cockpit-panel" style={{ marginTop: 16 }}>
        <div className="cockpit-panel-head" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3>Documentation requirements ({summary.total_requirements})</h3>
          <button
            type="button"
            onClick={() => setQaOpen(true)}
            style={{
              background: "var(--cockpit-brand, #1A1A1A)",
              color: "#F5F2E8",
              border: "none",
              padding: "8px 16px",
              fontSize: "var(--cockpit-fs-button)",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            💬 Ask the Compliance Agent
          </button>
        </div>

        <FilterBar
          areaFilter={areaFilter}
          severityFilter={severityFilter}
          verificationFilter={verificationFilter}
          searchQuery={searchQuery}
          setAreaFilter={setAreaFilter}
          setSeverityFilter={setSeverityFilter}
          setVerificationFilter={setVerificationFilter}
          setSearchQuery={setSearchQuery}
          totalCount={set.requirements.length}
          filteredCount={filtered.length}
        />

        <ComplianceRequirementsTable
          requirements={filtered}
          onRequirementClick={(req) => setActiveRequirementId(req.requirement_id)}
          activeRequirementId={activeRequirementId}
        />

        <NotInThisViewFooter />
      </div>

      {activeRequirement && (
        <RequirementDrillPanel
          requirement={activeRequirement}
          onClose={() => setActiveRequirementId(null)}
          onAskAgent={askAboutRequirement}
        />
      )}

      {qaOpen && (
        <ComplianceQAPanel
          grantId={set.grant_id}
          seedQuestion={qaSeedQuestion}
          onSeedConsumed={() => setQaSeedQuestion(null)}
          onClose={() => setQaOpen(false)}
          requirements={set.requirements}
        />
      )}
    </div>
  )
}

// ---------- subcomponents ----------

function DegradedState({ payload }: { payload: ComplianceTabPayload }) {
  const isUnreachable = payload.engine_status === "unreachable"
  const tone = isUnreachable ? "var(--cockpit-critical)" : "var(--cockpit-watch)"
  const heading = isUnreachable
    ? "Compliance engine unreachable"
    : "No requirements set generated yet"
  return (
    <div className="cockpit-panel">
      <div className="cockpit-panel-head">
        <h3>Compliance Requirements</h3>
      </div>
      <div style={{ padding: "16px", borderLeft: `4px solid ${tone}`, margin: "16px" }}>
        <div style={{ fontWeight: 600, color: tone, marginBottom: 8 }}>{heading}</div>
        {payload.engine_error && (
          <div style={{ fontSize: "var(--cockpit-fs-body)", color: "var(--cockpit-text-2)", whiteSpace: "pre-wrap" }}>
            {payload.engine_error}
          </div>
        )}
        {!isUnreachable && (
          <div style={{ marginTop: 12, fontSize: "var(--cockpit-fs-body)", color: "var(--cockpit-text-2)" }}>
            Run a Mode A generation first via the Compliance Requirements Agent
            (engine on :8000). See agents/grant-compliance/docs/compliance_requirements_agent_spec.md.
          </div>
        )}
      </div>
    </div>
  )
}

function SetMetadataBanner({ payload }: { payload: ComplianceTabPayload }) {
  const set = payload.current_set!
  const generated = new Date(set.generated_at).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit",
  })
  return (
    <div
      style={{
        background: "var(--cockpit-surface-alt)",
        padding: "10px 16px",
        marginBottom: 16,
        fontSize: "var(--cockpit-fs-meta)",
        color: "var(--cockpit-text-3)",
        borderLeft: "3px solid var(--cockpit-border-strong)",
        display: "flex",
        gap: 24,
        flexWrap: "wrap",
      }}
    >
      <span><strong style={{ color: "var(--cockpit-text-2)" }}>Generated:</strong> {generated}</span>
      <span><strong style={{ color: "var(--cockpit-text-2)" }}>Model:</strong> {set.model_name}</span>
      <span><strong style={{ color: "var(--cockpit-text-2)" }}>Corpus version:</strong> {set.regulatory_corpus_version}</span>
      <span><strong style={{ color: "var(--cockpit-text-2)" }}>Set ID:</strong> <code>{set.id.slice(0, 8)}…</code></span>
      {!set.reviewed_at && (
        <span style={{ color: "var(--cockpit-watch)" }}>
          ⚠ Not yet reviewed by Ritu / counsel — treat as draft
        </span>
      )}
    </div>
  )
}

function SummaryCards({ summary }: { summary: ReturnType<typeof computeSummary> }) {
  // Five cards. The verification status breakdown is the honesty discipline
  // made visual — the spec is explicit that this is not to be simplified.
  return (
    <div className="cockpit-panel">
      <div className="cockpit-panel-head">
        <h3>At a glance</h3>
      </div>
      <div className="cockpit-three-col" style={{ padding: "12px 16px", gridTemplateColumns: "repeat(5, 1fr)", gap: 16 }}>
        <StatCard
          label="Total requirements"
          value={summary.total_requirements.toString()}
          sub={`across ${summary.compliance_areas_covered} compliance areas`}
        />
        <StatCard
          label="Verbatim citations"
          value={summary.citations_verbatim.toString()}
          sub="quotable from corpus"
          tone="good"
        />
        <StatCard
          label="Mixed (verbatim ¶)"
          value={summary.citations_mixed_verbatim_paraphrase.toString()}
          sub="§200.318(c) verbatim, rest paraphrased"
          tone="good"
        />
        <StatCard
          label="Structured paraphrase"
          value={summary.citations_structured_paraphrase.toString()}
          sub="verify against eCFR before quoting"
          tone="watch"
        />
        <StatCard
          label="Skeleton corpus sources"
          value={summary.skeleton_corpus_sources.toString()}
          sub={`affects ${summary.skeleton_areas_affected.length} areas (OMB Compl. Suppl.)`}
          tone="critical"
        />
      </div>
    </div>
  )
}

function StatCard({
  label, value, sub, tone,
}: {
  label: string
  value: string
  sub?: string
  tone?: "good" | "watch" | "critical" | "neutral"
}) {
  const valueColor =
    tone === "good" ? "var(--cockpit-good)"
    : tone === "watch" ? "var(--cockpit-watch)"
    : tone === "critical" ? "var(--cockpit-critical)"
    : undefined
  return (
    <div className="cockpit-stat">
      <div className="cockpit-stat-label">{label}</div>
      <div className="cockpit-stat-value cockpit-num" style={{ color: valueColor }}>{value}</div>
      {sub && <div className="cockpit-stat-sub">{sub}</div>}
    </div>
  )
}

function FilterBar({
  areaFilter, severityFilter, verificationFilter, searchQuery,
  setAreaFilter, setSeverityFilter, setVerificationFilter, setSearchQuery,
  totalCount, filteredCount,
}: {
  areaFilter: Set<ComplianceArea>
  severityFilter: Set<Severity>
  verificationFilter: Set<VerificationStatus>
  searchQuery: string
  setAreaFilter: (s: Set<ComplianceArea>) => void
  setSeverityFilter: (s: Set<Severity>) => void
  setVerificationFilter: (s: Set<VerificationStatus>) => void
  setSearchQuery: (s: string) => void
  totalCount: number
  filteredCount: number
}) {
  // Filter-chip click semantics. The default state is "all selected" (which
  // renders as no filter applied), so a naive toggle (`if has, remove; else
  // add`) makes the first click *remove* the chip from the set — the
  // opposite of what users expect ("click to filter to this"). Instead:
  //   1. If all are selected (no filter), clicking solos that chip.
  //   2. If only the clicked chip is selected, clicking again clears
  //      the filter (re-select all).
  //   3. Otherwise toggle additively (shift-click style for multi-select).
  //   4. Never allow empty — would render zero rows; reset to all.
  const applyFilterClick = <T,>(current: Set<T>, all: T[], clicked: T): Set<T> => {
    if (current.size === all.length) return new Set([clicked])
    if (current.size === 1 && current.has(clicked)) return new Set(all)
    const next = new Set(current)
    if (next.has(clicked)) next.delete(clicked); else next.add(clicked)
    if (next.size === 0) return new Set(all)
    return next
  }

  const filterPillStyle = (active: boolean): React.CSSProperties => ({
    padding: "4px 10px",
    fontSize: "var(--cockpit-fs-meta)",
    border: `1px solid ${active ? "var(--cockpit-border-strong)" : "var(--cockpit-border)"}`,
    background: active ? "var(--cockpit-surface)" : "var(--cockpit-surface-alt)",
    color: active ? "var(--cockpit-text-1)" : "var(--cockpit-text-3)",
    cursor: "pointer",
    fontFamily: "inherit",
    borderRadius: 0,
  })

  return (
    <div style={{ padding: "12px 16px", borderTop: "1px solid var(--cockpit-border)", borderBottom: "1px solid var(--cockpit-border)", background: "var(--cockpit-surface-alt)" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start" }}>
        <FilterGroup label="Compliance area">
          {ALL_AREAS.map((a) => (
            <button key={a} type="button" style={filterPillStyle(areaFilter.has(a))} onClick={() => setAreaFilter(applyFilterClick(areaFilter, ALL_AREAS, a))}>
              {COMPLIANCE_AREA_LABELS[a]}
            </button>
          ))}
        </FilterGroup>

        <FilterGroup label="Severity">
          {ALL_SEVERITIES.map((s) => (
            <button key={s} type="button" style={filterPillStyle(severityFilter.has(s))} onClick={() => setSeverityFilter(applyFilterClick(severityFilter, ALL_SEVERITIES, s))}>
              {s}
            </button>
          ))}
        </FilterGroup>

        <FilterGroup label="Citation source">
          {ALL_VERIFICATIONS.filter((v) => v !== "unknown").map((v) => (
            <button key={v} type="button" style={filterPillStyle(verificationFilter.has(v))} onClick={() => setVerificationFilter(applyFilterClick(verificationFilter, ALL_VERIFICATIONS, v))}>
              <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", marginRight: 6, background: `var(--cockpit-${VERIFICATION_TONE[v]})` }} />
              {VERIFICATION_LABELS[v]}
            </button>
          ))}
        </FilterGroup>

        <FilterGroup label="Search">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="search summary, citation, CFA application…"
            style={{
              padding: "4px 10px",
              fontSize: "var(--cockpit-fs-meta)",
              border: "1px solid var(--cockpit-border-strong)",
              background: "var(--cockpit-surface)",
              minWidth: 240,
              fontFamily: "inherit",
            }}
          />
        </FilterGroup>
      </div>

      <div style={{ marginTop: 8, fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        Showing {filteredCount} of {totalCount} requirements
      </div>
    </div>
  )
}

function FilterGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", textTransform: "uppercase", letterSpacing: "0.04em" }}>{label}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>{children}</div>
    </div>
  )
}

function NotInThisViewFooter() {
  return (
    <div
      style={{
        background: "var(--cockpit-surface-alt)",
        padding: "10px 14px",
        margin: "12px 16px 16px",
        fontSize: "var(--cockpit-fs-meta)",
        color: "var(--cockpit-text-3)",
        borderLeft: "3px solid var(--cockpit-border-strong)",
      }}
    >
      <strong style={{ color: "var(--cockpit-text-2)" }}>What&rsquo;s not in this view:</strong>{" "}
      Subpart F audit requirements (covered by Audit Readiness tab),
      ESD-specific pass-through requirements (skeleton in v1; populated when
      ESD framework is added to the corpus), Time &amp; Effort certifications
      under §200.430 (covered by the v1.3.3 Time &amp; Effort dimension), and
      indirect cost rate methodology under §200.414 (covered by Allowable
      Costs dimension).
    </div>
  )
}

// ---------- requirement drill panel ----------
//
// Renders to the right side as an overlay when a requirement row is clicked.
// Composition follows the existing DrillPanel slide-out pattern visually
// (right-docked, 560px wide, white card on muted overlay) but the content
// is a custom layout per the spec's "per-requirement drill-down" section
// rather than the polymorphic section model used by other drills.

function RequirementDrillPanel({
  requirement, onClose, onAskAgent,
}: {
  requirement: Requirement
  onClose: () => void
  onAskAgent: (req: Requirement) => void
}) {
  const verification = getCitationVerification(requirement.regulatory_citation)
  const tone = VERIFICATION_TONE[verification]
  const toneColor = `var(--cockpit-${tone})`

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, background: "rgba(26,26,26,0.32)", zIndex: 200,
        }}
      />
      <div
        style={{
          position: "fixed", top: 0, right: 0, bottom: 0, width: "min(640px, 100vw)",
          background: "var(--cockpit-surface)", zIndex: 201, overflow: "auto",
          borderLeft: "1px solid var(--cockpit-border)",
          padding: "20px 24px",
          fontSize: "var(--cockpit-fs-body)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              {COMPLIANCE_AREA_LABELS[requirement.compliance_area]}
            </div>
            <h2 style={{ fontSize: "var(--cockpit-fs-h2, 18px)", margin: "4px 0 8px", lineHeight: 1.3 }}>
              {requirement.regulatory_citation}
            </h2>
            <div style={{ fontSize: "var(--cockpit-fs-meta)", display: "flex", gap: 12, alignItems: "center" }}>
              <span><strong>id:</strong> <code>{requirement.requirement_id}</code></span>
              <SeverityBadge severity={requirement.severity_if_missing} />
              <VerificationBadge verification={verification} />
            </div>
          </div>
          <button type="button" onClick={onClose} style={{ background: "transparent", border: "none", fontSize: 24, cursor: "pointer", color: "var(--cockpit-text-3)" }}>
            ×
          </button>
        </div>

        <DrillSection title="Requirement summary">
          <p style={{ margin: 0, lineHeight: 1.55 }}>{requirement.requirement_summary}</p>
        </DrillSection>

        <DrillSection title="Applicability">
          <p style={{ margin: 0, lineHeight: 1.55 }}>
            <strong>{requirement.applicability.applies_to.replace(/_/g, " ")}</strong>
            {requirement.applicability.threshold_value !== null && (
              <> · threshold ${Number(requirement.applicability.threshold_value).toLocaleString()}</>
            )}
          </p>
          {requirement.applicability.circumstance_description && (
            <p style={{ margin: "6px 0 0", lineHeight: 1.55, color: "var(--cockpit-text-2)" }}>
              {requirement.applicability.circumstance_description}
            </p>
          )}
        </DrillSection>

        <DrillSection title="Regulatory text excerpt" toneAccent={toneColor}>
          {verification === "verbatim" && (
            <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-good)", marginBottom: 6 }}>
              ✓ verbatim from official source — quotable as the regulation&rsquo;s exact wording
            </div>
          )}
          {verification === "structured-paraphrase" && (
            <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-watch)", marginBottom: 6 }}>
              ⚠ structured paraphrase — verify against eCFR before treating as authoritative quotation
            </div>
          )}
          {verification === "mixed-verbatim-paraphrase" && (
            <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-good)", marginBottom: 6 }}>
              ✓ §200.318(c) verbatim from CFR 2024 vol. 1; remainder paraphrased
            </div>
          )}
          {verification === "skeleton" && (
            <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-critical)", marginBottom: 6 }}>
              ✗ skeleton corpus source — not yet citable; requires manual transcription from the published OMB Compliance Supplement
            </div>
          )}
          <blockquote style={{
            margin: 0, padding: "12px 14px",
            background: "var(--cockpit-surface-alt)",
            borderLeft: `3px solid ${toneColor}`,
            fontSize: "var(--cockpit-fs-body)", lineHeight: 1.55,
            whiteSpace: "pre-wrap",
          }}>
            {requirement.regulatory_text_excerpt}
          </blockquote>
        </DrillSection>

        <DrillSection title="Documentation artifacts required">
          {requirement.documentation_artifacts_required.length === 0 ? (
            <p style={{ margin: 0, color: "var(--cockpit-text-3)", fontStyle: "italic" }}>None listed.</p>
          ) : (
            <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.55 }}>
              {requirement.documentation_artifacts_required.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          )}
        </DrillSection>

        {requirement.documentation_form_guidance && (
          <DrillSection title="Documentation form guidance">
            <p style={{ margin: 0, lineHeight: 1.55, whiteSpace: "pre-wrap" }}>{requirement.documentation_form_guidance}</p>
          </DrillSection>
        )}

        {requirement.cfa_specific_application && (
          <DrillSection title="CFA-specific application">
            <p style={{ margin: 0, lineHeight: 1.55, whiteSpace: "pre-wrap", color: "var(--cockpit-text-1)" }}>
              {requirement.cfa_specific_application}
            </p>
          </DrillSection>
        )}

        <div style={{ marginTop: 24, paddingTop: 16, borderTop: "1px solid var(--cockpit-border)", display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => onAskAgent(requirement)}
            style={{
              background: "var(--cockpit-brand)",
              color: "#F5F2E8",
              border: "none",
              padding: "8px 16px",
              fontSize: "var(--cockpit-fs-button)",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            💬 Ask the agent about this requirement
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: "transparent",
              color: "var(--cockpit-text-2)",
              border: "1px solid var(--cockpit-border-strong)",
              padding: "8px 16px",
              fontSize: "var(--cockpit-fs-button)",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Close
          </button>
        </div>

        <div style={{ marginTop: 16, padding: "10px 14px", background: "var(--cockpit-surface-alt)", fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", borderLeft: "3px solid var(--cockpit-border-strong)" }}>
          Documentation status workflow lands in Session 2. Currently the
          drill panel is read-only — status mutation, evidence links, and
          per-(requirement, target) status entries are not yet wired.
        </div>
      </div>
    </>
  )
}

function DrillSection({ title, children, toneAccent }: { title: string; children: React.ReactNode; toneAccent?: string }) {
  return (
    <div style={{
      marginBottom: 18,
      paddingLeft: toneAccent ? 12 : 0,
      borderLeft: toneAccent ? `3px solid ${toneAccent}` : undefined,
    }}>
      <div style={{
        fontSize: "var(--cockpit-fs-meta)",
        color: "var(--cockpit-text-3)",
        textTransform: "uppercase",
        letterSpacing: "0.04em",
        marginBottom: 6,
        fontWeight: 600,
      }}>
        {title}
      </div>
      {children}
    </div>
  )
}

// ---------- shared badges (also used by table rows) ----------

export function SeverityBadge({ severity }: { severity: Severity }) {
  const tone =
    severity === "material" ? "var(--cockpit-critical)"
    : severity === "significant" ? "var(--cockpit-watch)"
    : "var(--cockpit-text-3)"
  return (
    <span style={{
      padding: "2px 8px",
      fontSize: "var(--cockpit-fs-meta)",
      textTransform: "uppercase",
      letterSpacing: "0.04em",
      fontWeight: 600,
      color: tone,
      border: `1px solid ${tone}`,
    }}>
      {severity}
    </span>
  )
}

export function VerificationBadge({ verification }: { verification: VerificationStatus }) {
  const tone = VERIFICATION_TONE[verification]
  const color = `var(--cockpit-${tone})`
  return (
    <span title={`citation source: ${VERIFICATION_LABELS[verification]}`} style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      fontSize: "var(--cockpit-fs-meta)",
      color: "var(--cockpit-text-3)",
    }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
      <span>{VERIFICATION_LABELS[verification]}</span>
    </span>
  )
}

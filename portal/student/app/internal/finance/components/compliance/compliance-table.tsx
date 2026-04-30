"use client"

// Grouped requirements table for the Compliance Requirements tab.
// Rendered inside the main panel after the filter bar. Each compliance area
// gets a header row with counts + severity distribution; data rows render
// per-requirement with citation, severity, verification status, and a
// truncated summary.

import { useMemo } from "react"
import {
  COMPLIANCE_AREA_LABELS,
  getCitationVerification,
  type ComplianceArea,
  type Requirement,
  type Severity,
} from "../../lib/compliance-types"
import { SeverityBadge, VerificationBadge } from "./compliance-tab"

export function ComplianceRequirementsTable({
  requirements,
  onRequirementClick,
  activeRequirementId,
}: {
  requirements: Requirement[]
  onRequirementClick: (req: Requirement) => void
  activeRequirementId: string | null
}) {
  // Group by compliance_area, preserving the input order (the parent already
  // sorted by area declared order, then severity, then citation).
  const groups = useMemo(() => {
    const out: Array<{ area: ComplianceArea; rows: Requirement[] }> = []
    for (const req of requirements) {
      const last = out[out.length - 1]
      if (last && last.area === req.compliance_area) {
        last.rows.push(req)
      } else {
        out.push({ area: req.compliance_area, rows: [req] })
      }
    }
    return out
  }, [requirements])

  if (groups.length === 0) {
    return (
      <div style={{ padding: "32px 16px", textAlign: "center", color: "var(--cockpit-text-3)", fontSize: "var(--cockpit-fs-body)", fontStyle: "italic" }}>
        No requirements match the active filters.
      </div>
    )
  }

  return (
    <div>
      {groups.map(({ area, rows }) => (
        <AreaSection
          key={area}
          area={area}
          rows={rows}
          onRequirementClick={onRequirementClick}
          activeRequirementId={activeRequirementId}
        />
      ))}
    </div>
  )
}

function AreaSection({
  area, rows, onRequirementClick, activeRequirementId,
}: {
  area: ComplianceArea
  rows: Requirement[]
  onRequirementClick: (req: Requirement) => void
  activeRequirementId: string | null
}) {
  // Severity distribution for the section header
  const sevCounts = rows.reduce<Record<Severity, number>>((acc, r) => {
    acc[r.severity_if_missing] = (acc[r.severity_if_missing] || 0) + 1
    return acc
  }, { material: 0, significant: 0, minor: 0, procedural: 0 })

  return (
    <div>
      <div
        style={{
          background: "var(--cockpit-surface-alt)",
          padding: "10px 16px",
          borderTop: "1px solid var(--cockpit-border)",
          borderBottom: "1px solid var(--cockpit-border)",
          display: "flex",
          gap: 16,
          alignItems: "center",
          fontSize: "var(--cockpit-fs-body)",
        }}
      >
        <strong>{COMPLIANCE_AREA_LABELS[area]}</strong>
        <span style={{ color: "var(--cockpit-text-3)", fontSize: "var(--cockpit-fs-meta)" }}>
          {rows.length} requirement{rows.length === 1 ? "" : "s"}
        </span>
        <span style={{ marginLeft: "auto", display: "flex", gap: 12, fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)" }}>
          {sevCounts.material > 0 && <span style={{ color: "var(--cockpit-critical)" }}>{sevCounts.material} material</span>}
          {sevCounts.significant > 0 && <span style={{ color: "var(--cockpit-watch)" }}>{sevCounts.significant} significant</span>}
          {sevCounts.minor > 0 && <span>{sevCounts.minor} minor</span>}
          {sevCounts.procedural > 0 && <span>{sevCounts.procedural} procedural</span>}
        </span>
      </div>

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--cockpit-fs-body)" }}>
        <thead>
          <tr>
            <th style={th(16, "left")}>Requirement</th>
            <th style={th(0, "left")}>Citation</th>
            <th style={th(0, "left")}>Severity</th>
            <th style={th(0, "left")}>Source</th>
            <th style={th(16, "left")}>Applicability</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((req) => {
            const isActive = req.requirement_id === activeRequirementId
            return (
              <tr
                key={req.requirement_id}
                onClick={() => onRequirementClick(req)}
                style={{
                  cursor: "pointer",
                  background: isActive ? "var(--cockpit-surface-warm, #EAE6D8)" : undefined,
                }}
              >
                <td style={td(16, "left")}>
                  <div style={{ fontWeight: 500, lineHeight: 1.4 }}>
                    {truncate(req.requirement_summary, 140)}
                  </div>
                  <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", marginTop: 2 }}>
                    <code>{req.requirement_id}</code>
                  </div>
                </td>
                <td style={td(0, "left")}>
                  <code style={{ fontSize: "var(--cockpit-fs-meta)" }}>{req.regulatory_citation}</code>
                </td>
                <td style={td(0, "left")}>
                  <SeverityBadge severity={req.severity_if_missing} />
                </td>
                <td style={td(0, "left")}>
                  <VerificationBadge verification={getCitationVerification(req.regulatory_citation)} />
                </td>
                <td style={td(16, "left")}>
                  <span style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-2)" }}>
                    {applicabilityLabel(req)}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ---------- helpers ----------

function th(padHoriz: number, align: "left" | "right"): React.CSSProperties {
  return {
    textAlign: align,
    padding: `8px ${padHoriz || 12}px 8px ${padHoriz}px`,
    borderBottom: "1px solid var(--cockpit-border)",
    fontWeight: 600,
    fontSize: "var(--cockpit-fs-meta)",
    color: "var(--cockpit-text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    background: "var(--cockpit-surface)",
  }
}

function td(padHoriz: number, align: "left" | "right"): React.CSSProperties {
  return {
    textAlign: align,
    padding: `10px ${padHoriz || 12}px 10px ${padHoriz}px`,
    borderBottom: "1px solid var(--cockpit-border)",
    verticalAlign: "top",
  }
}

function truncate(s: string, max: number): string {
  if (s.length <= max) return s
  return s.slice(0, max - 1).trimEnd() + "…"
}

function applicabilityLabel(req: Requirement): string {
  const a = req.applicability
  if (a.applies_to === "contracts_above_threshold" && a.threshold_value !== null) {
    return `contracts above $${Number(a.threshold_value).toLocaleString()}`
  }
  if (a.applies_to === "specific_circumstance" && a.circumstance_description) {
    return truncate(a.circumstance_description, 60)
  }
  return a.applies_to.replace(/_/g, " ")
}

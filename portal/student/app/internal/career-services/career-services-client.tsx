"use client"

// Career Services student picker — clicks open the student portal
// (/student?id=<uuid>) in a new tab so staff don't lose their place
// in the internal dashboard. Intentionally thin: this is a gateway
// to the real student-facing portal, not a cockpit in its own right.

import { useCallback, useEffect, useMemo, useState } from "react"
import type {
  CaseloadPayload,
  CaseloadFilters,
  CaseloadRow,
} from "../recruiting/lib/types"
import { fetchCaseload } from "../recruiting/lib/api"

interface InitialState {
  caseload: CaseloadPayload
  initialFilters: CaseloadFilters
}

export function CareerServicesClient({ initial }: { initial: InitialState }) {
  const [filters, setFilters] = useState<CaseloadFilters>(initial.initialFilters)
  const [payload, setPayload] = useState<CaseloadPayload>(initial.caseload)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchCaseload(filters, 200)
      .then((p) => { if (!cancelled) setPayload(p) })
      .catch((e) => { if (!cancelled) setError(String(e)) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [filters])

  const rows = payload.rows
  const readyCount = useMemo(
    () => rows.filter((r) => (r.profile_completeness_score ?? 0) >= 0.5).length,
    [rows],
  )

  return (
    <div style={{ padding: "2rem 2.5rem", maxWidth: 1200 }}>
      <div style={{ marginBottom: "0.5rem", fontSize: "0.75rem", color: "var(--cockpit-text-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
        AGENT PREVIEW · Career Services
      </div>
      <h1 className="cockpit-display" style={{ margin: "0 0 0.5rem", fontSize: "2rem" }}>
        Student Portal
      </h1>
      <p style={{ color: "var(--cockpit-text-2)", maxWidth: 700, marginTop: 0 }}>
        Pick a student to open their portal. You&apos;ll see exactly what the
        student sees when they log in: profile, job matches, gap analysis,
        journey pipeline, showcase status, and the AI Career Navigator chat.
        Opens in a new tab.
      </p>

      <div style={summaryStrip}>
        <span>
          <strong>{rows.length}</strong> student{rows.length === 1 ? "" : "s"} in view
        </span>
        <span>·</span>
        <span>
          <strong>{readyCount}</strong> with profile ≥50% complete
        </span>
        <span>·</span>
        <span style={{ color: "var(--cockpit-text-3)" }}>
          {filters.tenant || "all tenants"}
        </span>
      </div>

      <FilterBar filters={filters} onChange={setFilters} />

      {error ? (
        <div className="cockpit-api-error" style={{ margin: "1rem 0" }}>
          <strong>Error loading students:</strong> {error}
        </div>
      ) : null}

      <StudentTable rows={rows} loading={loading} />

      <p style={{ fontSize: "0.75rem", color: "var(--cockpit-text-3)", marginTop: "2rem" }}>
        Note: clicking a student opens the real student portal — same page and
        same data the student sees on login. No authentication layer today, so
        treat the URL as sensitive.
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------

function FilterBar({
  filters,
  onChange,
}: {
  filters: CaseloadFilters
  onChange: (next: CaseloadFilters) => void
}) {
  return (
    <div
      style={{
        display: "flex",
        gap: "1rem",
        flexWrap: "wrap",
        alignItems: "center",
        padding: "1rem 0",
        borderTop: "1px solid var(--cockpit-border)",
        borderBottom: "1px solid var(--cockpit-border)",
        margin: "1rem 0 0",
      }}
    >
      <label style={filterLabel}>
        Tenant
        <select
          value={filters.tenant}
          onChange={(e) => onChange({ ...filters, tenant: e.target.value })}
          style={filterInput}
        >
          <option value="">All tenants</option>
          <option value="CFA">CFA</option>
          <option value="WSB">WSB (Borderplex)</option>
        </select>
      </label>
      <label style={filterLabel}>
        Cohort
        <input
          type="text"
          placeholder="e.g. cohort-1-feb-2026"
          value={filters.cohort}
          onChange={(e) => onChange({ ...filters, cohort: e.target.value })}
          style={filterInput}
        />
      </label>
      <label style={{ ...filterLabel, flex: 1, minWidth: "14rem" }}>
        Search
        <input
          type="text"
          placeholder="Name or email"
          value={filters.q}
          onChange={(e) => onChange({ ...filters, q: e.target.value })}
          style={filterInput}
        />
      </label>
    </div>
  )
}

function StudentTable({ rows, loading }: { rows: CaseloadRow[]; loading: boolean }) {
  if (rows.length === 0 && !loading) {
    return (
      <div style={{ padding: "2rem 0", color: "var(--cockpit-text-3)" }}>
        No students match the current filters.
      </div>
    )
  }
  return (
    <div style={{ opacity: loading ? 0.6 : 1, marginTop: "1rem" }}>
      <table className="cockpit-table">
        <thead>
          <tr>
            <th>Student</th>
            <th>Cohort</th>
            <th>Tenant</th>
            <th className="cockpit-num">Complete</th>
            <th className="cockpit-num">Matches</th>
            <th className="cockpit-num">Apps</th>
            <th>Portal</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.student_id}>
              <td>
                <strong>{r.full_name}</strong>
                {r.pipeline_status ? (
                  <div style={{ fontSize: "0.75rem", color: "var(--cockpit-text-3)" }}>
                    {r.pipeline_status}
                  </div>
                ) : null}
              </td>
              <td>{r.cohort_id ?? "—"}</td>
              <td>{r.tenant}</td>
              <td className="cockpit-num">
                {r.profile_completeness_score !== null
                  ? `${Math.round(r.profile_completeness_score * 100)}%`
                  : "—"}
              </td>
              <td className="cockpit-num">{r.match_count}</td>
              <td className="cockpit-num">{r.applications_count}</td>
              <td>
                <a
                  href={`/student?id=${r.student_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={portalLink}
                >
                  Open portal →
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ---------------------------------------------------------------------------

const summaryStrip: React.CSSProperties = {
  display: "flex",
  gap: "0.75rem",
  fontSize: "0.875rem",
  color: "var(--cockpit-text-2)",
  marginTop: "1rem",
  alignItems: "center",
}

const filterLabel: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  fontSize: "0.7rem",
  fontWeight: 600,
  color: "var(--cockpit-text-3)",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  gap: "0.25rem",
}

const filterInput: React.CSSProperties = {
  padding: "0.375rem 0.5rem",
  fontSize: "0.875rem",
  border: "1px solid var(--cockpit-border)",
  borderRadius: "0.25rem",
  background: "white",
  color: "var(--cockpit-text-1)",
  textTransform: "none",
  fontWeight: 400,
}

const portalLink: React.CSSProperties = {
  display: "inline-block",
  padding: "0.25rem 0.625rem",
  fontSize: "0.8125rem",
  fontWeight: 500,
  color: "var(--cockpit-text-1)",
  background: "var(--cockpit-accent, #F5F2E8)",
  border: "1px solid var(--cockpit-border)",
  borderRadius: "0.25rem",
  textDecoration: "none",
  whiteSpace: "nowrap",
}

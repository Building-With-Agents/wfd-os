"use client"

// Caseload view — Dinah's case-manager home. Table of students with
// per-row match summary + applications count. Filter bar drives tenant
// / cohort / tier / min-match-score. Row click opens the drill with
// full match list + narratives + "Initiate application" action.
//
// MVP: drill shows the student's top 10 matches from /students/{id}/matches.
// Later additions could include per-match narrative body, explicit
// "advance status" actions, and case-manager assignment.

import { useCallback, useEffect, useMemo, useState } from "react"
import type {
  CaseloadPayload,
  CaseloadFilters,
  CaseloadRow,
  StudentDetail,
} from "../lib/types"
import { fetchCaseload, fetchStudent, fetchStudentMatches } from "../lib/api"
import type { DrillEntry, HeroGridCell } from "../../_shared/types"
import { CockpitShell } from "../../_shared/cockpit-shell"
import { HeroGrid } from "../../_shared/hero/hero-grid"
import { DrillPanel } from "../../_shared/drill/drill-panel"
import { RecruitingTopbar } from "../components/recruiting-topbar"
import { RecruitingChatPanel } from "../components/recruiting-chat-panel"

interface InitialState {
  caseload: CaseloadPayload
  initialFilters: CaseloadFilters
}

export function CaseloadClient({ initial }: { initial: InitialState }) {
  const [filters, setFilters] = useState<CaseloadFilters>(initial.initialFilters)
  const [payload, setPayload] = useState<CaseloadPayload>(initial.caseload)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Drill state — selected student shows their detail + matches
  const [activeStudentId, setActiveStudentId] = useState<string | null>(null)
  const [drillCache, setDrillCache] = useState<Record<string, DrillEntry>>({})
  const [drillLoading, setDrillLoading] = useState(false)
  const [drillError, setDrillError] = useState<string | null>(null)

  // Re-fetch whenever filters change.
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

  // Stats hero — rough roll-up from the current filtered rows. Cheap to
  // compute client-side; no separate backend call.
  const heroCells: HeroGridCell[] = useMemo(() => {
    const rows = payload.rows
    const withMatches = rows.filter((r) => r.match_count > 0).length
    const withApps = rows.filter((r) => r.applications_count > 0).length
    const avgTop =
      rows.filter((r) => r.top_match_score !== null).length === 0
        ? null
        : rows.reduce((a, r) => a + (r.top_match_score ?? 0), 0) /
          Math.max(rows.filter((r) => r.top_match_score !== null).length, 1)
    return [
      {
        label: "Students in view",
        value: String(rows.length),
        subtitle: filters.tenant || "all tenants",
        status_chip: { tone: "neutral" as const, label: "CASELOAD" },
      },
      {
        label: "With job matches",
        value: String(withMatches),
        subtitle: `of ${rows.length} students`,
        status_chip: {
          tone: (withMatches > 0 ? "positive" : "warning") as const,
          label: withMatches > 0 ? "MATCHED" : "NO MATCHES",
        },
      },
      {
        label: "With open applications",
        value: String(withApps),
        subtitle: `of ${rows.length} students`,
        status_chip: {
          tone: (withApps > 0 ? "positive" : "neutral") as const,
          label: withApps > 0 ? "IN FLIGHT" : "NONE",
        },
      },
      {
        label: "Avg top-match score",
        value: avgTop !== null ? avgTop.toFixed(2) : "—",
        subtitle: "cosine similarity",
        status_chip: {
          tone:
            avgTop === null
              ? ("neutral" as const)
              : avgTop >= 0.5
                ? ("positive" as const)
                : ("warning" as const),
          label:
            avgTop === null
              ? "NO DATA"
              : avgTop >= 0.5
                ? "STRONG"
                : "WEAK",
        },
      },
    ]
  }, [payload.rows, filters.tenant])

  // Open drill for a student. Fetches /students/{id} + /students/{id}/matches
  // in parallel; renders as a RowsSection (student summary) + TableSection
  // (matches).
  const openStudentDrill = useCallback(async (studentId: string) => {
    setActiveStudentId(studentId)
    if (drillCache[studentId]) return
    setDrillLoading(true)
    setDrillError(null)
    try {
      const [studentResp, matchesData] = await Promise.all([
        fetchStudent(studentId),
        fetchStudentMatches(studentId, 10),
      ])
      const entry = buildStudentDrillEntry(
        studentResp.student,
        matchesData as {
          matches?: Array<{
            job_id: number
            job_title: string
            company: string | null
            cosine: number
            location: string | null
          }>
          matching_status?: string
        } | null,
      )
      setDrillCache((prev) => ({ ...prev, [studentId]: entry }))
    } catch (err) {
      setDrillError(String(err))
    } finally {
      setDrillLoading(false)
    }
  }, [drillCache])

  const closeDrill = useCallback(() => {
    setActiveStudentId(null)
    setDrillError(null)
  }, [])

  const activeDrill: DrillEntry | null =
    activeStudentId ? drillCache[activeStudentId] ?? null : null

  return (
    <>
      <CockpitShell
        main={
          <>
            <RecruitingTopbar leaf="Caseload view" />
            <div className="cockpit-hero">
              <div className="cockpit-hero-eyebrow">
                Case manager · student-first view · {payload.total} student
                {payload.total === 1 ? "" : "s"} loaded
              </div>
              <h1 className="cockpit-hero-title cockpit-display">
                Who needs attention today?
              </h1>
              <p className="cockpit-hero-subtitle">
                Filter by cohort or tier, click a student to see their top job
                matches and initiate applications.
              </p>
              <HeroGrid cells={heroCells} />
            </div>

            <CaseloadFilterBar filters={filters} onChange={setFilters} />

            {error ? (
              <div className="cockpit-api-error" style={{ margin: "1rem 0" }}>
                <strong>Caseload error:</strong> {error}
              </div>
            ) : null}

            <CaseloadTable
              rows={payload.rows}
              loading={loading}
              onRowClick={openStudentDrill}
            />
          </>
        }
        chat={<RecruitingChatPanel activeView="Caseload" />}
      />
      <DrillPanel
        entry={activeDrill}
        loading={drillLoading && !activeDrill}
        error={drillError}
        onClose={closeDrill}
      />
    </>
  )
}

// ---------------------------------------------------------------------------
// Subcomponents
// ---------------------------------------------------------------------------

function CaseloadFilterBar({
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
        gap: "0.75rem",
        flexWrap: "wrap",
        padding: "1rem 1.5rem",
        borderBottom: "1px solid var(--cockpit-border)",
        alignItems: "center",
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
      <label style={filterLabel}>
        Tier
        <select
          value={filters.tier}
          onChange={(e) => onChange({ ...filters, tier: e.target.value })}
          style={filterInput}
        >
          <option value="">Any tier</option>
          <option value="A">A (≥80% complete)</option>
          <option value="B">B (50-79%)</option>
          <option value="C">C (&lt;50%)</option>
        </select>
      </label>
      <label style={filterLabel}>
        Min match score
        <input
          type="number"
          step="0.05"
          min="0"
          max="1"
          placeholder="0.00"
          value={filters.min_match_score ?? ""}
          onChange={(e) =>
            onChange({
              ...filters,
              min_match_score: e.target.value === "" ? null : Number(e.target.value),
            })
          }
          style={{ ...filterInput, width: "6rem" }}
        />
      </label>
      <label style={{ ...filterLabel, flex: 1, minWidth: "12rem" }}>
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

function CaseloadTable({
  rows,
  loading,
  onRowClick,
}: {
  rows: CaseloadRow[]
  loading: boolean
  onRowClick: (studentId: string) => void
}) {
  if (rows.length === 0 && !loading) {
    return (
      <div style={{ padding: "2rem 1.5rem", color: "var(--cockpit-text-3)" }}>
        No students match the current filters.
      </div>
    )
  }
  return (
    <div style={{ padding: "0.5rem 1.5rem 2rem", opacity: loading ? 0.6 : 1 }}>
      <table className="cockpit-table">
        <thead>
          <tr>
            <th>Student</th>
            <th>Cohort</th>
            <th>Tenant</th>
            <th>Tier</th>
            <th>Top match</th>
            <th className="cockpit-num">Score</th>
            <th className="cockpit-num">Matches</th>
            <th className="cockpit-num">Apps</th>
            <th className="cockpit-num">Last touch</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.student_id}
              onClick={() => onRowClick(r.student_id)}
              style={{ cursor: "pointer" }}
              className="cockpit-table-row-clickable"
            >
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
              <td>
                <TierBadge tier={r.tier} />
              </td>
              <td>
                {r.top_match_job_title ? (
                  <>
                    <div>{truncate(r.top_match_job_title, 50)}</div>
                    {r.top_match_company ? (
                      <div style={{ fontSize: "0.75rem", color: "var(--cockpit-text-3)" }}>
                        {r.top_match_company}
                      </div>
                    ) : null}
                  </>
                ) : (
                  <span style={{ color: "var(--cockpit-text-3)" }}>—</span>
                )}
              </td>
              <td className="cockpit-num">
                {r.top_match_score !== null
                  ? r.top_match_score.toFixed(2)
                  : "—"}
              </td>
              <td className="cockpit-num">{r.match_count}</td>
              <td className="cockpit-num">{r.applications_count}</td>
              <td className="cockpit-num">
                {r.days_since_last_touch !== null
                  ? `${r.days_since_last_touch}d ago`
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TierBadge({ tier }: { tier: "A" | "B" | "C" }) {
  const colors = {
    A: { bg: "#d1fae5", fg: "#065f46" },
    B: { bg: "#fef3c7", fg: "#92400e" },
    C: { bg: "#fee2e2", fg: "#991b1b" },
  }
  const c = colors[tier]
  return (
    <span
      style={{
        background: c.bg,
        color: c.fg,
        padding: "0.125rem 0.5rem",
        borderRadius: "0.25rem",
        fontSize: "0.75rem",
        fontWeight: 600,
      }}
    >
      {tier}
    </span>
  )
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s
}

// ---------------------------------------------------------------------------
// Drill entry builder — student detail + top-N matches table
// ---------------------------------------------------------------------------

function buildStudentDrillEntry(
  student: StudentDetail,
  matchesData: {
    matches?: Array<{
      job_id: number
      job_title: string
      company: string | null
      cosine: number
      location: string | null
    }>
    matching_status?: string
  } | null,
): DrillEntry {
  const matches = matchesData?.matches ?? []

  const rows: Array<Record<string, string | number | boolean>> = matches.map((m) => ({
    job: m.job_title,
    company: m.company ?? "—",
    location: m.location ?? "—",
    cosine: m.cosine.toFixed(2),
  }))

  const noMatchesNote =
    matchesData?.matching_status === "pending_student_index"
      ? "Student embeddings haven't landed yet — matches will appear once they do."
      : rows.length === 0
        ? "No matches above the cosine threshold."
        : undefined

  return {
    eyebrow: "Student · caseload drill",
    title: student.full_name,
    summary:
      [student.cohort_id, student.institution, student.pipeline_status]
        .filter(Boolean)
        .join(" · ") || "No cohort info",
    sections: [
      {
        type: "rows",
        title: "Student profile",
        rows: [
          { label: "Email", value: student.email ?? "—" },
          { label: "Phone", value: student.phone ?? "—" },
          {
            label: "Location",
            value:
              [student.city, student.state].filter(Boolean).join(", ") || "—",
          },
          {
            label: "Education",
            value:
              [student.institution, student.degree, student.field_of_study]
                .filter(Boolean)
                .join(" · ") || "—",
          },
          {
            label: "Graduation",
            value: student.graduation_year ? String(student.graduation_year) : "—",
          },
          { label: "Pipeline", value: student.pipeline_status ?? "—" },
          { label: "Track", value: student.track ?? "—" },
          {
            label: "Skills",
            value:
              student.skills && student.skills.length > 0
                ? student.skills.map((s) => s.name).join(", ")
                : "No skills recorded",
          },
        ],
      },
      {
        type: "table",
        title: `Top ${matches.length} job matches`,
        columns: [
          { key: "job", label: "Job title" },
          { key: "company", label: "Company" },
          { key: "location", label: "Location" },
          { key: "cosine", label: "Cosine", align: "right" },
        ],
        rows,
        note: noMatchesNote,
      },
    ],
  }
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

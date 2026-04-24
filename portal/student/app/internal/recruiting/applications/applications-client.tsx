"use client"

// Applications view — pipeline table of in-progress applications.
// Status filter + grouping hero show where applications are sitting.
// Row click opens the student drill (same pattern as caseload — reuse
// /students/{id} + /students/{id}/matches).

import { useCallback, useEffect, useMemo, useState } from "react"
import type {
  ApplicationsListPayload,
  ApplicationsFilters,
  ApplicationListRow,
  StudentDetail,
} from "../lib/types"
import { fetchApplications, fetchStudent } from "../lib/api"
import type { DrillEntry, HeroGridCell } from "../../_shared/types"
import { CockpitShell } from "../../_shared/cockpit-shell"
import { HeroGrid } from "../../_shared/hero/hero-grid"
import { DrillPanel } from "../../_shared/drill/drill-panel"
import { RecruitingTopbar } from "../components/recruiting-topbar"
import { RecruitingChatPanel } from "../components/recruiting-chat-panel"

interface InitialState {
  applications: ApplicationsListPayload
  initialFilters: ApplicationsFilters
}

// Display order for status grouping. Rows with statuses not in this list
// fall into "Other".
const STATUS_ORDER: readonly string[] = [
  "draft",
  "submitted_for_review",
  "approved",
  "packaged",
  "sent",
  "delivered",
  "employer_ack",
  "interviewing",
  "offer",
  "hired",
  "rejected",
] as const

export function ApplicationsClient({ initial }: { initial: InitialState }) {
  const [filters, setFilters] = useState<ApplicationsFilters>(initial.initialFilters)
  const [payload, setPayload] = useState<ApplicationsListPayload>(initial.applications)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [activeStudentId, setActiveStudentId] = useState<string | null>(null)
  const [drillCache, setDrillCache] = useState<Record<string, DrillEntry>>({})
  const [drillLoading, setDrillLoading] = useState(false)
  const [drillError, setDrillError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchApplications(filters, 500)
      .then((p) => { if (!cancelled) setPayload(p) })
      .catch((e) => { if (!cancelled) setError(String(e)) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [filters])

  // Status counts for the hero + future chip legend.
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const r of payload.rows) {
      counts[r.status] = (counts[r.status] ?? 0) + 1
    }
    return counts
  }, [payload.rows])

  const heroCells: HeroGridCell[] = useMemo(() => {
    const total = payload.rows.length
    const inFlight = payload.rows.filter(
      (r) => !["draft", "hired", "rejected"].includes(r.status),
    ).length
    const stale = payload.rows.filter(
      (r) => (r.days_in_stage ?? 0) > 7 && !["hired", "rejected"].includes(r.status),
    ).length
    const closed = payload.rows.filter((r) =>
      ["hired", "rejected"].includes(r.status),
    ).length
    return [
      {
        label: "Total applications",
        value: String(total),
        subtitle: filters.tenant || "all tenants",
        status_chip: { tone: "neutral" as const, label: "PIPELINE" },
      },
      {
        label: "In flight",
        value: String(inFlight),
        subtitle: "excl. draft / closed",
        status_chip: {
          tone: (inFlight > 0 ? "positive" : "neutral") as const,
          label: inFlight > 0 ? "ACTIVE" : "NONE",
        },
      },
      {
        label: "Stale >7 days",
        value: String(stale),
        subtitle: "no status change",
        status_chip: {
          tone: (stale > 0 ? "warning" : "positive") as const,
          label: stale > 0 ? "NEEDS ATTENTION" : "FRESH",
        },
      },
      {
        label: "Closed",
        value: String(closed),
        subtitle: "hired + rejected",
        status_chip: { tone: "neutral" as const, label: "ARCHIVE" },
      },
    ]
  }, [payload.rows, filters.tenant])

  const openStudentDrill = useCallback(async (studentId: string) => {
    setActiveStudentId(studentId)
    if (drillCache[studentId]) return
    setDrillLoading(true)
    setDrillError(null)
    try {
      const studentResp = await fetchStudent(studentId)
      const entry = buildStudentDrillEntry(studentResp.student, payload.rows, studentId)
      setDrillCache((prev) => ({ ...prev, [studentId]: entry }))
    } catch (err) {
      setDrillError(String(err))
    } finally {
      setDrillLoading(false)
    }
  }, [drillCache, payload.rows])

  const closeDrill = useCallback(() => {
    setActiveStudentId(null)
    setDrillError(null)
  }, [])

  const activeDrill: DrillEntry | null =
    activeStudentId ? drillCache[activeStudentId] ?? null : null

  // Group rows by status in display order.
  const groupedRows = useMemo(() => {
    const byStatus: Record<string, ApplicationListRow[]> = {}
    for (const r of payload.rows) {
      const key = STATUS_ORDER.includes(r.status) ? r.status : "other"
      ;(byStatus[key] = byStatus[key] ?? []).push(r)
    }
    return byStatus
  }, [payload.rows])

  return (
    <>
      <CockpitShell
        main={
          <>
            <RecruitingTopbar leaf="Applications" />
            <div className="cockpit-hero">
              <div className="cockpit-hero-eyebrow">
                Pipeline view · {payload.total} application
                {payload.total === 1 ? "" : "s"}
              </div>
              <h1 className="cockpit-hero-title cockpit-display">
                Where is everything sitting?
              </h1>
              <p className="cockpit-hero-subtitle">
                Applications grouped by status. Stale items (no movement in
                more than 7 days) need follow-up.
              </p>
              <HeroGrid cells={heroCells} />
            </div>

            <ApplicationsFilterBar
              filters={filters}
              onChange={setFilters}
              statusCounts={statusCounts}
            />

            {error ? (
              <div className="cockpit-api-error" style={{ margin: "1rem 0" }}>
                <strong>Applications error:</strong> {error}
              </div>
            ) : null}

            <div style={{ padding: "0.5rem 1.5rem 2rem", opacity: loading ? 0.6 : 1 }}>
              {payload.rows.length === 0 ? (
                <div style={{ padding: "2rem 0", color: "var(--cockpit-text-3)" }}>
                  No applications match the current filters.
                </div>
              ) : (
                STATUS_ORDER.filter((s) => groupedRows[s]?.length).map((status) => (
                  <StatusGroup
                    key={status}
                    status={status}
                    rows={groupedRows[status]!}
                    onRowClick={openStudentDrill}
                  />
                ))
              )}
              {groupedRows.other?.length ? (
                <StatusGroup
                  key="other"
                  status="other"
                  rows={groupedRows.other}
                  onRowClick={openStudentDrill}
                />
              ) : null}
            </div>
          </>
        }
        chat={<RecruitingChatPanel activeView="Applications" />}
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

function ApplicationsFilterBar({
  filters,
  onChange,
  statusCounts,
}: {
  filters: ApplicationsFilters
  onChange: (next: ApplicationsFilters) => void
  statusCounts: Record<string, number>
}) {
  const statuses = Object.keys(statusCounts).sort()
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
        Status
        <select
          value={filters.status}
          onChange={(e) => onChange({ ...filters, status: e.target.value })}
          style={filterInput}
        >
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {s} ({statusCounts[s]})
            </option>
          ))}
        </select>
      </label>
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
    </div>
  )
}

function StatusGroup({
  status,
  rows,
  onRowClick,
}: {
  status: string
  rows: ApplicationListRow[]
  onRowClick: (studentId: string) => void
}) {
  return (
    <section style={{ marginTop: "1.5rem" }}>
      <h3
        style={{
          fontSize: "0.875rem",
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: "var(--cockpit-text-2)",
          margin: "0 0 0.5rem",
        }}
      >
        {humanStatus(status)} · {rows.length}
      </h3>
      <table className="cockpit-table">
        <thead>
          <tr>
            <th>Student</th>
            <th>Job</th>
            <th>Company</th>
            <th>Tenant</th>
            <th>Initiated by</th>
            <th className="cockpit-num">Days in stage</th>
            <th className="cockpit-num">Updated</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.id}
              onClick={() => r.student_id && onRowClick(r.student_id)}
              style={{ cursor: r.student_id ? "pointer" : "default" }}
              className="cockpit-table-row-clickable"
            >
              <td>
                <strong>{r.student_name ?? "(unknown)"}</strong>
                {r.student_cohort ? (
                  <div style={{ fontSize: "0.75rem", color: "var(--cockpit-text-3)" }}>
                    {r.student_cohort}
                  </div>
                ) : null}
              </td>
              <td>{truncate(r.job_title ?? "—", 50)}</td>
              <td>{r.job_company ?? "—"}</td>
              <td>{r.tenant}</td>
              <td>{r.initiated_by}</td>
              <td
                className="cockpit-num"
                style={{
                  color:
                    (r.days_in_stage ?? 0) > 7
                      ? "var(--cockpit-warning, #b45309)"
                      : undefined,
                }}
              >
                {r.days_in_stage !== null ? `${r.days_in_stage}d` : "—"}
              </td>
              <td className="cockpit-num">
                {r.updated_at ? formatDate(r.updated_at) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function buildStudentDrillEntry(
  student: StudentDetail,
  rows: ApplicationListRow[],
  studentId: string,
): DrillEntry {
  const studentApps = rows.filter((r) => r.student_id === studentId)
  const appRows: Array<Record<string, string | number | boolean>> = studentApps.map((r) => ({
    job: r.job_title ?? "(unknown)",
    company: r.job_company ?? "—",
    status: r.status,
    days: r.days_in_stage !== null ? `${r.days_in_stage}d` : "—",
  }))

  return {
    eyebrow: "Student · application drill",
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
          { label: "Pipeline", value: student.pipeline_status ?? "—" },
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
        title: `Applications (${studentApps.length})`,
        columns: [
          { key: "job", label: "Job" },
          { key: "company", label: "Company" },
          { key: "status", label: "Status" },
          { key: "days", label: "Days in stage", align: "right" },
        ],
        rows: appRows,
        note:
          appRows.length === 0
            ? "This student has no applications in the current view."
            : undefined,
      },
    ],
  }
}

function humanStatus(status: string): string {
  const map: Record<string, string> = {
    draft: "Draft",
    submitted_for_review: "Submitted for review",
    approved: "Approved",
    packaged: "Packaged",
    sent: "Sent",
    delivered: "Delivered",
    employer_ack: "Employer acknowledged",
    interviewing: "Interviewing",
    offer: "Offer",
    hired: "Hired",
    rejected: "Rejected",
    other: "Other",
  }
  return map[status] ?? status
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + "…" : s
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    if (diffDays === 0) return "today"
    if (diffDays === 1) return "yesterday"
    if (diffDays < 7) return `${diffDays}d ago`
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
  } catch {
    return iso.slice(0, 10)
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

"use client"

// Workday view — Recruiting's primary surface. Renders a stats row,
// filter chips, job list, and (via the shared drill panel) per-job
// detail drills. Filters re-fetch /api/recruiting/jobs; drill content
// is assembled client-side from /jobs/{id} + /jobs/{id}/matches when
// a card is clicked.

import { useCallback, useEffect, useMemo, useState } from "react"
import type {
  WorkdayStats,
  JobsListPayload,
  JobRow,
  WorkdayFilters,
} from "../lib/types"
import { emptyFilters } from "../lib/types"
import { fetchJobs, fetchJob, fetchJobMatches } from "../lib/api"
import type { DrillEntry, HeroGridCell } from "../../_shared/types"
import { CockpitShell } from "../../_shared/cockpit-shell"
import { HeroGrid } from "../../_shared/hero/hero-grid"
import { DrillPanel } from "../../_shared/drill/drill-panel"
import { RecruitingTopbar } from "../components/recruiting-topbar"
import { RecruitingChatPanel } from "../components/recruiting-chat-panel"
import { SearchBox } from "../components/search-box"
import { FilterChips } from "../components/filter-chips"
import { JobCard } from "../components/job-card"

const PAGE_SIZE = 20

interface InitialState {
  stats: WorkdayStats
  jobsFirstPage: JobsListPayload
}

export function WorkdayClient({ initial }: { initial: InitialState }) {
  const [filters, setFilters] = useState<WorkdayFilters>(emptyFilters())
  const [jobsPayload, setJobsPayload] = useState<JobsListPayload>(initial.jobsFirstPage)
  const [jobsLoading, setJobsLoading] = useState(false)
  const [jobsError, setJobsError] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)

  const [activeJobId, setActiveJobId] = useState<number | null>(null)
  const [drillCache, setDrillCache] = useState<Record<number, DrillEntry>>({})
  const [drillLoading, setDrillLoading] = useState(false)
  const [drillError, setDrillError] = useState<string | null>(null)

  const stats = initial.stats
  const matchingStatus = stats.matching_status

  // Reload jobs whenever filters or offset change.
  useEffect(() => {
    let cancelled = false
    setJobsLoading(true)
    setJobsError(null)
    fetchJobs(filters, PAGE_SIZE, offset)
      .then((p) => { if (!cancelled) setJobsPayload(p) })
      .catch((e) => { if (!cancelled) setJobsError(String(e)) })
      .finally(() => { if (!cancelled) setJobsLoading(false) })
    return () => { cancelled = true }
  }, [filters, offset])

  const handleFiltersChange = useCallback((next: WorkdayFilters) => {
    setFilters(next)
    setOffset(0)  // new filter state resets pagination
  }, [])

  // Cells for the stats hero strip. Non-drillable (no drill_key).
  const heroCells: HeroGridCell[] = [
    {
      label: "Open jobs",
      value: stats.open_jobs,
      subtitle: `${stats.embeddings_status.jobs_enriched_count} with embeddings`,
    },
    {
      label: "With matches",
      value: matchingStatus === "pending_student_index" ? "—" : stats.with_matches,
      subtitle: matchingStatus === "pending_student_index"
        ? "pending · Phase 2D"
        : "jobs with ≥1 candidate",
      status_chip: matchingStatus === "pending_student_index"
        ? { label: "Pending", tone: "watch" }
        : undefined,
    },
    {
      label: "Apps in flight",
      value: stats.apps_in_flight,
      subtitle: "submitted → delivered",
    },
  ]

  // Drill-entry factory for a job — fetched + assembled lazily on
  // open and cached by job_id. No recruiting drill endpoint on the
  // backend; the UI composes from /jobs/{id} + /jobs/{id}/matches.
  const openJobDrill = useCallback(async (jobId: number) => {
    setActiveJobId(jobId)
    if (drillCache[jobId]) return
    setDrillLoading(true)
    setDrillError(null)
    try {
      const [job, matches] = await Promise.all([
        fetchJob(jobId),
        fetchJobMatches(jobId, 10),
      ])
      setDrillCache((s) => ({ ...s, [jobId]: buildJobDrill(job, matches) }))
    } catch (err) {
      setDrillError(String(err))
    } finally {
      setDrillLoading(false)
    }
  }, [drillCache])

  const closeDrill = useCallback(() => {
    setActiveJobId(null)
    setDrillError(null)
  }, [])

  const activeDrill: DrillEntry | null = activeJobId != null
    ? drillCache[activeJobId] ?? null
    : null

  const hasNextPage = jobsPayload.jobs.length === PAGE_SIZE

  return (
    <>
      <CockpitShell
        main={
          <>
            <RecruitingTopbar leaf="Workday view" />
            <div className="cockpit-hero">
              <div className="cockpit-hero-eyebrow">
                Recruiting · live data from /api/recruiting
              </div>
              <h1 className="cockpit-hero-title cockpit-display">
                Workday view
              </h1>
              <p className="cockpit-hero-subtitle">
                {stats.open_jobs} jobs ·{" "}
                {stats.embeddings_status.jobs_enriched_count} embedded ·{" "}
                {matchingStatus === "pending_student_index"
                  ? "matching pending"
                  : `${stats.with_matches} with matches`}
              </p>
              <SearchBox />
              <FilterChips filters={filters} onChange={handleFiltersChange} />
              <HeroGrid cells={heroCells} />
            </div>

            <section className="workday-job-list">
              <div className="workday-job-list-head">
                <h2 className="cockpit-display">Jobs</h2>
                <span className="cockpit-helper">
                  {jobsLoading
                    ? "loading…"
                    : jobsError
                      ? "error"
                      : `${jobsPayload.count} shown · offset ${jobsPayload.offset}`}
                </span>
              </div>

              {jobsError ? (
                <div className="workday-job-list-error">
                  <p>{jobsError}</p>
                  <button
                    type="button"
                    onClick={() => setOffset((o) => o)}
                    className="workday-retry-btn"
                  >
                    Retry
                  </button>
                </div>
              ) : jobsPayload.jobs.length === 0 && !jobsLoading ? (
                <div className="workday-job-list-empty">
                  <p>No jobs match the current filters.</p>
                </div>
              ) : (
                <div className="workday-job-list-items">
                  {jobsPayload.jobs.map((job) => (
                    <JobCard
                      key={job.job_id}
                      job={job}
                      matchingStatus={matchingStatus}
                      onOpen={openJobDrill}
                    />
                  ))}
                </div>
              )}

              <div className="workday-pagination">
                <button
                  type="button"
                  className="workday-page-btn"
                  disabled={offset === 0 || jobsLoading}
                  onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                >
                  ← Previous
                </button>
                <span className="workday-page-meta">
                  Page {Math.floor(offset / PAGE_SIZE) + 1}
                </span>
                <button
                  type="button"
                  className="workday-page-btn"
                  disabled={!hasNextPage || jobsLoading}
                  onClick={() => setOffset((o) => o + PAGE_SIZE)}
                >
                  Next →
                </button>
              </div>
            </section>
          </>
        }
        chat={<RecruitingChatPanel activeView="Workday view" />}
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


// ---------- drill assembly ----------

/** Build a DrillEntry for a single job by composing the job row and
 *  its matches payload. Follows the polymorphic schema used by the
 *  shared DrillSectionRenderer so everything renders identically to
 *  Finance drills. */
function buildJobDrill(
  job: JobRow,
  matches: import("../lib/types").JobMatchesPayload,
): DrillEntry {
  const sections: DrillEntry["sections"] = []

  // Meta — agent, company, location, posted. Always present.
  sections.push({
    type: "rows",
    title: "Job detail",
    rows: [
      { label: "Company", value: job.company ?? "—" },
      {
        label: "Location",
        value: job.location ??
          (job.city && job.state ? `${job.city}, ${job.state}` : "—"),
      },
      { label: "Employment type", value: job.employment_type ?? "—" },
      { label: "Seniority", value: job.seniority ?? "—" },
      { label: "Posted", value: job.posted_at?.slice(0, 10) ?? "—" },
      { label: "Region", value: job.region ?? "—" },
      { label: "Remote", value: job.is_remote ? "Yes" : "No" },
    ],
    note: job.apply_url ? `Apply URL: ${job.apply_url}` : undefined,
  })

  // Description prose. Truncated to ~500 chars so the drill doesn't
  // become a wall of text; the full description lives in the DB if
  // a later phase needs it.
  if (job.description && job.description.trim()) {
    const body = job.description.trim()
    sections.push({
      type: "prose",
      title: "Description",
      body: body.length > 500 ? `${body.slice(0, 500).trim()}…` : body,
    })
  }

  // Required skills — rows with label-as-index, value-as-skill. Easy
  // to scan, reuses the shared rows renderer without inventing a new
  // section type.
  if (job.skills_required && job.skills_required.length > 0) {
    sections.push({
      type: "rows",
      title: `Required skills (${job.skills_required.length})`,
      rows: job.skills_required.map((skill, i) => ({
        label: `#${i + 1}`,
        value: skill,
      })),
    })
  }

  // Matches — verdict (watch tone) when pending; table once
  // embeddings land. The watch-tone framing communicates
  // expected-state, not error.
  if (matches.matching_status === "pending_student_index") {
    sections.push({
      type: "verdict",
      tone: "watch",
      headline: "Matching pending — student profiles not yet indexed.",
      body:
        `Will populate when student embeddings are generated (Phase 2D). ` +
        `Today: ${matches.embeddings_status.jobs_enriched_count} jobs embedded, ` +
        `${matches.embeddings_status.student_count} students embedded. ` +
        `Job→student cosine matching is wired and will auto-populate ` +
        `as soon as the student side lights up.`,
    })
  } else if (matches.matches.length === 0) {
    sections.push({
      type: "verdict",
      tone: "neutral",
      headline: "No candidate matches yet.",
      body:
        "Matching is active but no students score above the similarity " +
        "threshold for this role. Try broadening the student pool or " +
        "lowering the threshold when that knob exists.",
    })
  } else {
    sections.push({
      type: "table",
      title: `Top ${matches.matches.length} candidate matches`,
      columns: [
        { key: "full_name", label: "Name" },
        { key: "cohort_label", label: "Cohort" },
        { key: "pipeline_status", label: "Pipeline" },
        { key: "cosine_display", label: "Similarity", align: "right", numeric: true },
        { key: "app_state", label: "Application" },
      ],
      rows: matches.matches.map((m) => ({
        full_name: m.full_name,
        cohort_label: m.cohort_label,
        pipeline_status: m.pipeline_status ?? "—",
        cosine_display: `${(m.cosine * 100).toFixed(1)}%`,
        app_state: m.existing_application ? "In flight" : "none yet",
      })),
    })
  }

  return {
    eyebrow: "Job",
    title: job.title,
    summary: [
      job.company,
      job.location ?? (job.city && job.state ? `${job.city}, ${job.state}` : null),
      job.employment_type,
    ].filter(Boolean).join(" · "),
    sections,
    status_chip: job.in_flight_app_count > 0
      ? { label: `${job.in_flight_app_count} in flight`, tone: "good" }
      : undefined,
  }
}

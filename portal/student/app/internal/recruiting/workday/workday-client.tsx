"use client"

// Workday view — Recruiting's primary surface. Renders a stats row,
// filter chips, job list, and (via the shared drill panel) per-job
// detail drills. Filters re-fetch /api/recruiting/jobs; drill content
// is assembled client-side from /jobs/{id} + /jobs/{id}/matches when
// a card is clicked.
//
// Phase 2E drill-stack addition: clicking a matched student swaps the
// drill content to a student detail view while keeping the parent job
// context intact. The student drill shows a "← Back to <Job Title>"
// button; Escape from there returns to the job drill (not all the way
// out). See openStudentFromJob / backToJob below.

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import type {
  WorkdayStats,
  JobsListPayload,
  JobRow,
  WorkdayFilters,
  StudentDetail,
  ApplicationRow,
} from "../lib/types"
import { emptyFilters } from "../lib/types"
import {
  fetchJobs,
  fetchJob,
  fetchJobMatches,
  fetchStudent,
  fetchStudentApplication,
  postApplication,
} from "../lib/api"
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

/** Context carried from a job drill into a student drill so the back
 *  button can render the job title and the student drill can show
 *  "Matched to X · 57.4% similarity". Cleared when the student drill
 *  is closed or opened standalone (future caseload-view case). */
interface StudentParentContext {
  job_id: number
  job_title: string
  cosine: number
}

export function WorkdayClient({ initial }: { initial: InitialState }) {
  const [filters, setFilters] = useState<WorkdayFilters>(emptyFilters())
  const [jobsPayload, setJobsPayload] = useState<JobsListPayload>(initial.jobsFirstPage)
  const [jobsLoading, setJobsLoading] = useState(false)
  const [jobsError, setJobsError] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)

  const [activeJobId, setActiveJobId] = useState<number | null>(null)
  const [jobDrillCache, setJobDrillCache] = useState<Record<number, DrillEntry>>({})
  const [jobTitleCache, setJobTitleCache] = useState<Record<number, string>>({})
  const [jobDrillLoading, setJobDrillLoading] = useState(false)
  const [jobDrillError, setJobDrillError] = useState<string | null>(null)

  // Student drill (Phase 2E). Rendered on top of the job drill when
  // activeStudentId is set; activeJobId stays populated so back
  // navigation has somewhere to go.
  const [activeStudentId, setActiveStudentId] = useState<string | null>(null)
  const [studentParent, setStudentParent] = useState<StudentParentContext | null>(null)
  const [studentCache, setStudentCache] = useState<Record<string, StudentDetail>>({})
  const [studentAppCache, setStudentAppCache] =
    useState<Record<string, ApplicationRow | null>>({})
  const [studentDrillLoading, setStudentDrillLoading] = useState(false)
  const [studentDrillError, setStudentDrillError] = useState<string | null>(null)

  // Scroll restoration on back nav: snapshot scrollTop when leaving the
  // job drill, restore it after the student drill closes so the
  // recruiter lands back at the matched-students table.
  const drillBodyRef = useRef<HTMLDivElement>(null)
  const savedJobScrollRef = useRef<number>(0)

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

  // When a student drill opens, start it scrolled to the top. The job
  // drill's scroll position is captured in savedJobScrollRef so
  // backToJob can restore it below.
  useEffect(() => {
    if (activeStudentId && drillBodyRef.current) {
      drillBodyRef.current.scrollTop = 0
    }
  }, [activeStudentId])

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
    setActiveStudentId(null)   // ensure any stale student drill is gone
    setStudentParent(null)
    setActiveJobId(jobId)
    if (jobDrillCache[jobId]) return
    setJobDrillLoading(true)
    setJobDrillError(null)
    try {
      const [job, matches] = await Promise.all([
        fetchJob(jobId),
        fetchJobMatches(jobId, 10),
      ])
      setJobDrillCache((s) => ({ ...s, [jobId]: buildJobDrill(job, matches) }))
      setJobTitleCache((s) => ({ ...s, [jobId]: job.title }))
    } catch (err) {
      setJobDrillError(String(err))
    } finally {
      setJobDrillLoading(false)
    }
  }, [jobDrillCache])

  // Phase 2E — open a student drill from a match row inside the job
  // drill. Saves the job drill's scroll position so back nav returns
  // to the exact same spot (matched-students table).
  const openStudentFromJob = useCallback(async (studentId: string) => {
    if (activeJobId == null) return   // shouldn't happen from this path
    const jobTitle = jobTitleCache[activeJobId] ?? "Job"

    // Find the cosine from the cached match row for the subtitle.
    const jobEntry = jobDrillCache[activeJobId]
    let cosine = 0
    for (const section of jobEntry?.sections ?? []) {
      if (section.type === "table" && section.row_click_key === "student_id") {
        const row = section.rows.find((r) => r.student_id === studentId)
        if (row && typeof row._cosine === "number") cosine = row._cosine
        break
      }
    }

    // Snapshot scroll so backToJob can restore it. Only fires if we
    // actually have a body element mounted (guard for HMR edge cases).
    if (drillBodyRef.current) {
      savedJobScrollRef.current = drillBodyRef.current.scrollTop
    }
    setStudentParent({ job_id: activeJobId, job_title: jobTitle, cosine })
    setActiveStudentId(studentId)

    const cacheKey = `${studentId}:${activeJobId}`
    if (studentCache[studentId] && cacheKey in studentAppCache) return

    setStudentDrillLoading(true)
    setStudentDrillError(null)
    try {
      const [detailResp, appResp] = await Promise.all([
        studentCache[studentId]
          ? Promise.resolve({ student: studentCache[studentId] })
          : fetchStudent(studentId),
        fetchStudentApplication(studentId, activeJobId),
      ])
      setStudentCache((s) => ({ ...s, [studentId]: detailResp.student }))
      setStudentAppCache((s) => ({ ...s, [cacheKey]: appResp.application }))
    } catch (err) {
      setStudentDrillError(String(err))
    } finally {
      setStudentDrillLoading(false)
    }
  }, [activeJobId, jobDrillCache, jobTitleCache, studentCache, studentAppCache])

  const backToJob = useCallback(() => {
    setActiveStudentId(null)
    setStudentParent(null)
    // Restore scroll after React paints. requestAnimationFrame lands
    // after the commit so the scroll container is back to job-drill
    // content dimensions.
    requestAnimationFrame(() => {
      if (drillBodyRef.current) {
        drillBodyRef.current.scrollTop = savedJobScrollRef.current
      }
    })
  }, [])

  const closeDrill = useCallback(() => {
    setActiveStudentId(null)
    setStudentParent(null)
    setActiveJobId(null)
    setJobDrillError(null)
    setStudentDrillError(null)
  }, [])

  // Record application initiation in the local cache so the footer
  // flips to success state without a refetch. Called from the
  // InitiateApplicationFooter component below.
  const recordApplication = useCallback(
    (studentId: string, jobId: number, app: ApplicationRow) => {
      setStudentAppCache((s) => ({ ...s, [`${studentId}:${jobId}`]: app }))
    },
    [],
  )

  // ---------- effective drill entry + wrapper props ----------

  const activeStudent = activeStudentId ? studentCache[activeStudentId] ?? null : null
  const activeStudentApp = activeStudentId && studentParent
    ? studentAppCache[`${activeStudentId}:${studentParent.job_id}`] ?? null
    : null

  const studentDrill = useMemo<DrillEntry | null>(() => {
    if (!activeStudentId || !activeStudent) return null
    return buildStudentDrill(activeStudent, studentParent)
  }, [activeStudentId, activeStudent, studentParent])

  const activeEntry: DrillEntry | null = activeStudentId
    ? studentDrill
    : activeJobId != null
      ? jobDrillCache[activeJobId] ?? null
      : null

  const drillLoading = activeStudentId
    ? studentDrillLoading && !studentDrill
    : jobDrillLoading && activeJobId != null && !jobDrillCache[activeJobId]

  const drillError = activeStudentId ? studentDrillError : jobDrillError

  const parentJobTitle = studentParent?.job_title ?? null
  const drillOnBack = activeStudentId && studentParent ? backToJob : undefined
  const drillBackLabel = activeStudentId && parentJobTitle
    ? `Back to ${parentJobTitle}` : undefined

  const drillFooter = activeStudentId && activeStudent && studentParent
    ? (
      <InitiateApplicationFooter
        student={activeStudent}
        jobId={studentParent.job_id}
        jobTitle={studentParent.job_title}
        existing={activeStudentApp}
        onSuccess={(app) => recordApplication(activeStudent.id, studentParent.job_id, app)}
      />
    ) : undefined

  // Match-row click routing — the shared table renderer surfaces the
  // clicked row's `student_id` via onTableRowClick. Only relevant when
  // the job drill is the active entry.
  const drillOnTableRowClick = !activeStudentId
    ? (key: string, value: string | number | boolean) => {
        if (key === "student_id" && typeof value === "string") {
          openStudentFromJob(value)
        }
      }
    : undefined

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
        entry={activeEntry}
        loading={drillLoading || false}
        error={drillError}
        onClose={closeDrill}
        onBack={drillOnBack}
        backLabel={drillBackLabel}
        footer={drillFooter}
        onTableRowClick={drillOnTableRowClick}
        bodyRef={drillBodyRef}
      />
    </>
  )
}


// ---------- drill assembly: job ----------

/** Build a DrillEntry for a single job by composing the job row and
 *  its matches payload. Follows the polymorphic schema used by the
 *  shared DrillSectionRenderer so everything renders identically to
 *  Finance drills. Phase 2E: the matches table declares
 *  row_click_key='student_id' + stashes per-row cosine so the workday
 *  client can open a student drill on click. */
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
        // Displayed columns:
        full_name: m.full_name,
        cohort_label: m.cohort_label,
        pipeline_status: m.pipeline_status ?? "—",
        cosine_display: `${(m.cosine * 100).toFixed(1)}%`,
        app_state: m.existing_application ? "In flight" : "none yet",
        // Hidden row fields the workday client reads on click:
        student_id: m.id,
        _cosine: m.cosine,
      })),
      row_click_key: "student_id",
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


// ---------- drill assembly: student ----------

const PIPELINE_LABEL: Record<string, string> = {
  unknown: "Unknown",
  applied: "Applied",
  enrolled: "Enrolled",
  deferred: "Deferred",
  inactive: "Inactive",
}

function formatDate(iso: string | null): string {
  if (!iso) return "—"
  return iso.slice(0, 10)
}

function buildStudentDrill(
  student: StudentDetail,
  parent: StudentParentContext | null,
): DrillEntry {
  const sections: DrillEntry["sections"] = []

  // Subtitle line (when opened from a job) — a verdict-shaped block at
  // the top that communicates the match context without looking like
  // an error or warning. Uses "good" tone so it blends with the rest
  // of the drill.
  if (parent) {
    sections.push({
      type: "verdict",
      tone: "good",
      headline: `Matched to ${parent.job_title} · ${(parent.cosine * 100).toFixed(1)}% similarity`,
      body:
        `Cosine similarity between this student's profile embedding ` +
        `and the job embedding. Threshold for "match" is 50%.`,
    })
  }

  // Contact — name/email/phone/location + clickable social links.
  const contactRows: Array<{ label: string; value: string | number; href?: string }> = [
    { label: "Email", value: student.email ?? "—" },
    { label: "Phone", value: student.phone ?? "—" },
    {
      label: "Location",
      value: student.city && student.state
        ? `${student.city}, ${student.state}`
        : (student.city ?? student.state ?? "—"),
    },
  ]
  if (student.linkedin_url) {
    contactRows.push({
      label: "LinkedIn", value: "View profile", href: student.linkedin_url,
    })
  }
  if (student.github_url) {
    contactRows.push({
      label: "GitHub", value: "View profile", href: student.github_url,
    })
  }
  if (student.portfolio_url) {
    contactRows.push({
      label: "Portfolio", value: "View", href: student.portfolio_url,
    })
  }
  sections.push({ type: "rows", title: "Contact", rows: contactRows })

  // Education — one row per entry (the API returns a 1-element array
  // today; will scale when student_education is hydrated).
  if (student.education.length > 0) {
    const e = student.education[0]
    sections.push({
      type: "rows",
      title: "Education",
      rows: [
        { label: "Institution", value: e.institution ?? "—" },
        { label: "Degree", value: e.degree ?? "—" },
        { label: "Field of study", value: e.field_of_study ?? "—" },
        { label: "Graduation year", value: e.graduation_year ?? "—" },
      ],
    })
  }

  // Career objective (if present) — prose.
  if (student.career_objective && student.career_objective.trim()) {
    sections.push({
      type: "prose",
      title: "Career objective",
      body: student.career_objective.trim(),
    })
  }

  // Pipeline status + cohort/track as a verdict so it reads as a
  // distinct call-out rather than another generic rows block.
  const pipelineKey = (student.pipeline_status ?? "unknown").toLowerCase()
  const pipelineLabel = PIPELINE_LABEL[pipelineKey] ?? pipelineKey
  const pipelineBits: string[] = []
  if (student.cohort_id) pipelineBits.push(`cohort ${student.cohort_id}`)
  else pipelineBits.push("no cohort assigned")
  if (student.track) pipelineBits.push(`track: ${student.track}`)
  else pipelineBits.push("no track assigned")
  if (student.pipeline_stage) pipelineBits.push(`stage: ${student.pipeline_stage}`)
  sections.push({
    type: "verdict",
    tone: pipelineKey === "applied" || pipelineKey === "enrolled" ? "good" : "neutral",
    headline: `Pipeline status · ${pipelineLabel}`,
    body: pipelineBits.join(" · "),
  })

  // Skills — rows with source as label, skill name as value. A flat
  // alphabetized list scans faster than grouping by source.
  if (student.skills.length > 0) {
    sections.push({
      type: "rows",
      title: `Skills (${student.skills.length})`,
      rows: student.skills.map((s) => ({
        label: s.source ?? "—",
        value: s.name,
      })),
    })
  }

  // Work experience — table. Collapsed to company / title / range
  // columns; the description would explode the row height.
  if (student.work_experience.length > 0) {
    sections.push({
      type: "table",
      title: `Work experience (${student.work_experience.length})`,
      columns: [
        { key: "company", label: "Company" },
        { key: "title", label: "Title" },
        { key: "range", label: "Dates" },
      ],
      rows: student.work_experience.map((w) => ({
        company: w.company ?? "—",
        title: w.title ?? "—",
        range: `${formatDate(w.start_date)} → ${
          w.is_current ? "present" : formatDate(w.end_date)
        }`,
      })),
    })
  }

  const location = student.city && student.state
    ? `${student.city}, ${student.state}`
    : (student.city ?? student.state ?? null)
  const summaryBits = [
    student.institution,
    student.field_of_study,
    location,
  ].filter(Boolean).join(" · ")

  return {
    eyebrow: "Student",
    title: student.full_name,
    summary: summaryBits,
    sections,
  }
}


// ---------- initiate-application footer ----------

type AppState =
  | { kind: "existing"; app: ApplicationRow }
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success"; app: ApplicationRow }
  | { kind: "error"; message: string }

function InitiateApplicationFooter({
  student,
  jobId,
  jobTitle,
  existing,
  onSuccess,
}: {
  student: StudentDetail
  jobId: number
  jobTitle: string
  existing: ApplicationRow | null
  onSuccess: (app: ApplicationRow) => void
}) {
  const [state, setState] = useState<AppState>(
    existing ? { kind: "existing", app: existing } : { kind: "idle" },
  )

  // Suppress the next "existing changed" reset after our own submit
  // succeeds. Without this, the flow is:
  //   submit → success → onSuccess updates parent cache → new `existing`
  //   prop arrives → effect collapses success back into "existing".
  // The ref breaks that cycle so the recruiter actually sees the
  // "Application initiated · status: draft" confirmation.
  const justSubmittedRef = useRef(false)

  // Reset when the student OR the job changes (prevents leaking
  // success state from a previous candidate into the current drill).
  useEffect(() => {
    if (justSubmittedRef.current) {
      justSubmittedRef.current = false
      return
    }
    setState(existing ? { kind: "existing", app: existing } : { kind: "idle" })
  }, [existing, student.id, jobId])

  const submit = useCallback(async () => {
    setState({ kind: "submitting" })
    try {
      const app = await postApplication({
        student_id: student.id,
        job_id: jobId,
        initiated_by: "recruiter",
      })
      justSubmittedRef.current = true
      setState({ kind: "success", app })
      onSuccess(app)
    } catch (err) {
      setState({ kind: "error", message: String(err) })
    }
  }, [student.id, jobId, onSuccess])

  if (state.kind === "existing") {
    return (
      <div className="workday-app-action" data-tone="neutral">
        <div className="workday-app-action-label">Already applied</div>
        <div className="workday-app-action-meta">
          status: {state.app.status} · initiated by {state.app.initiated_by} ·{" "}
          {state.app.created_at.slice(0, 10)}
        </div>
      </div>
    )
  }

  if (state.kind === "success") {
    return (
      <div className="workday-app-action" data-tone="good">
        <div className="workday-app-action-label">
          Application initiated · status: {state.app.status}
        </div>
        <div className="workday-app-action-meta">
          {student.full_name} → {jobTitle}
        </div>
      </div>
    )
  }

  return (
    <div className="workday-app-action" data-tone="idle">
      <button
        type="button"
        className="workday-app-submit"
        disabled={state.kind === "submitting"}
        onClick={submit}
      >
        {state.kind === "submitting" ? "Initiating…" : "Initiate application"}
      </button>
      {state.kind === "error" && (
        <div className="workday-app-action-error">{state.message}</div>
      )}
    </div>
  )
}

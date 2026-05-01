"use client"

import type { JobRow, MatchingStatus } from "../lib/types"

// One card in the job list. Click → open drill. Match badge reads
// match_count when matching is ready; when matching is pending, the
// badge renders the expected-state copy "— matches pending" in
// watch-tone instead of a zero. This is a design call, not an error
// state — see recruiting-chat-panel's matching-status callout for
// the longer framing.

function buildMeta(job: JobRow): string {
  const parts: string[] = []
  if (job.company) parts.push(job.company)
  if (job.location) parts.push(job.location)
  else if (job.city && job.state) parts.push(`${job.city}, ${job.state}`)
  if (job.employment_type) parts.push(job.employment_type)
  if (job.seniority) parts.push(job.seniority)
  if (job.is_remote) parts.push("remote")
  return parts.join(" · ")
}

export function JobCard({
  job,
  matchingStatus,
  onOpen,
}: {
  job: JobRow
  matchingStatus: MatchingStatus
  onOpen: (jobId: number) => void
}) {
  const pending = matchingStatus === "pending_student_index"
  const inFlight = job.in_flight_app_count
  return (
    <button
      type="button"
      className="workday-job-card"
      onClick={() => onOpen(job.job_id)}
    >
      <div className="workday-job-card-main">
        <h3 className="workday-job-card-title">{job.title}</h3>
        <div className="workday-job-card-meta">{buildMeta(job)}</div>
        {inFlight > 0 && (
          <div className="workday-job-card-inflight">
            <span className="cockpit-num">{inFlight}</span>
            {" "}
            in-flight application{inFlight === 1 ? "" : "s"}
          </div>
        )}
      </div>
      <div className="workday-job-card-badge" data-pending={pending ? "true" : "false"}>
        {pending ? (
          <span className="workday-job-match-pending">— matches pending</span>
        ) : (
          <>
            <span className="cockpit-num">{job.match_count}</span> match
            {job.match_count === 1 ? "" : "es"}
          </>
        )}
      </div>
    </button>
  )
}

// Recruiting · Workday view. Server component wrapper — parallel-
// fetches /stats/workday + /jobs (first page, no filters) at request
// time. Filter changes + drill open happen client-side in
// workday-client.
//
// Sibling /internal/recruiting/caseload/ and /applications/ still
// render the coming-soon placeholder (Phase 2D+).

import { AgentShell } from "../../_shared/agent-shell"
import { WorkdayClient } from "./workday-client"
import { fetchWorkdayStats, fetchJobs } from "../lib/api"
import { emptyFilters } from "../lib/types"

export const dynamic = "force-dynamic"

const INITIAL_PAGE_SIZE = 20

async function loadInitialState() {
  const [stats, jobsFirstPage] = await Promise.all([
    fetchWorkdayStats(),
    fetchJobs(emptyFilters(), INITIAL_PAGE_SIZE, 0),
  ])
  return { stats, jobsFirstPage }
}

export default async function RecruitingWorkdayPage() {
  let initial
  try {
    initial = await loadInitialState()
  } catch (err) {
    return (
      <AgentShell>
        <div className="cockpit-api-error">
          <h1 className="cockpit-display">Recruiting API unavailable</h1>
          <p>
            Couldn&apos;t reach the recruiting API on <code>localhost:8012</code>.
            Start it with <code>python -m agents.job_board.api</code> and
            reload.
          </p>
          <pre className="cockpit-api-error-trace">{String(err)}</pre>
        </div>
      </AgentShell>
    )
  }
  return (
    <AgentShell>
      <WorkdayClient initial={initial} />
    </AgentShell>
  )
}

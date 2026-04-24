// Recruiting · Applications view — pipeline of in-progress applications.
// Server component wrapper: fetches all applications at request time,
// then filters + status grouping happen client-side.
//
// Replaces the "Coming Soon" stub with MVP option A — table view with
// status filter. Later: kanban grouping by stage + drill into individual
// application with status-advance actions.

import { AgentShell } from "../../_shared/agent-shell"
import { ApplicationsClient } from "./applications-client"
import { fetchApplications } from "../lib/api"
import { emptyApplicationsFilters } from "../lib/types"

export const dynamic = "force-dynamic"

async function loadInitialState() {
  const initialFilters = emptyApplicationsFilters()
  const applications = await fetchApplications(initialFilters, 500)
  return { applications, initialFilters }
}

export default async function RecruitingApplicationsPage() {
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
      <ApplicationsClient initial={initial} />
    </AgentShell>
  )
}

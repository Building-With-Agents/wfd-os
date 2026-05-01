// Recruiting · Caseload view — case-manager home view (Dinah).
// Server component wrapper: fetches initial caseload (WSB tenant by
// default since that's where the match data lives today) at request
// time. Filters + row click handled client-side in caseload-client.
//
// Replaces the "Coming Soon" placeholder with MVP option A — single
// table of students with match summary + application count. No auth
// or per-recruiter assignment yet; filter by tenant/cohort instead.

import { AgentShell } from "../../_shared/agent-shell"
import { CaseloadClient } from "./caseload-client"
import { fetchCaseload } from "../lib/api"
import { emptyCaseloadFilters } from "../lib/types"

export const dynamic = "force-dynamic"

async function loadInitialState() {
  // Default to WSB on first paint — that's where cohort_matches data
  // exists today. Users can switch to CFA via the filter bar.
  const initialFilters = { ...emptyCaseloadFilters(), tenant: "WSB" }
  const caseload = await fetchCaseload(initialFilters, 200)
  return { caseload, initialFilters }
}

export default async function RecruitingCaseloadPage() {
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
      <CaseloadClient initial={initial} />
    </AgentShell>
  )
}

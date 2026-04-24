// Career Services — staff's entry into the Student Portal.
//
// This page is a student picker. Click a student → opens that
// student's actual portal (/student?id=<uuid>) in a new tab. The
// portal itself (portal/student/app/student/page.tsx) is the live
// student-facing dashboard: profile, matches, gap analysis, journey
// pipeline, showcase status, AI Career Navigator chat.
//
// Same data as the Recruiting Caseload view — we re-use the
// /caseload endpoint from job_board rather than building a second
// student-list endpoint.
//
// Replaces the prior ComingSoon placeholder.

import { AgentShell } from "../_shared/agent-shell"
import { CareerServicesClient } from "./career-services-client"
import { fetchCaseload } from "../recruiting/lib/api"
import { emptyCaseloadFilters } from "../recruiting/lib/types"

export const dynamic = "force-dynamic"

async function loadInitialState() {
  // Default to WSB on first paint — that's where cohort_matches data
  // lives today. Users can switch via the filter.
  const initialFilters = { ...emptyCaseloadFilters(), tenant: "WSB" }
  const caseload = await fetchCaseload(initialFilters, 200)
  return { caseload, initialFilters }
}

export default async function CareerServicesPage() {
  let initial
  try {
    initial = await loadInitialState()
  } catch (err) {
    return (
      <AgentShell>
        <div className="cockpit-api-error">
          <h1 className="cockpit-display">Student data unavailable</h1>
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
      <CareerServicesClient initial={initial} />
    </AgentShell>
  )
}

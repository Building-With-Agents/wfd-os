// CFA Finance cockpit — server component wrapper (Phase 2B).
//
// Parallel-fetches status + hero + decisions from cockpit_api (:8013
// via the /api/finance rewrite) at request time. force-dynamic
// disables caching during dev so Excel edits + a refresh POST surface
// immediately on reload.
//
// Tab content and drill content are fetched lazily by cockpit-client
// on tab switch and drill open — this server pass only loads what the
// first paint needs.

import { AgentShell } from "../_shared/agent-shell"
import { CockpitClient } from "./cockpit-client"
import { fetchStatus, fetchHero, fetchDecisions } from "./lib/api"

export const dynamic = "force-dynamic"

async function loadInitialState() {
  const [status, hero, decisions] = await Promise.all([
    fetchStatus(),
    fetchHero(),
    fetchDecisions(),
  ])
  return { status, hero, decisions }
}

export default async function FinanceCockpitPage() {
  let initial
  try {
    initial = await loadInitialState()
  } catch (err) {
    return (
      <AgentShell>
        <div className="cockpit-api-error">
          <h1 className="cockpit-display">Finance API unavailable</h1>
          <p>
            Couldn&apos;t reach the cockpit API on <code>localhost:8013</code>.
            Start it with <code>python -m agents.finance.cockpit_api</code> and
            reload.
          </p>
          <pre className="cockpit-api-error-trace">{String(err)}</pre>
        </div>
      </AgentShell>
    )
  }
  return (
    <AgentShell>
      <CockpitClient initial={initial} />
    </AgentShell>
  )
}

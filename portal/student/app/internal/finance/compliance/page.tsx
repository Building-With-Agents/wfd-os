// Standalone Compliance Requirements page.
//
// The same ComplianceTab component that renders inside the Finance
// cockpit's tab strip also renders here on its own route — without the
// hero grid, decisions list, other tabs, or activity feed. Reached
// from the sidebar's "Finance → Compliance Requirements" sub-item.
//
// Server-fetches the same /cockpit/tabs/compliance payload that the
// embedded tab uses, so the standalone view stays in lockstep with the
// cockpit version (single source of truth on the engine side).

import { AgentShell } from "../../_shared/agent-shell"
import { ComplianceTab } from "../components/compliance/compliance-tab"
import { fetchTab } from "../lib/api"
import type { ComplianceTabPayload } from "../lib/types"

export const dynamic = "force-dynamic"

export default async function CompliancePage() {
  let payload: ComplianceTabPayload | null = null
  let error: string | null = null
  try {
    const tab = await fetchTab("compliance")
    if (tab.tab !== "compliance") {
      throw new Error(`unexpected tab payload: ${tab.tab}`)
    }
    payload = tab as ComplianceTabPayload
  } catch (err) {
    error = String(err)
  }

  if (!payload) {
    return (
      <AgentShell>
        <div className="cockpit-api-error">
          <h1 className="cockpit-display">Compliance Requirements unavailable</h1>
          <p>
            Couldn&apos;t reach the cockpit API on <code>localhost:8013</code>.
            Start it with <code>python -m agents.finance.cockpit_api</code> and
            reload.
          </p>
          {error && <pre className="cockpit-api-error-trace">{error}</pre>}
        </div>
      </AgentShell>
    )
  }

  return (
    <AgentShell>
      <div className="cockpit-surface" style={{ padding: "16px 24px" }}>
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: "var(--cockpit-fs-meta)",
              color: "var(--cockpit-text-3)",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            Finance · Compliance
          </div>
          <h1 className="cockpit-display" style={{ margin: "4px 0 0" }}>
            Compliance Requirements
          </h1>
        </div>
        <ComplianceTab payload={payload} />
      </div>
    </AgentShell>
  )
}

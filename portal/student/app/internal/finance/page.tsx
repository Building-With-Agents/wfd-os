// CFA Finance cockpit — server component wrapper.
//
// Phase 2A scaffold: reads from a static JSON fixture dumped from
// agents/finance/design/cockpit_data.py::extract_all(). Phase 2B will
// swap the import for fetches against agents/finance/cockpit_api.py
// endpoints (status / hero / decisions / tabs / drills) — the
// CockpitFixture shape stays the same on both sides.
//
// The previous /internal/finance/ scaffold (QB status + transactions +
// compliance flags against the grant-compliance scaffold on :8000)
// moved to /internal/finance/operations/ and is preserved verbatim.

import { AgentShell } from "../_shared/agent-shell"
import { CockpitClient } from "./cockpit-client"
import fixture from "./lib/cockpit-fixture.json"
import type { CockpitFixture } from "./lib/types"

export default function FinanceCockpitPage() {
  const data = fixture as unknown as CockpitFixture
  return (
    <AgentShell>
      <CockpitClient data={data} />
    </AgentShell>
  )
}

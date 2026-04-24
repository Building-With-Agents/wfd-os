import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="WJI Dashboard"
        tagline="Grant reporting for the Workforce Solutions Borderplex engagement (K8341)."
        description={
          <>
            Upload placement reports from WSB (WSAC Excel format) and QB
            payment CSVs for reconciliation against the grant ledger. Shows
            the running tallies of placements, unique students, employers,
            and programs; payment totals and vendor splits; latest-activity
            timestamps. Drives the Finance cockpit&apos;s backbone burn and
            Q1 recovery numbers.
          </>
        }
        targetUrl="/wji"
        caveat="The WJI dashboard accepts uploads, so edits from this page can modify data. Treat it as a live production surface, not a preview — the files you upload land in wji_placements / wji_payments tables."
      />
    </AgentShell>
  )
}

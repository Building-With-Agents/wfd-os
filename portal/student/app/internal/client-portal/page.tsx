import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="Client Portal"
        tagline="Project tracking for signed Waifinder consulting clients."
        description={
          <>
            Where consulting clients (post-contract) track their engagement —
            status (scoping → proposal sent → contract signed → in progress →
            review → complete), milestones, deliverables, team, and project
            updates. Data comes from <code>project_inquiries</code>,
            <code>consulting_engagements</code>, and the <code>engagement_*</code>
            tables driven by the Scoping Agent.
          </>
        }
        targetUrl="/client"
        caveat="The Client Portal expects a magic-link token in the URL (?token=…). Opening it without a token shows an auth error — that's expected. In production, CFA staff sends each consulting client a tokenized link via email at contract signing."
      />
    </AgentShell>
  )
}

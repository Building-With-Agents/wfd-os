import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="Employer Portal"
        tagline="The hiring-side surface for companies."
        description={
          <>
            Employers browse and shortlist candidates from the Talent Showcase,
            post jobs, manage their hiring pipeline, and message candidates
            (routed through CFA). Also the entry point for companies exploring
            Waifinder consulting engagements.
          </>
        }
        targetUrl="/for-employers"
        caveat="No authentication on the employer portal today. In production, employers will authenticate via magic-link before they see candidate profiles."
      />
    </AgentShell>
  )
}

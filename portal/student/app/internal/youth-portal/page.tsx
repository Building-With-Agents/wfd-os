import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="Youth Portal"
        tagline="The intake surface for youth program applicants."
        description={
          <>
            Entry point for youth (Waifinder Youth program) — program
            information, career path exploration, application steps, financial
            assistance options, and the conversational Youth Agent scoped to
            first-contact, accessibility, and next-step guidance.
          </>
        }
        targetUrl="/youth"
      />
    </AgentShell>
  )
}

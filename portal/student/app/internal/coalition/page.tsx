import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="Coalition"
        tagline="The public Washington Tech Coalition landing page."
        description={
          <>
            Marketing / top-of-funnel surface — explains the coalition model,
            shows live stats (student + employer + college counts pulled from
            the database), and links out to Talent Showcase, Employer Portal,
            College login, AI Consulting, and the Careers intake form. This
            is where most organic traffic lands.
          </>
        }
        targetUrl="/coalition"
      />
    </AgentShell>
  )
}

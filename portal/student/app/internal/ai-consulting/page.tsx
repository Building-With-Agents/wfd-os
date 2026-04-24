import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="AI Consulting"
        tagline="The Waifinder consulting prospect surface."
        description={
          <>
            Public landing + project scoping form + Consulting Agent chat
            (&ldquo;GUIDE DON&rsquo;T PITCH&rdquo; principle). Where prospects discover the
            Waifinder consulting offering, describe their project area,
            timeline, and budget, and trigger an <code>INTAKE_COMPLETE</code>
            signal that flows into the scoping workflow. Subroutes:
            <code> /cfa/ai-consulting/blog</code> (content marketing) and
            <code> /cfa/ai-consulting/chat</code> (conversational intake).
          </>
        }
        targetUrl="/cfa/ai-consulting"
      />
    </AgentShell>
  )
}

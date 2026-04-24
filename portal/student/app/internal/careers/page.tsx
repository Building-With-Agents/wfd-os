import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="Careers"
        tagline="Public intake + job exploration for students."
        description={
          <>
            The front door for students discovering CFA — resume upload, skill
            and role selection, existing-profile lookup, and the conversational
            Student Agent (&ldquo;VALUE BEFORE ASK&rdquo;: show jobs first, ask
            follow-ups one question at a time). New submissions create a
            <code> students</code> row and kick off the Resume Parser + Profile
            Agent chain.
          </>
        }
        targetUrl="/careers"
        caveat="Public surface — no authentication. Anyone can submit an intake form. In production, the form gates the student into the tokenized Student Portal via a welcome email."
      />
    </AgentShell>
  )
}

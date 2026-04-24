import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="Talent Showcase"
        tagline="The candidate-discovery surface employers use."
        description={
          <>
            Searchable list of job-ready CFA and WSB students. Employers can
            filter by skills, availability, location, and match score, then
            open individual profiles to see resume, project highlights, and
            career objective. This is where hiring signals originate — views,
            shortlists, and contact requests all flow back into the student
            pipeline.
          </>
        }
        targetUrl="/showcase"
      />
    </AgentShell>
  )
}

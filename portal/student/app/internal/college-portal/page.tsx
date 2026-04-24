import { AgentShell } from "../_shared/agent-shell"
import { PortalLauncher } from "../_shared/portal-launcher"

export default function Page() {
  return (
    <AgentShell>
      <PortalLauncher
        title="College Partner Portal"
        tagline="Program management + graduate outcome tracking for college partners."
        description={
          <>
            Colleges manage their program profile + skills mapping, see their
            graduates moving through the WFD OS pipeline, track placement
            outcomes, and post upcoming cohort availability. Also surfaces
            employer demand signals in their program skill areas and lets them
            request introductions to specific employers.
          </>
        }
        targetUrl="/college"
        caveat="The College Portal expects a magic-link token in the URL (?token=…). Opening it without a token shows an auth error — that's expected. In production, CFA staff sends each college partner a tokenized link via email."
      />
    </AgentShell>
  )
}

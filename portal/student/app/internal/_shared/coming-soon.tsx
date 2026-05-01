// Placeholder rendered when a sidebar route lands on an agent that
// isn't built yet. Each route owns its own page.tsx that renders
// <ComingSoon agent="recruiting-workday" /> (or similar), and that
// page.tsx wraps itself in <AgentShell> so the sidebar stays
// consistent. When the real agent lands, delete the route's
// page.tsx and replace with the actual cockpit.

interface AgentBlurb {
  title: string
  tagline: string
  body: string
}

const BLURBS: Record<string, AgentBlurb> = {
  "recruiting-workday": {
    title: "Recruiting · Workday view",
    tagline: "The hiring-manager lens on active reqs + pipeline health.",
    body:
      "Candidates stacked against open reqs, source attribution for each hire, " +
      "time-to-fill breakdowns, and the diversity + compliance signals that go " +
      "into every monthly WFB / EEOC attestation. Build target: early summer — " +
      "after the Finance cockpit lands in production and the agent-surface " +
      "shell is extracted from _shared/.",
  },
  "recruiting-caseload": {
    title: "Recruiting · Caseload view",
    tagline: "The recruiter lens on their own open reqs and candidates.",
    body:
      "Everything a recruiter needs mid-day — today's screens, tomorrow's " +
      "onsites, stalled candidates, SLA aging on offers out. Same underlying " +
      "data as Workday view, different frame.",
  },
  "recruiting-applications": {
    title: "Recruiting · Applications",
    tagline: "Top-of-funnel for every open req.",
    body:
      "New applications, where they came from, first-pass quality signals, " +
      "and triage queue for the next screen. Feeds into both Workday view " +
      "and Caseload view as candidates progress.",
  },
  "career-services": {
    title: "Career Services",
    tagline: "The student-facing placement agent.",
    body:
      "Gap analysis, pathway recommendations, interview prep, and the " +
      "Talent Showcase activation flow. The Finance cockpit's true-CPP " +
      "numbers come from here indirectly — this agent owns the data " +
      "behind every placement we report.",
  },
  "market-intel": {
    title: "Market Intel",
    tagline: "Regional labor-market signals for program and placement decisions.",
    body:
      "Employer demand by role family, salary bands, and cohort skill " +
      "alignment. Current implementation is the Workforce Solutions " +
      "Borderplex JIE pipeline; this surface lifts that out of workflow " +
      "code and into a conversational agent view.",
  },
}

export function ComingSoon({ agent }: { agent: string }) {
  const blurb = BLURBS[agent] ?? {
    title: "Coming soon",
    tagline: "This agent is being built.",
    body: "Check back once the build lands. Known agents: " +
      Object.keys(BLURBS).join(", "),
  }
  return (
    <div className="coming-soon-page">
      <div className="coming-soon-inner">
        <div className="coming-soon-eyebrow">Agent preview</div>
        <h1 className="coming-soon-title cockpit-display">{blurb.title}</h1>
        <p className="coming-soon-tagline">{blurb.tagline}</p>
        <p className="coming-soon-body">{blurb.body}</p>
        <div className="coming-soon-footer">
          <span className="coming-soon-chip">In build · check back soon</span>
        </div>
      </div>
    </div>
  )
}

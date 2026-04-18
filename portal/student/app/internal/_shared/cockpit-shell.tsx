// Shared cockpit layout for any agent surface (Finance, Recruiting,
// future agents). Renders the two-column main/chat grid that sits
// inside AgentShell's content slot.
//
// Usage:
//   <CockpitShell
//     main={<main agent content>}
//     chat={<Agent-specific ChatPanel />}
//   />
//
// The chat slot is any ReactNode — each agent supplies its own
// ChatPanel component (Finance's static placeholder, Recruiting's
// Recruiting-specific placeholder) until chat wiring lands.

import type { ReactNode } from "react"

export function CockpitShell({
  main,
  chat,
}: {
  main: ReactNode
  chat: ReactNode
}) {
  return (
    <div className="cockpit-app">
      <div className="cockpit-main">{main}</div>
      {chat}
    </div>
  )
}

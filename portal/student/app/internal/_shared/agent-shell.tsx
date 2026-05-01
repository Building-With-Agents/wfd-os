// Shared wrapper for every agent surface under /internal/*.
// Renders the left navigation sidebar + the agent's own page content
// to its right. Applies .cockpit-surface so the shell itself plus any
// children get cockpit design tokens (color bands, type scale, fonts).
//
// Finance is the first consumer (Phase 2A). Recruiting / Career
// Services / Market Intel consume via the coming-soon placeholder
// (also wrapped in this shell) until they're built. Phase 2C may
// extract the rest of the cockpit shell (hero grid, drill panel)
// into _shared/; for now, only the outermost navigation chrome lives
// here.

import { Sidebar } from "./sidebar"

export function AgentShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="cockpit-surface agent-shell">
      <Sidebar />
      <div className="agent-shell-content">{children}</div>
    </div>
  )
}

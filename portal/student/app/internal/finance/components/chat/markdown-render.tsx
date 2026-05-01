"use client"

// Minimal inline renderer for agent messages. Detects markdown links
// `[label](href)` and routes drill-scoped hrefs (matching
// `/internal/finance#drill=<key>`) through onDrillClick instead of
// navigating. Everything else renders as plain text with newlines
// preserved by the parent's whitespace-pre-wrap.
//
// We deliberately do NOT depend on react-markdown for v1 — the agent's
// expected output is plain English with the occasional drill link, not
// rich markdown. If we later need lists, headers, tables, swap this
// module for react-markdown without touching callers.

import type { ReactNode } from "react"

const LINK_RE = /\[([^\]]+)\]\(([^)\s]+)\)/g
const DRILL_HREF_RE = /^\/internal\/finance#drill=(.+)$/

export function renderAgentText(
  text: string,
  onDrillClick: (drillKey: string) => void,
): ReactNode[] {
  const parts: ReactNode[] = []
  let lastIdx = 0
  let key = 0
  // Reset .lastIndex on every call — RegExp is shared (`/g` is stateful).
  LINK_RE.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = LINK_RE.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.slice(lastIdx, match.index))
    }
    const [, label, href] = match
    const drillMatch = href.match(DRILL_HREF_RE)
    if (drillMatch) {
      const drillKey = decodeURIComponent(drillMatch[1])
      parts.push(
        <button
          key={`drill-${key++}`}
          type="button"
          className="cockpit-chat-drill-link"
          onClick={() => onDrillClick(drillKey)}
        >
          {label}
        </button>,
      )
    } else {
      parts.push(
        <a
          key={`ext-${key++}`}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="cockpit-chat-ext-link"
        >
          {label}
        </a>,
      )
    }
    lastIdx = match.index + match[0].length
  }
  if (lastIdx < text.length) {
    parts.push(text.slice(lastIdx))
  }
  // Wrap each top-level text node in a fragment-friendly key so React
  // is happy with the mixed array of strings + elements.
  return parts.map((p, i) =>
    typeof p === "string" ? <span key={`t-${i}`}>{p}</span> : p,
  )
}

"use client"

import type { DecisionsPayload } from "../../lib/types"

export function DecisionsList({
  decisions,
  onOpen,
}: {
  decisions: DecisionsPayload
  onOpen: (key: string) => void
}) {
  return (
    <div className="cockpit-decisions">
      <div className="cockpit-section-head">
        <h2 className="cockpit-display">This week&apos;s decisions</h2>
        <span className="cockpit-helper">
          {decisions.total} items from v3 reconciliation Action Items · prioritized
        </span>
      </div>
      <div className="cockpit-decision-list">
        {decisions.items.map((item) => (
          <button
            key={item.id}
            type="button"
            className="cockpit-decision"
            onClick={() => onOpen(item.drill_key)}
          >
            <div className="cockpit-decision-marker" data-tone={item.priority_tone} />
            <div>
              <div className="cockpit-decision-title">{item.title}</div>
              <div className="cockpit-decision-meta">Owner: {item.owner}</div>
            </div>
            <div className="cockpit-decision-right">
              <div className="cockpit-decision-priority">{item.priority}</div>
              <div>{item.status}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

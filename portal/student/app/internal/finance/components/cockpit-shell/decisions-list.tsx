"use client"

import type { ActionItem_, Tone } from "../../lib/types"

function priorityTone(priority: string): Tone {
  if (priority === "HIGH") return "critical"
  if (priority === "MEDIUM") return "watch"
  return "neutral"
}

export function DecisionsList({
  items,
  onOpen,
}: {
  items: ActionItem_[]
  onOpen: (key: string) => void
}) {
  return (
    <div className="cockpit-decisions">
      <div className="cockpit-section-head">
        <h2 className="cockpit-display">This week&apos;s decisions</h2>
        <span className="cockpit-helper">
          {items.length} items from v3 reconciliation Action Items · prioritized
        </span>
      </div>
      <div className="cockpit-decision-list">
        {items.map((item, i) => (
          <button
            key={i}
            type="button"
            className="cockpit-decision"
            onClick={() => onOpen(`decision:${i}`)}
          >
            <div
              className="cockpit-decision-marker"
              data-tone={priorityTone(item.priority)}
            />
            <div>
              <div className="cockpit-decision-title">
                {item.area} — {item.action}
              </div>
              <div className="cockpit-decision-meta">Owner: {item.owner}</div>
            </div>
            <div className="cockpit-decision-right">
              <div className="cockpit-decision-priority">{item.priority}</div>
              <div>open</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

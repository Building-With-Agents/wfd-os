"use client"

import type { HeroCellPayload } from "../../lib/types"

export function HeroCell({
  cell,
  onOpen,
}: {
  cell: HeroCellPayload
  onOpen: (key: string) => void
}) {
  return (
    <button
      type="button"
      className="cockpit-hero-cell"
      onClick={() => onOpen(cell.drill_key)}
      data-drill={cell.drill_key}
      style={{ border: "none", textAlign: "left", font: "inherit", color: "inherit" }}
    >
      <div className="cockpit-hero-label">
        {cell.label}
        {cell.live_minutes_ago !== undefined && (
          <span
            style={{
              color: "var(--cockpit-good)",
              fontSize: "var(--cockpit-fs-micro)",
              letterSpacing: "0.04em",
              textTransform: "none",
              fontWeight: 500,
              marginLeft: 8,
            }}
          >
            ● live · {cell.live_minutes_ago} min ago
          </span>
        )}
      </div>
      <div className="cockpit-hero-value cockpit-num">
        {cell.value}
        {cell.value_suffix && (
          <span
            style={{
              color: "var(--cockpit-text-3)",
              fontSize: "var(--cockpit-fs-section)",
              marginLeft: 4,
            }}
          >
            {cell.value_suffix}
          </span>
        )}
      </div>
      <div className="cockpit-hero-sub">{cell.subtitle}</div>
      {cell.status_chip && (
        <span className="cockpit-hero-badge" data-tone={cell.status_chip.tone}>
          {cell.status_chip.label}
        </span>
      )}
    </button>
  )
}

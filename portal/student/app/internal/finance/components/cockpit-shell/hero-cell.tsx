"use client"

import type { Tone } from "../../lib/types"

export interface HeroCellProps {
  drillKey: string
  label: React.ReactNode
  value: React.ReactNode
  sub: React.ReactNode
  badge?: { text: string; tone: Tone }
  onOpen: (key: string) => void
}

export function HeroCell({ drillKey, label, value, sub, badge, onOpen }: HeroCellProps) {
  return (
    <button
      type="button"
      className="cockpit-hero-cell"
      onClick={() => onOpen(drillKey)}
      data-drill={drillKey}
      style={{ border: "none", textAlign: "left", font: "inherit", color: "inherit" }}
    >
      <div className="cockpit-hero-label">{label}</div>
      <div className="cockpit-hero-value cockpit-num">{value}</div>
      <div className="cockpit-hero-sub">{sub}</div>
      {badge && (
        <span className="cockpit-hero-badge" data-tone={badge.tone}>
          {badge.text}
        </span>
      )}
    </button>
  )
}

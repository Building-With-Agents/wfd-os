"use client"

import type { HeroPayload, CockpitStatusPayload } from "../../lib/types"
import { HeroCell } from "./hero-cell"

export function HeroGrid({
  status,
  hero,
  onOpen,
}: {
  status: CockpitStatusPayload
  hero: HeroPayload
  onOpen: (key: string) => void
}) {
  const cells = [hero.backbone, hero.placements, hero.cash, hero.flags]
  return (
    <div className="cockpit-hero">
      <div className="cockpit-hero-eyebrow">
        Status as of {status.as_of} — {status.months_remaining} months remaining
      </div>
      <h1 className="cockpit-hero-title cockpit-display">Are we okay?</h1>
      <p className="cockpit-hero-subtitle">
        A daily glance at runway, placements, and what needs your attention this week.
      </p>
      <div className="cockpit-hero-grid">
        {cells.map((cell) => (
          <HeroCell key={cell.drill_key} cell={cell} onOpen={onOpen} />
        ))}
      </div>
    </div>
  )
}

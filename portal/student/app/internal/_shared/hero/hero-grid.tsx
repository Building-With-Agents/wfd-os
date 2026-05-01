"use client"

// N-cell grid of stat/hero cells. Agent-agnostic — each agent page
// composes its own outer <div class="cockpit-hero"> wrapper (with
// title + subtitle above) and passes cells down. Column count tracks
// `cells.length` via a CSS custom property so 3-cell and 4-cell rows
// both render cleanly without layout thrash.
//
// Cells with drill_key become <button>s that fire onOpen(drill_key).
// Cells without drill_key render as <div>s (used for stat-only rows
// like Recruiting's open_jobs / with_matches / apps_in_flight).

import type { HeroGridCell } from "../types"
import { HeroCell } from "./hero-cell"

export function HeroGrid({
  cells,
  onOpen,
}: {
  cells: HeroGridCell[]
  onOpen?: (drillKey: string) => void
}) {
  return (
    <div
      className="cockpit-hero-grid"
      style={{ ["--hero-columns" as unknown as string]: String(cells.length) }}
    >
      {cells.map((cell, i) => (
        <HeroCell
          key={cell.drill_key ?? String(i)}
          cell={cell}
          onOpen={onOpen}
        />
      ))}
    </div>
  )
}

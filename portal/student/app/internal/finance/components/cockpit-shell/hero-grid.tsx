"use client"

import type { CockpitFixture } from "../../lib/types"
import { fmtUSD, fmtNum } from "../../lib/format"
import { HeroCell } from "./hero-cell"

export function HeroGrid({
  data,
  onOpen,
}: {
  data: CockpitFixture
  onOpen: (key: string) => void
}) {
  const { summary, placements, trailing_q1_total, high_priority_count } = data
  return (
    <div className="cockpit-hero">
      <div className="cockpit-hero-eyebrow">
        Status as of {summary.today} — {summary.months_remaining} months remaining
      </div>
      <h1 className="cockpit-hero-title cockpit-display">Are we okay?</h1>
      <p className="cockpit-hero-subtitle">
        A daily glance at runway, placements, and what needs your attention this week.
      </p>
      <div className="cockpit-hero-grid">
        <HeroCell
          drillKey="backbone"
          label="Backbone Runway"
          value={fmtUSD(summary.backbone_runway_combined)}
          sub={
            <>
              {fmtUSD(summary.backbone_remaining)} staff &amp; overhead ·{" "}
              {fmtUSD(summary.cfa_contractor_remaining)} recovery contractors
            </>
          }
          badge={{ text: "Tight · On Track", tone: "watch" }}
          onOpen={onOpen}
        />
        <HeroCell
          drillKey="placements"
          label={
            <>
              Placements{" "}
              <span
                style={{
                  color: "var(--cockpit-good)",
                  fontSize: "var(--cockpit-fs-micro)",
                  letterSpacing: "0.04em",
                  textTransform: "none",
                  fontWeight: 500,
                }}
              >
                ● live · {placements.live_synced_minutes_ago} min ago
              </span>
            </>
          }
          value={
            <>
              {placements.confirmed_total}{" "}
              <span
                style={{
                  color: "var(--cockpit-text-3)",
                  fontSize: "var(--cockpit-fs-section)",
                }}
              >
                / {fmtNum(placements.grant_goal)}
              </span>
            </>
          }
          sub={
            <>
              PIP threshold ({placements.pip_threshold}) cleared ·{" "}
              {placements.grant_goal - placements.confirmed_total} to grant goal
            </>
          }
          badge={{ text: "Above PIP", tone: "good" }}
          onOpen={onOpen}
        />
        <HeroCell
          drillKey="reimbursement"
          label="Cash Position"
          value={fmtUSD(trailing_q1_total)}
          sub="Q1 provider reimbursement pending from ESD"
          badge={{ text: "Awaiting ESD", tone: "watch" }}
          onOpen={onOpen}
        />
        <HeroCell
          drillKey="flags"
          label="Critical Flags"
          value={String(high_priority_count)}
          sub="From v3 reconciliation Action Items · HIGH priority"
          badge={{ text: "Action Needed", tone: "critical" }}
          onOpen={onOpen}
        />
      </div>
    </div>
  )
}

import type { ChartSection } from "../../lib/types"

// Inline SVG bar chart. Compact (drill panel is ~520px wide). Tones on
// individual bars come from data; reference lines come from
// section.reference_lines. Recharts comes in Phase 2C when we rebuild
// the cockpit body charts — for the drill panel, hand-rolled SVG keeps
// the bundle small and the styling consistent with the cockpit tokens.

export function DrillSectionChart({ section }: { section: ChartSection }) {
  const data = section.data ?? []
  const refLines = section.reference_lines ?? []
  const xKey = section.x_axis.key
  const yKey = section.y_axis.key
  const values = data.map((d) => Number(d[yKey]) || 0)
  const refVals = refLines.map((r) => Number(r.value) || 0)
  const maxY = Math.max(1, ...values, ...refVals)

  const W = 480
  const H = 200
  const PL = 36
  const PR = 16
  const PT = 16
  const PB = 32
  const cW = W - PL - PR
  const cH = H - PT - PB
  const gap = 4
  const barW = data.length ? (cW - gap * (data.length - 1)) / data.length : 0

  return (
    <div className="cockpit-drill-section">
      <h3 className="cockpit-drill-section-title">{section.title}</h3>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: "100%", height: "auto", display: "block" }}
      >
        {/* x-axis */}
        <line
          x1={PL}
          y1={PT + cH}
          x2={W - PR}
          y2={PT + cH}
          stroke="var(--cockpit-border-strong)"
          strokeWidth={1}
        />
        {/* bars */}
        {data.map((d, i) => {
          const v = Number(d[yKey]) || 0
          const h = (Math.max(0, v) / maxY) * cH
          const x = PL + i * (barW + gap)
          const y = PT + cH - h
          const tone =
            (d.tone as string | undefined) &&
            ["good", "watch", "critical", "neutral"].includes(d.tone!)
              ? d.tone
              : "neutral"
          return (
            <g key={i}>
              <rect
                x={x}
                y={y}
                width={barW}
                height={h}
                fill={
                  tone === "neutral"
                    ? "var(--cockpit-brand)"
                    : `var(--cockpit-${tone})`
                }
              />
              <text
                x={x + barW / 2}
                y={y - 3}
                textAnchor="middle"
                fontSize={10}
                fontFamily="var(--font-cockpit-mono), 'DM Mono', monospace"
                fontWeight={600}
                fill="var(--cockpit-text-2)"
              >
                {v}
              </text>
              <text
                x={x + barW / 2}
                y={PT + cH + 14}
                textAnchor="middle"
                fontSize={9}
                fontFamily="var(--font-cockpit-mono), 'DM Mono', monospace"
                fill="var(--cockpit-text-3)"
              >
                {String(d[xKey] ?? "")}
              </text>
            </g>
          )
        })}
        {/* reference lines */}
        {refLines.map((r, i) => {
          const v = Number(r.value)
          const y = PT + cH - (v / maxY) * cH
          const tone =
            r.tone && ["good", "watch", "critical"].includes(r.tone)
              ? r.tone
              : "watch"
          return (
            <g key={`ref-${i}`}>
              <line
                x1={PL}
                y1={y}
                x2={W - PR}
                y2={y}
                stroke={`var(--cockpit-${tone})`}
                strokeWidth={1}
                strokeDasharray="3 3"
              />
              <text
                x={W - PR}
                y={y - 4}
                textAnchor="end"
                fontSize={9}
                fontFamily="var(--font-cockpit-mono), 'DM Mono', monospace"
                fill={`var(--cockpit-${tone})`}
              >
                {r.label ? `${r.label}: ${v}` : String(v)}
              </text>
            </g>
          )
        })}
      </svg>
      {section.note && (
        <div className="cockpit-drill-callout">{section.note}</div>
      )}
    </div>
  )
}

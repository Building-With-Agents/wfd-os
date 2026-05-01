import type { StatusChip as ChipData } from "./types"

export function StatusChip({ chip }: { chip: ChipData }) {
  return (
    <span
      className="cockpit-status-chip"
      data-tone={chip.tone}
      style={{
        display: "inline-block",
        fontSize: "var(--cockpit-fs-meta)",
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        padding: "3px 10px",
        borderRadius: 2,
        background: `var(--cockpit-${chip.tone}-soft, var(--cockpit-surface-alt))`,
        color: `var(--cockpit-${chip.tone}, var(--cockpit-text-3))`,
      }}
    >
      {chip.label}
    </span>
  )
}

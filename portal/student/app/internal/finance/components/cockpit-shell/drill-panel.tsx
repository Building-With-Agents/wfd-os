"use client"

import { useEffect } from "react"
import type { DrillEntry } from "../../lib/types"
import { DrillSectionRenderer } from "../drill-sections/drill-section-renderer"
import { StatusChip } from "./status-chip"

export function DrillPanel({
  entry,
  onClose,
}: {
  entry: DrillEntry | null
  onClose: () => void
}) {
  const open = entry !== null

  // Close on Escape
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [open, onClose])

  return (
    <>
      <div
        className="cockpit-drill-overlay"
        data-open={open ? "true" : "false"}
        onClick={onClose}
      />
      <aside
        className="cockpit-drill-panel"
        data-open={open ? "true" : "false"}
        aria-hidden={!open}
      >
        {entry && (
          <>
            <div className="cockpit-drill-head">
              <button
                type="button"
                className="cockpit-drill-close"
                onClick={onClose}
                aria-label="Close drill"
              >
                ×
              </button>
              <div className="cockpit-drill-eyebrow">{entry.eyebrow}</div>
              <h2 className="cockpit-drill-title">{entry.title}</h2>
              <div className="cockpit-drill-summary">{entry.summary}</div>
            </div>
            <div className="cockpit-drill-body">
              {entry.status_chip && (
                <div className="cockpit-drill-status-chip-wrap">
                  <StatusChip chip={entry.status_chip} />
                </div>
              )}
              {entry.sections.map((s, i) => (
                <DrillSectionRenderer key={i} section={s} />
              ))}
              {entry.note && (
                <div className="cockpit-drill-callout">{entry.note}</div>
              )}
            </div>
          </>
        )}
      </aside>
    </>
  )
}

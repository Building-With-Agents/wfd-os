"use client"

import { useEffect } from "react"
import type { DrillEntry } from "../types"
import { DrillSectionRenderer } from "./sections/drill-section-renderer"
import { StatusChip } from "../status-chip"

export function DrillPanel({
  entry,
  loading = false,
  error,
  onClose,
}: {
  entry: DrillEntry | null
  loading?: boolean
  error?: string | null
  onClose: () => void
}) {
  const open = entry !== null || loading || !!error

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
        <div className="cockpit-drill-head">
          <button
            type="button"
            className="cockpit-drill-close"
            onClick={onClose}
            aria-label="Close drill"
          >
            ×
          </button>
          {entry ? (
            <>
              <div className="cockpit-drill-eyebrow">{entry.eyebrow}</div>
              <h2 className="cockpit-drill-title">{entry.title}</h2>
              <div className="cockpit-drill-summary">{entry.summary}</div>
            </>
          ) : loading ? (
            <>
              <div className="cockpit-drill-eyebrow">Loading</div>
              <h2 className="cockpit-drill-title">&nbsp;</h2>
              <div className="cockpit-drill-summary">Fetching drill content…</div>
            </>
          ) : error ? (
            <>
              <div className="cockpit-drill-eyebrow" style={{ color: "var(--cockpit-critical)" }}>
                Error
              </div>
              <h2 className="cockpit-drill-title">Couldn&apos;t load drill</h2>
              <div className="cockpit-drill-summary">{error}</div>
            </>
          ) : null}
        </div>
        <div className="cockpit-drill-body">
          {entry ? (
            <>
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
            </>
          ) : loading ? (
            <div style={{ padding: 24, color: "var(--cockpit-text-3)" }}>
              Loading…
            </div>
          ) : null}
        </div>
      </aside>
    </>
  )
}

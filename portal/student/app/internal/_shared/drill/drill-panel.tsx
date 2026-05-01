"use client"

import { useEffect, useRef } from "react"
import type { DrillEntry } from "../types"
import { DrillSectionRenderer } from "./sections/drill-section-renderer"
import { StatusChip } from "../status-chip"

/**
 * Shared drill panel. Finance uses the minimal shape (entry + close).
 * Recruiting (Phase 2E) uses the extra slots:
 *   - onBack/backLabel   — render a "← Back to X" bar above the eyebrow
 *                          and redirect Escape to it when set, so a
 *                          student drill opened from a job can return
 *                          to the job without closing the whole panel.
 *   - footer             — custom footer content below the sections.
 *                          Used for the Initiate Application button.
 *   - onTableRowClick    — forwarded to DrillSectionTable so table rows
 *                          declaring `row_click_key` become clickable
 *                          (click → open next drill in the stack).
 *   - bodyRef            — external ref on the scrollable body element.
 *                          Lets the caller snapshot scrollTop before
 *                          navigating away and restore it on back.
 */
export function DrillPanel({
  entry,
  loading = false,
  error,
  onClose,
  onBack,
  backLabel,
  footer,
  onTableRowClick,
  bodyRef,
}: {
  entry: DrillEntry | null
  loading?: boolean
  error?: string | null
  onClose: () => void
  onBack?: () => void
  backLabel?: string
  footer?: React.ReactNode
  onTableRowClick?: (key: string, value: string | number | boolean) => void
  bodyRef?: React.RefObject<HTMLDivElement | null>
}) {
  const open = entry !== null || loading || !!error
  const internalBodyRef = useRef<HTMLDivElement>(null)
  const effectiveBodyRef = bodyRef ?? internalBodyRef

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        // Spec: Escape in a nested drill goes back one level; Escape
        // in a top-level drill closes the whole panel.
        if (onBack) onBack()
        else onClose()
      }
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [open, onBack, onClose])

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
          {onBack && backLabel && (
            <button
              type="button"
              className="cockpit-drill-back"
              onClick={onBack}
            >
              ← {backLabel}
            </button>
          )}
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
        <div className="cockpit-drill-body" ref={effectiveBodyRef}>
          {entry ? (
            <>
              {entry.status_chip && (
                <div className="cockpit-drill-status-chip-wrap">
                  <StatusChip chip={entry.status_chip} />
                </div>
              )}
              {entry.sections.map((s, i) => (
                <DrillSectionRenderer
                  key={i}
                  section={s}
                  onTableRowClick={onTableRowClick}
                />
              ))}
              {entry.note && (
                <div className="cockpit-drill-callout">{entry.note}</div>
              )}
              {footer && (
                <div className="cockpit-drill-footer">{footer}</div>
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

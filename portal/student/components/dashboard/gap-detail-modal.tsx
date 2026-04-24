"use client"

import { useEffect, useState } from "react"
import { X, Target, CheckCircle2, AlertCircle, TrendingUp } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { fetchGapDetail, type GapDetailPayload } from "@/lib/api"

// Gap Detail Modal — Student Portal second-level drill.
// Shows the LLM-generated narrative that justified the student↔job match +
// Career Pathway (the student's other top matches as progression context).
// Triggered by clicking a JobMatchCard; closed via Escape, close button,
// or backdrop click.
//
// Per spec priorities (Ritu, Apr 24):
//   1. LLM narrative (verdict + full narrative + strengths + gaps) — most
//      important; pulled from match_narratives table.
//   2. Career Pathway — student's other matches with their own calibration
//      labels + top gaps so the student sees progression options.

export interface GapDetailModalProps {
  studentId: string
  jobId: number | string
  onClose: () => void
}

export function GapDetailModal({ studentId, jobId, onClose }: GapDetailModalProps) {
  const [data, setData] = useState<GapDetailPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchGapDetail(studentId, jobId)
      .then((d) => { if (!cancelled) setData(d) })
      .catch((e) => { if (!cancelled) setError(String(e.message ?? e)) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [studentId, jobId])

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  const core = data?.core
  const narrative = data?.narrative
  const pathway = data?.career_pathway ?? []

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="relative flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-lg bg-background shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b bg-card px-6 py-4">
          <div className="min-w-0 flex-1">
            <div className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Match detail
            </div>
            <div className="truncate text-lg font-semibold text-foreground">
              {loading ? "Loading…" : (core?.title ?? "Match")}
            </div>
            <div className="text-sm text-muted-foreground">
              {core?.company ?? ""}
              {core?.city ? ` · ${core.city}${core.state ? `, ${core.state}` : ""}` : ""}
            </div>
            {core?.cosine_similarity != null ? (
              <div className="mt-2 flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className={
                    narrative?.calibration_label === "Strong"
                      ? "bg-green-100 text-green-900"
                      : narrative?.calibration_label === "Match"
                        ? "bg-blue-100 text-blue-900"
                        : "bg-amber-100 text-amber-900"
                  }
                >
                  {narrative?.calibration_label ?? "—"}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {Math.round(core.cosine_similarity * 100)}% match
                </span>
              </div>
            ) : null}
          </div>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body (scrollable) */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error ? (
            <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
              {error}
            </div>
          ) : null}

          {/* VERDICT */}
          {narrative?.verdict_line ? (
            <section className="mb-5">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <Target className="h-3.5 w-3.5" />
                Verdict
              </div>
              <div className="text-sm font-medium leading-relaxed text-foreground">
                {narrative.verdict_line}
              </div>
            </section>
          ) : null}

          {/* FULL NARRATIVE */}
          {narrative?.narrative_text ? (
            <section className="mb-5">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Why this match
              </div>
              <div className="whitespace-pre-line text-sm leading-relaxed text-foreground">
                {narrative.narrative_text}
              </div>
            </section>
          ) : null}

          {/* STRENGTHS */}
          {narrative?.match_strengths && narrative.match_strengths.length > 0 ? (
            <section className="mb-5">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                Strengths ({narrative.match_strengths.length})
              </div>
              <ul className="space-y-2">
                {narrative.match_strengths.map((s, i) => (
                  <li key={i} className="rounded-md border bg-green-50/40 p-3 text-sm">
                    <div className="font-medium text-foreground">
                      {s.area ?? s.skill ?? "—"}
                    </div>
                    {s.evidence ? (
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {s.evidence}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {/* GAPS */}
          {narrative?.match_gaps && narrative.match_gaps.length > 0 ? (
            <section className="mb-5">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
                Gaps to close ({narrative.match_gaps.length})
              </div>
              <ul className="space-y-2">
                {narrative.match_gaps.map((g, i) => (
                  <li key={i} className="rounded-md border bg-amber-50/40 p-3 text-sm">
                    <div className="font-medium text-foreground">
                      {g.area ?? g.skill ?? "—"}
                    </div>
                    {g.note ? (
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {g.note}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {/* CAREER PATHWAY */}
          {pathway.length > 0 ? (
            <section className="mb-2">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" />
                Career Pathway — your other matches
              </div>
              <ul className="space-y-2">
                {pathway.map((p) => (
                  <li
                    key={p.job_id}
                    className="rounded-md border p-3 text-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="font-medium text-foreground">
                          {p.title}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">
                          {p.company ?? ""}
                          {p.city ? ` · ${p.city}${p.state ? `, ${p.state}` : ""}` : ""}
                        </div>
                        {p.verdict_line ? (
                          <div className="mt-1 line-clamp-2 text-xs italic text-muted-foreground">
                            &ldquo;{p.verdict_line}&rdquo;
                          </div>
                        ) : null}
                        {p.missing_skills && p.missing_skills.length > 0 ? (
                          <div className="mt-1.5 flex flex-wrap gap-1">
                            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                              Top gaps:
                            </span>
                            {p.missing_skills.slice(0, 3).map((s) => (
                              <Badge key={s} variant="outline" className="text-xs">
                                {s}
                              </Badge>
                            ))}
                            {p.missing_skills.length > 3 ? (
                              <Badge variant="outline" className="text-xs">
                                +{p.missing_skills.length - 3}
                              </Badge>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <Badge variant="secondary" className="text-xs">
                          {p.calibration_label ?? "—"}
                        </Badge>
                        <div className="text-xs font-medium tabular-nums text-muted-foreground">
                          {Math.round(p.cosine_similarity * 100)}%
                        </div>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {loading ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              Loading detail…
            </div>
          ) : !narrative && !error ? (
            <div className="rounded-md border bg-muted/30 p-4 text-sm text-muted-foreground">
              No narrative or gap analysis available for this match yet.
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

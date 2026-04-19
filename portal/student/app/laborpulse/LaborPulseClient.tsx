"use client"

import { useEffect, useRef, useState } from "react"

/**
 * LaborPulse client component — request/response JSON model.
 *
 * The FastAPI service at /api/laborpulse/query already buffers JIE's SSE
 * stream and returns a single assembled JSON body, so this component is
 * a plain fetch + await. While the request is in-flight, a staged
 * loading skeleton rotates through "Analyzing postings..." /
 * "Synthesizing..." / "Citing evidence..." so the director sees
 * progress even without true streaming.
 *
 * See docs/laborpulse.md for the SSE-vs-JSON decision record.
 */

type QueryResponse = {
  conversation_id: string | null
  answer: string
  evidence: Array<Record<string, unknown>>
  confidence: string | null
  follow_up_questions: string[]
  cost_usd: number | null
  sql_generated: string | null
}

type EnvelopeError = {
  error?: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

const LOADING_STAGES = [
  "Analyzing job-posting data…",
  "Running the query…",
  "Synthesizing the answer…",
  "Citing the evidence…",
]

export default function LaborPulseClient() {
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [stageIndex, setStageIndex] = useState(0)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [feedbackSent, setFeedbackSent] = useState<"up" | "down" | null>(null)
  const stageTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (loading) {
      setStageIndex(0)
      stageTimer.current = setInterval(() => {
        setStageIndex((i) => (i + 1) % LOADING_STAGES.length)
      }, 4500)
    } else if (stageTimer.current) {
      clearInterval(stageTimer.current)
      stageTimer.current = null
    }
    return () => {
      if (stageTimer.current) clearInterval(stageTimer.current)
    }
  }, [loading])

  async function ask(q: string, conv: string | null) {
    if (!q.trim()) return
    setLoading(true)
    setResult(null)
    setErrorMsg(null)
    setFeedbackSent(null)

    try {
      const resp = await fetch("/api/laborpulse/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          question: q,
          conversation_id: conv ?? undefined,
        }),
      })

      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as EnvelopeError | null
        const code = body?.error?.code ?? "error"
        const msg =
          body?.error?.message ??
          (resp.status === 401
            ? "Please sign in to use LaborPulse."
            : resp.status === 503
              ? "LaborPulse is temporarily unavailable."
              : "Something went wrong.")
        setErrorMsg(`${code}: ${msg}`)
        return
      }

      const data = (await resp.json()) as QueryResponse
      setResult(data)
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }

  async function sendFeedback(rating: 1 | -1) {
    if (!result?.conversation_id) return
    try {
      await fetch("/api/laborpulse/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          conversation_id: result.conversation_id,
          question,
          rating,
          answer_snapshot: result.answer?.slice(0, 16000),
          confidence: result.confidence ?? undefined,
          cost_usd: result.cost_usd ?? undefined,
        }),
      })
      setFeedbackSent(rating === 1 ? "up" : "down")
    } catch {
      // Feedback is best-effort; don't block the director on failure.
    }
  }

  return (
    <div className="space-y-6">
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault()
          ask(question, null)
        }}
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Which sectors gained the most postings in Doña Ana in Q1?"
          className="flex-1 rounded border px-3 py-2"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="rounded bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {loading && (
        <div className="rounded border bg-muted/30 p-4 text-sm">
          <div className="flex items-center gap-3">
            <span
              aria-hidden
              className="inline-block h-3 w-3 animate-pulse rounded-full bg-primary"
            />
            <span className="text-muted-foreground">{LOADING_STAGES[stageIndex]}</span>
          </div>
        </div>
      )}

      {errorMsg && (
        <div role="alert" className="rounded border border-destructive bg-destructive/10 p-4 text-sm">
          {errorMsg}
        </div>
      )}

      {result && (
        <>
          <section>
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Answer
              {result.confidence && (
                <span className="ml-2 rounded bg-muted px-2 py-0.5 text-xs normal-case">
                  confidence: {result.confidence}
                </span>
              )}
            </h2>
            <div className="prose prose-sm whitespace-pre-wrap">{result.answer}</div>
          </section>

          {result.evidence.length > 0 && (
            <section>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Evidence
              </h2>
              <ul className="space-y-2">
                {result.evidence.map((e, i) => (
                  <li key={i} className="rounded border p-3 text-sm">
                    {typeof e.source === "string" && (
                      <div className="font-mono text-xs text-muted-foreground">
                        {e.source as string}
                      </div>
                    )}
                    {typeof e.text === "string" && <div>{e.text as string}</div>}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {result.follow_up_questions.length > 0 && (
            <section>
              <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                Follow-up questions
              </h2>
              <div className="flex flex-wrap gap-2">
                {result.follow_up_questions.map((fq, i) => (
                  <button
                    key={i}
                    className="rounded-full border px-3 py-1 text-sm hover:bg-muted"
                    onClick={() => {
                      setQuestion(fq)
                      ask(fq, result.conversation_id)
                    }}
                  >
                    {fq}
                  </button>
                ))}
              </div>
            </section>
          )}

          {result.conversation_id && !feedbackSent && (
            <section className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Was this useful?</span>
              <button
                onClick={() => sendFeedback(1)}
                className="rounded border px-3 py-1 hover:bg-muted"
                aria-label="Thumbs up"
              >
                👍
              </button>
              <button
                onClick={() => sendFeedback(-1)}
                className="rounded border px-3 py-1 hover:bg-muted"
                aria-label="Thumbs down"
              >
                👎
              </button>
            </section>
          )}
          {feedbackSent && (
            <p className="text-sm text-muted-foreground">
              Thanks for the {feedbackSent === "up" ? "👍" : "👎"} — it helps us tune answers.
            </p>
          )}
        </>
      )}
    </div>
  )
}

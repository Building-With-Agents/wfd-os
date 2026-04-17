"use client"

import { useState } from "react"

/**
 * LaborPulse client component.
 *
 * Responsibilities:
 *  1. Capture the director's question.
 *  2. POST /api/laborpulse/query and parse the SSE body chunk-by-chunk
 *     using fetch + ReadableStream (EventSource doesn't support POST).
 *  3. Dispatch each SSE event to the right piece of state:
 *       event: answer    → append to `answer` (progressive markdown)
 *       event: evidence  → push into `evidence[]`
 *       event: confidence→ set `confidence`
 *       event: followup  → push into `followUps[]`
 *       event: done      → capture `conversation_id` + `cost_usd`
 *  4. Render the structured response + thumbs-up/down + follow-up chips.
 *
 * Styling is minimal on purpose — the refactor already established brand
 * config via `request.state.brand` in the server layout; this component
 * just paints the content inside that.
 */
export default function LaborPulseClient() {
  const [question, setQuestion] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [answer, setAnswer] = useState("")
  const [evidence, setEvidence] = useState<
    Array<{ source?: string; text?: string }>
  >([])
  const [confidence, setConfidence] = useState<string | null>(null)
  const [followUps, setFollowUps] = useState<string[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [costUsd, setCostUsd] = useState<number | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [feedbackSent, setFeedbackSent] = useState<"up" | "down" | null>(null)

  async function ask(q: string, conv: string | null) {
    if (!q.trim()) return
    setStreaming(true)
    setAnswer("")
    setEvidence([])
    setConfidence(null)
    setFollowUps([])
    setConversationId(null)
    setCostUsd(null)
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
        const body = await resp.json().catch(() => null)
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

      const reader = resp.body?.getReader()
      if (!reader) {
        setErrorMsg("Stream not available in this browser.")
        return
      }

      const decoder = new TextDecoder()
      let buffer = ""
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        // SSE frames are separated by a blank line (\n\n).
        let idx
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, idx)
          buffer = buffer.slice(idx + 2)
          handleFrame(frame)
        }
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setStreaming(false)
    }
  }

  function handleFrame(frame: string) {
    // Each SSE frame is a series of "field: value" lines. We only
    // care about `event:` + `data:`. `data:` may contain JSON.
    let eventName = "message"
    let dataLine = ""
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim()
      else if (line.startsWith("data:")) dataLine += line.slice(5).trim()
    }
    let payload: Record<string, unknown> = {}
    try {
      payload = dataLine ? JSON.parse(dataLine) : {}
    } catch {
      // Non-JSON data — JIE sometimes emits plain-text chunks for
      // streamed tokens. Treat the raw string as `.text`.
      payload = { text: dataLine }
    }
    switch (eventName) {
      case "answer":
        if (typeof payload.text === "string") setAnswer((a) => a + payload.text)
        break
      case "evidence":
        setEvidence((ev) => [...ev, payload as { source?: string; text?: string }])
        break
      case "confidence":
        if (typeof payload.level === "string") setConfidence(payload.level)
        else if (typeof payload.text === "string") setConfidence(payload.text)
        break
      case "followup":
      case "follow_up":
        if (typeof payload.question === "string")
          setFollowUps((f) => [...f, payload.question as string])
        else if (Array.isArray(payload.questions))
          setFollowUps((f) => [...f, ...(payload.questions as string[])])
        break
      case "done":
        if (typeof payload.conversation_id === "string")
          setConversationId(payload.conversation_id)
        if (typeof payload.cost_usd === "number") setCostUsd(payload.cost_usd)
        break
    }
  }

  async function sendFeedback(rating: 1 | -1) {
    if (!conversationId) return
    try {
      await fetch("/api/laborpulse/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          conversation_id: conversationId,
          question,
          rating,
          answer_snapshot: answer.slice(0, 16000),
          confidence: confidence ?? undefined,
          cost_usd: costUsd ?? undefined,
        }),
      })
      setFeedbackSent(rating === 1 ? "up" : "down")
    } catch {
      // Feedback is best-effort; don't pester the director on failure.
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
          disabled={streaming}
        />
        <button
          type="submit"
          disabled={streaming || !question.trim()}
          className="rounded bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50"
        >
          {streaming ? "Thinking…" : "Ask"}
        </button>
      </form>

      {errorMsg && (
        <div role="alert" className="rounded border border-destructive bg-destructive/10 p-4 text-sm">
          {errorMsg}
        </div>
      )}

      {(answer || streaming) && (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Answer
            {confidence && (
              <span className="ml-2 rounded bg-muted px-2 py-0.5 text-xs normal-case">
                confidence: {confidence}
              </span>
            )}
          </h2>
          <div className="prose prose-sm whitespace-pre-wrap">{answer}</div>
        </section>
      )}

      {evidence.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Evidence
          </h2>
          <ul className="space-y-2">
            {evidence.map((e, i) => (
              <li key={i} className="rounded border p-3 text-sm">
                {e.source && <div className="font-mono text-xs text-muted-foreground">{e.source}</div>}
                {e.text && <div>{e.text}</div>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {followUps.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Follow-up questions
          </h2>
          <div className="flex flex-wrap gap-2">
            {followUps.map((fq, i) => (
              <button
                key={i}
                className="rounded-full border px-3 py-1 text-sm hover:bg-muted"
                onClick={() => {
                  setQuestion(fq)
                  ask(fq, conversationId)
                }}
              >
                {fq}
              </button>
            ))}
          </div>
        </section>
      )}

      {conversationId && !feedbackSent && (
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
          Thanks for the {feedbackSent === "up" ? "👍" : "👎"} — it helps us
          tune answers.
        </p>
      )}
    </div>
  )
}

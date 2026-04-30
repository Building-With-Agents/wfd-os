"use client"

// Mode B Q&A panel for the Compliance Requirements tab. Right-docked overlay.
// Toggle from the main view; conversation history is per-session (closes
// when the panel closes, per spec). The engine's compliance_qa_log table
// holds the permanent audit record server-side.
//
// Per-question behavior:
//   1. Question appears immediately (right-aligned, user style)
//   2. Loading indicator (typical 20-40s for Sonnet; longer for Opus)
//   3. Response replaces loading: answer text + citations + relevant
//      requirements + caveats. Refusals + out-of-scope warnings render
//      with distinct visual treatment per spec §"Refusal handling".
//
// Citation linking: when a Mode B response cites a requirement_id from
// the current set, clicking the link opens that requirement's drill panel
// in the parent view. Done via the onCiteRequirement callback.

import { useEffect, useRef, useState } from "react"
import {
  postComplianceQA,
  ComplianceQAError,
} from "../../lib/compliance-api"
import type {
  QAResponse,
  Requirement,
} from "../../lib/compliance-types"

const INPUT_MAX_LENGTH = 4000

interface QAExchange {
  id: string
  question: string
  pending: boolean
  response: QAResponse | null
  error: string | null
  asked_at: string
}

export function ComplianceQAPanel({
  grantId, seedQuestion, onSeedConsumed, onClose, requirements,
}: {
  grantId: string
  seedQuestion: string | null
  onSeedConsumed: () => void
  onClose: () => void
  requirements: Requirement[]
}) {
  const [exchanges, setExchanges] = useState<QAExchange[]>([])
  const [input, setInput] = useState("")
  const [busy, setBusy] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const bodyRef = useRef<HTMLDivElement>(null)

  // Build a lookup so we can render Mode B's relevant_existing_requirements
  // as click-through links.
  const reqById = useRef(new Map<string, Requirement>())
  useEffect(() => {
    const m = new Map<string, Requirement>()
    for (const r of requirements) m.set(r.requirement_id, r)
    reqById.current = m
  }, [requirements])

  // Seed-question handling: when the panel opens via "Ask the agent about
  // this requirement", pre-fill the input. The parent clears the seed
  // after it's consumed.
  useEffect(() => {
    if (seedQuestion) {
      setInput(seedQuestion)
      onSeedConsumed()
      // Focus the input so the user can edit + send
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [seedQuestion, onSeedConsumed])

  // Auto-scroll on new content
  useEffect(() => {
    const el = bodyRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [exchanges])

  async function send() {
    const trimmed = input.trim()
    if (!trimmed || busy) return
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    setExchanges((prev) => [
      ...prev,
      { id, question: trimmed, pending: true, response: null, error: null, asked_at: new Date().toISOString() },
    ])
    setInput("")
    setBusy(true)
    try {
      const response = await postComplianceQA({
        question: trimmed,
        grant_id: grantId,
        asked_by: "ritu",
      })
      setExchanges((prev) =>
        prev.map((x) => (x.id === id ? { ...x, pending: false, response } : x)),
      )
    } catch (err: unknown) {
      const msg =
        err instanceof ComplianceQAError ? `${err.message}: ${err.detail ?? ""}`
          : err instanceof Error ? err.message
          : String(err)
      setExchanges((prev) =>
        prev.map((x) => (x.id === id ? { ...x, pending: false, error: msg } : x)),
      )
    } finally {
      setBusy(false)
      inputRef.current?.focus()
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      void send()
    }
  }

  function clearConversation() {
    setExchanges([])
    inputRef.current?.focus()
  }

  return (
    <>
      <div
        onClick={onClose}
        style={{ position: "fixed", inset: 0, background: "rgba(26,26,26,0.32)", zIndex: 200 }}
      />
      <div
        style={{
          position: "fixed", top: 0, right: 0, bottom: 0, width: "min(560px, 100vw)",
          background: "var(--cockpit-surface)", zIndex: 201,
          borderLeft: "1px solid var(--cockpit-border)",
          display: "flex", flexDirection: "column",
          fontSize: "var(--cockpit-fs-body)",
        }}
      >
        {/* Header */}
        <div style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--cockpit-border)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: "var(--cockpit-fs-button)" }}>Ask the Compliance Agent</div>
            <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)" }}>
              Mode B · grounded in 2 CFR 200 corpus · Sonnet 4.5
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {exchanges.length > 0 && (
              <button type="button" onClick={clearConversation} style={iconBtnStyle} title="Clear conversation">
                Clear
              </button>
            )}
            <button type="button" onClick={onClose} style={iconBtnStyle} title="Close">×</button>
          </div>
        </div>

        {/* Conversation body */}
        <div ref={bodyRef} style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {exchanges.length === 0 && (
            <EmptyHint />
          )}
          {exchanges.map((x) => (
            <ExchangeBlock key={x.id} exchange={x} reqById={reqById.current} />
          ))}
        </div>

        {/* Input */}
        <div style={{ padding: "12px 16px", borderTop: "1px solid var(--cockpit-border)", background: "var(--cockpit-surface-alt)" }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value.slice(0, INPUT_MAX_LENGTH))}
            onKeyDown={handleKey}
            disabled={busy}
            placeholder="Ask about a specific compliance question — e.g. cost analysis requirements for a $245K sole-source contract."
            rows={3}
            maxLength={INPUT_MAX_LENGTH}
            style={{
              width: "100%",
              padding: "10px 12px",
              fontSize: "var(--cockpit-fs-body)",
              border: "1px solid var(--cockpit-border-strong)",
              background: "var(--cockpit-surface)",
              fontFamily: "inherit",
              resize: "vertical",
              minHeight: 64,
              outline: "none",
            }}
            aria-label="Ask the Compliance Agent"
          />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
            <span style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
              ⌘ / Ctrl + Enter to send · {input.length}/{INPUT_MAX_LENGTH}
            </span>
            <button
              type="button"
              onClick={send}
              disabled={busy || !input.trim()}
              style={{
                padding: "6px 16px",
                fontSize: "var(--cockpit-fs-button)",
                background: busy || !input.trim() ? "var(--cockpit-text-3)" : "var(--cockpit-brand)",
                color: "#F5F2E8",
                border: "none",
                cursor: busy || !input.trim() ? "not-allowed" : "pointer",
                fontFamily: "inherit",
              }}
            >
              {busy ? "Asking…" : "Ask"}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

const iconBtnStyle: React.CSSProperties = {
  background: "transparent",
  border: "none",
  fontSize: "var(--cockpit-fs-meta)",
  color: "var(--cockpit-text-3)",
  cursor: "pointer",
  padding: "4px 8px",
  fontFamily: "inherit",
}

function EmptyHint() {
  return (
    <div style={{ color: "var(--cockpit-text-3)", fontSize: "var(--cockpit-fs-body)", lineHeight: 1.55 }}>
      <p style={{ margin: "0 0 12px" }}>
        Ask narrowly-scoped questions about federal grant documentation
        requirements. The agent answers with citations to the corpus.
      </p>
      <p style={{ margin: "0 0 8px", color: "var(--cockpit-text-2)" }}>Examples:</p>
      <ul style={{ margin: 0, paddingLeft: 20, lineHeight: 1.55 }}>
        <li>What documentation is required for a sole-source procurement above the SAT?</li>
        <li>How do I distinguish a subrecipient from a contractor for AI Engage?</li>
        <li>Does §200.318(c) require a written COI policy with disciplinary provisions?</li>
      </ul>
      <p style={{ margin: "12px 0 0", fontSize: "var(--cockpit-fs-meta)" }}>
        The agent will refuse legal-opinion questions and surface out-of-scope topics
        rather than guess.
      </p>
    </div>
  )
}

function ExchangeBlock({ exchange, reqById }: {
  exchange: QAExchange
  reqById: Map<string, Requirement>
}) {
  return (
    <div style={{ marginBottom: 20 }}>
      {/* User question */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}>
        <div style={{
          maxWidth: "85%", padding: "8px 12px",
          background: "var(--cockpit-surface-warm, #EAE6D8)",
          color: "var(--cockpit-text-1)",
          fontSize: "var(--cockpit-fs-body)",
          lineHeight: 1.5,
          whiteSpace: "pre-wrap",
        }}>
          {exchange.question}
        </div>
      </div>

      {/* Loading state */}
      {exchange.pending && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", color: "var(--cockpit-text-3)", fontSize: "var(--cockpit-fs-meta)" }}>
          <Dots /> Thinking… (typically 20–40 seconds)
        </div>
      )}

      {/* Error */}
      {exchange.error && (
        <div style={{
          padding: "10px 14px",
          background: "var(--cockpit-critical-soft, #FBE9E9)",
          color: "var(--cockpit-critical)",
          border: "1px solid var(--cockpit-critical)",
          fontSize: "var(--cockpit-fs-body)",
        }}>
          <strong>Error:</strong> {exchange.error}
        </div>
      )}

      {/* Response */}
      {exchange.response && <ResponseBlock response={exchange.response} reqById={reqById} />}
    </div>
  )
}

function ResponseBlock({ response, reqById }: {
  response: QAResponse
  reqById: Map<string, Requirement>
}) {
  const isRefusal = response.refused
  const isOutOfScope = !!response.out_of_scope_warning

  // Distinct visual treatment for refusals and out-of-scope per spec
  const containerBorder =
    isRefusal ? "var(--cockpit-watch)"
    : isOutOfScope ? "var(--cockpit-watch)"
    : "var(--cockpit-border)"

  return (
    <div style={{
      maxWidth: "100%",
      padding: "12px 14px",
      background: "#FFFFFF",
      border: `1px solid ${containerBorder}`,
      fontSize: "var(--cockpit-fs-body)",
      lineHeight: 1.55,
    }}>
      {isRefusal && (
        <div style={{ marginBottom: 8, fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-watch)", fontWeight: 600 }}>
          ⚠ Agent declined — counsel review recommended
        </div>
      )}
      {isOutOfScope && !isRefusal && (
        <div style={{ marginBottom: 8, fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-watch)", fontWeight: 600 }}>
          ⓘ Out-of-scope of current corpus
        </div>
      )}

      {/* Answer (markdown not rendered for v1 — agent emits plain English / structured headings) */}
      <div style={{ whiteSpace: "pre-wrap" }}>{response.answer}</div>

      {/* Out-of-scope warning, if present */}
      {isOutOfScope && (
        <div style={{
          marginTop: 12,
          padding: "8px 12px",
          background: "var(--cockpit-watch-soft, #FAF3DD)",
          fontSize: "var(--cockpit-fs-meta)",
          color: "var(--cockpit-text-2)",
          borderLeft: "3px solid var(--cockpit-watch)",
          whiteSpace: "pre-wrap",
        }}>
          <strong>Out of scope:</strong> {response.out_of_scope_warning}
        </div>
      )}

      {/* Citations */}
      {response.regulatory_citations.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 8, borderTop: "1px solid var(--cockpit-border)" }}>
          <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>
            Citations ({response.regulatory_citations.length})
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {response.regulatory_citations.map((c) => (
              <code key={c} style={{ fontSize: "var(--cockpit-fs-meta)", background: "var(--cockpit-surface-alt)", padding: "2px 6px" }}>{c}</code>
            ))}
          </div>
        </div>
      )}

      {/* Relevant existing requirements (deep-link tag) */}
      {response.relevant_existing_requirements.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 8, borderTop: "1px solid var(--cockpit-border)" }}>
          <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>
            Relevant requirements in current set ({response.relevant_existing_requirements.length})
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {response.relevant_existing_requirements.map((rid) => {
              const req = reqById.get(rid)
              const style: React.CSSProperties = {
                fontSize: "var(--cockpit-fs-meta)",
                padding: "2px 6px",
                background: req ? "var(--cockpit-surface-alt)" : "transparent",
                color: req ? "var(--cockpit-brand)" : "var(--cockpit-text-3)",
                textDecoration: req ? "underline" : "line-through",
                cursor: req ? "default" : undefined,
              }
              const title = req ? `${req.regulatory_citation} — ${req.requirement_summary.slice(0, 80)}` : `not in current set`
              // Click handling for deep-link not yet wired in v1 — would require
              // lifting drill state to the parent. The link visual signals
              // it as a navigable reference; v1.1 wires the click action.
              return (
                <code key={rid} title={title} style={style}>{rid}</code>
              )
            })}
          </div>
        </div>
      )}

      {/* Caveats — must be visible per spec, not hidden */}
      {response.caveats.length > 0 && (
        <div style={{ marginTop: 12, paddingTop: 8, borderTop: "1px solid var(--cockpit-border)" }}>
          <div style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: 4 }}>
            Caveats ({response.caveats.length})
          </div>
          <ul style={{ margin: 0, paddingLeft: 20, fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-2)", lineHeight: 1.5 }}>
            {response.caveats.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function Dots() {
  return (
    <span style={{ display: "inline-flex", gap: 3 }}>
      <span style={dotStyle(0)}>•</span>
      <span style={dotStyle(1)}>•</span>
      <span style={dotStyle(2)}>•</span>
    </span>
  )
}

function dotStyle(idx: number): React.CSSProperties {
  return {
    animation: `cockpit-chat-pulse 1.2s ease-in-out infinite`,
    animationDelay: `${idx * 0.15}s`,
  }
}

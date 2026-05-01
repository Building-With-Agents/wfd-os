"use client"

// Broad chat — Surface 1 from agents/finance/design/chat_spec.md.
// Right-docked column visible on every cockpit tab. Single rolling
// session for the visit. Replaces the v0 ChatPanel placeholder.
//
// State lives in FinanceChatProvider (sibling file). This component is
// a presentation layer: it reads + writes the context, owns the input
// ref + scroll ref, and renders the panel — including the collapsed
// rail variant.

import {
  useEffect,
  useRef,
  type FormEvent,
  type KeyboardEvent,
} from "react"
import { ChevronLeft, ChevronRight, MessageSquare } from "lucide-react"

import { useFinanceChat } from "./finance-chat-context"
import { renderAgentText } from "./markdown-render"

const SEEDED_PROMPTS: readonly string[] = [
  "Which providers are behind on reporting?",
  "Draft this month's update for Andrew",
  "What's in next month's advance request?",
  "Summarize recent activity on K8341",
  "What do I need to prepare for ESD monitoring?",
]

const INPUT_MAX_LENGTH = 1000

export function BroadChat({
  onOpenDrill,
}: {
  onOpenDrill: (drillKey: string) => void
}) {
  const {
    messages,
    loading,
    inputValue,
    setInputValue,
    sendMessage,
    clearConversation,
    collapsed,
    setCollapsed,
    focusToken,
  } = useFinanceChat()

  const bodyRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-scroll the message list to the bottom on new content.
  useEffect(() => {
    const el = bodyRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, loading])

  // External focus requests (from drill-chat handoff in step 5, or from
  // the user expanding the panel). Triggered by an incrementing token.
  useEffect(() => {
    if (collapsed) return
    inputRef.current?.focus()
  }, [focusToken, collapsed])

  // ---------------------------------------------------------------------
  // Collapsed: render a 44px-wide rail with a chat icon. Click expands.
  // ---------------------------------------------------------------------
  if (collapsed) {
    return (
      <div
        className="cockpit-chat-col"
        data-collapsed="true"
        aria-label="Finance Assistant (collapsed)"
      >
        <button
          type="button"
          className="cockpit-chat-rail-btn"
          onClick={() => setCollapsed(false)}
          aria-label="Expand Finance Assistant"
          title="Expand Finance Assistant"
        >
          <ChevronLeft size={16} aria-hidden="true" />
          <MessageSquare size={18} aria-hidden="true" />
        </button>
      </div>
    )
  }

  // ---------------------------------------------------------------------
  // Expanded: full panel with header, body, input.
  // ---------------------------------------------------------------------
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    void sendMessage(inputValue)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // ⌘/Ctrl + Enter sends, mirroring the placeholder's hint.
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      void sendMessage(inputValue)
    }
  }

  const handlePromptClick = (text: string) => {
    void sendMessage(text)
  }

  return (
    <div className="cockpit-chat-col" data-collapsed="false">
      <div className="cockpit-chat-head">
        <button
          type="button"
          className="cockpit-chat-collapse-btn"
          onClick={() => setCollapsed(true)}
          aria-label="Collapse Finance Assistant"
          title="Collapse"
        >
          <ChevronRight size={16} aria-hidden="true" />
        </button>
        <div className="cockpit-chat-head-title">Finance Assistant</div>
        {messages.length > 0 && (
          <button
            type="button"
            className="cockpit-chat-clear-btn"
            onClick={clearConversation}
          >
            Clear conversation
          </button>
        )}
      </div>

      <div className="cockpit-chat-body" ref={bodyRef}>
        {messages.length === 0 && (
          <>
            <div className="cockpit-chat-section-head">Try asking</div>
            <div className="cockpit-chat-pills">
              {SEEDED_PROMPTS.map((p) => (
                <button
                  key={p}
                  type="button"
                  className="cockpit-chat-pill"
                  onClick={() => handlePromptClick(p)}
                  disabled={loading}
                >
                  <span className="cockpit-chat-pill-icon">→</span>
                  {p}
                </button>
              ))}
            </div>
          </>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className="cockpit-chat-msg-row"
            data-role={m.role}
            data-error={m.error ? "true" : undefined}
          >
            <div className="cockpit-chat-msg-bubble">
              {m.role === "assistant"
                ? renderAgentText(m.content, onOpenDrill)
                : m.content}
            </div>
            {m.error && (
              <button
                type="button"
                className="cockpit-chat-retry-btn"
                onClick={() => {
                  // Re-send the most recent user message (the one that
                  // produced this error). It's the message immediately
                  // preceding this errored assistant entry.
                  for (let j = i - 1; j >= 0; j--) {
                    if (messages[j].role === "user") {
                      void sendMessage(messages[j].content)
                      return
                    }
                  }
                }}
              >
                Try again
              </button>
            )}
          </div>
        ))}

        {loading && (
          <div className="cockpit-chat-msg-row" data-role="assistant">
            <div className="cockpit-chat-msg-bubble cockpit-chat-typing">
              <span className="cockpit-chat-typing-dot" />
              <span className="cockpit-chat-typing-dot" />
              <span className="cockpit-chat-typing-dot" />
            </div>
          </div>
        )}
      </div>

      <form className="cockpit-chat-input" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          className="cockpit-chat-input-field"
          placeholder="Ask about runway, providers, flags, audit prep…"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value.slice(0, INPUT_MAX_LENGTH))}
          onKeyDown={handleKeyDown}
          disabled={loading}
          maxLength={INPUT_MAX_LENGTH}
          aria-label="Ask the Finance Assistant"
        />
        <div className="cockpit-chat-meta">⌘ / Ctrl + Enter to send</div>
      </form>
    </div>
  )
}

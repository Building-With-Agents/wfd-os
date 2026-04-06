"use client"

import { useEffect, useRef, useState } from "react"
import { usePathname } from "next/navigation"
import { MessageCircle, X, Send, Sparkles } from "lucide-react"

const API_BASE = "/api/assistant"

// Page → agent type mapping (rule-based, not LLM)
function agentForPath(path: string): string {
  if (path.startsWith("/showcase") || path.startsWith("/for-employers")) return "employer"
  if (path.startsWith("/careers") || path.startsWith("/student")) return "student"
  if (path.startsWith("/college")) return "college"
  if (path.startsWith("/youth")) return "youth"
  if (path.startsWith("/cfa/ai-consulting")) return "consulting"
  if (path.startsWith("/internal")) return "staff"
  return "employer" // default for homepage visitors
}

function openingForAgent(agent: string): { text: string; suggestions: string[] } {
  switch (agent) {
    case "student":
      return {
        text: "Hi! What kind of tech work are you looking for?\n\n(Even a rough idea is fine \u2014 I can help narrow it down.)",
        suggestions: ["Software development", "IT support / help desk", "Data and analytics", "Cloud and infrastructure", "I\u2019m not sure yet"],
      }
    case "employer":
      return {
        text: "Hi! I can help you find qualified tech talent from our verified pipeline, or connect you with our AI consulting team.\n\nWhat brings you here today?",
        suggestions: ["I\u2019m hiring", "I need AI consulting", "Tell me about CFA", "Browse candidates"],
      }
    case "college":
      return {
        text: "Hi! I\u2019m the CFA college partner advisor. I have real-time employer demand data and graduate pipeline stats.\n\nWhich institution are you with?",
        suggestions: ["Bellevue College", "North Seattle College", "Another institution", "Show me curriculum gaps"],
      }
    case "youth":
      return {
        text: "Hi! \ud83d\udc4b Are you curious about tech careers?\n\nI can tell you about our free coding program for Washington State residents aged 16-24 \u2014 no experience needed at all.\n\nWhat would you like to know?",
        suggestions: ["What does the program teach?", "How do I apply?", "What jobs can I get?", "Is it really free?"],
      }
    case "staff":
      return {
        text: "Hi! I\u2019m the CFA ops assistant. What do you need to know?",
        suggestions: ["Grant status", "Consulting pipeline", "Cohort status", "Placement update"],
      }
    case "consulting":
      return {
        text: "Hi! I\u2019m the CFA consulting advisor. I work with workforce boards, healthcare organizations, and professional services firms to figure out where AI agents can eliminate manual work.\n\nAre you with a workforce board, a healthcare organization, a professional services firm, or something else?",
        suggestions: ["Workforce board", "Healthcare organization", "Professional services firm", "Something else"],
      }
    default:
      return { text: "Hi! How can I help you today?", suggestions: [] }
  }
}

interface Msg {
  id: string
  role: "user" | "assistant"
  content: string
  suggestions?: string[] | null
}

export default function ChatWidget() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [sessionId, setSessionId] = useState("")
  const [agentType, setAgentType] = useState("employer")
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Determine agent from current page
  useEffect(() => {
    const agent = agentForPath(pathname)
    setAgentType(agent)
    const sid = `widget-${agent}-${crypto.randomUUID().slice(0, 8)}`
    setSessionId(sid)
    const opening = openingForAgent(agent)
    setMessages([{ id: "opening", role: "assistant", content: opening.text, suggestions: opening.suggestions }])
  }, [pathname])

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages])

  // Focus input on open
  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus()
  }, [open, sending])

  const sendMsg = async (text: string) => {
    if (!text.trim() || sending) return
    const userMsg: Msg = { id: `u-${Date.now()}`, role: "user", content: text.trim() }
    // Clear suggestions from previous assistant message
    setMessages((prev) => [
      ...prev.map((m) => (m.role === "assistant" ? { ...m, suggestions: null } : m)),
      userMsg,
    ])
    setInput("")
    setSending(true)

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, agent_type: agentType, user_role: "visitor", message: text.trim() }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setMessages((prev) => [...prev, {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: data.response,
        suggestions: data.suggestions || null,
      }])
    } catch {
      setMessages((prev) => [...prev, { id: `e-${Date.now()}`, role: "assistant", content: "Something went wrong. Please try again." }])
    } finally {
      setSending(false)
    }
  }

  // Don't show widget on pages that have their own full chat (/cfa/ai-consulting/chat)
  if (pathname.startsWith("/cfa/ai-consulting/chat")) return null
  // Don't show on /internal (staff has their own interface)
  if (pathname.startsWith("/internal")) return null

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-primary shadow-lg transition-transform hover:scale-105 hover:shadow-xl"
          aria-label="Open chat"
        >
          <MessageCircle className="h-6 w-6 text-white" />
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 flex h-[500px] w-[380px] flex-col overflow-hidden rounded-2xl border bg-white shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between bg-primary px-4 py-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-white/80" />
              <span className="text-sm font-semibold text-white">CFA Advisor</span>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded p-1 text-white/70 transition-colors hover:bg-white/20 hover:text-white"
              aria-label="Close chat"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            {messages.map((msg, idx) => {
              const isLast = idx === messages.length - 1
              const showSuggestions = msg.role === "assistant" && isLast && msg.suggestions && msg.suggestions.length > 0 && !sending
              return (
                <div key={msg.id}>
                  <div className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-[13px] leading-relaxed ${
                      msg.role === "user"
                        ? "rounded-br-sm border border-primary/20 bg-white text-foreground"
                        : "rounded-bl-sm bg-primary/5 text-foreground"
                    }`}>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                  {showSuggestions && (
                    <div className="mt-1.5 flex flex-wrap gap-1 pl-1">
                      {msg.suggestions!.map((s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => sendMsg(s)}
                          className="rounded-full border border-primary/30 bg-primary/5 px-2.5 py-1 text-[11px] font-medium text-primary transition-all hover:border-primary hover:bg-primary hover:text-white"
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
            {sending && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-sm bg-primary/5 px-3 py-2">
                  <div className="flex items-center gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/40 [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/40 [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary/40 [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t px-3 py-2">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMsg(input) } }}
                placeholder="Type a message..."
                disabled={sending}
                className="flex-1 rounded-full border border-input bg-muted/30 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
              />
              <button
                type="button"
                onClick={() => sendMsg(input)}
                disabled={!input.trim() || sending}
                className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-white disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useRef, useState } from "react"
import {
  ArrowLeft, CheckCircle2, Send, Sparkles, ExternalLink,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

const API_BASE = "/api/assistant"

const OPENING_MESSAGE = `Hi! I\u2019m the CFA consulting advisor. I work with workforce boards, healthcare organizations, and professional services firms to figure out where AI agents can eliminate the manual work that\u2019s eating your team\u2019s time.

To point you in the right direction \u2014 are you with a workforce board, a healthcare organization, a professional services firm, or something else?`

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  action?: any
  suggestions?: string[] | null
}

function getOrCreateSession(): string {
  if (typeof window === "undefined") return crypto.randomUUID()
  const key = "cfa_consulting_session_id"
  let sid = sessionStorage.getItem(key)
  if (!sid) {
    sid = crypto.randomUUID()
    sessionStorage.setItem(key, sid)
  }
  return sid
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
}

export default function ConsultingChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [sessionId, setSessionId] = useState("")
  const [completed, setCompleted] = useState(false)
  const [referenceNumber, setReferenceNumber] = useState<string | null>(null)
  const [contactName, setContactName] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Init session + opening message
  useEffect(() => {
    const sid = getOrCreateSession()
    setSessionId(sid)
    setMessages([
      {
        id: "opening",
        role: "assistant",
        content: OPENING_MESSAGE,
        timestamp: new Date(),
        suggestions: ["Workforce board", "Healthcare organization", "Professional services firm", "Something else"],
      },
    ])
  }, [])

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Focus input after agent responds
  useEffect(() => {
    if (!sending && inputRef.current) {
      inputRef.current.focus()
    }
  }, [sending])

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || sending || completed) return

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setSending(true)

    try {
      const res = await apiFetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          agent_type: "consulting",
          user_role: "prospect",
          message: text,
        }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
        action: data.action,
        suggestions: data.suggestions || null,
      }
      setMessages((prev) => [...prev, assistantMsg])

      // Check for INTAKE_COMPLETE signal or submit_inquiry tool result in the response
      const responseText = data.response || ""
      // Look for reference number pattern in the response
      const refMatch = responseText.match(/INQ-\d{4}-\d{4}/)
      if (refMatch) {
        setReferenceNumber(refMatch[0])
        // Try to extract contact name from conversation
        const allUserMsgs = [...messages, userMsg].filter((m) => m.role === "user").map((m) => m.content).join(" ")
        const nameMatch = allUserMsgs.match(/(?:my name is|I'm|I am|name's)\s+([A-Z][a-z]+)/i)
        if (nameMatch) setContactName(nameMatch[1])
        setCompleted(true)
      }
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: "I'm having trouble connecting right now. Please try again in a moment.",
          timestamp: new Date(),
        },
      ])
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex-shrink-0 border-b bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <a
              href="/cfa/ai-consulting"
              className="flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back to consulting
            </a>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <div>
              <p className="text-sm font-semibold text-foreground">CFA AI Consulting</p>
              <p className="text-[10px] text-muted-foreground">Tell us about your project</p>
            </div>
          </div>
        </div>
      </header>

      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl space-y-4 px-4 py-6">
          {messages.map((msg, idx) => {
            const isLast = idx === messages.length - 1
            const showSuggestions =
              msg.role === "assistant" &&
              isLast &&
              msg.suggestions &&
              msg.suggestions.length > 0 &&
              !sending &&
              !completed

            return (
              <div key={msg.id}>
                <div className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      msg.role === "user"
                        ? "rounded-br-md border-2 border-primary/20 bg-white text-foreground"
                        : "rounded-bl-md bg-primary/5 text-foreground"
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                    <p
                      className={`mt-1 text-[10px] ${
                        msg.role === "user" ? "text-right text-muted-foreground" : "text-muted-foreground"
                      }`}
                    >
                      {formatTime(msg.timestamp)}
                    </p>
                  </div>
                </div>

                {/* Suggested reply pills */}
                {showSuggestions && (
                  <div className="mt-2 flex flex-wrap gap-2 pl-2">
                    {msg.suggestions!.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => {
                          setInput(s)
                          // Clear suggestions from this message so they disappear after click
                          setMessages((prev) =>
                            prev.map((m) =>
                              m.id === msg.id ? { ...m, suggestions: null } : m
                            )
                          )
                          // Auto-send after a tick so the input renders first
                          setTimeout(() => {
                            const userMsg: Message = {
                              id: `user-${Date.now()}`,
                              role: "user",
                              content: s,
                              timestamp: new Date(),
                            }
                            setMessages((prev) => [...prev, userMsg])
                            setInput("")
                            setSending(true)
                            apiFetch(`${API_BASE}/chat`, {
                              method: "POST",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({
                                session_id: sessionId,
                                agent_type: "consulting",
                                user_role: "prospect",
                                message: s,
                              }),
                            })
                              .then((r) => r.json())
                              .then((data) => {
                                const assistantReply: Message = {
                                  id: `assistant-${Date.now()}`,
                                  role: "assistant",
                                  content: data.response,
                                  timestamp: new Date(),
                                  action: data.action,
                                  suggestions: data.suggestions || null,
                                }
                                setMessages((prev) => [...prev, assistantReply])
                                const refMatch = data.response?.match(/INQ-\d{4}-\d{4}/)
                                if (refMatch) {
                                  setReferenceNumber(refMatch[0])
                                  setCompleted(true)
                                }
                              })
                              .catch(() => {
                                setMessages((prev) => [
                                  ...prev,
                                  {
                                    id: `error-${Date.now()}`,
                                    role: "assistant",
                                    content: "Something went wrong. Please try again.",
                                    timestamp: new Date(),
                                  },
                                ])
                              })
                              .finally(() => setSending(false))
                          }, 50)
                        }}
                        className="rounded-full border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary transition-all hover:border-primary hover:bg-primary hover:text-white"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          })}

          {/* Typing indicator */}
          {sending && (
            <div className="flex justify-start">
              <div className="rounded-2xl rounded-bl-md bg-primary/5 px-4 py-3">
                <div className="flex items-center gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-primary/40 [animation-delay:0ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-primary/40 [animation-delay:150ms]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-primary/40 [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}

          {/* Completion card */}
          {completed && (
            <div className="mx-auto max-w-md">
              <Card className="border-2 border-green-200 bg-green-50 p-6 text-center">
                <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-500" />
                <h3 className="text-lg font-bold text-foreground">
                  Thank you{contactName ? `, ${contactName}` : ""}!
                </h3>
                {referenceNumber && (
                  <p className="mt-2 text-sm text-muted-foreground">
                    Reference: <span className="font-mono font-semibold text-primary">{referenceNumber}</span>
                  </p>
                )}
                <p className="mt-2 text-sm text-muted-foreground">
                  Ritu will reach out within 24 hours to schedule a scoping conversation.
                </p>
                <div className="mt-4 flex gap-2">
                  <a href="/showcase" className="flex-1">
                    <Button variant="outline" size="sm" className="w-full gap-1 text-xs">
                      Browse our work <ExternalLink className="h-3 w-3" />
                    </Button>
                  </a>
                  <a href="/cfa/ai-consulting" className="flex-1">
                    <Button size="sm" className="w-full gap-1 text-xs">
                      Return to consulting <ArrowLeft className="h-3 w-3" />
                    </Button>
                  </a>
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* Input area */}
      {!completed && (
        <div className="flex-shrink-0 border-t bg-white">
          <div className="mx-auto max-w-3xl px-4 py-3">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe your situation..."
                disabled={sending}
                className="flex-1 rounded-full border border-input bg-muted/30 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
              />
              <Button
                size="icon"
                className="h-10 w-10 rounded-full"
                onClick={sendMessage}
                disabled={!input.trim() || sending}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
            <div className="mt-2 text-center">
              <a
                href="/cfa/ai-consulting#intake-form"
                className="text-[10px] text-muted-foreground transition-colors hover:text-primary hover:underline"
              >
                Prefer a form instead? →
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

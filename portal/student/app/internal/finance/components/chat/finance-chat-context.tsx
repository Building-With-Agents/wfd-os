"use client"

// Finance Cockpit chat state — single source of truth for the broad-chat
// surface (Surface 1 in agents/finance/design/chat_spec.md). Wraps the
// cockpit; BroadChat consumes it. The drill-chat surface (Surface 2,
// step 5) reuses this context for the "→ Ask in broad chat" handoff:
// it calls setInputValue + setCollapsed(false) + requestInputFocus().
//
// State lives here (not in BroadChat) so the panel can collapse without
// losing messages or input draft, and so DrillChat can prepopulate from
// across the React tree without imperative refs.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

export type ChatRole = "user" | "assistant"

export interface ChatMessage {
  role: ChatRole
  content: string
  /** Set to true when a turn fails. The renderer shows a retry button. */
  error?: boolean
}

interface FinanceChatContextValue {
  messages: ChatMessage[]
  sessionId: string | null
  loading: boolean
  inputValue: string
  setInputValue: (value: string) => void
  /** Send the supplied text. If empty/whitespace, no-op. */
  sendMessage: (text: string) => Promise<void>
  /** Wipe messages and start a fresh session id on the next send. */
  clearConversation: () => void
  /** Persisted to localStorage. Default: expanded. */
  collapsed: boolean
  setCollapsed: (value: boolean) => void
  /** Bumped each time a caller wants the input focused. BroadChat watches
   *  this via useEffect and calls input.focus() on every increment. */
  focusToken: number
  requestInputFocus: () => void
}

const FinanceChatContext = createContext<FinanceChatContextValue | null>(null)

const ASSISTANT_API = "/api/assistant/chat"
const USER_ROLE = "krista"
const COLLAPSE_STORAGE_KEY = "wfdos:finance-chat:collapsed"

export function FinanceChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [inputValue, setInputValue] = useState("")
  const [focusToken, setFocusToken] = useState(0)

  // Initialize collapsed=false on the server so SSR matches first paint;
  // hydrate from localStorage in an effect to avoid mismatch warnings.
  const [collapsed, setCollapsedState] = useState(false)
  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(COLLAPSE_STORAGE_KEY)
      if (stored === "1") setCollapsedState(true)
    } catch {
      // localStorage may be unavailable (privacy mode); ignore.
    }
  }, [])
  const setCollapsed = useCallback((value: boolean) => {
    setCollapsedState(value)
    try {
      window.localStorage.setItem(COLLAPSE_STORAGE_KEY, value ? "1" : "0")
    } catch {
      // ignore
    }
  }, [])

  const requestInputFocus = useCallback(() => {
    setFocusToken((n) => n + 1)
  }, [])

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || loading) return

      setMessages((prev) => [...prev, { role: "user", content: trimmed }])
      setInputValue("")
      setLoading(true)

      try {
        const res = await fetch(ASSISTANT_API, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            agent_type: "finance",
            message: trimmed,
            session_id: sessionId,
            user_role: USER_ROLE,
            context: { scope: "cockpit-broad", user: USER_ROLE },
          }),
        })
        const data = await res.json().catch(() => null)
        if (!res.ok || !data) {
          const detail = data?.detail ?? `HTTP ${res.status}`
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: `Couldn't answer that — ${detail}.`, error: true },
          ])
          return
        }
        if (data.session_id) setSessionId(data.session_id)
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.response || "(no response)" },
        ])
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err)
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Couldn't answer that — ${msg}.`, error: true },
        ])
      } finally {
        setLoading(false)
      }
    },
    [loading, sessionId],
  )

  const clearConversation = useCallback(() => {
    setMessages([])
    setSessionId(null)
    setInputValue("")
  }, [])

  const value = useMemo<FinanceChatContextValue>(
    () => ({
      messages,
      sessionId,
      loading,
      inputValue,
      setInputValue,
      sendMessage,
      clearConversation,
      collapsed,
      setCollapsed,
      focusToken,
      requestInputFocus,
    }),
    [
      messages,
      sessionId,
      loading,
      inputValue,
      sendMessage,
      clearConversation,
      collapsed,
      setCollapsed,
      focusToken,
      requestInputFocus,
    ],
  )

  return (
    <FinanceChatContext.Provider value={value}>
      {children}
    </FinanceChatContext.Provider>
  )
}

export function useFinanceChat(): FinanceChatContextValue {
  const ctx = useContext(FinanceChatContext)
  if (!ctx) {
    throw new Error("useFinanceChat must be used inside <FinanceChatProvider>")
  }
  return ctx
}

"use client"

import { useEffect, useRef, useState } from "react"
import { apiFetch } from "@/lib/fetch"
import {
  DollarSign,
  Database,
  AlertTriangle,
  FileText,
  MessageSquare,
  Send,
  Loader2,
  RefreshCw,
  CheckCircle2,
  XCircle,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import type { QbStatus, TransactionSummary, ComplianceFlag } from "./page"

const ASSISTANT_API = "/api/assistant"
const GC_API = "/api/grant-compliance"

interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

const STARTER_PROMPTS = [
  "What's my QB connection status?",
  "Show me the last 10 transactions",
  "Any open compliance flags?",
  "What grants are configured?",
  "Anything in Krista's review queue?",
]

function formatCents(cents: number): string {
  return `$${(cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function formatDate(iso: string | null): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—"
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function FinanceClient({
  initialQbStatus,
  initialTransactions,
  initialFlags,
}: {
  initialQbStatus: QbStatus | null
  initialTransactions: TransactionSummary[]
  initialFlags: ComplianceFlag[]
}) {
  const [qbStatus, setQbStatus] = useState<QbStatus | null>(initialQbStatus)
  const [transactions, setTransactions] = useState<TransactionSummary[]>(initialTransactions)
  const [flags, setFlags] = useState<ComplianceFlag[]>(initialFlags)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<string | null>(null)

  // Chat state — mirrors the pattern in bd-client.tsx / jessica/page.tsx
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState("")
  const [chatLoading, setChatLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const refreshAll = async () => {
    const safe = async <T,>(path: string): Promise<T | null> => {
      try {
        const r = await apiFetch(`${GC_API}${path}`)
        if (!r.ok) return null
        return (await r.json()) as T
      } catch {
        return null
      }
    }
    const [s, t, f] = await Promise.all([
      safe<QbStatus>("/qb/status"),
      safe<TransactionSummary[]>("/transactions"),
      safe<ComplianceFlag[]>("/compliance/flags"),
    ])
    if (s) setQbStatus(s)
    if (t) setTransactions(t)
    if (f) setFlags(f)
  }

  const triggerSync = async () => {
    setSyncing(true)
    setSyncResult(null)
    try {
      const r = await apiFetch(`${GC_API}/qb/sync?since=2024-01-01`, { method: "POST" })
      const data = await r.json().catch(() => ({}))
      if (r.ok) {
        setSyncResult(
          `Sync OK — +${data.accounts_added} accounts, +${data.classes_added} classes, +${data.transactions_added} transactions`,
        )
        await refreshAll()
      } else if (r.status === 401) {
        setSyncResult("Access token expired. Re-authorize at /api/grant-compliance/qb/connect")
      } else {
        setSyncResult(`Sync failed: HTTP ${r.status} — ${data.detail ?? ""}`)
      }
    } catch (e: any) {
      setSyncResult(`Sync error: ${e.message}`)
    } finally {
      setSyncing(false)
    }
  }

  const sendPill = (msg: string) => sendMessage(msg, null)
  const sendFollowup = (msg: string) => sendMessage(msg, sessionId)

  async function sendMessage(msg: string, sessionOverride: string | null) {
    if (!msg.trim()) return

    if (sessionOverride === null) {
      setMessages([{ role: "user", content: msg }])
      setSessionId(null)
    } else {
      setMessages((prev) => [...prev, { role: "user", content: msg }])
    }
    setChatLoading(true)
    setChatInput("")

    try {
      const res = await apiFetch(`${ASSISTANT_API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agent_type: "finance",
          message: msg,
          session_id: sessionOverride,
          user_role: "ritu",
        }),
      })
      const data = await res.json()
      setMessages((prev) => [...prev, { role: "assistant", content: data.response || "(no response)" }])
      if (data.session_id) setSessionId(data.session_id)
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${e.message}` }])
    } finally {
      setChatLoading(false)
    }
  }

  const startNewConversation = () => {
    setMessages([])
    setSessionId(null)
  }

  // Derived state
  const realm = qbStatus?.connected_realms[0]
  const accessExpired = realm?.access_expired ?? false
  const openFlags = flags.filter((f) => f.status === "open")
  const blockerFlags = openFlags.filter((f) => f.severity === "blocker").length
  const warningFlags = openFlags.filter((f) => f.severity === "warning").length
  const recentTxns = [...transactions]
    .sort((a, b) => (b.txn_date || "").localeCompare(a.txn_date || ""))
    .slice(0, 10)

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white px-6 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-slate-900">
            Finance · Grant Compliance
          </h1>
          <nav className="flex gap-4 text-sm">
            <a href="/internal" className="text-slate-600 hover:text-slate-900">
              Internal Home
            </a>
            <a href="/internal/bd" className="text-slate-600 hover:text-slate-900">
              BD
            </a>
            <a href="/internal/jessica" className="text-slate-600 hover:text-slate-900">
              Marketing
            </a>
            <a href="/internal/finance" className="font-semibold text-blue-600">
              Finance
            </a>
          </nav>
        </div>
      </div>

      <div className="flex h-[calc(100vh-57px)]">
        {/* LEFT PANEL — 60% — dashboard */}
        <div className="w-3/5 space-y-6 overflow-y-auto p-6">
          {/* QB Connection Status */}
          <Card className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Database className="h-5 w-5 text-blue-600" />
                QuickBooks Connection
              </h2>
              <Button size="sm" variant="ghost" onClick={refreshAll}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>

            {!qbStatus || qbStatus.connected_realms.length === 0 ? (
              <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
                No QB realm connected yet.{" "}
                <a
                  href={`${GC_API}/qb/connect`}
                  className="font-medium text-blue-700 underline"
                >
                  Authorize now
                </a>
              </div>
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  {accessExpired ? (
                    <XCircle className="h-4 w-4 text-red-600" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  )}
                  <span>
                    Realm <code className="rounded bg-slate-100 px-1">{realm!.realm_id}</code>{" "}
                    · env{" "}
                    <Badge
                      className={
                        realm!.environment === "production"
                          ? "bg-red-600"
                          : "bg-slate-500"
                      }
                    >
                      {realm!.environment}
                    </Badge>
                  </span>
                </div>
                <div className="text-slate-600">
                  Access token{" "}
                  {accessExpired ? (
                    <span className="font-medium text-red-600">
                      expired at {formatDateTime(realm!.access_expires_at)} —{" "}
                      <a
                        href={`${GC_API}/qb/connect`}
                        className="underline"
                      >
                        re-authorize
                      </a>
                    </span>
                  ) : (
                    <span>expires {formatDateTime(realm!.access_expires_at)}</span>
                  )}
                </div>
                <div className="text-xs text-slate-500">
                  Refresh token expires {formatDate(realm!.refresh_expires_at)}
                </div>
                <div className="pt-2">
                  <Button
                    size="sm"
                    onClick={triggerSync}
                    disabled={syncing || accessExpired}
                    className="gap-1"
                  >
                    {syncing ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4" />
                    )}
                    {syncing ? "Syncing..." : "Sync since 2024-01-01"}
                  </Button>
                  {syncResult && (
                    <div className="mt-2 text-xs text-slate-700">{syncResult}</div>
                  )}
                </div>
              </div>
            )}
          </Card>

          {/* Sync summary stats */}
          <Card className="p-5">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
              <DollarSign className="h-5 w-5 text-green-600" />
              Mirror Summary
            </h2>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <div className="text-xs text-slate-500">Transactions</div>
                <div className="text-2xl font-bold">{transactions.length}</div>
                <div className="mt-1 text-xs text-slate-500">
                  Bill {transactions.filter((t) => t.qb_type === "Bill").length} ·
                  Purchase {transactions.filter((t) => t.qb_type === "Purchase").length} ·
                  JE {transactions.filter((t) => t.qb_type === "JournalEntry").length}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Total mirrored</div>
                <div className="text-2xl font-bold">
                  {formatCents(
                    transactions.reduce((s, t) => s + (t.amount_cents || 0), 0),
                  )}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-500">Tagged w/ Class</div>
                <div className="text-2xl font-bold">
                  {transactions.filter((t) => t.qb_class_id).length}
                  <span className="text-base text-slate-400">
                    /{transactions.length}
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Open Compliance Flags */}
          <Card className="p-5">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
              <AlertTriangle className="h-5 w-5 text-amber-600" />
              Open Compliance Flags
              {openFlags.length > 0 && (
                <Badge className="ml-2 bg-amber-600">{openFlags.length}</Badge>
              )}
            </h2>
            {openFlags.length === 0 ? (
              <div className="text-sm italic text-slate-500">
                No open flags. Either the Compliance Monitor hasn't been run
                against the current transaction set, or it has and found
                nothing. Run via{" "}
                <code className="rounded bg-slate-100 px-1">
                  POST /compliance/scan
                </code>
                .
              </div>
            ) : (
              <div className="space-y-2">
                <div className="text-xs text-slate-600">
                  {blockerFlags} blocker · {warningFlags} warning
                </div>
                {openFlags.slice(0, 10).map((f) => (
                  <div key={f.id} className="rounded border p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="text-sm font-medium">{f.message}</div>
                        <div className="mt-1 text-xs text-slate-500">
                          {f.rule_citation} · raised {formatDateTime(f.raised_at)}
                        </div>
                      </div>
                      <Badge
                        className={
                          f.severity === "blocker"
                            ? "bg-red-600"
                            : f.severity === "warning"
                              ? "bg-amber-500"
                              : "bg-slate-400"
                        }
                      >
                        {f.severity}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Recent Transactions */}
          <Card className="p-5">
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold">
              <FileText className="h-5 w-5 text-slate-700" />
              Recent Transactions
              <span className="text-sm font-normal text-slate-500">
                (top 10 of {transactions.length})
              </span>
            </h2>
            {recentTxns.length === 0 ? (
              <div className="text-sm italic text-slate-500">
                No transactions mirrored. Trigger a sync from the panel above.
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-600">
                    <th className="py-2 pr-3">Date</th>
                    <th className="py-2 pr-3">Type</th>
                    <th className="py-2 pr-3">Vendor</th>
                    <th className="py-2 pr-3">Memo</th>
                    <th className="py-2 pr-3 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {recentTxns.map((t) => (
                    <tr key={t.id} className="border-b hover:bg-slate-50">
                      <td className="py-2 pr-3 text-xs text-slate-600">
                        {formatDate(t.txn_date)}
                      </td>
                      <td className="py-2 pr-3">
                        <Badge variant="outline" className="text-xs">
                          {t.qb_type}
                        </Badge>
                      </td>
                      <td className="py-2 pr-3">{t.vendor_name ?? "—"}</td>
                      <td className="max-w-[200px] truncate py-2 pr-3 text-xs text-slate-600">
                        {t.memo ?? ""}
                      </td>
                      <td className="py-2 pr-3 text-right font-mono text-xs">
                        {formatCents(t.amount_cents)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>

        {/* RIGHT PANEL — 40% — Finance Assistant Chat */}
        <div className="flex w-2/5 flex-col border-l bg-white">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div>
              <h2 className="flex items-center gap-2 font-semibold">
                <MessageSquare className="h-5 w-5" />
                Finance Assistant
              </h2>
              <div className="text-xs text-slate-500">
                Powered by Gemini · Reads grant_compliance.*
              </div>
            </div>
            {messages.length > 0 && (
              <Button size="sm" variant="ghost" onClick={startNewConversation}>
                New
              </Button>
            )}
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {messages.length === 0 && (
              <div className="space-y-2 text-sm text-slate-500">
                <div>Ask me about grant compliance state:</div>
                <div className="space-y-1">
                  {STARTER_PROMPTS.map((p) => (
                    <button
                      key={p}
                      className="block text-left text-blue-600 hover:underline"
                      onClick={() => sendPill(p)}
                    >
                      → {p}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-sm ${
                    m.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-900"
                  }`}
                >
                  {m.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" /> Thinking...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault()
              sendFollowup(chatInput)
            }}
            className="flex gap-2 border-t p-3"
          >
            <Input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask the Finance Assistant..."
              disabled={chatLoading}
              suppressHydrationWarning
            />
            <Button type="submit" disabled={chatLoading || !chatInput.trim()}>
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}

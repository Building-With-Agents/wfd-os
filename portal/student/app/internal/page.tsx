"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useState } from "react"
import {
  Compass, Mail, Phone, Building, DollarSign, Clock, ArrowRight,
  CheckCircle2, Circle, AlertCircle, ExternalLink, Plus, Settings,
  Users, Briefcase, TrendingUp, Zap, X, FileText, Calendar, RefreshCw,
  MessageSquare, PenTool, Copy, Check, Loader2, Send, Trash2,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

const API_BASE = "/api/consulting"

interface Inquiry {
  id: string
  reference_number: string | null
  organization_name: string
  contact_name: string
  contact_role: string | null
  email: string
  phone: string | null
  project_description: string
  project_description_short: string
  problem_statement: string | null
  project_area: string | null
  timeline: string | null
  budget_range: string | null
  status: string
  notes: string | null
  created_at: string
  apollo_contact_id: string | null
  apollo_sequence_suggested: string | null
}

interface Engagement {
  id: string
  organization_name: string
  project_name: string
  status: string
  progress_pct: number
  next_milestone: string | null
  next_milestone_date: string | null
  cfa_lead: string | null
  cfa_lead_email: string | null
  budget: number
  invoiced_amount: number
  paid_amount: number
  client_access_token: string | null
  portal_token: string
  sharepoint_workspace_url: string | null
  updates_count: number
  last_update_at: string | null
}

interface Pipeline {
  inquiries: Inquiry[]
  engagements: Engagement[]
  stats: {
    new: number
    contacted: number
    scoped: number
    active_projects: number
    closed: number
    pipeline_value: number
    active_value: number
    total_pipeline_value: number
  }
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; border: string }> = {
  new: { label: "NEW", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-300" },
  contacted: { label: "CONTACTED", color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-300" },
  scoping: { label: "SCOPING (AGENT)", color: "text-fuchsia-700", bg: "bg-fuchsia-50", border: "border-fuchsia-300" },
  scoped: { label: "SCOPED", color: "text-purple-700", bg: "bg-purple-50", border: "border-purple-300" },
  active: { label: "ACTIVE", color: "text-green-700", bg: "bg-green-50", border: "border-green-300" },
  closed: { label: "CLOSED", color: "text-slate-600", bg: "bg-slate-50", border: "border-slate-300" },
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const hours = Math.floor((Date.now() - d.getTime()) / 3600000)
  if (hours < 1) return "just now"
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n)
}

function InquiryCard({ inquiry, onUpdate, onView, onConvert, onDelete }: {
  inquiry: Inquiry
  onUpdate: (id: string, newStatus: string) => void
  onView: (i: Inquiry) => void
  onConvert: (id: string) => void
  onDelete: (i: Inquiry) => void
}) {
  const nextStatus: Record<string, { next: string; label: string }> = {
    new: { next: "contacted", label: "Move to Contacted" },
    contacted: { next: "scoping", label: "Fire Scoping Agent" },
  }
  const transition = nextStatus[inquiry.status]

  return (
    <Card className="group relative p-3 space-y-2 text-sm">
      {/* Hover-reveal delete button — top right, subtle */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          onDelete(inquiry)
        }}
        aria-label={`Delete inquiry from ${inquiry.organization_name}`}
        title="Delete inquiry"
        className="absolute right-1 top-1 z-10 rounded p-1 text-slate-300 opacity-0 transition-all hover:bg-red-50 hover:text-red-600 group-hover:opacity-100 focus:opacity-100"
      >
        <X className="h-3.5 w-3.5" />
      </button>

      <div className="flex items-start justify-between gap-2 pr-5">
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-foreground truncate">{inquiry.organization_name}</p>
          <p className="text-xs text-muted-foreground truncate">{inquiry.contact_name}</p>
        </div>
        <span className="text-[10px] text-muted-foreground flex-shrink-0">{formatTime(inquiry.created_at)}</span>
      </div>

      {inquiry.budget_range && (
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <DollarSign className="h-3 w-3" /> {inquiry.budget_range}
        </div>
      )}
      {inquiry.project_area && (
        <Badge variant="outline" className="text-[10px]">{inquiry.project_area}</Badge>
      )}

      <p className="text-xs text-muted-foreground line-clamp-2">{inquiry.project_description_short}</p>

      {/* Apollo status */}
      {inquiry.apollo_contact_id ? (
        <div className="flex items-center gap-1 text-[10px] text-green-700">
          <CheckCircle2 className="h-3 w-3" /> Apollo
          {inquiry.apollo_sequence_suggested && (
            <span className="text-muted-foreground"> · {inquiry.apollo_sequence_suggested.replace(" Sequence", "")}</span>
          )}
        </div>
      ) : (
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
          <Circle className="h-3 w-3" /> Not in Apollo
        </div>
      )}

      {inquiry.status === "scoping" && (
        <div className="flex items-center gap-1 rounded-md bg-fuchsia-100 px-2 py-1 text-[10px] text-fuchsia-800">
          <Zap className="h-3 w-3 animate-pulse" />
          Agent running — creating SharePoint workspace…
        </div>
      )}

      <div className="flex gap-1">
        <Button size="sm" variant="outline" className="h-7 flex-1 text-[10px]" onClick={() => onView(inquiry)}>
          View
        </Button>
        {transition && (
          <Button
            size="sm"
            className="h-7 flex-1 text-[10px]"
            onClick={() => onUpdate(inquiry.id, transition.next)}
          >
            {transition.label} <ArrowRight className="ml-0.5 h-3 w-3" />
          </Button>
        )}
        {inquiry.status === "scoped" && (
          <Button
            size="sm"
            className="h-7 flex-1 text-[10px] bg-green-600 hover:bg-green-700"
            onClick={() => onConvert(inquiry.id)}
          >
            Convert <ArrowRight className="ml-0.5 h-3 w-3" />
          </Button>
        )}
      </div>
    </Card>
  )
}

function StatusColumn({ status, inquiries, onUpdate, onView, onConvert, onDelete }: {
  status: string
  inquiries: Inquiry[]
  onUpdate: (id: string, newStatus: string) => void
  onView: (i: Inquiry) => void
  onConvert: (id: string) => void
  onDelete: (i: Inquiry) => void
}) {
  const cfg = STATUS_CONFIG[status]
  const filtered = inquiries.filter((i) => i.status === status)

  return (
    <div className={`rounded-lg border-2 ${cfg.border} ${cfg.bg} p-3 flex-1 min-w-0`}>
      <div className="mb-3 flex items-center justify-between">
        <h3 className={`text-xs font-bold ${cfg.color}`}>{cfg.label}</h3>
        <Badge variant="secondary" className={`text-xs ${cfg.color}`}>{filtered.length}</Badge>
      </div>
      <div className="space-y-2">
        {filtered.length === 0 && (
          <p className="text-center text-xs text-muted-foreground py-6 italic">No inquiries</p>
        )}
        {filtered.map((inq) => (
          <InquiryCard key={inq.id} inquiry={inq} onUpdate={onUpdate} onView={onView} onConvert={onConvert} onDelete={onDelete} />
        ))}
      </div>
    </div>
  )
}

function ScopingChecklist({ inquiry, onComplete }: { inquiry: Inquiry; onComplete: () => void }) {
  const [checked, setChecked] = useState<string[]>([])
  const items = [
    `Create SharePoint workspace at /sites/Waifinder/Clients/${inquiry.organization_name}`,
    "Create Teams channel for client communications",
    "Schedule 30-min scoping call",
    `Send calendar invite to ${inquiry.email}`,
    "Prepare scoping questions based on project description",
  ]
  const allComplete = checked.length === items.length

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold">Scoping checklist for {inquiry.organization_name}:</h4>
      <div className="space-y-2">
        {items.map((item, i) => (
          <label key={i} className="flex items-start gap-2 cursor-pointer text-sm">
            <input
              type="checkbox"
              checked={checked.includes(item)}
              onChange={(e) => {
                if (e.target.checked) setChecked([...checked, item])
                else setChecked(checked.filter(c => c !== item))
              }}
              className="mt-0.5"
            />
            <span className={checked.includes(item) ? "line-through text-muted-foreground" : ""}>{item}</span>
          </label>
        ))}
      </div>
      <Button disabled={!allComplete} onClick={onComplete} className="w-full">
        Mark all complete &mdash; move to Scoped
      </Button>
    </div>
  )
}

const REFRESH_INTERVAL_MS = 30_000

export default function InternalDashboard() {
  const [data, setData] = useState<Pipeline | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [viewingInquiry, setViewingInquiry] = useState<Inquiry | null>(null)
  const [scopingInquiry, setScopingInquiry] = useState<Inquiry | null>(null)
  const [convertSuccess, setConvertSuccess] = useState<any>(null)
  const [postingUpdateFor, setPostingUpdateFor] = useState<Engagement | null>(null)
  const [signingFor, setSigningFor] = useState<Engagement | null>(null)
  const [copiedTokenId, setCopiedTokenId] = useState<string | null>(null)
  const [deletingInquiry, setDeletingInquiry] = useState<Inquiry | null>(null)
  const [confirmClearTest, setConfirmClearTest] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [toast, setToast] = useState<{ kind: "info" | "error"; msg: string } | null>(null)

  const loadData = (opts: { silent?: boolean } = {}) => {
    if (!opts.silent) setRefreshing(true)
    apiFetch(`${API_BASE}/pipeline`)
      .then(r => r.json())
      .then((d) => {
        setData(d)
        setLastRefreshed(new Date())
      })
      .finally(() => {
        setLoading(false)
        setRefreshing(false)
      })
  }

  useEffect(() => { loadData() }, [])

  // Auto-refresh every 30s while tab is visible and no modal is open.
  useEffect(() => {
    if (!autoRefresh) return
    const paused = !!viewingInquiry || !!scopingInquiry || !!convertSuccess || !!postingUpdateFor || !!signingFor || !!deletingInquiry || confirmClearTest
    if (paused) return
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState === "visible") {
        loadData({ silent: true })
      }
    }, REFRESH_INTERVAL_MS)
    return () => clearInterval(id)
  }, [autoRefresh, viewingInquiry, scopingInquiry, convertSuccess, postingUpdateFor, signingFor, deletingInquiry, confirmClearTest])

  const showToast = (kind: "info" | "error", msg: string) => {
    setToast({ kind, msg })
    setTimeout(() => setToast((t) => (t?.msg === msg ? null : t)), 2500)
  }

  const confirmDelete = async () => {
    if (!deletingInquiry) return
    setDeleting(true)
    try {
      const res = await apiFetch(`${API_BASE}/inquiry/${deletingInquiry.id}`, { method: "DELETE" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      // Optimistic local removal so the card disappears immediately
      setData((prev) => prev
        ? { ...prev, inquiries: prev.inquiries.filter((i) => i.id !== deletingInquiry.id) }
        : prev
      )
      showToast("info", "Inquiry deleted")
      setDeletingInquiry(null)
      loadData({ silent: true })
    } catch (e: any) {
      showToast("error", `Delete failed: ${e.message || "unknown"}`)
    } finally {
      setDeleting(false)
    }
  }

  const clearTestEntries = async () => {
    setDeleting(true)
    try {
      const res = await apiFetch(`${API_BASE}/inquiries/test-entries`, { method: "DELETE" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      showToast("info", `Cleared ${data.deleted_count} test entr${data.deleted_count === 1 ? "y" : "ies"}`)
      setConfirmClearTest(false)
      loadData()
    } catch (e: any) {
      showToast("error", `Clear failed: ${e.message || "unknown"}`)
    } finally {
      setDeleting(false)
    }
  }

  const handleUpdate = async (id: string, newStatus: string) => {
    const res = await apiFetch(`${API_BASE}/inquiry/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    })
    const result = await res.json().catch(() => ({}))
    if (result?.scoping_triggered) {
      // Agent is now running in the background on the API server.
      // Kanban will auto-refresh every 30s and show status move to 'scoped' on success.
      console.log(`[SCOPING] Agent fired for inquiry ${id}`)
    }
    loadData()
  }

  const handleConvert = async (id: string) => {
    const res = await apiFetch(`${API_BASE}/inquiry/${id}/convert`, { method: "POST" })
    const result = await res.json()
    setConvertSuccess(result)
    loadData()
  }

  const completeScoping = async () => {
    if (!scopingInquiry) return
    await apiFetch(`${API_BASE}/inquiry/${scopingInquiry.id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: "scoped" }),
    })
    setScopingInquiry(null)
    loadData()
  }

  if (loading) return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  )

  if (!data) return null

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="border-b border-border bg-white">
        <div className="mx-auto max-w-[1600px] px-4 py-3 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
                <Compass className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-foreground">CFA Consulting Pipeline</h1>
                <p className="text-xs text-muted-foreground">Internal view &mdash; Ritu Bahl</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setAutoRefresh((v) => !v)}
                title={autoRefresh ? "Auto-refresh on (click to pause)" : "Auto-refresh paused (click to resume)"}
                className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${
                  autoRefresh
                    ? "border-green-300 bg-green-50 text-green-700 hover:bg-green-100"
                    : "border-slate-300 bg-slate-50 text-slate-600 hover:bg-slate-100"
                }`}
              >
                <RefreshCw className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} />
                {autoRefresh ? "Live" : "Paused"}
                <span className="text-slate-500">
                  · {lastRefreshed ? `${Math.max(0, Math.floor((Date.now() - lastRefreshed.getTime()) / 1000))}s ago` : "—"}
                </span>
              </button>
              <Button
                size="sm"
                variant="outline"
                className="gap-1 text-xs h-7"
                onClick={() => loadData()}
                disabled={refreshing}
              >
                <RefreshCw className={`h-3 w-3 ${refreshing ? "animate-spin" : ""}`} /> Refresh
              </Button>
              <a href="/cfa/ai-consulting#intake-form">
                <Button size="sm" variant="outline" className="gap-1 text-xs">
                  <Plus className="h-3.5 w-3.5" /> Add manual inquiry
                </Button>
              </a>
              <a href="/cfa/ai-consulting" target="_blank" rel="noopener noreferrer">
                <Button size="sm" variant="outline" className="gap-1 text-xs">
                  <ExternalLink className="h-3.5 w-3.5" /> View public consulting page
                </Button>
              </a>
              <a href="/internal/bd">
                <Button size="sm" variant="outline" className="gap-1 text-xs">
                  <Briefcase className="h-3.5 w-3.5" /> BD Command Center
                </Button>
              </a>
              <a href="/internal/jessica">
                <Button size="sm" variant="outline" className="gap-1 text-xs">
                  <PenTool className="h-3.5 w-3.5" /> Jessica
                </Button>
              </a>
              <a href="/internal/marketing">
                <Button size="sm" variant="outline" className="gap-1 text-xs">
                  <FileText className="h-3.5 w-3.5" /> Marketing
                </Button>
              </a>
              <a href="/internal/finance">
                <Button size="sm" variant="outline" className="gap-1 text-xs">
                  <DollarSign className="h-3.5 w-3.5" /> Finance
                </Button>
              </a>
              <Button size="sm" variant="outline" className="gap-1 text-xs">
                <Settings className="h-3.5 w-3.5" /> Set up Apollo
              </Button>
              <button
                type="button"
                onClick={() => setConfirmClearTest(true)}
                className="text-[10px] text-slate-400 transition-colors hover:text-red-600 hover:underline"
              >
                Clear test entries →
              </button>
            </div>
          </div>

          {/* Stats Row */}
          <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Card className="p-3 border-l-4 border-amber-500">
              <p className="text-xs text-muted-foreground">New inquiries</p>
              <p className="text-xl font-bold">{data.stats.new}</p>
            </Card>
            <Card className="p-3 border-l-4 border-green-500">
              <p className="text-xs text-muted-foreground">Active projects</p>
              <p className="text-xl font-bold">{data.stats.active_projects}</p>
            </Card>
            <Card className="p-3 border-l-4 border-purple-500">
              <p className="text-xs text-muted-foreground">Total pipeline value</p>
              <p className="text-xl font-bold">{formatCurrency(data.stats.total_pipeline_value)}</p>
            </Card>
            <Card className="p-3 border-l-4 border-blue-500">
              <p className="text-xs text-muted-foreground">Placements pending</p>
              <p className="text-xl font-bold">0</p>
            </Card>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1600px] px-4 py-4 sm:px-6">

        {/* Apollo Connected Status */}
        <Card className="mb-4 p-4 border border-green-200 bg-green-50">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-green-900">Apollo connected</p>
              <p className="text-sm text-green-800">
                New inquiries auto-create Apollo contacts. Webhook active for &ldquo;Ready to Scope&rdquo; triggers.
              </p>
            </div>
            <div className="flex gap-1">
              <a href="/api/apollo/stages" target="_blank" rel="noopener noreferrer">
                <Button size="sm" variant="outline" className="flex-shrink-0 gap-1 text-xs text-green-700 border-green-300 hover:bg-green-100">
                  9 stages <ExternalLink className="h-3 w-3" />
                </Button>
              </a>
            </div>
          </div>
        </Card>

        <div className="grid gap-4 lg:grid-cols-3">
          {/* LEFT: Inquiry Kanban (2 cols) */}
          <div className="lg:col-span-2">
            <h2 className="mb-3 text-sm font-semibold text-foreground">Inquiry Pipeline</h2>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {(["new", "contacted", "scoping", "scoped", "closed"] as const).map((status) => (
                <StatusColumn
                  key={status}
                  status={status}
                  inquiries={data.inquiries}
                  onUpdate={handleUpdate}
                  onView={setViewingInquiry}
                  onConvert={handleConvert}
                  onDelete={setDeletingInquiry}
                />
              ))}
            </div>
          </div>

          {/* RIGHT: Active Engagements */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-foreground">Active Engagements</h2>
            <div className="space-y-3">
              {data.engagements.filter(e => e.status === "in_progress").map((e) => {
                const portalPath = `/coalition/client?token=${e.portal_token}`
                const portalAbsolute = typeof window !== "undefined"
                  ? `${window.location.origin}${portalPath}`
                  : portalPath
                const lastUpdate = e.last_update_at ? formatTime(e.last_update_at) : "no updates yet"

                return (
                  <Card key={e.id} className="p-4">
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div className="min-w-0">
                        <p className="font-semibold text-sm truncate">{e.organization_name}</p>
                        <p className="text-xs text-muted-foreground truncate">{e.project_name}</p>
                      </div>
                      <span className="text-sm font-bold text-primary flex-shrink-0">{e.progress_pct}%</span>
                    </div>
                    <Progress value={e.progress_pct} className="h-1.5 mb-2" />

                    <div className="text-xs text-muted-foreground mb-3 space-y-0.5">
                      <div className="flex items-center gap-1">
                        <Zap className="h-3 w-3" /> Next: {e.next_milestone}
                      </div>
                      {e.next_milestone_date && (
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" /> {new Date(e.next_milestone_date).toLocaleDateString()}
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" />
                        {e.updates_count || 0} update{e.updates_count === 1 ? "" : "s"} · {lastUpdate}
                      </div>
                    </div>

                    {/* Client portal link with copy-token action */}
                    <div className="mb-2 rounded-md border border-slate-200 bg-slate-50 px-2 py-1.5">
                      <div className="flex items-center justify-between gap-1">
                        <a
                          href={portalPath}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex min-w-0 items-center gap-1 text-[10px] text-primary hover:underline"
                        >
                          <ExternalLink className="h-3 w-3 flex-shrink-0" />
                          <span className="truncate font-mono">
                            /coalition/client?token={e.portal_token.slice(0, 10)}…
                          </span>
                        </a>
                        <button
                          type="button"
                          onClick={() => {
                            if (typeof navigator !== "undefined") {
                              navigator.clipboard?.writeText(portalAbsolute)
                              setCopiedTokenId(e.id)
                              setTimeout(() => setCopiedTokenId((prev) => (prev === e.id ? null : prev)), 2000)
                            }
                          }}
                          className="flex-shrink-0 rounded px-1 py-0.5 text-[10px] text-slate-500 hover:bg-white hover:text-slate-900"
                          title="Copy full portal URL to clipboard"
                        >
                          {copiedTokenId === e.id ? <Check className="h-3 w-3 text-green-600" /> : <Copy className="h-3 w-3" />}
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-1">
                      <Button
                        size="sm"
                        className="h-7 text-[10px] gap-1"
                        onClick={() => setPostingUpdateFor(e)}
                      >
                        <MessageSquare className="h-3 w-3" /> Post update
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[10px] gap-1"
                        onClick={() => setSigningFor(e)}
                      >
                        <PenTool className="h-3 w-3" /> Send for signing
                      </Button>
                      {e.sharepoint_workspace_url && (
                        <a
                          href={e.sharepoint_workspace_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="col-span-2"
                        >
                          <Button size="sm" variant="ghost" className="w-full h-7 text-[10px] gap-1">
                            <FileText className="h-3 w-3" /> SharePoint workspace
                          </Button>
                        </a>
                      )}
                    </div>
                  </Card>
                )
              })}
              {data.engagements.filter(e => e.status === "in_progress").length === 0 && (
                <p className="text-sm text-muted-foreground italic text-center py-6">No active engagements</p>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Inquiry Detail Modal */}
      <Dialog open={!!viewingInquiry} onOpenChange={(o) => !o && setViewingInquiry(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogTitle className="sr-only">
            {viewingInquiry ? `Inquiry details: ${viewingInquiry.organization_name}` : "Inquiry details"}
          </DialogTitle>
          {viewingInquiry && (
            <div className="space-y-4">
              <div>
                <h2 className="text-xl font-bold">{viewingInquiry.organization_name}</h2>
                <p className="text-sm text-muted-foreground">{viewingInquiry.contact_name}{viewingInquiry.contact_role ? ` · ${viewingInquiry.contact_role}` : ""}</p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="flex items-center gap-2"><Mail className="h-4 w-4" /> {viewingInquiry.email}</div>
                {viewingInquiry.phone && <div className="flex items-center gap-2"><Phone className="h-4 w-4" /> {viewingInquiry.phone}</div>}
                {viewingInquiry.budget_range && <div className="flex items-center gap-2"><DollarSign className="h-4 w-4" /> {viewingInquiry.budget_range}</div>}
                {viewingInquiry.timeline && <div className="flex items-center gap-2"><Clock className="h-4 w-4" /> {viewingInquiry.timeline}</div>}
                {viewingInquiry.project_area && <div className="flex items-center gap-2"><Briefcase className="h-4 w-4" /> {viewingInquiry.project_area}</div>}
                <div className="flex items-center gap-2"><Calendar className="h-4 w-4" /> {formatTime(viewingInquiry.created_at)}</div>
              </div>
              <Separator />
              <div>
                <h3 className="font-semibold text-sm mb-1">Project description</h3>
                <p className="text-sm text-muted-foreground">{viewingInquiry.project_description}</p>
              </div>
              {viewingInquiry.problem_statement && (
                <div>
                  <h3 className="font-semibold text-sm mb-1">Problem statement</h3>
                  <p className="text-sm text-muted-foreground">{viewingInquiry.problem_statement}</p>
                </div>
              )}
              {viewingInquiry.notes && (
                <div>
                  <h3 className="font-semibold text-sm mb-1">Notes</h3>
                  <p className="text-sm text-muted-foreground">{viewingInquiry.notes}</p>
                </div>
              )}
              <div className="flex gap-2 pt-2">
                <a href={`mailto:${viewingInquiry.email}?subject=Your project inquiry`} className="flex-1">
                  <Button className="w-full gap-1" size="sm">
                    <Mail className="h-4 w-4" /> Reply to {viewingInquiry.contact_name.split(" ")[0]}
                  </Button>
                </a>
                <Button variant="outline" size="sm" onClick={() => setViewingInquiry(null)}>Close</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Scoping Checklist Modal */}
      <Dialog open={!!scopingInquiry} onOpenChange={(o) => !o && setScopingInquiry(null)}>
        <DialogContent className="max-w-lg">
          <DialogTitle className="sr-only">Scoping checklist</DialogTitle>
          {scopingInquiry && (
            <ScopingChecklist inquiry={scopingInquiry} onComplete={completeScoping} />
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Inquiry Confirmation */}
      <Dialog open={!!deletingInquiry} onOpenChange={(o) => { if (!o) setDeletingInquiry(null) }}>
        <DialogContent className="max-w-sm">
          <DialogTitle className="sr-only">Confirm inquiry deletion</DialogTitle>
          {deletingInquiry && (
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-red-100">
                  <Trash2 className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-foreground">Delete this inquiry?</h2>
                  <p className="mt-1 text-sm font-medium text-foreground">{deletingInquiry.organization_name}</p>
                  <p className="mt-1 text-xs text-muted-foreground">This cannot be undone.</p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setDeletingInquiry(null)}
                  disabled={deleting}
                >
                  Cancel
                </Button>
                <Button
                  className="flex-1 bg-red-600 hover:bg-red-700"
                  onClick={confirmDelete}
                  disabled={deleting}
                >
                  {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Delete"}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Clear Test Entries Confirmation */}
      <Dialog open={confirmClearTest} onOpenChange={(o) => { if (!o) setConfirmClearTest(false) }}>
        <DialogContent className="max-w-sm">
          <DialogTitle className="sr-only">Confirm clear test entries</DialogTitle>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-red-100">
                <Trash2 className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-foreground">Delete all inquiries marked as test?</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  This will remove entries where organization or email contains &ldquo;test&rdquo;.
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setConfirmClearTest(false)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                className="flex-1 bg-red-600 hover:bg-red-700"
                onClick={clearTestEntries}
                disabled={deleting}
              >
                {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Clear"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 flex animate-in fade-in slide-in-from-bottom-4 items-center gap-2 rounded-lg border bg-white px-4 py-2.5 shadow-lg">
          {toast.kind === "info" ? (
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          ) : (
            <AlertCircle className="h-4 w-4 text-red-600" />
          )}
          <span className="text-sm font-medium text-foreground">{toast.msg}</span>
        </div>
      )}

      {/* Convert Success Modal */}
      <Dialog open={!!convertSuccess} onOpenChange={(o) => !o && setConvertSuccess(null)}>
        <DialogContent className="max-w-lg">
          <DialogTitle className="sr-only">Engagement activated</DialogTitle>
          {convertSuccess && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-6 w-6 text-green-500" />
                <h2 className="text-xl font-bold">Converted to Active Project!</h2>
              </div>
              <div className="rounded-lg bg-muted p-3">
                <p className="text-xs text-muted-foreground">Client Access Token</p>
                <p className="font-mono text-sm">{convertSuccess.client_access_token}</p>
              </div>
              <div>
                <h3 className="font-semibold text-sm mb-2">Next steps:</h3>
                <ul className="space-y-1">
                  {convertSuccess.next_steps?.map((step: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <Circle className="h-3 w-3 mt-1 flex-shrink-0" />
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex gap-2">
                <a href={convertSuccess.client_portal_url} className="flex-1">
                  <Button className="w-full gap-1">
                    <ExternalLink className="h-4 w-4" /> Open client portal
                  </Button>
                </a>
                <Button variant="outline" onClick={() => setConvertSuccess(null)}>Close</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Post Update Modal */}
      <Dialog open={!!postingUpdateFor} onOpenChange={(o) => !o && setPostingUpdateFor(null)}>
        <DialogContent className="max-w-lg">
          <DialogTitle className="sr-only">Post project update</DialogTitle>
          {postingUpdateFor && (
            <PostUpdateForm
              engagement={postingUpdateFor}
              onCancel={() => setPostingUpdateFor(null)}
              onPosted={() => {
                setPostingUpdateFor(null)
                loadData()
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Send for Signing Modal (DocuSeal placeholder) */}
      <Dialog open={!!signingFor} onOpenChange={(o) => !o && setSigningFor(null)}>
        <DialogContent className="max-w-lg">
          <DialogTitle className="sr-only">Send for signing</DialogTitle>
          {signingFor && (
            <SendForSigningPlaceholder
              engagement={signingFor}
              onClose={() => setSigningFor(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

function PostUpdateForm({
  engagement,
  onCancel,
  onPosted,
}: {
  engagement: Engagement
  onCancel: () => void
  onPosted: () => void
}) {
  const [author, setAuthor] = useState("Ritu Bahl")
  const [authorEmail, setAuthorEmail] = useState("ritu@computingforall.org")
  const [updateType, setUpdateType] = useState("progress")
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [clientVisible, setClientVisible] = useState(true)
  const [postToTeams, setPostToTeams] = useState(() => ["milestone", "delivery", "deliverable"].includes(updateType))
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-toggle Teams checkbox based on type
  const handleTypeChange = (t: string) => {
    setUpdateType(t)
    setPostToTeams(["milestone", "delivery", "deliverable"].includes(t))
  }

  const canSubmit = title.trim().length > 0 && body.trim().length > 0 && !submitting

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const res = await apiFetch(`${API_BASE}/engagement/${engagement.id}/updates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          author,
          author_email: authorEmail,
          update_type: updateType,
          title,
          body,
          is_client_visible: clientVisible,
          post_to_teams: postToTeams,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      onPosted()
    } catch (e: any) {
      setError(e.message || "Failed to post update")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-primary" /> Post project update
        </h2>
        <p className="text-xs text-muted-foreground">
          For <span className="font-medium">{engagement.organization_name}</span> — appears on the client portal activity feed.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] font-semibold uppercase text-muted-foreground">Author</label>
          <Input value={author} onChange={(e) => setAuthor(e.target.value)} className="h-8 text-xs" />
        </div>
        <div>
          <label className="text-[10px] font-semibold uppercase text-muted-foreground">Type</label>
          <select
            value={updateType}
            onChange={(e) => handleTypeChange(e.target.value)}
            className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
          >
            <option value="progress">Progress</option>
            <option value="kickoff">Kickoff</option>
            <option value="milestone">Milestone</option>
            <option value="delivery">Delivery</option>
            <option value="note">Note</option>
          </select>
        </div>
      </div>

      <div>
        <label className="text-[10px] font-semibold uppercase text-muted-foreground">Title</label>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Sprint 2 review complete"
          className="h-8 text-xs"
          maxLength={200}
        />
      </div>

      <div>
        <label className="text-[10px] font-semibold uppercase text-muted-foreground">Update body</label>
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="What did we ship this week? What's next? Any blockers or decisions needed from the client?"
          className="min-h-[110px] text-xs"
        />
      </div>

      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <input
          type="checkbox"
          checked={clientVisible}
          onChange={(e) => setClientVisible(e.target.checked)}
        />
        Visible to client (uncheck for internal-only note)
      </label>

      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <input
          type="checkbox"
          checked={postToTeams}
          onChange={(e) => setPostToTeams(e.target.checked)}
        />
        Also post to Teams channel
      </label>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <Button variant="outline" className="flex-1" onClick={onCancel} disabled={submitting}>
          Cancel
        </Button>
        <Button className="flex-1 gap-1" onClick={submit} disabled={!canSubmit}>
          {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
          {submitting ? "Posting…" : "Post update"}
        </Button>
      </div>
    </div>
  )
}

function SendForSigningPlaceholder({
  engagement,
  onClose,
}: {
  engagement: Engagement
  onClose: () => void
}) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold flex items-center gap-2">
          <PenTool className="h-5 w-5 text-primary" /> Send for signing
        </h2>
        <p className="text-xs text-muted-foreground">
          For <span className="font-medium">{engagement.organization_name}</span>
        </p>
      </div>

      <div className="rounded-lg border-2 border-dashed border-amber-300 bg-amber-50 p-4">
        <div className="flex items-start gap-2">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-600" />
          <div className="space-y-2">
            <p className="text-sm font-semibold text-amber-900">
              DocuSeal integration not yet configured
            </p>
            <p className="text-xs text-amber-800">
              When DocuSeal is connected, this button will:
            </p>
            <ul className="list-disc space-y-0.5 pl-4 text-xs text-amber-800">
              <li>Pull the latest proposal .docx from <code className="rounded bg-amber-100 px-1">Clients/{engagement.organization_name.replace(/\s+/g, "")}/Proposal/</code></li>
              <li>Convert it to a fillable DocuSeal template</li>
              <li>Send for signature to the client contact email</li>
              <li>Webhook the signed copy back to SharePoint + update engagement status to <code className="rounded bg-amber-100 px-1">contract_signed</code></li>
            </ul>
            <p className="pt-1 text-xs text-amber-800">
              <strong>To enable:</strong> add <code className="rounded bg-amber-100 px-1">DOCUSEAL_API_KEY</code> and <code className="rounded bg-amber-100 px-1">DOCUSEAL_WEBHOOK_SECRET</code> to <code className="rounded bg-amber-100 px-1">.env</code>,
              then build the <code className="rounded bg-amber-100 px-1">POST /api/consulting/engagement/{"{id}"}/send-for-signing</code> endpoint.
            </p>
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" className="flex-1" onClick={onClose}>
          Close
        </Button>
        <a href="https://www.docuseal.com" target="_blank" rel="noopener noreferrer" className="flex-1">
          <Button variant="ghost" className="w-full gap-1">
            <ExternalLink className="h-3.5 w-3.5" /> DocuSeal docs
          </Button>
        </a>
      </div>
    </div>
  )
}

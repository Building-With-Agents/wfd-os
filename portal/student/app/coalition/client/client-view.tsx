"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"
import {
  Compass, Mail, Calendar, CheckCircle2, Circle, Clock, ArrowRight,
  Users, FileText, DollarSign, TrendingUp, Shield, ExternalLink,
  ChevronRight, Briefcase, Zap, Sparkles, Download, Play, MapPin,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

const API_BASE = "/api"

// File-type icon + friendly label helpers for the live Documents section
function fileIconFor(name: string): string {
  const ext = name.toLowerCase().split(".").pop() || ""
  if (["docx", "doc"].includes(ext)) return "📄"
  if (["xlsx", "xls", "csv"].includes(ext)) return "📊"
  if (["pptx", "ppt"].includes(ext)) return "📽️"
  if (["pdf"].includes(ext)) return "📕"
  if (["txt", "md"].includes(ext)) return "📝"
  if (["mp4", "mov", "webm", "m4a", "mp3"].includes(ext)) return "🎬"
  if (["png", "jpg", "jpeg", "gif", "svg"].includes(ext)) return "🖼️"
  return "📎"
}

function formatFileSize(bytes: number): string {
  if (!bytes) return ""
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatFileDate(iso: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

interface SharePointFile {
  name: string
  folder_path: string
  relative_path: string
  size: number
  last_modified: string
  web_url: string
  download_url: string
  mime_type: string
  id: string
}

function formatUpdateTimestamp(iso: string): string {
  if (!iso) return ""
  const d = new Date(iso)
  const now = Date.now()
  const diffMs = now - d.getTime()
  const diffHours = Math.floor(diffMs / 3_600_000)
  const diffDays = Math.floor(diffMs / 86_400_000)
  if (diffHours < 1) return "just now"
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

function updateTypeColor(type: string): string {
  switch (type) {
    case "kickoff": return "bg-blue-500"
    case "milestone": return "bg-purple-500"
    case "delivery": return "bg-green-500"
    case "note": return "bg-slate-400"
    default: return "bg-primary"
  }
}

interface DocumentsResponse {
  engagement_id: string
  organization_name: string
  safe_name: string
  sharepoint_base_url: string
  total_files: number
  sections: Record<string, SharePointFile[]>
  files: SharePointFile[]
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  scoping: { label: "Scoping", color: "text-slate-600", bg: "bg-slate-100" },
  proposal_sent: { label: "Proposal Sent", color: "text-amber-600", bg: "bg-amber-100" },
  contract_signed: { label: "Contract Signed", color: "text-blue-600", bg: "bg-blue-100" },
  in_progress: { label: "In Progress", color: "text-purple-600", bg: "bg-purple-100" },
  review: { label: "In Review", color: "text-orange-600", bg: "bg-orange-100" },
  complete: { label: "Complete", color: "text-green-600", bg: "bg-green-100" },
}

const MILESTONE_ICON: Record<string, typeof CheckCircle2> = {
  complete: CheckCircle2,
  in_progress: Clock,
  pending: Circle,
}

function formatCurrency(n: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n)
}

function formatDate(d: string | null) {
  if (!d) return "TBD"
  return new Date(d + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export function ClientPortalContent({ initialData, initialDocs }: { initialData?: any; initialDocs?: DocumentsResponse | null }) {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  const [data, setData] = useState<any>(initialData || null)
  const [loading, setLoading] = useState(!initialData)
  const [error, setError] = useState<string | null>(null)
  const [docs, setDocs] = useState<DocumentsResponse | null>(initialDocs || null)
  const [docsLoading, setDocsLoading] = useState(false)

  useEffect(() => {
    if (initialData) return // already have server-fetched data
    if (!token) {
      setError("No access token provided. Use ?token=<client_id> in the URL.")
      setLoading(false)
      return
    }
    apiFetch(`${API_BASE}/consulting/client/${token}`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))

    // Fetch live SharePoint documents in parallel
    setDocsLoading(true)
    apiFetch(`${API_BASE}/consulting/client/${token}/documents`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setDocs(d))
      .catch(() => setDocs(null))
      .finally(() => setDocsLoading(false))
  }, [token])

  if (loading) return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  )

  if (error) return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="max-w-md p-8 text-center">
        <h2 className="text-lg font-semibold text-destructive">Access Error</h2>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
      </Card>
    </div>
  )

  const eng = data.engagement
  const statusCfg = STATUS_CONFIG[eng.status] || STATUS_CONFIG.scoping
  const progress = data.progress
  const budget = data.budget_summary

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
                <Compass className="h-5 w-5 text-primary-foreground" />
              </div>
              <div>
                <span className="text-lg font-bold text-foreground">Waifinder</span>
                <span className="ml-2 text-sm text-muted-foreground">Client Portal</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-foreground">{eng.contact_name}</p>
              <p className="text-xs text-muted-foreground">{eng.organization_name}</p>
            </div>
          </div>
          <div className="mt-3">
            <h1 className="text-2xl font-semibold text-foreground">
              Welcome back, {eng.contact_name?.split(" ")[0]}
            </h1>
            <div className="mt-1 flex items-center gap-3">
              <Badge className={`${statusCfg.bg} ${statusCfg.color} border-0`}>
                {statusCfg.label}
              </Badge>
              <span className="text-sm text-muted-foreground">{eng.project_name}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6">

        {/* What's New Banner — driven by latest engagement update if present */}
        {data.updates && data.updates.length > 0 ? (
          <div className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
            <Sparkles className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
            <div className="min-w-0">
              <p className="text-sm font-medium text-green-800">
                {data.updates[0].title}
              </p>
              <p className="text-xs text-green-700">
                {formatUpdateTimestamp(data.updates[0].update_date)} &middot; {data.updates[0].author}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <Sparkles className="mt-0.5 h-5 w-5 flex-shrink-0 text-slate-500" />
            <div>
              <p className="text-sm font-medium text-slate-700">
                Welcome &mdash; your project workspace is live
              </p>
              <p className="text-sm text-slate-600">
                Updates from your CFA team will appear here as work progresses.
              </p>
            </div>
          </div>
        )}

        {/* Project Activity Feed — latest updates from the CFA team */}
        {data.updates && data.updates.length > 0 && (
          <Card className="p-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="flex items-center gap-2 font-semibold text-foreground">
                <TrendingUp className="h-5 w-5 text-primary" /> Project Updates
              </h3>
              <Badge variant="secondary" className="text-[10px]">
                {data.updates.length} update{data.updates.length === 1 ? "" : "s"}
              </Badge>
            </div>
            <div className="space-y-4">
              {data.updates.map((u: any) => (
                <div key={u.id} className="relative pl-6">
                  <div className={`absolute left-0 top-1.5 h-3 w-3 rounded-full ring-2 ring-white ${updateTypeColor(u.update_type)}`} />
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="text-sm font-semibold text-foreground">{u.title}</p>
                    <span className="flex-shrink-0 text-[10px] text-muted-foreground">
                      {formatUpdateTimestamp(u.update_date)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    <span className="font-medium">{u.author}</span>
                    {u.update_type && u.update_type !== "progress" && (
                      <>
                        {" · "}
                        <span className="uppercase tracking-wide">{u.update_type}</span>
                      </>
                    )}
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-foreground/80">{u.body}</p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Project Status Card */}
        <Card className="overflow-hidden">
          <div className="border-b bg-gradient-to-r from-primary/5 to-primary/10 p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-foreground">{eng.project_name}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{eng.project_description}</p>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-3xl font-bold text-primary">{progress.progress_pct}%</div>
                <p className="text-xs text-muted-foreground">complete</p>
              </div>
            </div>
            <Progress value={progress.progress_pct} className="mt-4 h-2" />
            <div className="mt-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
              <span className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                Started {formatDate(eng.start_date)}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                {progress.days_remaining} days remaining
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                {progress.completed_milestones}/{progress.total_milestones} milestones
              </span>
            </div>
          </div>
          {/* Next Milestone */}
          <div className="flex items-center justify-between bg-amber-50 p-4">
            <div className="flex items-center gap-3">
              <Zap className="h-5 w-5 text-amber-600" />
              <div>
                <p className="text-sm font-medium text-foreground">Next: {eng.next_milestone}</p>
                <p className="text-xs text-muted-foreground">{formatDate(eng.next_milestone_date)}</p>
              </div>
            </div>
            <a href={`mailto:${eng.cfa_lead_email}?subject=${encodeURIComponent(`Check-in request: ${eng.project_name}`)}&body=${encodeURIComponent(`Hi ${eng.cfa_lead?.split(" ")[0]}, I'd like to schedule a check-in on the ${eng.project_name} project. Please suggest some times.`)}`}>
              <Button size="sm" variant="outline" className="gap-1 text-xs">
                Schedule check-in <ArrowRight className="h-3 w-3" />
              </Button>
            </a>
          </div>
        </Card>

        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left: Milestones + Deliverables */}
          <div className="space-y-6 lg:col-span-2">

            {/* Milestones */}
            <Card className="p-5">
              <h3 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
                <TrendingUp className="h-5 w-5 text-primary" /> Project Milestones
              </h3>
              <div className="space-y-1">
                {data.milestones.map((m: any, i: number) => {
                  const Icon = MILESTONE_ICON[m.status] || Circle
                  const isComplete = m.status === "complete"
                  const isCurrent = m.status === "in_progress"
                  return (
                    <div key={i} className={`flex gap-3 rounded-lg p-3 ${isCurrent ? "bg-primary/5 border border-primary/20" : ""}`}>
                      <div className="flex flex-col items-center">
                        <Icon className={`h-5 w-5 flex-shrink-0 ${isComplete ? "text-green-500" : isCurrent ? "text-primary" : "text-muted-foreground/40"}`} />
                        {i < data.milestones.length - 1 && (
                          <div className={`mt-1 w-0.5 flex-1 ${isComplete ? "bg-green-300" : "bg-muted"}`} />
                        )}
                      </div>
                      <div className="flex-1 pb-2">
                        <div className="flex items-center justify-between">
                          <p className={`text-sm font-medium ${isComplete ? "text-foreground" : isCurrent ? "text-primary font-semibold" : "text-muted-foreground"}`}>
                            {m.title}
                          </p>
                          <span className="text-xs text-muted-foreground">
                            {m.completed_date ? formatDate(m.completed_date) : formatDate(m.target_date)}
                          </span>
                        </div>
                        {m.deliverables && (
                          <p className="mt-0.5 text-xs text-muted-foreground">{m.deliverables}</p>
                        )}
                        {isCurrent && (
                          <Badge variant="secondary" className="mt-1.5 text-xs">In Progress</Badge>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>

            {/* Deliverables */}
            <Card className="p-5">
              <h3 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
                <FileText className="h-5 w-5 text-primary" /> Deliverables
              </h3>
              <div className="space-y-2">
                {data.deliverables.map((d: any, i: number) => (
                  <div key={i} className="flex items-center justify-between rounded-md border p-3">
                    <div className="flex items-center gap-3">
                      {d.status === "delivered" ? (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      ) : d.status === "in_progress" ? (
                        <Clock className="h-5 w-5 text-amber-500" />
                      ) : (
                        <Circle className="h-5 w-5 text-muted-foreground/40" />
                      )}
                      <div>
                        <p className="text-sm font-medium text-foreground">{d.title}</p>
                        <p className="text-xs text-muted-foreground">{d.description}</p>
                      </div>
                    </div>
                    {d.delivered_date && (
                      <span className="text-xs text-muted-foreground">{formatDate(d.delivered_date)}</span>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Right sidebar */}
          <div className="space-y-6">

            {/* Your Team */}
            <Card className="p-5">
              <h3 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
                <Users className="h-5 w-5 text-primary" /> Your CFA Team
              </h3>
              <div className="space-y-3">
                {data.team.map((t: any, i: number) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                      {t.avatar_initials}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{t.member_name}</p>
                      <p className="text-xs text-muted-foreground">{t.role}</p>
                    </div>
                  </div>
                ))}
              </div>
              <Separator className="my-4" />
              <div className="space-y-2">
                <a href={`mailto:${eng.cfa_lead_email}`} className="flex items-center gap-2 text-sm text-primary hover:underline">
                  <Mail className="h-4 w-4" /> Email {eng.cfa_lead?.split(" ")[0]}
                </a>
                <Button variant="outline" size="sm" className="w-full gap-1 text-xs">
                  <Calendar className="h-3.5 w-3.5" /> Schedule a meeting
                </Button>
              </div>
            </Card>

            {/* Budget */}
            <Card className="p-5">
              <h3 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
                <DollarSign className="h-5 w-5 text-primary" /> Budget
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Total budget</span>
                  <span className="font-semibold text-foreground">{formatCurrency(budget.total)}</span>
                </div>
                <Progress value={(budget.invoiced / budget.total) * 100} className="h-2" />
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="rounded-md bg-green-50 p-2 text-center">
                    <p className="font-semibold text-green-700">{formatCurrency(budget.paid)}</p>
                    <p className="text-green-600">Paid</p>
                  </div>
                  <div className="rounded-md bg-amber-50 p-2 text-center">
                    <p className="font-semibold text-amber-700">{formatCurrency(budget.outstanding)}</p>
                    <p className="text-amber-600">Outstanding</p>
                  </div>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Invoiced: {formatCurrency(budget.invoiced)}</span>
                  <span>Remaining: {formatCurrency(budget.remaining)}</span>
                </div>
              </div>
            </Card>

            {/* Talent Pipeline */}
            {data.apprentices && data.apprentices.length > 0 && (
              <Card className="p-5">
                <h3 className="mb-1 flex items-center gap-2 font-semibold text-foreground">
                  <Briefcase className="h-5 w-5 text-primary" /> Your talent pipeline
                </h3>
                <p className="mb-4 text-xs text-muted-foreground">
                  The engineers on your project are available to hire when complete
                </p>
                <div className="space-y-3">
                  {data.apprentices.map((a: any, i: number) => (
                    <div key={i} className="rounded-lg border p-3">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-teal-100 text-sm font-semibold text-teal-700">
                          {a.avatar_initials}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-foreground">{a.member_name}</p>
                          <p className="text-xs text-muted-foreground">{a.role}</p>
                        </div>
                      </div>
                      {a.skills && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {a.skills.map((s: string, j: number) => (
                            <Badge key={j} variant="secondary" className="text-xs">{s}</Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                <Separator className="my-3" />
                <a href={`mailto:${eng.cfa_lead_email}?subject=${encodeURIComponent(`Hiring inquiry: ${eng.project_name} team`)}&body=${encodeURIComponent(`Hi ${eng.cfa_lead?.split(" ")[0]}, I'm interested in hiring from the team working on the ${eng.project_name} project.`)}`}>
                  <Button variant="outline" size="sm" className="w-full gap-1 text-xs">
                    Interested in hiring from your team? <ArrowRight className="h-3 w-3" />
                  </Button>
                </a>
              </Card>
            )}

            {/* WSB-specific: Funded Participants + Outcomes + Payroll + Intelligence */}
            {eng.id === "wsb-001" && (
              <>
                {/* Funded Participants */}
                <Card className="p-5">
                  <h3 className="mb-1 flex items-center gap-2 font-semibold text-foreground">
                    <Users className="h-5 w-5 text-primary" /> Your Funded Participants
                  </h3>
                  <p className="mb-4 text-xs text-muted-foreground">
                    Apprentices funded through your workforce development investment. Available for placement anywhere in the US.
                  </p>
                  <div className="space-y-3">
                    {[
                      { name: "Angel Rodriguez", initials: "AR", role: "AI/Data Engineering", skills: ["Python 4/5", "PostgreSQL 3/5", "Claude API 3/5", "FastAPI 4/5"], readiness: 85, projected: "May 2026", salary: "$58-75K" },
                      { name: "Fabian Martinez", initials: "FM", role: "AI/Analytics Engineering", skills: ["Azure OpenAI 4/5", "pgvector 4/5", "FastAPI 4/5", "Python 4/5"], readiness: 82, projected: "May 2026", salary: "$62-78K" },
                    ].map((p) => (
                      <div key={p.name} className="rounded-lg border p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">{p.initials}</div>
                            <div>
                              <p className="text-sm font-medium text-foreground">{p.name}</p>
                              <p className="text-xs text-muted-foreground">{p.role}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-bold text-primary">{p.readiness}%</p>
                            <p className="text-[10px] text-muted-foreground">job ready</p>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {p.skills.map((s) => <Badge key={s} variant="secondary" className="text-[10px]">{s}</Badge>)}
                        </div>
                        <div className="flex justify-between text-[10px] text-muted-foreground">
                          <span>Projected placement: {p.projected}</span>
                          <span>Projected salary: {p.salary}</span>
                        </div>
                        <p className="text-[10px] text-green-700 font-medium">Available anywhere in the US</p>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* Outcomes for Board */}
                <Card className="p-5">
                  <h3 className="mb-3 flex items-center gap-2 font-semibold text-foreground">
                    <TrendingUp className="h-5 w-5 text-primary" /> Outcomes for Your Board
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground">Your Investment</p>
                      <p className="text-lg font-bold text-foreground">$25,500</p>
                      <p className="text-[10px] text-muted-foreground">Fixed price engagement</p>
                    </div>
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground">Projected ROI</p>
                      <p className="text-lg font-bold text-green-600">2 placements</p>
                      <p className="text-[10px] text-muted-foreground">Unemployed to $65K+ employed</p>
                    </div>
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground">Skills Gained</p>
                      <p className="text-sm font-bold text-foreground">Python, AI, PostgreSQL, FastAPI</p>
                      <p className="text-[10px] text-muted-foreground">Production-verified</p>
                    </div>
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground">Job Readiness</p>
                      <p className="text-lg font-bold text-primary">83%</p>
                      <p className="text-[10px] text-muted-foreground">Up from 20% at intake</p>
                    </div>
                  </div>
                </Card>

                {/* Regional Labor Market Intelligence */}
                <Card className="p-5">
                  <h3 className="mb-1 flex items-center gap-2 font-semibold text-foreground">
                    <MapPin className="h-5 w-5 text-primary" /> Your Regional Labor Market
                  </h3>
                  <p className="mb-3 text-xs text-muted-foreground">
                    Powered by the Job Intelligence Engine
                  </p>
                  <div className="space-y-2">
                    {[
                      { skill: "Python", roles: 127, trend: "+18%" },
                      { skill: "SQL", roles: 89, trend: "+12%" },
                      { skill: "Cloud / AWS", roles: 73, trend: "+22%" },
                      { skill: "JavaScript", roles: 67, trend: "+8%" },
                      { skill: "Data Analysis", roles: 54, trend: "+15%" },
                    ].map((s) => (
                      <div key={s.skill} className="flex items-center justify-between rounded-md border px-3 py-2">
                        <span className="text-sm font-medium text-foreground">{s.skill}</span>
                        <div className="text-right">
                          <span className="text-sm font-bold text-primary">{s.roles}</span>
                          <span className="ml-1 text-[10px] text-muted-foreground">open roles</span>
                          <span className="ml-2 text-[10px] text-green-600">{s.trend}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <p className="mt-3 text-xs text-green-700 font-medium">
                    Your funded participants have skills in Python, SQL, and Cloud — qualified for 47 open roles in your region today.
                  </p>
                  <p className="mt-2 text-[10px] text-muted-foreground italic">
                    Interested in the full JIE intelligence subscription? Contact ritu@computingforall.org
                  </p>
                </Card>
              </>
            )}

            {/* Documents — live from SharePoint */}
            <Card className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="flex items-center gap-2 font-semibold text-foreground">
                  <FileText className="h-5 w-5 text-primary" /> Project Documents
                </h3>
                {docs && docs.total_files > 0 && (
                  <Badge variant="secondary" className="text-[10px]">
                    {docs.total_files} file{docs.total_files === 1 ? "" : "s"}
                  </Badge>
                )}
              </div>

              {docsLoading && (
                <p className="text-xs text-muted-foreground italic">Loading from SharePoint…</p>
              )}

              {!docsLoading && docs && docs.total_files === 0 && (
                <div className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-center">
                  <FileText className="mx-auto mb-2 h-6 w-6 text-slate-400" />
                  <p className="text-xs text-muted-foreground">
                    Your SharePoint workspace is ready. Documents will appear here as your project progresses.
                  </p>
                </div>
              )}

              {!docsLoading && docs && docs.total_files > 0 && (
                <div className="space-y-4">
                  {Object.entries(docs.sections).map(([sectionName, files]) => (
                    <div key={sectionName}>
                      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                        {sectionName === "Root" ? "General" : sectionName}
                      </p>
                      <div className="space-y-1.5">
                        {files.map((f) => (
                          <a
                            key={f.id}
                            href={f.web_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-left transition-colors hover:border-primary hover:bg-primary/5"
                          >
                            <div className="flex min-w-0 items-center gap-2">
                              <span className="text-lg flex-shrink-0">{fileIconFor(f.name)}</span>
                              <div className="min-w-0">
                                <p className="truncate text-xs font-medium text-foreground">{f.name}</p>
                                <p className="text-[10px] text-muted-foreground">
                                  {formatFileDate(f.last_modified)}
                                  {f.size ? ` · ${formatFileSize(f.size)}` : ""}
                                </p>
                              </div>
                            </div>
                            <ExternalLink className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
                          </a>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {docs && (
                <a
                  href={docs.sharepoint_base_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-3 block"
                >
                  <Button variant="outline" size="sm" className="w-full gap-1 text-xs">
                    <ExternalLink className="h-3 w-3" /> Open full workspace in SharePoint
                  </Button>
                </a>
              )}
            </Card>

            {/* Quick Actions */}
            <Card className="p-5">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Quick Actions</h3>
              <div className="space-y-2">
                <a href="/showcase">
                  <Button variant="outline" size="sm" className="w-full justify-start gap-2 text-xs">
                    <Users className="h-3.5 w-3.5" /> Browse Talent Showcase
                  </Button>
                </a>
                <Button variant="outline" size="sm" className="w-full justify-start gap-2 text-xs">
                  <FileText className="h-3.5 w-3.5" /> View latest report
                </Button>
                <a href={`mailto:${eng.cfa_lead_email}?subject=Question about ${eng.project_name}`}>
                  <Button variant="outline" size="sm" className="w-full justify-start gap-2 text-xs">
                    <Mail className="h-3.5 w-3.5" /> Contact project lead
                  </Button>
                </a>
              </div>
            </Card>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card py-4 mt-8">
        <NewsletterSubscribe />
        <div className="mx-auto max-w-6xl px-4 text-center">
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <Shield className="h-3.5 w-3.5" />
            <span>Secure client portal</span>
            <span className="text-muted-foreground/40">|</span>
            <span>Waifinder by Computing for All</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default function ClientPortal() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    }>
      <ClientPortalContent />
    </Suspense>
  )
}

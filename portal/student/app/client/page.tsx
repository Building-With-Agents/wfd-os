"use client"

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

const API_BASE = "/api"

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

function ClientPortalContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      setError("No access token provided. Use ?token=<client_id> in the URL.")
      setLoading(false)
      return
    }
    fetch(`${API_BASE}/consulting/client/${token}`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
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

        {/* What's New Banner */}
        <div className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
          <Sparkles className="mt-0.5 h-5 w-5 flex-shrink-0 text-green-600" />
          <div>
            <p className="text-sm font-medium text-green-800">
              Talent Showcase delivered April 4 <CheckCircle2 className="inline h-4 w-4 text-green-600" />
            </p>
            <p className="text-sm text-green-700">
              Sprint 3 underway &mdash; next check-in recommended before April 15
            </p>
          </div>
        </div>

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

            {/* Documents */}
            {data.documents && data.documents.length > 0 && (
              <Card className="p-5">
                <h3 className="mb-3 flex items-center gap-2 font-semibold text-foreground">
                  <FileText className="h-5 w-5 text-primary" /> Documents
                </h3>
                <div className="space-y-2">
                  {data.documents.map((doc: any, i: number) => (
                    <div key={i} className="flex items-center justify-between rounded-md border px-3 py-2">
                      <div className="flex items-center gap-2 min-w-0">
                        {doc.title.includes('Recording') ? (
                          <Play className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                        ) : (
                          <FileText className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                        )}
                        <div className="min-w-0">
                          <p className="truncate text-xs font-medium text-foreground">{doc.title}</p>
                          {doc.delivered_date && (
                            <p className="text-xs text-muted-foreground">{formatDate(doc.delivered_date)}</p>
                          )}
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" className="h-7 text-xs">
                        View
                      </Button>
                    </div>
                  ))}
                </div>
              </Card>
            )}

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

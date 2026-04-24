"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"
import {
  Compass, Mail, GraduationCap, Users, TrendingUp, AlertTriangle,
  CheckCircle2, BarChart3, Briefcase, ArrowRight, Target, BookOpen,
  Shield, Star, Zap,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

const API_BASE = "/api"

function MetricCard({ label, value, subtitle, icon: Icon, color }: {
  label: string; value: string | number; subtitle?: string;
  icon: any; color: string
}) {
  const colorMap: Record<string, string> = {
    blue: "border-blue-500 bg-blue-50 text-blue-600",
    green: "border-green-500 bg-green-50 text-green-600",
    purple: "border-purple-500 bg-purple-50 text-purple-600",
    amber: "border-amber-500 bg-amber-50 text-amber-600",
    teal: "border-teal-500 bg-teal-50 text-teal-600",
  }
  return (
    <Card className={`border-l-4 p-4 ${colorMap[color] || colorMap.blue}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className="mt-1 text-2xl font-bold text-foreground">{typeof value === 'number' ? value.toLocaleString() : value}</p>
          {subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>}
        </div>
        <Icon className="h-5 w-5 opacity-60" />
      </div>
    </Card>
  )
}

function CollegeContent() {
  const searchParams = useSearchParams()
  const token = searchParams.get("token")
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) { setError("No token. Use ?token=bc-001 or ?token=nsc-001"); setLoading(false); return }
    apiFetch(`${API_BASE}/college/dashboard/${token}`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json() })
      .then(setData)
      .catch(e => setError(e.message))
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

  const inst = data.institution
  const pipe = data.pipeline
  const cfa = data.cfa_contact

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
                <span className="ml-2 text-sm text-muted-foreground">College Partner</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium text-foreground">Your CFA contact: {cfa.name}</p>
              <a href={`mailto:${cfa.email}`} className="text-xs text-primary hover:underline">{cfa.email}</a>
            </div>
          </div>
          <div className="mt-3">
            <h1 className="text-2xl font-semibold text-foreground">
              Welcome back, {inst.name}
            </h1>
            <p className="mt-0.5 text-sm text-muted-foreground">Career Services Dashboard</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6">

        {/* Morning Briefing */}
        <Card className="border-l-4 border-primary bg-gradient-to-r from-primary/5 to-background p-5">
          <div className="flex items-start gap-3">
            <Zap className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary" />
            <div>
              <h2 className="font-semibold text-foreground">Morning Briefing</h2>
              <p className="mt-1 text-sm text-muted-foreground">{data.briefing}</p>
            </div>
          </div>
        </Card>

        {/* Graduate Pipeline — Hero Metrics */}
        <div>
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold text-foreground">
            <GraduationCap className="h-5 w-5 text-primary" /> Graduate Pipeline
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="In Pipeline" value={pipe.total_in_pipeline} subtitle="Total graduates tracked" icon={Users} color="blue" />
            <MetricCard label="Parsed & Assessed" value={pipe.parsed_and_assessed} subtitle="Resumes analyzed" icon={CheckCircle2} color="green" />
            <MetricCard label="Matched to Roles" value={pipe.matched_to_roles} subtitle="Score > 70%" icon={Target} color="purple" />
            <MetricCard label="Placed" value={pipe.placed} subtitle={`${pipe.placement_rate}% rate`} icon={Briefcase} color="teal" />
          </div>

          {/* Pipeline funnel */}
          <Card className="mt-4 p-5">
            <h3 className="mb-3 text-sm font-semibold text-muted-foreground">Pipeline by Status</h3>
            <div className="space-y-2">
              {Object.entries(pipe.by_status as Record<string, number>).map(([status, count]) => {
                const pct = pipe.total_in_pipeline > 0 ? (count / pipe.total_in_pipeline) * 100 : 0
                return (
                  <div key={status} className="flex items-center gap-3">
                    <span className="w-20 text-xs font-medium capitalize text-muted-foreground">{status}</span>
                    <div className="flex-1">
                      <div className="h-5 w-full overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary/70 transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                    <span className="w-12 text-right text-sm font-semibold text-foreground">{count}</span>
                  </div>
                )
              })}
            </div>
          </Card>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Top Skills */}
          <Card className="p-5">
            <h3 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
              <Star className="h-5 w-5 text-primary" /> Graduate Skills Profile
            </h3>
            {data.top_skills.length > 0 ? (
              <div className="space-y-2">
                {data.top_skills.map((s: any, i: number) => {
                  const maxCount = data.top_skills[0]?.students || 1
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <span className="w-32 truncate text-sm text-foreground">{s.skill}</span>
                      <div className="flex-1">
                        <div className="h-4 w-full overflow-hidden rounded-full bg-muted">
                          <div className="h-full rounded-full bg-teal-500/70" style={{ width: `${(s.students / maxCount) * 100}%` }} />
                        </div>
                      </div>
                      <span className="w-16 text-right text-xs text-muted-foreground">{s.students} grad{s.students > 1 ? 's' : ''}</span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">Parse more resumes to see graduate skills</p>
            )}
          </Card>

          {/* Skills Gap */}
          <Card className="p-5">
            <h3 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
              <AlertTriangle className="h-5 w-5 text-amber-500" /> Curriculum Gaps
            </h3>
            <p className="mb-3 text-xs text-muted-foreground">Skills employers are asking for that your graduates don&apos;t have yet</p>
            {data.skills_gap.length > 0 ? (
              <div className="space-y-2">
                {data.skills_gap.slice(0, 7).map((g: any, i: number) => (
                  <div key={i} className="flex items-center justify-between rounded-md border border-amber-200 bg-amber-50 px-3 py-2">
                    <span className="text-sm text-foreground">{g.skill}</span>
                    <Badge variant="outline" className="border-amber-300 text-xs text-amber-700">
                      {g.employer_demand} listings
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">No gaps detected</p>
            )}
          </Card>
        </div>

        {/* Employer Demand */}
        <Card className="p-5">
          <h3 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
            <BarChart3 className="h-5 w-5 text-primary" /> Employer Demand for Your Graduates
          </h3>
          <p className="mb-3 text-xs text-muted-foreground">Job titles actively hiring for skills your graduates have</p>
          {data.employer_demand.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {data.employer_demand.map((j: any, i: number) => (
                <div key={i} className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">{j.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {j.listings} listing{j.listings > 1 ? 's' : ''}
                      {j.avg_salary_min && j.avg_salary_max ? ` · $${Math.round(j.avg_salary_min/1000)}K-$${Math.round(j.avg_salary_max/1000)}K` : ''}
                    </p>
                  </div>
                  <Badge variant="secondary" className="text-xs">{j.matching_skills} skill match{j.matching_skills > 1 ? 'es' : ''}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">Parse more graduate resumes to see demand matches</p>
          )}
        </Card>

        {/* Recent Matches */}
        {data.recent_matches.length > 0 && (
          <Card className="p-5">
            <h3 className="mb-4 flex items-center gap-2 font-semibold text-foreground">
              <Target className="h-5 w-5 text-green-500" /> Recent Graduate Matches
            </h3>
            <div className="space-y-2">
              {data.recent_matches.map((m: any, i: number) => (
                <div key={i} className="flex items-center justify-between rounded-md border p-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-green-100 text-sm font-semibold text-green-700">
                      {m.display_name[0]}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{m.display_name}</p>
                      <p className="text-xs text-muted-foreground">Matched: {m.target_role}</p>
                    </div>
                  </div>
                  <Badge className="bg-green-100 text-green-800 border-green-200">Gap: {m.gap_score}%</Badge>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Programs */}
        <Card className="p-5">
          <h3 className="mb-3 flex items-center gap-2 font-semibold text-foreground">
            <BookOpen className="h-5 w-5 text-primary" /> Your Programs in CFA
          </h3>
          <div className="flex flex-wrap gap-2">
            {inst.programs.map((p: string, i: number) => (
              <Badge key={i} variant="outline" className="text-sm">{p}</Badge>
            ))}
          </div>
          <Separator className="my-4" />
          <a href={`mailto:${cfa.email}?subject=Program update: ${inst.name}&body=Hi ${cfa.name.split(' ')[0]}, I'd like to update our program listings in the CFA system.`}>
            <Button variant="outline" size="sm" className="gap-1 text-xs">
              <Mail className="h-3.5 w-3.5" /> Update program listings
            </Button>
          </a>
        </Card>

        {/* CTA */}
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-5 text-center">
          <h3 className="font-semibold text-foreground">Want to improve your graduates&apos; placement outcomes?</h3>
          <p className="mt-1 text-sm text-muted-foreground">Schedule a curriculum alignment review with CFA</p>
          <a href={`mailto:${cfa.email}?subject=Curriculum alignment: ${inst.name}&body=Hi ${cfa.name.split(' ')[0]}, I'd like to discuss aligning our curriculum with employer demand data from the Waifinder platform.`}>
            <Button className="mt-3 gap-2">
              Schedule curriculum review <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </main>

      <footer className="border-t border-border bg-card py-4 mt-8">
        <NewsletterSubscribe />
        <div className="mx-auto max-w-6xl px-4 text-center">
          <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <Shield className="h-3.5 w-3.5" />
            <span>College Partner Portal</span>
            <span className="text-muted-foreground/40">|</span>
            <span>Waifinder by Computing for All</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default function CollegePortal() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    }>
      <CollegeContent />
    </Suspense>
  )
}

"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useState } from "react"
import {
  Compass, ArrowRight, Users, Building, GraduationCap,
  BarChart3, Briefcase, Zap, Globe, ChevronRight, Lightbulb,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

interface Stats {
  total_students: number
  parsed_students: number
  job_listings: number
  total_employers: number
  regions_count: number
}

function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary shadow-md">
            <Compass className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-lg font-bold text-foreground">WA Tech Coalition</span>
        </div>
        <div className="hidden items-center gap-6 md:flex">
          <a href="/cfa/ai-consulting" className="text-sm text-muted-foreground hover:text-foreground">AI Consulting</a>
          <a href="/showcase" className="text-sm text-muted-foreground hover:text-foreground">Talent Showcase</a>
          <a href="/for-employers" className="text-sm text-muted-foreground hover:text-foreground">For Employers</a>
          <a href="/college/login" className="text-sm text-muted-foreground hover:text-foreground">For Colleges</a>
          <a href="#coalition" className="text-sm text-muted-foreground hover:text-foreground">About</a>
          <div className="flex gap-2">
            <a href="/careers">
              <Button size="sm" className="gap-1">Find your tech career <ArrowRight className="h-3.5 w-3.5" /></Button>
            </a>
            <a href="/for-employers">
              <Button size="sm" variant="outline" className="gap-1">Hire tech talent</Button>
            </a>
          </div>
        </div>
      </div>
    </nav>
  )
}

function PathCard({ icon: Icon, iconColor, title, description, cta, href }: {
  icon: any; iconColor: string; title: string; description: string; cta: string; href: string
}) {
  return (
    <a href={href} className="group">
      <Card className="flex h-full flex-col p-6 transition-all hover:border-primary hover:shadow-lg">
        <div className={`mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl ${iconColor}`}>
          <Icon className="h-6 w-6" />
        </div>
        <h3 className="mb-2 text-lg font-semibold text-foreground">{title}</h3>
        <p className="mb-4 flex-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
        <span className="inline-flex items-center gap-1 text-sm font-medium text-primary group-hover:gap-2 transition-all">
          {cta} <ArrowRight className="h-4 w-4" />
        </span>
      </Card>
    </a>
  )
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-foreground sm:text-3xl">{value}</div>
      <div className="mt-1 text-sm text-muted-foreground">{label}</div>
    </div>
  )
}

export default function CoalitionClient({
  initialStats,
  initialCandidateCount,
}: {
  initialStats?: Stats | null
  initialCandidateCount?: number | null
}) {
  const [stats, setStats] = useState<Stats | null>(initialStats || null)
  const [candidateCount, setCandidateCount] = useState<number | null>(
    typeof initialCandidateCount === "number" ? initialCandidateCount : null,
  )

  useEffect(() => {
    // Only fetch client-side if SSR didn't provide stats (fallback for dev/navigation).
    if (!initialStats) {
      apiFetch("/api/stats")
        .then(r => r.ok ? r.json() : null)
        .then(setStats)
        .catch(() => null)
    }
    if (typeof initialCandidateCount !== "number") {
      apiFetch("/api/coalition/candidate-count")
        .then(r => r.ok ? r.json() : null)
        .then((d) => {
          if (d && typeof d.count === "number") setCandidateCount(d.count)
        })
        .catch(() => null)
    }
  }, [initialStats, initialCandidateCount])

  return (
    <div className="min-h-screen bg-background">
      <NavBar />

      {/* Hero */}
      <section className="bg-gradient-to-b from-primary/5 via-primary/3 to-background px-4 py-16 sm:py-24">
        <div className="mx-auto max-w-5xl text-center">
          <h1 className="text-3xl font-bold leading-tight tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Technology and talent,{" "}
            <span className="text-primary">built for the people who need it most.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
            Computing for All connects job seekers, employers, and colleges through the
            Washington Tech Workforce Coalition &mdash; powered by agentic AI.
          </p>
        </div>

        {/* Three Path Cards */}
        <div className="mx-auto mt-12 grid max-w-5xl gap-6 sm:grid-cols-3">
          <PathCard
            icon={Users}
            iconColor="bg-purple-100 text-purple-600"
            title="I'm looking for a tech career"
            description="Browse open roles matched to your skills. Get a personalized gap analysis. Find the training you need."
            cta="Start here"
            href="/careers"
          />
          {/*
            Candidate count is DYNAMIC — pulled from /api/coalition/candidate-count
            (live count of students.resume_parsed = TRUE, the same predicate used
            by the talent showcase listing). When the SSR fetch succeeds the real
            number renders on first paint; the dash placeholder appears only if
            both SSR and client fetches fail.
          */}
          <PathCard
            icon={Building}
            iconColor="bg-teal-100 text-teal-600"
            title="I want to hire tech talent"
            description={`Browse ${
              candidateCount !== null
                ? candidateCount.toLocaleString()
                : stats
                ? stats.parsed_students.toLocaleString()
                : "—"
            } job-ready candidates, skilled in Python, Java, and SQL.`}
            cta="See the talent"
            href="/showcase"
          />
          <PathCard
            icon={GraduationCap}
            iconColor="bg-blue-100 text-blue-600"
            title="I represent a college or training program"
            description="See how your graduates are performing. Get real-time employer demand signals for your curriculum."
            cta="View your dashboard"
            href="/college/login"
          />
        </div>

        {/* Secondary CTA — softer styling than primary PathCards above */}
        <div className="mx-auto mt-8 max-w-3xl">
          <div className="rounded-xl border border-border bg-muted/30 p-6 sm:p-8">
            <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-background">
                  <Lightbulb className="h-5 w-5 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground sm:text-lg">
                    Have a project but don&apos;t know where to start?
                  </h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    CFA staff and apprentices will build it for you. Option to keep the talent when we&apos;re done.
                  </p>
                </div>
              </div>
              <a href="/cfa/ai-consulting" className="flex-shrink-0">
                <Button variant="outline" className="gap-1">
                  Learn More <ArrowRight className="h-4 w-4" />
                </Button>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="border-y border-border bg-card px-4 py-10">
        <div className="mx-auto grid max-w-4xl grid-cols-2 gap-8 sm:grid-cols-4">
          <StatCard
            value={stats ? stats.total_students.toLocaleString() : "4,727"}
            label="students in pipeline"
          />
          <StatCard
            value={stats ? stats.parsed_students.toLocaleString() : "101"}
            label="job-ready candidates"
          />
          <StatCard
            value={stats ? `${Math.round(stats.job_listings / 100) * 100}+` : "2,700+"}
            label="job listings tracked"
          />
          <StatCard
            value={stats ? String(stats.regions_count) : "3"}
            label="regions served"
          />
        </div>
      </section>

      {/* The Coalition */}
      <section id="coalition" className="px-4 py-16">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">
            The Washington Tech Workforce Coalition
          </h2>
          <p className="mt-4 text-muted-foreground">
            Connecting tech employers, community colleges, and workforce organizations
            across Washington State and beyond. Guided by AWS, Microsoft, Accenture, and WTIA.
            Managed by Computing for All.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-6">
            {["AWS", "Microsoft", "Accenture", "WTIA"].map((name) => (
              <div key={name} className="flex h-12 items-center rounded-lg border bg-card px-5 text-sm font-medium text-muted-foreground">
                {name}
              </div>
            ))}
          </div>
          <a href="/for-employers#intake-form">
            <Button variant="outline" className="mt-6 gap-1">
              Join the coalition <ChevronRight className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </section>

      {/* Powered by AI */}
      <section className="bg-primary px-4 py-16 text-primary-foreground">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary-foreground/20">
            <Zap className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold sm:text-3xl">Powered by AI</h2>
          <p className="mt-4 text-primary-foreground/80">
            Every match. Every gap analysis. Every market signal.
            Powered by 14 AI agents running on WFD OS &mdash;
            CFA&apos;s own agentic operating system.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            {["Profile Agent", "Market Intelligence", "Matching Agent", "Career Services",
              "Resume Parser", "Reporting Agent", "College Pipeline", "Orchestrator"
            ].map((agent) => (
              <span key={agent} className="rounded-full bg-primary-foreground/10 px-3 py-1 text-xs font-medium text-primary-foreground/80">
                {agent}
              </span>
            ))}
          </div>
          <a href="/for-employers#proof">
            <Button variant="secondary" className="mt-6 gap-1">
              See what we&apos;ve built <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-card py-10">
        <NewsletterSubscribe />
        <div className="mx-auto max-w-5xl px-4">
          <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
            <div className="flex items-center gap-2">
              <Compass className="h-5 w-5 text-primary" />
              <span className="font-semibold text-foreground">Computing for All</span>
            </div>
            <div className="flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
              <a href="#" className="hover:text-foreground">youth.computingforall.org</a>
              <a href="#" className="hover:text-foreground">careers.computingforall.org</a>
              <a href="/showcase" className="hover:text-foreground">watechcoalition.computingforall.org</a>
              <a href="/for-employers" className="hover:text-foreground">waifinder.computingforall.org</a>
            </div>
          </div>
          <p className="mt-6 text-center text-xs text-muted-foreground">
            &copy; 2026 Computing for All. 501(c)(3) nonprofit. Bellevue, WA.
          </p>
        </div>
      </footer>
    </div>
  )
}

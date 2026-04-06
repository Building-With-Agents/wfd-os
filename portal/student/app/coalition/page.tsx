"use client"

import { useEffect, useState } from "react"
import {
  Compass, ArrowRight, Users, Building, GraduationCap,
  BarChart3, Briefcase, Zap, Globe, ChevronRight, ExternalLink,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"

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
          <a href="/showcase" className="text-sm text-muted-foreground hover:text-foreground">Talent Showcase</a>
          <a href="/for-employers" className="text-sm text-muted-foreground hover:text-foreground">For Employers</a>
          <a href="/college/login" className="text-sm text-muted-foreground hover:text-foreground">For Colleges</a>
          <a href="/cfa/ai-consulting" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            AI Consulting <ExternalLink className="h-3 w-3" />
          </a>
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

export default function HomePage() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    fetch("/api/stats")
      .then(r => r.ok ? r.json() : null)
      .then(setStats)
      .catch(() => null)
  }, [])

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
          <PathCard
            icon={Building}
            iconColor="bg-teal-100 text-teal-600"
            title="I want to hire tech talent"
            description="Browse 101 job-ready candidates. Or give us a project — our apprentices build it, you evaluate, then hire."
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

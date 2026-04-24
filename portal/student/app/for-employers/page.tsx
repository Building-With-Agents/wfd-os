"use client"

import { useEffect, useState } from "react"
import {
  Compass, ArrowRight, Users, Briefcase, CheckCircle2,
  Search, Filter, Target, Zap, ExternalLink, GraduationCap,
  MapPin, Mail,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

// Matches the shape returned by student_api.py::get_stats (routed via
// next.config.mjs /api/stats -> :8001/api/stats). If fetch fails, the
// Stats component falls back to hardcoded defaults so the page still
// renders — same graceful-degradation pattern /coalition uses.
interface PlatformStats {
  total_students: number
  parsed_students: number
  job_listings: number
  total_employers: number
  skills_tracked: number
  regions_count: number
}

function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <a href="/coalition" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <Compass className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-lg font-bold text-foreground">WA Tech Coalition</span>
        </a>
        <div className="hidden items-center gap-6 sm:flex">
          <a href="/showcase" className="text-sm text-muted-foreground hover:text-foreground">Talent Showcase</a>
          <a href="/for-employers" className="text-sm font-medium text-foreground">For Employers</a>
          <a href="/college/login" className="text-sm text-muted-foreground hover:text-foreground">For Colleges</a>
          <a href="/cfa/ai-consulting" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            AI Consulting <ExternalLink className="h-3 w-3" />
          </a>
          <a href="/showcase">
            <Button size="sm" className="gap-1">Browse talent <ArrowRight className="h-3.5 w-3.5" /></Button>
          </a>
        </div>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <section className="bg-gradient-to-b from-primary/5 to-background px-4 py-16 sm:py-24">
      <div className="mx-auto max-w-4xl text-center">
        <Badge className="mb-4 bg-teal-100 text-teal-700 border-teal-200">
          For Employers &middot; Washington Tech Coalition
        </Badge>
        <h1 className="text-3xl font-bold leading-tight text-foreground sm:text-5xl">
          Hire vetted tech talent from Washington&apos;s{" "}
          <span className="text-primary">most diverse pipeline.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          Browse 101 job-ready candidates with parsed resumes, verified skills, and
          live match scores. All pre-screened. All available now.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <a href="/showcase">
            <Button size="lg" className="gap-2 text-base">
              Browse the Talent Showcase <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
          <a href="#how-it-works">
            <Button size="lg" variant="outline" className="gap-2 text-base">
              How it works
            </Button>
          </a>
        </div>
      </div>
    </section>
  )
}

// Fallback numbers used when /api/stats is unreachable — keeps the page
// looking populated during backend outages. These should stay close to
// the last-known live figures so reviewers don't see wildly wrong data
// if the API blips.
const FALLBACK_STATS: PlatformStats = {
  total_students: 4727,
  parsed_students: 160,
  job_listings: 2700,
  total_employers: 1577,
  skills_tracked: 335,
  regions_count: 3,
}

function Stats() {
  const [stats, setStats] = useState<PlatformStats>(FALLBACK_STATS)

  useEffect(() => {
    let cancelled = false
    fetch("/api/stats")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!cancelled && data) setStats(data as PlatformStats)
      })
      .catch(() => {
        // Silent — FALLBACK_STATS already rendered.
      })
    return () => { cancelled = true }
  }, [])

  const display = [
    { value: stats.total_students.toLocaleString(), label: "students in pipeline" },
    { value: stats.parsed_students.toLocaleString(), label: "job-ready candidates" },
    { value: stats.skills_tracked.toLocaleString(), label: "skills tracked" },
    { value: stats.total_employers.toLocaleString(), label: "employers in coalition" },
  ]

  return (
    <section className="border-y border-border bg-card px-4 py-10">
      <div className="mx-auto grid max-w-4xl grid-cols-2 gap-8 sm:grid-cols-4">
        {display.map((s) => (
          <div key={s.label} className="text-center">
            <div className="text-2xl font-bold text-foreground sm:text-3xl">{s.value}</div>
            <p className="mt-1 text-sm text-muted-foreground">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function HowItWorks() {
  const steps = [
    { icon: Search, title: "Browse the showcase", desc: "Filter 101 candidates by skills, location, availability, and track. See live match scores and verified skills." },
    { icon: Target, title: "Shortlist candidates", desc: "Review full profiles with parsed resume data, education history, and work experience." },
    { icon: Mail, title: "Contact through CFA", desc: "All initial contact flows through Computing for All to protect candidate privacy. CFA facilitates the introduction." },
    { icon: CheckCircle2, title: "Interview and hire", desc: "Move forward with candidates who match. No placement fee for coalition members." },
  ]
  return (
    <section id="how-it-works" className="px-4 py-16">
      <div className="mx-auto max-w-5xl">
        <h2 className="mb-10 text-center text-2xl font-bold text-foreground sm:text-3xl">How it works</h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((s, i) => (
            <Card key={i} className="p-5">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <s.icon className="h-5 w-5 text-primary" />
              </div>
              <div className="mb-1 text-xs font-semibold text-primary">STEP {i + 1}</div>
              <h3 className="mb-2 font-semibold text-foreground">{s.title}</h3>
              <p className="text-sm text-muted-foreground">{s.desc}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

function WhyCoalition() {
  return (
    <section className="bg-muted/30 px-4 py-16">
      <div className="mx-auto max-w-5xl">
        <h2 className="mb-10 text-center text-2xl font-bold text-foreground sm:text-3xl">Why coalition talent?</h2>
        <div className="grid gap-6 md:grid-cols-3">
          <Card className="p-6">
            <Users className="mb-3 h-8 w-8 text-teal-600" />
            <h3 className="mb-2 font-semibold text-foreground">Pre-screened</h3>
            <p className="text-sm text-muted-foreground">
              Every candidate has been through CFA&apos;s career services program. Their resumes are parsed,
              their skills are verified, and their profiles are active.
            </p>
          </Card>
          <Card className="p-6">
            <GraduationCap className="mb-3 h-8 w-8 text-purple-600" />
            <h3 className="mb-2 font-semibold text-foreground">Diverse pipeline</h3>
            <p className="text-sm text-muted-foreground">
              Graduates from Bellevue College, North Seattle College, and training programs across
              Washington State &mdash; including underrepresented tech backgrounds.
            </p>
          </Card>
          <Card className="p-6">
            <MapPin className="mb-3 h-8 w-8 text-blue-600" />
            <h3 className="mb-2 font-semibold text-foreground">Local to Washington</h3>
            <p className="text-sm text-muted-foreground">
              Most candidates are based in Seattle, Bellevue, Redmond, and surrounding areas.
              Ready for in-person, hybrid, or remote roles.
            </p>
          </Card>
        </div>
      </div>
    </section>
  )
}

// Bridge to CFA consulting
function ConsultingBridge() {
  return (
    <section className="px-4 py-16">
      <div className="mx-auto max-w-4xl rounded-2xl border-2 border-primary/20 bg-gradient-to-r from-primary/5 to-primary/10 p-8 sm:p-10">
        <div className="flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex-1">
            <Badge className="mb-3 bg-primary/20 text-primary border-primary/30">
              <Zap className="mr-1 h-3 w-3" /> CFA AI Consulting
            </Badge>
            <h2 className="text-2xl font-bold text-foreground sm:text-3xl">
              Ready for more than hiring?
            </h2>
            <p className="mt-2 text-muted-foreground">
              Let CFA build your agentic AI system. The same talent you&apos;re browsing
              will build it &mdash; under expert supervision, at fixed prices.
            </p>
          </div>
          <a href="/cfa/ai-consulting" className="flex-shrink-0">
            <Button size="lg" className="gap-2">
              Tell us about your project <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-border bg-card py-8">
      <div className="mx-auto max-w-6xl px-4 text-center">
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Compass className="h-4 w-4 text-primary" />
          <span>WA Tech Workforce Coalition</span>
          <span className="text-muted-foreground/50">|</span>
          <span>Managed by Computing for All</span>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          watechcoalition.org | info@computingforall.org
        </p>
      </div>
    </footer>
  )
}

export default function ForEmployersPage() {
  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <Hero />
      <Stats />
      <HowItWorks />
      <WhyCoalition />
      <ConsultingBridge />
      <Footer />
    </div>
  )
}

"use client"
import { apiFetch } from "@/lib/fetch"

import { useEffect, useState } from "react"
import {
  Compass, ArrowRight, Heart, Users, MapPin, ExternalLink,
  GraduationCap, Mail, Zap, Sparkles,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
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
    <nav className="sticky top-0 z-50 border-b border-border bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <a href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Compass className="h-4.5 w-4.5 text-primary-foreground" />
          </div>
          <span className="text-lg font-bold text-foreground">Computing for All</span>
        </a>
        <div className="hidden items-center gap-6 md:flex">
          <a href="/cfa/ai-consulting" className="text-sm text-muted-foreground hover:text-foreground">AI Consulting</a>
          <a href="/youth" className="text-sm text-muted-foreground hover:text-foreground">Youth Program</a>
          <a href="/coalition" className="text-sm text-muted-foreground hover:text-foreground">Coalition</a>
          <a href="/resources" className="text-sm text-muted-foreground hover:text-foreground">Resources</a>
          <a href="#about" className="text-sm text-muted-foreground hover:text-foreground">About</a>
          <a href="https://secure.givelively.org/donate/computing-for-all" target="_blank" rel="noopener noreferrer">
            <Button size="sm" variant="outline" className="gap-1">
              <Heart className="h-3.5 w-3.5" /> Donate
            </Button>
          </a>
        </div>
      </div>
    </nav>
  )
}

interface ProgramCardProps {
  icon: any
  accentColor: string  // text color class for icon + badge
  accentBg: string     // bg color for icon container
  badgeText: string
  badgeColor: string   // bg class for badge
  title: string
  description: string
  href: string
  ctaText: string
  subNote?: string
}

function ProgramCard({ icon: Icon, accentColor, accentBg, badgeText, badgeColor, title, description, href, ctaText, subNote }: ProgramCardProps) {
  return (
    <Card className="flex h-full flex-col p-6">
      <div className="mb-4 flex items-start justify-between gap-2">
        <div className={`inline-flex h-12 w-12 items-center justify-center rounded-xl ${accentBg}`}>
          <Icon className={`h-6 w-6 ${accentColor}`} />
        </div>
        <Badge className={`${badgeColor} border-0 text-xs`}>{badgeText}</Badge>
      </div>
      <h3 className="mb-3 text-lg font-semibold text-foreground">{title}</h3>
      <p className="mb-5 flex-1 text-sm leading-relaxed text-muted-foreground">{description}</p>
      <div>
        <a href={href} className={`inline-flex items-center gap-1 text-sm font-semibold hover:underline ${accentColor}`}>
          {ctaText} <ArrowRight className="h-4 w-4" />
        </a>
        {subNote && (
          <p className="mt-2 text-xs text-muted-foreground italic">{subNote}</p>
        )}
      </div>
    </Card>
  )
}

export default function CFAHomePage({ initialStats }: { initialStats?: Stats | null }) {
  const [stats, setStats] = useState<Stats | null>(initialStats || null)

  useEffect(() => {
    if (!initialStats) {
      apiFetch("/api/stats")
        .then((r) => (r.ok ? r.json() : null))
        .then(setStats)
        .catch(() => null)
    }
  }, [initialStats])

  return (
    <div className="min-h-screen bg-white">
      <NavBar />

      {/* Hero */}
      <section className="px-4 py-20 sm:py-28">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold leading-tight tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Technology and talent,{" "}
            <span className="text-primary">built for the people who need it most.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-xl text-muted-foreground">
            Computing for All is a nonprofit building pathways into technology
            through education, community, and AI-powered employment.
          </p>
          <div className="mt-4 flex items-center justify-center gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1"><MapPin className="h-4 w-4" /> Washington State</span>
            <span className="text-muted-foreground/30">|</span>
            <span>Est. 2019</span>
          </div>
          <a href="#programs">
            <Button className="mt-8 gap-2" size="lg">
              Learn about our work <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </section>

      {/* Stats */}
      <section className="border-y border-border bg-card px-4 py-10">
        <div className="mx-auto grid max-w-4xl grid-cols-2 gap-8 sm:grid-cols-4">
          {[
            { value: "2", label: "active deployments" },
            { value: stats ? stats.total_students.toLocaleString() : "4,727", label: "students served" },
            { value: stats ? stats.parsed_students.toLocaleString() : "101", label: "job-ready candidates" },
            { value: stats ? `${Math.round(stats.job_listings / 100) * 100}+` : "2,700+", label: "jobs tracked" },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-3xl font-bold text-foreground">{s.value}</div>
              <p className="mt-1 text-sm text-muted-foreground">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Programs */}
      <section id="programs" className="bg-slate-50 px-4 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-bold text-foreground sm:text-4xl">Our Programs</h2>
            <p className="mt-3 text-lg text-muted-foreground">
              Three programs. One mission. Technology access for everyone.
            </p>
            <p className="mt-1 text-sm text-muted-foreground italic">
              We educate &middot; We connect &middot; We build
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {/* Program 1: AI Consulting (amber) */}
            <ProgramCard
              icon={Zap}
              accentColor="text-amber-700"
              accentBg="bg-amber-100"
              badgeText="Now available"
              badgeColor="bg-green-100 text-green-700"
              title="AI Consulting"
              description="CFA builds agentic AI systems for coalition employers. Fixed price. Expert supervision from our own apprentice pipeline. Try before you hire."
              href="/cfa/ai-consulting"
              ctaText="Tell us about your project"
            />

            {/* Program 2: Talent Network (purple) */}
            <ProgramCard
              icon={Users}
              accentColor="text-purple-700"
              accentBg="bg-purple-100"
              badgeText="Sector partnership"
              badgeColor="bg-purple-100 text-purple-700"
              title="Washington Tech Talent Network"
              description={`Connecting tech employers, community colleges, and job seekers across Washington State. Browse ${stats ? stats.parsed_students.toLocaleString() : "101"} job-ready candidates, access real-time labor market intelligence, and find your next tech role.`}
              href="/coalition"
              ctaText="Visit the Talent Network"
              subNote="Includes the WA Tech Career Accelerator — job placement for trained tech talent"
            />

            {/* Program 3: Youth Education Program (teal) */}
            <div id="youth">
              <ProgramCard
                icon={GraduationCap}
                accentColor="text-teal-700"
                accentBg="bg-teal-100"
                badgeText="Free program · Ages 16-24"
                badgeColor="bg-teal-100 text-teal-700"
                title="Youth Education Program"
                description="Free full stack web development education for Washington State residents aged 16-24 who need financial assistance. From zero to job-ready in six levels."
                href="/youth"
                ctaText="Learn about the Youth Program"
              />
            </div>
          </div>
        </div>
      </section>

      {/* About */}
      <section id="about" className="px-4 py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="mb-6 text-2xl font-bold text-foreground sm:text-3xl">About CFA</h2>
          <div className="space-y-4 text-left text-muted-foreground">
            <p>
              Computing for All was founded on a simple belief &mdash; technology should work for
              everyone, not just those who can already afford access. We run three programs that
              together form a complete pathway from first exposure to meaningful employment in tech.
            </p>
            <p>
              We are a 501(c)(3) nonprofit based in Bellevue, Washington. Our Youth Program gives
              young people free coding education. Our Coalition connects graduates with employers
              across Washington State. Our AI Consulting practice builds real systems for real clients
              &mdash; and every engagement creates apprenticeship opportunities.
            </p>
          </div>
        </div>
      </section>

      {/* Coalition Partners */}
      <section className="bg-slate-50 px-4 py-16">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="mb-6 text-xl font-bold text-foreground sm:text-2xl">Coalition Partners</h2>
          <div className="flex flex-wrap items-center justify-center gap-6">
            {["AWS", "Microsoft", "Accenture", "WTIA"].map((name) => (
              <div
                key={name}
                className="flex h-12 items-center rounded-lg border bg-white px-5 text-sm font-medium text-muted-foreground"
              >
                {name}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Donate */}
      <section className="bg-primary px-4 py-16 text-primary-foreground">
        <div className="mx-auto max-w-2xl text-center">
          <Heart className="mx-auto mb-4 h-8 w-8" />
          <h2 className="text-2xl font-bold sm:text-3xl">Support our mission</h2>
          <p className="mt-3 text-primary-foreground/80">
            Every dollar helps build pathways into technology for people who need it most.
            Your donation supports free training, career services, and placement for
            underrepresented communities.
          </p>
          <a
            href="https://secure.givelively.org/donate/computing-for-all"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="secondary" size="lg" className="mt-6 gap-2">
              Donate to Computing for All <ExternalLink className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-white py-12">
        <NewsletterSubscribe />
        <Separator className="mb-8" />
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="grid gap-8 md:grid-cols-3">
            {/* Youth Program column */}
            <div>
              <div className="mb-3 flex items-center gap-2">
                <GraduationCap className="h-4 w-4 text-teal-600" />
                <h3 className="text-sm font-semibold text-foreground">Youth Program</h3>
              </div>
              <p className="text-sm text-muted-foreground">Computing for All Youth Program</p>
              <a href="/youth" className="mt-1 block text-xs text-teal-600 hover:underline">
                youth.computingforall.org
              </a>
              <p className="mt-2 text-xs text-muted-foreground">
                Free coding education, ages 16-24
              </p>
              <p className="mt-1 text-xs text-muted-foreground italic">Led by Leslie</p>
            </div>

            {/* Coalition column */}
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Users className="h-4 w-4 text-purple-600" />
                <h3 className="text-sm font-semibold text-foreground">WA Tech Coalition</h3>
              </div>
              <p className="text-sm text-muted-foreground">Washington Tech Workforce Coalition</p>
              <a href="/coalition" className="mt-1 block text-xs text-purple-600 hover:underline">
                watechcoalition.computingforall.org
              </a>
              <p className="mt-2 text-xs text-muted-foreground">
                Talent platform, employer connections, career acceleration
              </p>
            </div>

            {/* AI Consulting column */}
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-600" />
                <h3 className="text-sm font-semibold text-foreground">AI Consulting</h3>
              </div>
              <p className="text-sm text-muted-foreground">CFA AI Consulting</p>
              <a href="/cfa/ai-consulting" className="mt-1 block text-xs text-amber-600 hover:underline">
                computingforall.org/ai-consulting
              </a>
              <p className="mt-2 text-xs text-muted-foreground">
                Agentic AI for coalition employers
              </p>
            </div>
          </div>

          <Separator className="my-8" />

          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-between">
            <div className="flex items-center gap-2">
              <Compass className="h-4 w-4 text-primary" />
              <span className="text-xs font-semibold text-foreground">Computing for All</span>
              <span className="text-xs text-muted-foreground">| 501(c)(3) nonprofit | Bellevue, WA</span>
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <a href="#about" className="hover:text-foreground">About</a>
              <a href="mailto:info@computingforall.org" className="hover:text-foreground">Contact</a>
              <a href="https://secure.givelively.org/donate/computing-for-all" target="_blank" rel="noopener noreferrer" className="hover:text-foreground">Donate</a>
              <a href="#" className="hover:text-foreground">Privacy</a>
            </div>
          </div>

          <p className="mt-4 text-center text-xs text-muted-foreground">
            &copy; 2026 Computing for All. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  )
}

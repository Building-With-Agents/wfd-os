"use client"
import { apiFetch } from "@/lib/fetch"

import { useState } from "react"
import {
  Compass, ArrowRight, Check, X, Zap, Users, Shield, TrendingUp,
  Building, Briefcase, UserCheck, RotateCw, Mail, Phone, ExternalLink,
  ChevronRight, Github, Star, Clock, DollarSign, Send, CheckCircle2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

const PROJECT_AREAS = [
  "Labor market intelligence",
  "Talent matching and placement",
  "Operations automation",
  "Customer experience AI",
  "Data pipeline and analytics",
  "Something else",
]

const TIMELINES = [
  "Start immediately",
  "Within 30 days",
  "Within 60 days",
  "Just exploring",
]

const BUDGETS = [
  "Under $10K",
  "$10K - $25K",
  "$25K - $50K",
  "$50K+",
  "Not sure - let's talk",
]

function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
            <Compass className="h-5 w-5 text-primary-foreground" />
          </div>
          <span className="text-lg font-bold text-foreground">WA Tech Coalition</span>
        </div>
        <div className="hidden items-center gap-6 sm:flex">
          <a href="/cfa/ai-consulting" className="text-sm text-muted-foreground hover:text-foreground">AI Consulting</a>
          <a href="/showcase" className="text-sm text-muted-foreground hover:text-foreground">Talent Showcase</a>
          <a href="/for-employers" className="text-sm font-medium text-foreground">For Employers</a>
          <a href="#intake-form">
            <Button size="sm" className="gap-1">Schedule a conversation <ArrowRight className="h-3.5 w-3.5" /></Button>
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
        <h1 className="text-3xl font-bold leading-tight text-foreground sm:text-5xl">
          Your sector is being transformed by AI.{" "}
          <span className="text-primary">We can help you lead that transformation.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          CFA builds agentic AI systems for coalition employers &mdash; using apprentices from our own
          talent pipeline, under expert supervision, at a price that works for mid-market organizations.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <a href="#intake-form">
            <Button size="lg" className="gap-2 text-base">
              Tell us about your project <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
          <a href="#proof">
            <Button size="lg" variant="outline" className="gap-2 text-base">
              See what we&apos;ve built <ChevronRight className="h-4 w-4" />
            </Button>
          </a>
        </div>
        <p className="mt-6 text-sm text-muted-foreground">
          Trusted by coalition employers across Washington State and Texas
        </p>
      </div>
    </section>
  )
}

function ProblemSection() {
  return (
    <section className="px-4 py-16">
      <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-2">
        <Card className="border-green-200 bg-green-50/50 p-6">
          <h3 className="mb-4 text-lg font-semibold text-green-800">The opportunity</h3>
          <p className="mb-4 text-sm text-green-700">Agentic AI will transform your operations:</p>
          <ul className="space-y-3">
            {["Workflows that run themselves", "Customer experiences that delight",
              "Real-time intelligence for decisions", "Scale without headcount growth"].map((item) => (
              <li key={item} className="flex items-center gap-2 text-sm text-green-800">
                <Check className="h-4 w-4 flex-shrink-0 text-green-600" />
                {item}
              </li>
            ))}
          </ul>
        </Card>
        <Card className="border-red-200 bg-red-50/50 p-6">
          <h3 className="mb-4 text-lg font-semibold text-red-800">The barrier</h3>
          <p className="mb-4 text-sm text-red-700">But most organizations face the same wall:</p>
          <ul className="space-y-3">
            {["Enterprise firms charge enterprise prices", "Generic AI tools aren't enough",
              "AI talent is nearly impossible to hire", "Junior hires are too risky"].map((item) => (
              <li key={item} className="flex items-center gap-2 text-sm text-red-800">
                <X className="h-4 w-4 flex-shrink-0 text-red-500" />
                {item}
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <p className="mx-auto mt-8 max-w-2xl text-center text-lg font-semibold text-foreground">
        CFA was built to break down exactly this barrier.
      </p>
    </section>
  )
}

function OfferSection() {
  const cards = [
    { icon: Zap, title: "We build it", color: "text-purple-600 bg-purple-100",
      desc: "CFA designs and builds custom agentic AI systems for your specific operations. Not generic tools. Not off-the-shelf software. Systems built around your data, your workflows, your needs." },
    { icon: Users, title: "Apprentices deliver it", color: "text-teal-600 bg-teal-100",
      desc: "Our apprentices \u2014 trained specifically in agentic AI \u2014 build under expert supervision. You see every milestone. You give feedback throughout. Nothing ships without your approval." },
    { icon: TrendingUp, title: "You decide what comes next", color: "text-blue-600 bg-blue-100",
      desc: "When the project is done, three paths are open. Hire the talent. Keep them as managed services. Or bring us back for the next project." },
  ]

  return (
    <section className="bg-muted/30 px-4 py-16">
      <div className="mx-auto max-w-6xl">
        <h2 className="mb-8 text-center text-2xl font-bold text-foreground sm:text-3xl">Here&apos;s what we do</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {cards.map((card) => (
            <Card key={card.title} className="p-6">
              <div className={`mb-4 inline-flex rounded-lg p-2.5 ${card.color}`}>
                <card.icon className="h-6 w-6" />
              </div>
              <h3 className="mb-2 text-lg font-semibold text-foreground">{card.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{card.desc}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

function DeRiskSection() {
  const steps = [
    { num: "1", title: "Tell us your problem", desc: "Describe what you need in plain English. No technical jargon required. We translate business problems into agentic AI solutions." },
    { num: "2", title: "We scope and price it", desc: "CFA scopes your project, defines deliverables, and gives you a fixed price before anything starts. No surprises. No scope creep." },
    { num: "3", title: "We build it", desc: "Apprentices deliver under expert supervision. Weekly milestones. You see progress at every stage. You give feedback throughout." },
    { num: "4", title: "You decide", desc: "Hire the talent. Keep as managed services. Come back for the next project. Any path works." },
  ]

  return (
    <section className="px-4 py-16">
      <div className="mx-auto max-w-4xl">
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">Not sure if AI will work for your organization?</h2>
          <p className="mt-2 text-muted-foreground">Most organizations aren&apos;t. That uncertainty is exactly why we work the way we do.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {steps.map((step) => (
            <Card key={step.num} className="flex gap-4 p-5">
              <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
                {step.num}
              </div>
              <div>
                <h3 className="font-semibold text-foreground">{step.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{step.desc}</p>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

function OutcomesSection() {
  const outcomes = [
    { title: "Hire", color: "border-green-300 bg-green-50", icon: UserCheck, iconColor: "text-green-600",
      desc: "The apprentice delivered. You want them full time. CFA places them with you. You get a proven hire \u2014 they already know your systems.",
      detail: "Placement fee: 15-20% first year salary" },
    { title: "Managed Services", color: "border-purple-300 bg-purple-50", icon: Shield, iconColor: "text-purple-600",
      desc: "System is built and running. You want CFA to keep it running. Monthly managed services fee. Same team that built it maintains it.",
      detail: "Monthly retainer pricing" },
    { title: "Next Project", color: "border-teal-300 bg-teal-50", icon: RotateCw, iconColor: "text-teal-600",
      desc: "That worked. You have another problem. CFA team already knows your org. Next project scoped and started faster.",
      detail: "Repeat engagement pricing" },
  ]

  return (
    <section className="bg-muted/30 px-4 py-16">
      <div className="mx-auto max-w-6xl">
        <h2 className="mb-8 text-center text-2xl font-bold text-foreground sm:text-3xl">Three ways this ends well</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {outcomes.map((o) => (
            <Card key={o.title} className={`border-2 p-6 ${o.color}`}>
              <o.icon className={`mb-3 h-8 w-8 ${o.iconColor}`} />
              <h3 className="mb-2 text-lg font-semibold text-foreground">{o.title}</h3>
              <p className="mb-3 text-sm text-muted-foreground">{o.desc}</p>
              <Badge variant="secondary" className="text-xs">{o.detail}</Badge>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

function ProofSection() {
  return (
    <section id="proof" className="bg-primary px-4 py-16 text-primary-foreground">
      <div className="mx-auto max-w-4xl text-center">
        <h2 className="mb-8 text-2xl font-bold sm:text-3xl">We built it for ourselves first</h2>
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="border-primary-foreground/20 bg-primary-foreground/10 p-6 text-left">
            <h3 className="mb-2 font-semibold text-primary-foreground">WFD OS</h3>
            <p className="text-sm text-primary-foreground/80">
              CFA&apos;s own workforce development operating system. 14 AI agents managing 4,727 students,
              1,577 employers, 5,061 skills. Built by Ritu + Claude in 4 weeks.
            </p>
          </Card>
          <Card className="border-primary-foreground/20 bg-primary-foreground/10 p-6 text-left">
            <h3 className="mb-2 font-semibold text-primary-foreground">JIE for Borderplex</h3>
            <p className="text-sm text-primary-foreground/80">
              Job Intelligence Engine for Workforce Solutions Borderplex (El Paso, TX).
              2,700+ job listings analyzed. Top skills, demand trends, talent pipeline matching.
            </p>
          </Card>
        </div>
        <a href="https://github.com/Building-With-Agents/watechcoalition" target="_blank" rel="noopener noreferrer">
          <Button variant="secondary" className="mt-6 gap-2">
            <Github className="h-4 w-4" /> View our code on GitHub
          </Button>
        </a>
      </div>
    </section>
  )
}

function TalentConnection() {
  return (
    <section className="px-4 py-16">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="mb-4 text-2xl font-bold text-foreground sm:text-3xl">
          The people who build your system are available to hire
        </h2>
        <p className="text-muted-foreground">
          No other consulting firm can say this: the apprentices who build your system know it better
          than anyone &mdash; because they built it. When the project is done, they can join your team
          full time, continue as managed services, or both. The talent comes with the work.
        </p>
        <a href="/showcase">
          <Button className="mt-6 gap-2" size="lg">
            Browse the Talent Showcase <ArrowRight className="h-4 w-4" />
          </Button>
        </a>
      </div>
    </section>
  )
}

function IntakeForm() {
  const [formData, setFormData] = useState({
    organization_name: "", contact_name: "", contact_role: "",
    email: "", phone: "", is_coalition_member: false,
    project_description: "", problem_statement: "", success_criteria: "",
    project_area: "", timeline: "", budget_range: "",
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)

    try {
      const res = await apiFetch("/api/consulting/inquire", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      })
      if (!res.ok) throw new Error("Failed to submit")
      setSubmitted(true)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const update = (field: string, value: any) => setFormData((prev) => ({ ...prev, [field]: value }))

  if (submitted) {
    return (
      <section id="intake-form" className="bg-muted/30 px-4 py-16">
        <div className="mx-auto max-w-xl rounded-xl border bg-card p-8 text-center shadow-sm">
          <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-green-500" />
          <h2 className="text-2xl font-bold text-foreground">Project submitted!</h2>
          <p className="mt-2 text-muted-foreground">We&apos;ll reach out within 24 hours to schedule a scoping conversation.</p>
          <div className="mt-6 space-y-2 text-left">
            {["CFA reviews your project description", "We schedule a 30-minute scoping call",
              "You receive a fixed-price proposal", "You approve before anything starts"].map((step) => (
              <div key={step} className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="h-4 w-4 text-green-500" /> {step}
              </div>
            ))}
          </div>
        </div>
      </section>
    )
  }

  return (
    <section id="intake-form" className="bg-muted/30 px-4 py-16">
      <div className="mx-auto max-w-2xl">
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-bold text-foreground sm:text-3xl">Tell us about your project</h2>
          <p className="mt-2 text-muted-foreground">
            We&apos;ll scope it, price it, and show you exactly what we can build &mdash; before you commit to anything.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 rounded-xl border bg-card p-6 shadow-sm">
          {/* Your Organization */}
          <div>
            <h3 className="mb-3 font-semibold text-foreground">Your organization</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm text-muted-foreground">Organization name *</label>
                <Input value={formData.organization_name} onChange={(e) => update("organization_name", e.target.value)} required />
              </div>
              <div>
                <label className="mb-1 block text-sm text-muted-foreground">Your name *</label>
                <Input value={formData.contact_name} onChange={(e) => update("contact_name", e.target.value)} required />
              </div>
              <div>
                <label className="mb-1 block text-sm text-muted-foreground">Email *</label>
                <Input type="email" value={formData.email} onChange={(e) => update("email", e.target.value)} required />
              </div>
              <div>
                <label className="mb-1 block text-sm text-muted-foreground">Phone (optional)</label>
                <Input value={formData.phone} onChange={(e) => update("phone", e.target.value)} />
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <input type="checkbox" id="coalition" checked={formData.is_coalition_member}
                onChange={(e) => update("is_coalition_member", e.target.checked)} className="rounded" />
              <label htmlFor="coalition" className="text-sm text-muted-foreground">We are a coalition member</label>
            </div>
          </div>

          <Separator />

          {/* Your Project */}
          <div>
            <h3 className="mb-3 font-semibold text-foreground">Your project</h3>
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-sm text-muted-foreground">What do you need built? *</label>
                <textarea rows={4} value={formData.project_description}
                  onChange={(e) => update("project_description", e.target.value)} required
                  placeholder="e.g. An AI system that automatically processes our job postings, extracts skills, and matches candidates..."
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary" />
              </div>
              <div>
                <label className="mb-1 block text-sm text-muted-foreground">What problem does this solve?</label>
                <textarea rows={2} value={formData.problem_statement}
                  onChange={(e) => update("problem_statement", e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none" />
              </div>
              <div>
                <label className="mb-1 block text-sm text-muted-foreground">What does success look like?</label>
                <textarea rows={2} value={formData.success_criteria}
                  onChange={(e) => update("success_criteria", e.target.value)}
                  placeholder="e.g. Our team spends 80% less time on manual data entry"
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:border-primary focus:outline-none" />
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <label className="mb-1 block text-sm text-muted-foreground">Project area</label>
                  <select value={formData.project_area} onChange={(e) => update("project_area", e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                    <option value="">Select...</option>
                    {PROJECT_AREAS.map((a) => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted-foreground">Timeline</label>
                  <select value={formData.timeline} onChange={(e) => update("timeline", e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                    <option value="">Select...</option>
                    {TIMELINES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm text-muted-foreground">Budget range</label>
                  <select value={formData.budget_range} onChange={(e) => update("budget_range", e.target.value)}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                    <option value="">Select...</option>
                    {BUDGETS.map((b) => <option key={b} value={b}>{b}</option>)}
                  </select>
                </div>
              </div>
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" size="lg" className="w-full gap-2" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit project to CFA"}
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-border bg-card py-8">
        <NewsletterSubscribe />
      <div className="mx-auto max-w-6xl px-4 text-center">
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Compass className="h-4 w-4 text-primary" />
          <span>WA Tech Workforce Coalition</span>
          <span className="text-muted-foreground/50">|</span>
          <span>Managed by Computing for All</span>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          computingforall.org | thewaifinder.com | info@computingforall.org
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
      <ProblemSection />
      <OfferSection />
      <DeRiskSection />
      <OutcomesSection />
      <ProofSection />
      <TalentConnection />
      <IntakeForm />
      <Footer />
    </div>
  )
}

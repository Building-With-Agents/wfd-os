"use client"

import { ExternalLink, Compass, Users, Briefcase, GraduationCap, MessageCircle, FileText, DollarSign, Sparkles } from "lucide-react"

const PORTALS = [
  {
    name: "CFA Homepage",
    description: "Main Computing for All landing page. Shows the three programs: Youth, Coalition, AI Consulting.",
    path: "/",
    icon: Compass,
    color: "bg-primary",
    review: "Check: branding consistency, messaging clarity, navigation between programs.",
  },
  {
    name: "AI Consulting — Marketing Page",
    description: "Public-facing consulting page with service offering, proof points, and intake form. The main marketing surface for Waifinder.",
    path: "/cfa/ai-consulting",
    icon: Sparkles,
    color: "bg-purple-600",
    review: "Check: messaging tone (guide don't pitch), Borderplex case study, intake form flow, CTA placement.",
  },
  {
    name: "AI Consulting — Chat Intake",
    description: "Conversational intake experience powered by Gemini. Prospects chat with an AI advisor instead of filling a form.",
    path: "/cfa/ai-consulting/chat",
    icon: MessageCircle,
    color: "bg-purple-600",
    review: "Check: conversation quality, domain knowledge, does it feel like talking to an expert? Try 'workforce board' as your org type.",
  },
  {
    name: "AI Consulting — Blog",
    description: "Blog posts and case studies. Content is managed through the marketing approval workflow.",
    path: "/cfa/ai-consulting/blog",
    icon: FileText,
    color: "bg-purple-600",
    review: "Check: article formatting, case study presentation, CTA at bottom. Note: most posts are 'in review' — not yet published.",
  },
  {
    name: "Coalition Homepage",
    description: "Washington Tech Workforce Coalition platform. Talent pipeline for employers.",
    path: "/coalition",
    icon: Users,
    color: "bg-blue-600",
    review: "Check: employer value proposition, navigation to showcase, consulting bridge.",
  },
  {
    name: "Talent Showcase",
    description: "Browse pre-vetted tech candidates with verified skills. Employers can view profiles and request introductions.",
    path: "/showcase",
    icon: Briefcase,
    color: "bg-teal-600",
    review: "Check: candidate cards, profile modal (click 'View Profile'), skill display, search/filter.",
  },
  {
    name: "For Employers",
    description: "Employer-facing page connecting talent hiring with AI consulting services.",
    path: "/for-employers",
    icon: Users,
    color: "bg-blue-600",
    review: "Check: dual value prop (hire talent + get AI built), CTA paths.",
  },
  {
    name: "Client Portal — WSB",
    description: "Active client portal for Workforce Solutions Borderplex. Shows milestones, documents, team, activity feed, and labor market intelligence.",
    path: "/coalition/client?token=wsb-001",
    icon: Compass,
    color: "bg-green-600",
    review: "Check: milestone tracker, live SharePoint documents, project updates feed, funded participants section, outcomes for board.",
  },
  {
    name: "Youth Program — Tech Career Bridge",
    description: "Landing page for the CFA youth coding program (ages 16-24, free, WA state).",
    path: "/youth",
    icon: GraduationCap,
    color: "bg-teal-600",
    review: "Check: accessibility of language, does it feel welcoming to non-tech youth? Application flow.",
  },
  {
    name: "College Partner Portal",
    description: "Portal for college career services directors showing graduate pipeline and employer demand data.",
    path: "/college",
    icon: GraduationCap,
    color: "bg-indigo-600",
    review: "Check: data presentation, curriculum gap signals, employer demand display.",
  },
  {
    name: "WJI Grant Dashboard",
    description: "Grant closeout tracking for WJI K8341. WSAC placement data upload and QuickBooks payment reconciliation.",
    path: "/wji",
    icon: DollarSign,
    color: "bg-amber-600",
    review: "Check: upload UI clarity, stats display, data status banner.",
  },
  {
    name: "Internal Pipeline Dashboard",
    description: "CFA staff view — consulting pipeline kanban, engagement management, Apollo status, marketing link.",
    path: "/internal",
    icon: Compass,
    color: "bg-slate-700",
    review: "Check: inquiry cards, status flow, post update modal, Teams checkbox, Apollo status badge.",
  },
  {
    name: "Marketing Content Pipeline",
    description: "Content approval workflow — kanban view of blog posts, case studies, email sequences, and sales assets.",
    path: "/internal/marketing",
    icon: FileText,
    color: "bg-slate-700",
    review: "Check: content cards, 'View content' modal, approve/publish buttons, status flow.",
  },
]

export default function ReviewLanding() {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
              <Compass className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">WFD OS — Portal Review</h1>
              <p className="text-sm text-muted-foreground">For Jessica Mangold — Marketing Review</p>
            </div>
          </div>
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-800">
            <p className="font-medium">How to review:</p>
            <ul className="mt-2 space-y-1 text-blue-700">
              <li>• Click each portal link below to open it in a new tab</li>
              <li>• Check messaging, branding, tone, and user experience</li>
              <li>• The purple chat bubble in the bottom-right corner is the AI advisor — try talking to it</li>
              <li>• Send feedback to Ritu via Teams or email with the portal name + your notes</li>
              <li>• This is a live dev environment — data is real but the URL is temporary</li>
            </ul>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
        <div className="grid gap-4 sm:grid-cols-2">
          {PORTALS.map((p) => {
            const Icon = p.icon
            return (
              <a
                key={p.path}
                href={p.path}
                target="_blank"
                rel="noopener noreferrer"
                className="group block rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:border-primary hover:shadow-md"
              >
                <div className="flex items-start gap-3">
                  <div className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${p.color}`}>
                    <Icon className="h-5 w-5 text-white" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-foreground group-hover:text-primary">{p.name}</h3>
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{p.description}</p>
                    <p className="mt-2 text-[10px] text-primary/70 font-medium">{p.review}</p>
                  </div>
                </div>
              </a>
            )
          })}
        </div>

        <div className="mt-8 rounded-lg border border-slate-200 bg-white p-5 text-center">
          <p className="text-sm text-muted-foreground">
            Questions? Reach out to Ritu at{" "}
            <a href="mailto:ritu@computingforall.org" className="text-primary hover:underline">
              ritu@computingforall.org
            </a>
          </p>
          <p className="mt-1 text-[10px] text-muted-foreground">
            WFD OS v1.0 — Built by Computing for All
          </p>
        </div>
      </main>
    </div>
  )
}

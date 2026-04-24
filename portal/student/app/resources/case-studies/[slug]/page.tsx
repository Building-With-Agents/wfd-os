import { getContentBySlug, renderMarkdown } from "@/lib/content"
import Link from "next/link"
import { Calendar, Clock, Compass, TrendingUp, ArrowRight } from "lucide-react"
import { notFound } from "next/navigation"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

export default async function CaseStudyPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const cs = getContentBySlug("case-studies", slug)
  if (!cs) notFound()

  const html = renderMarkdown(cs.body)
  const formattedDate = cs.date ? new Date(cs.date + "T00:00:00").toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) : ""
  const metricLabels: Record<string, string> = {
    staff_hours_saved: "Staff hours saved", data_freshness: "Data freshness", job_postings_processed: "Jobs processed",
    skill_extraction_accuracy: "Extraction accuracy", query_response_time: "Query speed", timeline: "Timeline", cost: "Investment",
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary"><Compass className="h-5 w-5 text-primary-foreground" /></div>
            <span className="text-lg font-bold">Computing for All</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/resources" className="text-muted-foreground hover:text-primary">Resources</Link>
            <Link href="/resources/case-studies" className="text-muted-foreground hover:text-primary">Case Studies</Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        <nav className="mb-6 flex items-center gap-2 text-xs text-muted-foreground">
          <Link href="/resources" className="hover:text-primary">Resources</Link><span>/</span>
          <Link href="/resources/case-studies" className="hover:text-primary">Case Studies</Link><span>/</span>
          <span className="text-foreground">{cs.title.slice(0, 40)}...</span>
        </nav>

        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <span className="rounded-full bg-green-600 px-3 py-1 text-xs font-medium text-white">{cs.industry}</span>
            <span className="rounded-full border px-2.5 py-0.5 text-xs">{cs.client}</span>
          </div>
          <h1 className="text-3xl font-bold text-foreground leading-tight">{cs.title}</h1>
          <div className="mt-3 flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1"><Calendar className="h-3.5 w-3.5" /> {formattedDate}</span>
            <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {cs.read_time}</span>
          </div>
        </div>

        {cs.metrics && Object.keys(cs.metrics).length > 0 && (
          <div className="mb-8 rounded-xl border-2 border-green-200 bg-green-50 p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="h-5 w-5 text-green-600" />
              <h3 className="font-bold text-green-900">Key Outcomes</h3>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {Object.entries(cs.metrics).map(([key, value]) => (
                <div key={key} className="rounded-lg bg-white p-3 text-center">
                  <p className="text-lg font-bold text-green-700">{value}</p>
                  <p className="text-[10px] text-muted-foreground">{metricLabels[key] || key.replace(/_/g, " ")}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {(cs.challenge || cs.solution) && (
          <div className="mb-8 grid gap-4 sm:grid-cols-2">
            {cs.challenge && (
              <div className="rounded-xl border-l-4 border-red-400 border bg-card p-4">
                <h4 className="text-xs font-bold uppercase text-red-600 mb-2">The Challenge</h4>
                <p className="text-sm text-foreground/80">{cs.challenge}</p>
              </div>
            )}
            {cs.solution && (
              <div className="rounded-xl border-l-4 border-green-400 border bg-card p-4">
                <h4 className="text-xs font-bold uppercase text-green-600 mb-2">The Solution</h4>
                <p className="text-sm text-foreground/80">{cs.solution}</p>
              </div>
            )}
          </div>
        )}

        <hr className="mb-8 border-border" />
        <article className="prose prose-slate max-w-none" dangerouslySetInnerHTML={{ __html: html }} />
        <hr className="my-8 border-border" />

        <div className="rounded-xl bg-gradient-to-r from-green-500/5 to-primary/10 border p-6 text-center">
          <h3 className="text-lg font-bold">Facing a similar challenge?</h3>
          <p className="mt-1 text-sm text-muted-foreground">We build custom agentic AI systems — fixed price, 10-14 weeks, production-ready.</p>
          <Link href="/cfa/ai-consulting/chat" className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
            Tell us about your situation <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </main>

      <footer className="border-t bg-card py-8 text-center">
        <NewsletterSubscribe />
        <p className="text-xs text-muted-foreground">Computing for All &middot; Bellevue, WA</p>
      </footer>
    </div>
  )
}

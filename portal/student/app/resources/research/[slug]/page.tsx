import { getContentBySlug, renderMarkdown } from "@/lib/content"
import Link from "next/link"
import { Calendar, Clock, Compass, ArrowRight } from "lucide-react"
import { notFound } from "next/navigation"
import GatedDownload from "./gated-download"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

export default async function ResearchReport({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const report = getContentBySlug("research", slug)
  if (!report) notFound()

  const html = renderMarkdown(report.body)
  const formattedDate = report.date ? new Date(report.date + "T00:00:00").toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) : ""

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
            <Link href="/resources/research" className="text-muted-foreground hover:text-primary">Research</Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        <nav className="mb-6 flex items-center gap-2 text-xs text-muted-foreground">
          <Link href="/resources" className="hover:text-primary">Resources</Link><span>/</span>
          <Link href="/resources/research" className="hover:text-primary">Research</Link><span>/</span>
          <span className="text-foreground">{report.title.slice(0, 40)}...</span>
        </nav>

        <div className="mb-8">
          <div className="flex flex-wrap gap-1.5 mb-4">
            {report.tags.map((t) => <span key={t} className="rounded-full bg-purple-100 text-purple-700 px-2.5 py-0.5 text-xs font-medium">{t}</span>)}
          </div>
          <h1 className="text-3xl font-bold text-foreground leading-tight">{report.title}</h1>
          <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1"><Calendar className="h-3.5 w-3.5" /> {formattedDate}</span>
            <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" /> {report.read_time}</span>
            <span>{report.author}</span>
          </div>
        </div>

        {report.is_gated && (
          <GatedDownload slug={report.slug} title={report.title} pdfUrl={report.pdf_url || "#"} />
        )}

        <hr className="my-8 border-border" />

        <article className="prose prose-slate max-w-none" dangerouslySetInnerHTML={{ __html: html }} />

        <hr className="my-8 border-border" />

        {report.is_gated && (
          <GatedDownload slug={report.slug} title={report.title} pdfUrl={report.pdf_url || "#"} />
        )}

        <div className="mt-8 rounded-xl bg-gradient-to-r from-purple-500/5 to-primary/10 border p-6 text-center">
          <h3 className="text-lg font-bold">Need custom regional analysis?</h3>
          <p className="mt-1 text-sm text-muted-foreground">Our Job Intelligence Engine can generate reports specific to your region, industry, and skills.</p>
          <Link href="/cfa/ai-consulting/chat" className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
            Talk to us <ArrowRight className="h-4 w-4" />
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

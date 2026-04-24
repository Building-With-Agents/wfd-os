import { getContentByType } from "@/lib/content"
import Link from "next/link"
import { ArrowLeft, Compass, Lock } from "lucide-react"
import ResearchFilter from "./filter"

export default function ResearchIndex() {
  const reports = getContentByType("research")

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
            <Link href="/resources/blog" className="text-muted-foreground hover:text-primary">Blog</Link>
            <Link href="/resources/case-studies" className="text-muted-foreground hover:text-primary">Case Studies</Link>
          </nav>
        </div>
      </header>

      <section className="bg-gradient-to-b from-purple-500/5 to-background px-4 py-16">
        <div className="mx-auto max-w-6xl">
          <Link href="/resources" className="mb-4 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary"><ArrowLeft className="h-3 w-3" /> Resources</Link>
          <h1 className="text-3xl font-bold text-foreground sm:text-4xl">Research</h1>
          <p className="mt-2 text-muted-foreground">Data-driven reports and labor market intelligence powered by the CFA Job Intelligence Engine.</p>
        </div>
      </section>

      <ResearchFilter reports={JSON.parse(JSON.stringify(reports))} />
    </div>
  )
}

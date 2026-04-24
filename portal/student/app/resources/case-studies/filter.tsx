"use client"

import { useState } from "react"
import Link from "next/link"
import { ArrowRight } from "lucide-react"

interface CaseStudy {
  title: string; client?: string; industry?: string; date: string; tags: string[]
  excerpt: string; slug: string; metrics?: Record<string, string>
}

const CATEGORIES = ["All", "Workforce", "Healthcare", "Legal", "Professional Services"]

export default function CaseStudyFilter({ studies }: { studies: CaseStudy[] }) {
  const [active, setActive] = useState("All")
  const filtered = active === "All" ? studies : studies.filter((s) => s.tags?.some((t) => t === active) || s.industry === active)

  return (
    <>
      <div className="border-b bg-card sticky top-[57px] z-40">
        <div className="mx-auto max-w-6xl px-4 py-3">
          <div className="flex gap-2 overflow-x-auto">
            {CATEGORIES.map((cat) => (
              <button key={cat} onClick={() => setActive(cat)}
                className={`flex-shrink-0 rounded-full px-4 py-1.5 text-xs font-medium transition-all ${active === cat ? "bg-green-600 text-white" : "border border-border text-muted-foreground hover:border-green-400 hover:text-green-600"}`}>
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((cs) => (
            <Link key={cs.slug} href={`/resources/case-studies/${cs.slug}`} className="group block">
              <div className="overflow-hidden rounded-xl border bg-card shadow-sm transition-all hover:shadow-md hover:border-green-300">
                <div className="h-44 bg-gradient-to-br from-green-500/20 to-primary/10 flex items-end p-4">
                  <span className="rounded-full bg-green-600 px-3 py-1 text-xs font-medium text-white">{cs.industry}</span>
                </div>
                <div className="p-4 space-y-2">
                  <h3 className="font-bold text-foreground group-hover:text-green-600 transition-colors line-clamp-2">{cs.title}</h3>
                  <p className="text-xs text-muted-foreground italic">{cs.client}</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{cs.excerpt}</p>
                  {cs.metrics && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {Object.entries(cs.metrics).slice(0, 3).map(([k, v]) => (
                        <span key={k} className="rounded bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700">{v}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </Link>
          ))}
        </div>
        <div className="mt-12 text-center">
          <div className="inline-block rounded-xl bg-gradient-to-r from-green-500/5 to-primary/10 border p-6">
            <h3 className="font-bold text-foreground">Have a similar challenge?</h3>
            <p className="mt-1 text-sm text-muted-foreground">We'd love to hear about it.</p>
            <Link href="/cfa/ai-consulting/chat" className="mt-3 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
              Start a conversation <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </main>
    </>
  )
}

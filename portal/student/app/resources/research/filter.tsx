"use client"

import { useState } from "react"
import Link from "next/link"
import { Lock } from "lucide-react"

interface Report {
  title: string; author: string; date: string; tags: string[]; excerpt: string
  read_time: string; slug: string; is_gated?: boolean
}

const CATEGORIES = ["All", "Labor Market", "Skills Gap", "AI Hiring Trends", "Regional Intelligence", "Workforce Development"]

export default function ResearchFilter({ reports }: { reports: Report[] }) {
  const [active, setActive] = useState("All")
  const filtered = active === "All" ? reports : reports.filter((r) => r.tags.some((t) => t === active))

  return (
    <>
      <div className="border-b bg-card sticky top-[57px] z-40">
        <div className="mx-auto max-w-6xl px-4 py-3">
          <div className="flex gap-2 overflow-x-auto">
            {CATEGORIES.map((cat) => (
              <button key={cat} onClick={() => setActive(cat)}
                className={`flex-shrink-0 rounded-full px-4 py-1.5 text-xs font-medium transition-all ${active === cat ? "bg-purple-600 text-white" : "border border-border text-muted-foreground hover:border-purple-400 hover:text-purple-600"}`}>
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((r) => (
            <Link key={r.slug} href={`/resources/research/${r.slug}`} className="group block">
              <div className="overflow-hidden rounded-xl border bg-card shadow-sm transition-all hover:shadow-md hover:border-purple-300">
                <div className="relative h-44 bg-gradient-to-br from-purple-500/20 to-primary/10 flex items-center justify-center">
                  {r.is_gated && <div className="flex items-center gap-1.5 rounded-full bg-amber-500 px-3 py-1 text-xs font-medium text-white"><Lock className="h-3 w-3" /> Gated PDF</div>}
                </div>
                <div className="p-4 space-y-2">
                  <div className="flex flex-wrap gap-1">{r.tags.slice(0, 2).map((t) => <span key={t} className="rounded-full border px-2 py-0.5 text-[10px]">{t}</span>)}</div>
                  <h3 className="font-bold text-foreground group-hover:text-purple-600 transition-colors line-clamp-2">{r.title}</h3>
                  <p className="text-xs text-muted-foreground line-clamp-2">{r.excerpt}</p>
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1"><span>{r.author}</span><span>{r.read_time}</span></div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </main>
    </>
  )
}

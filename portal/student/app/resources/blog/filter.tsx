"use client"

import { useState } from "react"
import Link from "next/link"

interface Post {
  title: string; author: string; date: string; tags: string[]; excerpt: string
  read_time: string; slug: string
}

const CATEGORIES = ["All", "AI Adoption", "Workforce Intelligence", "Data Engineering", "Agentic AI", "Hiring Trends", "General"]

export default function BlogFilter({ posts }: { posts: Post[] }) {
  const [active, setActive] = useState("All")
  const filtered = active === "All" ? posts : posts.filter((p) => p.tags.some((t) => t === active))

  return (
    <>
      <div className="border-b bg-card sticky top-[57px] z-40">
        <div className="mx-auto max-w-6xl px-4 py-3">
          <div className="flex gap-2 overflow-x-auto">
            {CATEGORIES.map((cat) => (
              <button key={cat} onClick={() => setActive(cat)}
                className={`flex-shrink-0 rounded-full px-4 py-1.5 text-xs font-medium transition-all ${active === cat ? "bg-primary text-primary-foreground" : "border border-border text-muted-foreground hover:border-primary hover:text-primary"}`}>
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      <main className="mx-auto max-w-6xl px-4 py-8">
        {filtered.length === 0 ? (
          <p className="py-20 text-center text-muted-foreground">No posts in this category yet.</p>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map((post) => (
              <Link key={post.slug} href={`/resources/blog/${post.slug}`} className="group block">
                <div className="overflow-hidden rounded-xl border bg-card shadow-sm transition-all hover:shadow-md hover:border-primary/30">
                  <div className="h-44 bg-gradient-to-br from-blue-500/20 to-primary/10" />
                  <div className="p-4 space-y-2">
                    <div className="flex flex-wrap gap-1">
                      {post.tags.map((t) => <span key={t} className="rounded-full border px-2 py-0.5 text-[10px]">{t}</span>)}
                    </div>
                    <h3 className="font-bold text-foreground group-hover:text-primary transition-colors line-clamp-2">{post.title}</h3>
                    <p className="text-xs text-muted-foreground line-clamp-3">{post.excerpt}</p>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1">
                      <span>{post.author} &middot; {post.read_time}</span>
                      <span>{post.date ? new Date(post.date + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : ""}</span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </>
  )
}

"use client"

import { useEffect, useState } from "react"
import { ArrowLeft, ArrowRight, Calendar, Tag, User } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

const API_BASE = "/api/marketing"

interface Post {
  id: string
  title: string
  slug: string
  content_body: string
  author: string
  audience_tag: string
  content_type: string
  published_at: string | null
  created_at: string
}

const AUDIENCE_LABELS: Record<string, string> = {
  workforce_boards: "Workforce Boards",
  healthcare: "Healthcare",
  professional_services: "Professional Services",
  employers: "Employers",
  workforce_development: "Workforce Development",
  general: "General",
}

export default function BlogPage() {
  const [posts, setPosts] = useState<Post[]>([])
  const [caseStudies, setCaseStudies] = useState<Post[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/content?content_type=blog_post&status=published`).then((r) => r.ok ? r.json() : { content: [] }),
      fetch(`${API_BASE}/content?content_type=case_study&status=published`).then((r) => r.ok ? r.json() : { content: [] }),
      // Also show in_review for now so the page isn't empty pre-publish
      fetch(`${API_BASE}/content?content_type=blog_post`).then((r) => r.ok ? r.json() : { content: [] }),
      fetch(`${API_BASE}/content?content_type=case_study`).then((r) => r.ok ? r.json() : { content: [] }),
    ]).then(([pubPosts, pubCS, allPosts, allCS]) => {
      setPosts(pubPosts.content.length > 0 ? pubPosts.content : allPosts.content)
      setCaseStudies(pubCS.content.length > 0 ? pubCS.content : allCS.content)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-white">
        <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
          <a href="/cfa/ai-consulting" className="mb-4 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary">
            <ArrowLeft className="h-3 w-3" /> Back to AI Consulting
          </a>
          <h1 className="text-3xl font-bold text-foreground">From the CFA Team</h1>
          <p className="mt-2 text-muted-foreground">Insights on agentic AI, workforce intelligence, and building with data.</p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-10 px-4 py-8 sm:px-6">
        {/* Case Studies */}
        {caseStudies.length > 0 && (
          <section>
            <h2 className="mb-4 text-xl font-bold text-foreground">Case Studies</h2>
            <div className="space-y-4">
              {caseStudies.map((cs) => (
                <Card key={cs.id} className="overflow-hidden border-l-4 border-primary p-6">
                  <Badge className="mb-2 bg-primary/10 text-primary border-0 text-[10px]">Case Study</Badge>
                  <h3 className="text-lg font-bold text-foreground">{cs.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground line-clamp-3">{cs.content_body}</p>
                  <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1"><User className="h-3 w-3" /> {cs.author}</span>
                    <span className="flex items-center gap-1"><Tag className="h-3 w-3" /> {AUDIENCE_LABELS[cs.audience_tag] || cs.audience_tag}</span>
                  </div>
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* Blog Posts */}
        <section>
          <h2 className="mb-4 text-xl font-bold text-foreground">Blog</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {posts.map((post) => (
              <Card key={post.id} className="p-5">
                <Badge variant="outline" className="mb-2 text-[10px]">{AUDIENCE_LABELS[post.audience_tag] || post.audience_tag}</Badge>
                <h3 className="font-bold text-foreground">{post.title}</h3>
                <p className="mt-2 text-xs text-muted-foreground line-clamp-3">{post.content_body}</p>
                <div className="mt-3 flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span>{post.author}</span>
                  {post.published_at && <span>{new Date(post.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>}
                </div>
              </Card>
            ))}
          </div>
        </section>

        <div className="text-center">
          <a href="/cfa/ai-consulting/chat">
            <Button className="gap-2">
              Talk to us about your project <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </main>
    </div>
  )
}

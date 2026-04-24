import { getContentBySlug, getContentByType, renderMarkdown } from "@/lib/content"
import Link from "next/link"
import { ArrowRight, Calendar, Clock, Compass } from "lucide-react"
import { notFound } from "next/navigation"
import ShareButton from "./share"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

export default async function BlogPost({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const post = getContentBySlug("blog", slug)
  if (!post) notFound()

  const allPosts = getContentByType("blog")
  const related = allPosts.filter((p) => p.slug !== slug).slice(0, 3)
  const html = renderMarkdown(post.body)
  const formattedDate = post.date ? new Date(post.date + "T00:00:00").toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) : ""

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
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        <nav className="mb-6 flex items-center gap-2 text-xs text-muted-foreground">
          <Link href="/resources" className="hover:text-primary">Resources</Link><span>/</span>
          <Link href="/resources/blog" className="hover:text-primary">Blog</Link><span>/</span>
          <span className="text-foreground">{post.title.slice(0, 40)}...</span>
        </nav>

        <div className="mb-8">
          <div className="flex flex-wrap gap-1.5 mb-4">
            {post.tags.map((t) => <span key={t} className="rounded-full border px-2.5 py-0.5 text-xs">{t}</span>)}
          </div>
          <h1 className="text-3xl font-bold text-foreground sm:text-4xl leading-tight">{post.title}</h1>
          <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-sm font-bold text-primary">
                {post.author.split(" ").map((n) => n[0]).join("").slice(0, 2)}
              </div>
              <div>
                <p className="font-medium text-foreground">{post.author}</p>
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1"><Calendar className="h-3 w-3" /> {formattedDate}</span>
                  <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {post.read_time}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <hr className="mb-8 border-border" />

        <article className="prose prose-slate max-w-none" dangerouslySetInnerHTML={{ __html: html }} />

        <hr className="my-8 border-border" />

        <ShareButton />

        <div className="mt-8 rounded-xl bg-gradient-to-r from-primary/5 to-primary/10 p-6 text-center border">
          <h3 className="text-lg font-bold text-foreground">Ready to build something?</h3>
          <p className="mt-1 text-sm text-muted-foreground">Talk to our team about your AI project — no commitment, just a conversation.</p>
          <Link href="/cfa/ai-consulting/chat" className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
            Start a conversation <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        {related.length > 0 && (
          <section className="mt-12">
            <h3 className="mb-4 text-lg font-bold text-foreground">More from the blog</h3>
            <div className="grid gap-4 sm:grid-cols-3">
              {related.map((r) => (
                <Link key={r.slug} href={`/resources/blog/${r.slug}`} className="group">
                  <div className="rounded-xl border p-4 transition-all hover:shadow-md hover:border-primary/30">
                    <h4 className="font-semibold text-sm text-foreground group-hover:text-primary line-clamp-2">{r.title}</h4>
                    <p className="mt-1 text-[10px] text-muted-foreground">
                      {r.author} &middot; {r.date ? new Date(r.date + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" }) : ""}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer className="border-t bg-card py-8 text-center">
        <NewsletterSubscribe />
        <p className="text-xs text-muted-foreground">Computing for All &middot; Bellevue, WA</p>
      </footer>
    </div>
  )
}

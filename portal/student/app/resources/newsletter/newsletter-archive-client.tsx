"use client"

import Link from "next/link"
import { Compass, Mail, ArrowRight } from "lucide-react"
import NewsletterSubscribe from "@/components/newsletter-subscribe"
import type { NewsletterIssueSummary } from "./page"

export default function NewsletterArchiveClient({
  issues,
}: {
  issues: NewsletterIssueSummary[]
}) {
  return (
    <div className="min-h-screen bg-background">
      {/* Header (matches resources landing) */}
      <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Compass className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold">Computing for All</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/cfa/ai-consulting" className="text-muted-foreground hover:text-primary">
              AI Consulting
            </Link>
            <Link href="/youth" className="text-muted-foreground hover:text-primary">
              Youth Program
            </Link>
            <Link href="/coalition" className="text-muted-foreground hover:text-primary">
              Coalition
            </Link>
            <Link href="/resources/blog" className="text-muted-foreground hover:text-primary">
              Blog
            </Link>
            <Link href="/resources/research" className="text-muted-foreground hover:text-primary">
              Research
            </Link>
            <Link href="/resources/case-studies" className="text-muted-foreground hover:text-primary">
              Case Studies
            </Link>
            <Link href="/resources/newsletter" className="font-semibold text-primary">
              Newsletter
            </Link>
            <Link
              href="/cfa/ai-consulting"
              className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground"
            >
              Get in touch
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-b from-primary/5 to-background px-4 py-16 text-center">
        <div className="mx-auto max-w-2xl">
          <div className="mb-3 flex items-center justify-center gap-2 text-primary">
            <Mail className="h-5 w-5" />
            <span className="text-xs font-semibold uppercase tracking-wider">Newsletter</span>
          </div>
          <h1 className="text-4xl font-bold text-foreground sm:text-5xl">Newsletter Archive</h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
            Monthly AI insights for Washington State businesses
          </p>
        </div>

        {/* Subscribe form at top */}
        <div className="mt-8 border-t border-border pt-8">
          <NewsletterSubscribe />
        </div>
      </section>

      {/* Issues list */}
      <main className="mx-auto max-w-4xl space-y-6 px-4 py-12">
        {issues.length === 0 ? (
          <p className="py-16 text-center text-sm italic text-muted-foreground">
            No newsletter issues yet — first issue coming soon.
          </p>
        ) : (
          issues.map((issue) => (
            <Link
              key={issue.id}
              href={`/resources/newsletter/${issue.issue_number}`}
              className="group block"
            >
              <article className="overflow-hidden rounded-xl border bg-card p-6 shadow-sm transition-all hover:border-primary/30 hover:shadow-md">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex-1">
                    <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="rounded-full border px-2 py-0.5 font-medium">
                        Issue {issue.issue_number}
                      </span>
                      <span>
                        {issue.issue_date
                          ? new Date(issue.issue_date + "T00:00:00").toLocaleDateString("en-US", {
                              month: "long",
                              day: "numeric",
                              year: "numeric",
                            })
                          : ""}
                      </span>
                    </div>
                    <h2 className="text-xl font-bold text-foreground transition-colors group-hover:text-primary sm:text-2xl">
                      {issue.headline}
                    </h2>
                    {issue.subheadline && (
                      <p className="mt-1 text-sm text-muted-foreground">{issue.subheadline}</p>
                    )}
                    <p className="mt-3 text-sm text-foreground/80">{issue.description}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1 self-end text-sm font-medium text-primary sm:self-center">
                    View Issue
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                  </div>
                </div>
              </article>
            </Link>
          ))
        )}
      </main>

      {/* Footer */}
      <footer className="border-t bg-card py-8 text-center">
        <NewsletterSubscribe />
        <p className="text-xs text-muted-foreground">
          Computing for All &middot; Bellevue, WA &middot;{" "}
          <Link href="/cfa/ai-consulting" className="text-primary hover:underline">
            computingforall.org
          </Link>
        </p>
      </footer>
    </div>
  )
}

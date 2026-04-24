"use client"

import Link from "next/link"
import { Compass, ArrowLeft, Mail } from "lucide-react"
import NewsletterSubscribe from "@/components/newsletter-subscribe"
import type { NewsletterIssueDetail } from "./page"

interface Props {
  issue: NewsletterIssueDetail | null
  requestedId: string
}

export default function NewsletterIssueClient({ issue, requestedId }: Props) {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-card/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Compass className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-lg font-bold">Computing for All</span>
          </Link>
          <nav className="flex items-center gap-4 text-sm">
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
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-12">
        <Link
          href="/resources/newsletter"
          className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Newsletter Archive
        </Link>

        {issue ? (
          <article className="space-y-6">
            <div className="border-b border-border pb-6">
              <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                <Mail className="h-4 w-4 text-primary" />
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
              <h1 className="text-3xl font-bold text-foreground sm:text-4xl">{issue.headline}</h1>
              {issue.subheadline && (
                <p className="mt-2 text-base text-muted-foreground">{issue.subheadline}</p>
              )}
            </div>

            {/* Render the stored HTML content */}
            <div
              className="prose prose-sm max-w-none text-foreground"
              dangerouslySetInnerHTML={{ __html: issue.html_content }}
            />
          </article>
        ) : (
          <div className="py-16 text-center">
            <h1 className="text-2xl font-bold text-foreground">Issue not found</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              No newsletter issue with id <span className="font-mono">{requestedId}</span> was found.
            </p>
            <Link
              href="/resources/newsletter"
              className="mt-6 inline-flex items-center gap-1 text-sm text-primary hover:underline"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to archive
            </Link>
          </div>
        )}
      </main>

      <footer className="mt-12 border-t bg-card py-8 text-center">
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

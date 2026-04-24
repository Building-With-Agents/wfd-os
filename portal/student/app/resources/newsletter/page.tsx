import NewsletterArchiveClient from "./newsletter-archive-client"

// Server component — fetches issue list at request time so the archive
// renders with real cards on first paint.
export const dynamic = "force-dynamic"

export interface NewsletterIssueSummary {
  id: number
  issue_number: number
  issue_date: string
  headline: string
  subheadline: string
  description: string
  status: string
  published_at: string | null
}

async function getIssues(): Promise<NewsletterIssueSummary[]> {
  try {
    const r = await fetch("http://localhost:8008/api/marketing/newsletter-issues", {
      cache: "no-store",
    })
    if (!r.ok) return []
    const data = await r.json()
    return (data.issues || []) as NewsletterIssueSummary[]
  } catch {
    return []
  }
}

export default async function Page() {
  const issues = await getIssues()
  return <NewsletterArchiveClient issues={issues} />
}

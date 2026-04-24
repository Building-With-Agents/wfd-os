import NewsletterIssueClient from "./newsletter-issue-client"

// Server component — fetches the full issue (including html_content) at
// request time. Uses force-dynamic so issues update immediately when edited
// in the DB.
export const dynamic = "force-dynamic"

export interface NewsletterIssueDetail {
  id: number
  issue_number: number
  issue_date: string
  headline: string
  subheadline: string
  description: string
  html_content: string
  status: string
  published_at: string | null
}

async function getIssue(id: string): Promise<NewsletterIssueDetail | null> {
  try {
    const r = await fetch(`http://localhost:8008/api/marketing/newsletter-issues/${id}`, {
      cache: "no-store",
    })
    if (!r.ok) return null
    return (await r.json()) as NewsletterIssueDetail
  } catch {
    return null
  }
}

export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const issue = await getIssue(id)
  return <NewsletterIssueClient issue={issue} requestedId={id} />
}

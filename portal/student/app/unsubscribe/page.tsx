import UnsubscribeClient from "./unsubscribe-client"

// Server component — runs the unsubscribe against the marketing backend
// at request time so the DB update and Apollo untag happen before the
// page renders. Follows the server-component-wrapper pattern.
export const dynamic = "force-dynamic"

interface UnsubscribeResult {
  success: boolean
  email: string
  found: boolean
  apollo?: { ok: boolean; contact_id?: string | null; note?: string; error?: string }
}

async function runUnsubscribe(email: string): Promise<UnsubscribeResult | null> {
  if (!email) return null
  try {
    const r = await fetch(
      `http://localhost:8008/api/marketing/newsletter-unsubscribe?email=${encodeURIComponent(email)}`,
      { cache: "no-store" }
    )
    return r.ok ? ((await r.json()) as UnsubscribeResult) : null
  } catch {
    return null
  }
}

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ email?: string; contact_id?: string }>
}) {
  const params = await searchParams
  const email = (params?.email || "").trim().toLowerCase()
  const result = email ? await runUnsubscribe(email) : null

  return <UnsubscribeClient initialEmail={email} initialResult={result} />
}

import ForEmployersClient from "./for-employers-client"

// Force dynamic rendering — this page fetches live data from localhost APIs
// on every request and must not be statically prerendered at build time.
export const dynamic = "force-dynamic"

// Server component — fetches stats at request time so the candidate count
// renders correctly on first paint (no flash of fallback "101").
async function getStats() {
  try {
    const r = await fetch("http://localhost:8001/api/stats", { cache: "no-store" })
    return r.ok ? await r.json() : null
  } catch {
    return null
  }
}

export default async function Page() {
  const stats = await getStats()
  return <ForEmployersClient initialStats={stats} />
}

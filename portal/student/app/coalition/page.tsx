import CoalitionClient from "./coalition-client"

// Force dynamic rendering — this page fetches live data from localhost APIs
// on every request and must not be statically prerendered at build time.
export const dynamic = "force-dynamic"

// Server component — fetches stats AND the live candidate count at request
// time so the talent showcase number renders correctly on first paint (no
// flash of stale fallback). Both fetches run in parallel.
async function getStats() {
  try {
    const r = await fetch("http://localhost:8001/api/stats", { cache: "no-store" })
    return r.ok ? await r.json() : null
  } catch {
    return null
  }
}

async function getCandidateCount(): Promise<number | null> {
  try {
    const r = await fetch("http://localhost:8001/api/coalition/candidate-count", { cache: "no-store" })
    if (!r.ok) return null
    const data = await r.json()
    return typeof data.count === "number" ? data.count : null
  } catch {
    return null
  }
}

export default async function Page() {
  const [stats, candidateCount] = await Promise.all([getStats(), getCandidateCount()])
  return <CoalitionClient initialStats={stats} initialCandidateCount={candidateCount} />
}

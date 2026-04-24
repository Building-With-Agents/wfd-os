import TalentShowcase from "./showcase-client"

// Force dynamic rendering — this page fetches live data from localhost APIs
// on every request and must not be statically prerendered at build time.
export const dynamic = "force-dynamic"

async function getInitialData() {
  try {
    const [candidatesRes, filtersRes] = await Promise.all([
      fetch("http://localhost:8002/api/showcase/candidates?limit=50", { cache: "no-store" }),
      fetch("http://localhost:8002/api/showcase/filters", { cache: "no-store" }),
    ])

    const candidatesData = candidatesRes.ok ? await candidatesRes.json() : { candidates: [], total: 0 }
    const filtersData = filtersRes.ok ? await filtersRes.json() : { skills: [], locations: [] }

    return {
      candidates: candidatesData.candidates || [],
      total: candidatesData.total || 0,
      skills: filtersData.skills || [],
      locations: filtersData.locations || [],
    }
  } catch (e) {
    console.error("[SHOWCASE SSR] Failed to pre-fetch:", e)
    return undefined
  }
}

export default async function ShowcasePage() {
  const initialData = await getInitialData()
  return <TalentShowcase initialData={initialData} />
}

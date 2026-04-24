import TalentShowcase from "./showcase-client"

// Force dynamic rendering — this page fetches live data from localhost APIs
// on every request and must not be statically prerendered at build time.
export const dynamic = "force-dynamic"

async function getInitialData() {
  try {
    const [c, f] = await Promise.all([
      fetch("http://localhost:8002/api/showcase/candidates?limit=50", { cache: "no-store" }),
      fetch("http://localhost:8002/api/showcase/filters", { cache: "no-store" }),
    ])
    const cd = c.ok ? await c.json() : { candidates: [], total: 0 }
    const fd = f.ok ? await f.json() : { skills: [], locations: [] }
    return { candidates: cd.candidates || [], total: cd.total || 0, skills: fd.skills || [], locations: fd.locations || [] }
  } catch { return undefined }
}

export default async function Page() {
  const initialData = await getInitialData()
  return <TalentShowcase initialData={initialData} />
}

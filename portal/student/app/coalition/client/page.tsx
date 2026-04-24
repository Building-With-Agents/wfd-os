import { Suspense } from "react"
import { ClientPortalContent } from "./client-view"

// Force dynamic rendering — this page fetches live data from localhost APIs
// on every request and must not be statically prerendered at build time.
export const dynamic = "force-dynamic"

async function getClientData(token: string) {
  try {
    const [dataRes, docsRes] = await Promise.all([
      fetch(`http://localhost:8006/api/consulting/client/${token}`, { cache: "no-store" }),
      fetch(`http://localhost:8006/api/consulting/client/${token}/documents`, { cache: "no-store" }),
    ])
    const data = dataRes.ok ? await dataRes.json() : null
    const docs = docsRes.ok ? await docsRes.json() : null
    return { data, docs }
  } catch { return { data: null, docs: null } }
}

export default async function ClientPortalPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const params = await searchParams
  const token = params.token || ""

  let initialData = null
  let initialDocs = null

  if (token) {
    const result = await getClientData(token)
    initialData = result.data
    initialDocs = result.docs
  }

  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" /></div>}>
      <ClientPortalContent initialData={initialData} initialDocs={initialDocs} />
    </Suspense>
  )
}

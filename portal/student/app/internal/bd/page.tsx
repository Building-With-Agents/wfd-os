// Server component wrapper for the BD Command Center.
//
// Fetches all data at request time from the consulting API running on
// localhost:8003 (server-to-localhost, never through ngrok) and passes
// the results to BDClient as initial props. This guarantees that the
// dashboard shows real data on first paint regardless of whether the
// user is on localhost, ngrok, a slow connection, or during a Turbopack
// hot-reload cycle.
//
// Port note: consulting_api.py hardcodes port 8003 at its __main__. The
// next.config.mjs rewrite for /api/consulting/:path* also points at 8003.
// Both the server-side fetch below and the client-side rewrite path must
// stay aligned — if you move consulting_api to a different port, update
// both this constant and next.config.mjs.
//
// See CLAUDE.md "Standing rule — Portal pages that show live data" for
// the full rationale and checklist.

import { headers } from "next/headers"
import BDClient from "./bd-client"

// Force dynamic rendering. This page fetches from localhost APIs on every
// request and must NEVER be statically prerendered at build time — the
// consulting API isn't available inside the build worker, so prerendering
// throws "Expected workStore to be initialized". This directive tells
// Next.js to render on each request, which is what we want for live data.
export const dynamic = "force-dynamic"

const BD_API_BASE = "http://localhost:8003/api/consulting/bd"

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    // Forward the user's session cookie — direct localhost fetch bypasses
    // the Next.js rewrite proxy that would otherwise carry it, so without
    // this consulting-api's @read_only routes return 401. Forward the
    // raw header verbatim — cookies().toString() mangles the JSON-encoded
    // wfdos_session value.
    const cookieHeader = (await headers()).get("cookie")
    const r = await fetch(url, {
      cache: "no-store",
      headers: cookieHeader ? { Cookie: cookieHeader } : undefined,
    })
    if (!r.ok) {
      console.error(`[BD page] ${url} -> HTTP ${r.status}`)
      return null
    }
    return (await r.json()) as T
  } catch (e) {
    console.error(`[BD page] ${url} fetch error`, e)
    return null
  }
}

export default async function Page() {
  const [priorities, hotProspects, warmSignals, pipeline, emailDrafts] = await Promise.all([
    fetchJson<{ signals: any[]; new_hot: any[] }>(`${BD_API_BASE}/priorities`),
    fetchJson<{ prospects: any[] }>(`${BD_API_BASE}/hot-prospects`),
    fetchJson<{ signals: any[] }>(`${BD_API_BASE}/warm-signals`),
    fetchJson<{ stages: string[]; pipeline: Record<string, any[]> }>(`${BD_API_BASE}/pipeline`),
    fetchJson<{ drafts: any[] }>(`${BD_API_BASE}/email-drafts`),
  ])

  return (
    <BDClient
      initialPriorities={
        priorities ? { signals: priorities.signals || [], new_hot: priorities.new_hot || [] } : null
      }
      initialHotProspects={hotProspects?.prospects || []}
      initialWarmSignals={warmSignals?.signals || []}
      initialPipeline={
        pipeline ? { stages: pipeline.stages || [], pipeline: pipeline.pipeline || {} } : null
      }
      initialEmailDrafts={emailDrafts?.drafts || []}
    />
  )
}

// Thin client for /api/finance/* endpoints.
// Works both server-side (page.tsx pre-render) and client-side (lazy
// fetches in cockpit-client.tsx for tabs + drills).
//
// On the server the absolute URL is required; Next.js rewrites only
// apply to browser-initiated fetches. On the client, relative paths
// hit the same origin and get rewritten to localhost:8013 by
// next.config.mjs.

import type {
  ActivityPayload,
  CockpitStatusPayload,
  HeroPayload,
  DecisionsPayload,
  TabPayload,
  DrillEntry,
} from "./types"

const SERVER_BASE = process.env.COCKPIT_API_URL ?? "http://127.0.0.1:8013"
const CLIENT_BASE = "/api/finance"

function base(): string {
  // On the server there's no window; hit the Python service directly.
  return typeof window === "undefined" ? SERVER_BASE : CLIENT_BASE
}

// On the server we must forward the user's session cookie ourselves —
// fetch() to 127.0.0.1 bypasses the Next.js rewrite proxy that would
// otherwise carry it. We forward the *raw* incoming Cookie header
// verbatim rather than round-tripping through cookies().toString(),
// because the wfdos_session value contains JSON braces + commas that
// don't round-trip cleanly through Next's cookie serializer.
// Dynamic import keeps `next/headers` out of the client bundle
// (cockpit-client.tsx imports from this module).
async function ssrCookieHeader(): Promise<string | null> {
  if (typeof window !== "undefined") return null
  const { headers } = await import("next/headers")
  return (await headers()).get("cookie") || null
}

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const opts: RequestInit = { cache: "no-store", ...init }
  const cookie = await ssrCookieHeader()
  if (cookie) {
    opts.headers = { ...(opts.headers as Record<string, string> | undefined), Cookie: cookie }
  }
  const r = await fetch(`${base()}${path}`, opts)
  if (!r.ok) {
    throw new Error(`GET ${path} -> HTTP ${r.status}`)
  }
  return (await r.json()) as T
}

export function fetchStatus(): Promise<CockpitStatusPayload> {
  return getJSON("/cockpit/status")
}

export function fetchHero(): Promise<HeroPayload> {
  return getJSON("/cockpit/hero")
}

export function fetchDecisions(): Promise<DecisionsPayload> {
  return getJSON("/cockpit/decisions")
}

export function fetchActivity(): Promise<ActivityPayload> {
  return getJSON("/cockpit/activity")
}

export function fetchTab(tabId: string): Promise<TabPayload> {
  return getJSON(`/cockpit/tabs/${encodeURIComponent(tabId)}`)
}

export function fetchDrill(drillKey: string): Promise<DrillEntry> {
  return getJSON(`/cockpit/drills/${encodeURIComponent(drillKey)}`)
}

export async function postRefresh(): Promise<CockpitStatusPayload> {
  const opts: RequestInit = { method: "POST", cache: "no-store" }
  const cookie = await ssrCookieHeader()
  if (cookie) opts.headers = { Cookie: cookie }
  const r = await fetch(`${base()}/cockpit/refresh`, opts)
  if (!r.ok) throw new Error(`POST /cockpit/refresh -> HTTP ${r.status}`)
  return (await r.json()) as CockpitStatusPayload
}

// Thin client for /api/finance/* endpoints.
// Works both server-side (page.tsx pre-render) and client-side (lazy
// fetches in cockpit-client.tsx for tabs + drills).
//
// On the server the absolute URL is required; Next.js rewrites only
// apply to browser-initiated fetches. On the client, relative paths
// hit the same origin and get rewritten to localhost:8013 by
// next.config.mjs.

import type {
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

async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${base()}${path}`, {
    cache: "no-store",
    ...init,
  })
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

export function fetchTab(tabId: string): Promise<TabPayload> {
  return getJSON(`/cockpit/tabs/${encodeURIComponent(tabId)}`)
}

export function fetchDrill(drillKey: string): Promise<DrillEntry> {
  return getJSON(`/cockpit/drills/${encodeURIComponent(drillKey)}`)
}

export async function postRefresh(): Promise<CockpitStatusPayload> {
  const r = await fetch(`${base()}/cockpit/refresh`, {
    method: "POST",
    cache: "no-store",
  })
  if (!r.ok) throw new Error(`POST /cockpit/refresh -> HTTP ${r.status}`)
  return (await r.json()) as CockpitStatusPayload
}

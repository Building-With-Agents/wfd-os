import FinanceClient from "./finance-client"

// Server component wrapper. Fetches initial dashboard state from the
// grant-compliance FastAPI on :8000 (via the /api/grant-compliance/*
// rewrite in next.config.mjs) so the page renders with real data on
// first paint instead of flashing empty placeholders.
//
// Follows the server-component-wrapper pattern per CLAUDE.md.

export const dynamic = "force-dynamic"

export interface QbStatus {
  qb_environment: string
  connected_realms: Array<{
    realm_id: string
    environment: string
    authorized_by: string | null
    access_expires_at: string
    refresh_expires_at: string
    access_expired: boolean
  }>
}

export interface TransactionSummary {
  id: string
  qb_id: string
  qb_type: string
  txn_date: string
  vendor_name: string | null
  memo: string | null
  amount_cents: number
  qb_class_id: string | null
}

export interface ComplianceFlag {
  id: string
  rule_id: string
  rule_citation: string
  message: string
  severity: string
  status: string
  raised_at: string
}

// Server-side fetch helper. The grant-compliance API has no /api prefix
// on its routes (unlike consulting_api etc.) — routes are at /grants,
// /transactions, /qb/status, etc. We hit localhost:8000 directly at
// request time.
const GC_API = "http://localhost:8000"

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${GC_API}${path}`, { cache: "no-store" })
    if (!r.ok) {
      console.error(`[Finance page] GET ${path} -> HTTP ${r.status}`)
      return null
    }
    return (await r.json()) as T
  } catch (e) {
    console.error(`[Finance page] GET ${path} fetch error`, e)
    return null
  }
}

export default async function Page() {
  const [qbStatus, transactions, flags] = await Promise.all([
    fetchJson<QbStatus>("/qb/status"),
    fetchJson<TransactionSummary[]>("/transactions"),
    fetchJson<ComplianceFlag[]>("/compliance/flags"),
  ])

  return (
    <FinanceClient
      initialQbStatus={qbStatus}
      initialTransactions={transactions ?? []}
      initialFlags={flags ?? []}
    />
  )
}

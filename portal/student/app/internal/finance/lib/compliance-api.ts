// Cockpit-side client for the engine's Compliance Requirements Agent.
//
// Mode A data (the current ComplianceRequirementsSet) is delivered via the
// cockpit's tab-load pattern — see _tab_compliance in cockpit_api.py, which
// proxies the engine fetch and includes the result in the tab payload that
// fetchTab() returns. So this file does NOT need to fetch the set directly.
//
// Mode B Q&A is a per-question POST that doesn't fit tab-load semantics.
// This file exposes that POST helper.
//
// Engine routes (per agents/grant-compliance/src/.../compliance_requirements.py):
//   GET  /compliance/requirements/current?grant_id=<id>
//   POST /compliance/requirements/qa
//
// Reached via the existing /api/grant-compliance/* rewrite in
// portal/student/next.config.mjs (engine port :8000).

import type { QARequest, QAResponse } from "./compliance-types"

const GC_API = "/api/grant-compliance"

export class ComplianceQAError extends Error {
  status: number
  detail: string | null
  constructor(message: string, status: number, detail: string | null) {
    super(message)
    this.name = "ComplianceQAError"
    this.status = status
    this.detail = detail
  }
}

export async function postComplianceQA(req: QARequest): Promise<QAResponse> {
  const r = await fetch(`${GC_API}/compliance/requirements/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    cache: "no-store",
  })
  if (!r.ok) {
    let detail: string | null = null
    try {
      const body = await r.json()
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body)
    } catch {
      // body is not JSON; fall back to status text
      detail = r.statusText || null
    }
    throw new ComplianceQAError(
      `Compliance Q&A request failed (${r.status})`,
      r.status,
      detail,
    )
  }
  return (await r.json()) as QAResponse
}

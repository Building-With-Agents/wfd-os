// Thin client for /api/recruiting/*. Works both server-side (initial
// render) and client-side (filter changes + drill open). On the server
// the absolute URL is required; on the client the relative path hits
// the /api/recruiting rewrite in next.config.mjs.
//
// Mirrors the Finance pattern in finance/lib/api.ts — same base()
// helper, same cache:"no-store" default, same fetch-then-JSON.

import type {
  WorkdayStats,
  JobsListPayload,
  JobRow,
  JobMatchesPayload,
  ApplicationRow,
  CreateApplicationBody,
  WorkdayFilters,
  StudentDetailPayload,
  StudentApplicationPayload,
  CaseloadPayload,
  CaseloadFilters,
  ApplicationsListPayload,
  ApplicationsFilters,
} from "./types"

const SERVER_BASE = process.env.RECRUITING_API_URL ?? "http://127.0.0.1:8012"
const CLIENT_BASE = "/api/recruiting"

function base(): string {
  return typeof window === "undefined" ? SERVER_BASE : CLIENT_BASE
}

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${base()}${path}`, { cache: "no-store" })
  if (!r.ok) throw new Error(`GET ${path} -> HTTP ${r.status}`)
  return (await r.json()) as T
}

export function fetchWorkdayStats(): Promise<WorkdayStats> {
  return getJSON("/stats/workday")
}

export function fetchJobs(
  filters: WorkdayFilters,
  limit = 50,
  offset = 0,
): Promise<JobsListPayload> {
  const params = new URLSearchParams()
  if (filters.q) params.set("q", filters.q)
  if (filters.city) params.set("city", filters.city)
  if (filters.state) params.set("state", filters.state)
  if (filters.is_remote !== null) params.set("is_remote", String(filters.is_remote))
  if (filters.seniority) params.set("seniority", filters.seniority)
  if (filters.employment_type) params.set("employment_type", filters.employment_type)
  params.set("limit", String(limit))
  params.set("offset", String(offset))
  return getJSON(`/jobs?${params.toString()}`)
}

export function fetchJob(jobId: number): Promise<JobRow> {
  return getJSON(`/jobs/${jobId}`)
}

export function fetchJobMatches(jobId: number, limit = 10): Promise<JobMatchesPayload> {
  return getJSON(`/jobs/${jobId}/matches?limit=${limit}`)
}

// Top-N job matches for a given student (student-first flip of
// fetchJobMatches). Shape matches the backend's /students/{id}/matches
// envelope which is NOT typed here yet — treated as unknown payload so
// callers read fields defensively.
export function fetchStudentMatches(studentId: string, limit = 10): Promise<unknown> {
  return getJSON(`/students/${encodeURIComponent(studentId)}/matches?limit=${limit}`)
}

export function fetchStudent(studentId: string): Promise<StudentDetailPayload> {
  return getJSON(`/students/${studentId}`)
}

export function fetchStudentApplication(
  studentId: string,
  jobId: number,
): Promise<StudentApplicationPayload> {
  return getJSON(`/students/${studentId}/applications/${jobId}`)
}

export function fetchCaseload(filters: CaseloadFilters, limit = 200): Promise<CaseloadPayload> {
  const params = new URLSearchParams()
  if (filters.tenant) params.set("tenant", filters.tenant)
  if (filters.cohort) params.set("cohort", filters.cohort)
  if (filters.tier) params.set("tier", filters.tier)
  if (filters.min_match_score !== null) params.set("min_match_score", String(filters.min_match_score))
  if (filters.q) params.set("q", filters.q)
  params.set("limit", String(limit))
  return getJSON(`/caseload?${params.toString()}`)
}

export function fetchApplications(filters: ApplicationsFilters, limit = 500): Promise<ApplicationsListPayload> {
  const params = new URLSearchParams()
  if (filters.status) params.set("status", filters.status)
  if (filters.tenant) params.set("tenant", filters.tenant)
  if (filters.student_id) params.set("student_id", filters.student_id)
  params.set("limit", String(limit))
  return getJSON(`/applications?${params.toString()}`)
}

export async function postApplication(body: CreateApplicationBody): Promise<ApplicationRow> {
  const r = await fetch(`${base()}/applications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  })
  if (!r.ok) {
    const detail = await r.json().catch(() => ({ detail: "unknown error" }))
    throw new Error(`POST /applications -> HTTP ${r.status}: ${detail.detail}`)
  }
  return (await r.json()) as ApplicationRow
}

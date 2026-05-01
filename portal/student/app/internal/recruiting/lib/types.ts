// Recruiting-specific API response shapes. Mirror the envelopes
// emitted by agents/job_board/api.py (port 8012, exposed via the
// /api/recruiting/* Next.js rewrite).
//
// Cross-agent primitives (Tone, DrillEntry, StatusChip, HeroGridCell)
// come from _shared/types. Recruiting drill entries are assembled
// client-side from /jobs/{id} + /jobs/{id}/matches rather than served
// by a dedicated backend endpoint, so the Recruiting drill "registry"
// is really a small factory in workday-client.

import type { Tone } from "../../_shared/types"

export type MatchingStatus = "ready" | "pending_student_index"

export interface EmbeddingsStatus {
  by_entity_type: Record<string, number>
  student_count: number
  jobs_enriched_count: number
  student_index_ready: boolean
}

// ---------- /jobs ----------

export interface JobRow {
  job_id: number
  deployment_id: string | null
  region: string | null
  title: string
  company: string | null
  company_domain: string | null
  location: string | null
  description: string | null
  skills_required: string[] | null
  seniority: string | null
  is_ai_role: boolean | null
  is_data_role: boolean | null
  is_workforce_role: boolean | null
  posted_at: string | null
  apply_url: string | null
  enriched_at: string | null
  city: string | null
  state: string | null
  country: string | null
  is_remote: boolean | null
  latitude: number | null
  longitude: number | null
  employment_type: string | null
  match_count: number
  in_flight_app_count: number
}

export interface JobsListPayload {
  jobs: JobRow[]
  count: number
  limit: number
  offset: number
}

// ---------- /jobs/{id}/matches ----------

export interface JobMatchRow {
  id: string
  full_name: string
  cohort_id: string | null
  cohort_label: string
  pipeline_status: string | null
  cosine: number
  existing_application: boolean
  skill_overlap: string[] | null
}

export interface JobMatchesPayload {
  matches: JobMatchRow[]
  matching_status: MatchingStatus
  note?: string
  embeddings_status: EmbeddingsStatus
}

// ---------- /stats/workday ----------

export interface WorkdayStats {
  open_jobs: number
  with_matches: number
  apps_in_flight: number
  matching_status: MatchingStatus
  embeddings_status: EmbeddingsStatus
}

// ---------- /applications (POST) ----------

export interface CreateApplicationBody {
  student_id: string
  job_id: number
  initiated_by: "candidate" | "recruiter"
}

export interface ApplicationRow {
  id: string
  student_id: string
  job_id: number
  status: string
  initiated_by: string
  created_at: string
  last_status_change_at: string
}

// ---------- /students/{id} (Phase 2E student drill) ----------

export interface StudentSkill {
  name: string
  source: string | null
}

export interface StudentWorkExperience {
  company: string | null
  title: string | null
  responsibilities: string | null
  start_date: string | null
  end_date: string | null
  is_current: boolean | null
}

export interface StudentEducation {
  institution: string | null
  degree: string | null
  field_of_study: string | null
  graduation_year: number | null
}

export interface StudentDetail {
  id: string
  full_name: string
  email: string | null
  phone: string | null
  city: string | null
  state: string | null
  institution: string | null
  degree: string | null
  field_of_study: string | null
  graduation_year: number | null
  linkedin_url: string | null
  github_url: string | null
  portfolio_url: string | null
  career_objective: string | null
  pipeline_status: string | null
  pipeline_stage: string | null
  cohort_id: string | null
  track: string | null
  skills: StudentSkill[]
  work_experience: StudentWorkExperience[]
  education: StudentEducation[]
}

export interface StudentDetailPayload {
  student: StudentDetail
}

export interface StudentApplicationPayload {
  application: ApplicationRow | null
}

// ---------- filter state (client-only) ----------

export interface WorkdayFilters {
  q: string
  city: string
  state: string
  is_remote: boolean | null
  seniority: string
  employment_type: string
}

export function emptyFilters(): WorkdayFilters {
  return { q: "", city: "", state: "", is_remote: null, seniority: "", employment_type: "" }
}

// ---------- /caseload (Dinah's case-manager home view) ----------

export type Tier = "A" | "B" | "C"

export interface CaseloadRow {
  student_id: string
  full_name: string
  cohort_id: string | null
  tenant: string
  profile_completeness_score: number | null
  tier: Tier
  top_match_score: number | null
  top_match_job_title: string | null
  top_match_job_id: number | null
  top_match_company: string | null
  match_count: number
  applications_count: number
  updated_at: string | null
  days_since_last_touch: number | null
  pipeline_stage: string | null
  pipeline_status: string | null
}

export interface CaseloadPayload {
  rows: CaseloadRow[]
  total: number
}

export interface CaseloadFilters {
  tenant: string       // "", "CFA", "WSB"
  cohort: string
  tier: string         // "", "A", "B", "C"
  min_match_score: number | null
  q: string
}

export function emptyCaseloadFilters(): CaseloadFilters {
  return { tenant: "", cohort: "", tier: "", min_match_score: null, q: "" }
}

// ---------- /applications (pipeline list view) ----------

export interface ApplicationListRow {
  id: string
  student_id: string
  student_name: string | null
  student_cohort: string | null
  job_id: number
  job_title: string | null
  job_company: string | null
  job_location: string | null
  status: string
  owning_recruiter_id: string | null
  initiated_by: string
  created_at: string
  updated_at: string
  last_status_change_at: string | null
  days_in_stage: number | null
  tenant: string
}

export interface ApplicationsListPayload {
  rows: ApplicationListRow[]
  total: number
}

export interface ApplicationsFilters {
  status: string       // "" = all
  tenant: string
  student_id: string
  q: string
}

export function emptyApplicationsFilters(): ApplicationsFilters {
  return { status: "", tenant: "", student_id: "", q: "" }
}

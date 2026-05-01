const API_BASE = "/api"

export interface WorkExperienceEntry {
  company: string | null
  title: string | null
  start_date: string | null
  end_date: string | null
  is_current: boolean | null
  description: string | null
}

export interface StudentProfile {
  id: string
  full_name: string
  email: string
  phone: string | null
  city: string | null
  state: string | null
  institution: string | null
  degree: string | null
  field_of_study: string | null
  graduation_year: number | null
  linkedin_url: string | null
  github_url?: string | null
  portfolio_url?: string | null
  profile_completeness_score: number
  required_fields_complete: number
  preferred_fields_complete: number
  missing_required: string[]
  missing_preferred: string[]
  showcase_eligible: boolean
  showcase_active: boolean
  pipeline_status: string
  pipeline_stage: string | null
  track: string | null
  cohort_id: string | null
  resume_parsed: boolean
  parse_confidence_score: number | null
  skills: string[]
  skill_count: number
  // Resume summary extension (Apr 24 — added in student_api.get_profile)
  career_objective?: string | null
  certifications?: string[]
  work_experience?: WorkExperienceEntry[]
}

export interface JobMatch {
  job_id: string
  title: string
  company: string | null
  city: string | null
  state: string | null
  salary_min: number | null
  salary_max: number | null
  match_score: number
  matched_skills: string[]
  missing_skills: string[]
  total_job_skills: number
}

export interface SkillGapItem {
  skill: string
  recommendation: string
  transferable_from: string | null
  priority_score: number
  resource: {
    title: string
    provider: string
    duration_hours: number
    is_free: boolean
    url: string
  }
}

export interface GapAnalysis {
  has_analysis: boolean
  gap_score: number
  target_role: string | null
  company: string | null
  missing_skills_count: number
  skill_gaps: SkillGapItem[]
  hours_to_close: number
  matched_count: number
  total_job_skills: number
  analyzed_at: string | null
  message?: string
}

export interface JourneyStage {
  id: number
  name: string
  completed: boolean
  current: boolean
}

export interface Journey {
  stages: JourneyStage[]
  current_stage: number
  track: string
  cohort: string | null
  next_step: string
  estimated_weeks_to_next: number
}

export interface ShowcaseItem {
  id: string
  label: string
  completed: boolean
  action_label?: string | null
  action_link?: string | null
}

export interface Showcase {
  showcase_active: boolean
  showcase_eligible: boolean
  profile_completeness: number
  checklist: ShowcaseItem[]
  completed_items: number
  total_items: number
  employer_views: number
  employer_shortlists: number
}

export interface ChatResponse {
  response: string
  status: string
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options)
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export function fetchProfile(studentId: string) {
  return fetchJSON<StudentProfile>(`${API_BASE}/student/${studentId}/profile`)
}

export function fetchMatches(studentId: string) {
  return fetchJSON<{ matches: JobMatch[] }>(`${API_BASE}/student/${studentId}/matches`)
}

export function fetchGapAnalysis(studentId: string) {
  return fetchJSON<GapAnalysis>(`${API_BASE}/student/${studentId}/gap-analysis`)
}

export function fetchJourney(studentId: string) {
  return fetchJSON<Journey>(`${API_BASE}/student/${studentId}/journey`)
}

export function fetchShowcase(studentId: string) {
  return fetchJSON<Showcase>(`${API_BASE}/student/${studentId}/showcase`)
}

export function sendChatMessage(studentId: string, message: string) {
  return fetchJSON<ChatResponse>(`${API_BASE}/student/${studentId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  })
}

// ---------- /api/student/{id}/gap-detail/{job_id} (drill) ----------

export interface MatchStrength {
  area?: string
  skill?: string
  evidence?: string
}

export interface MatchGap {
  area?: string
  skill?: string
  note?: string
}

export interface GapDetailCore {
  job_id: number
  title: string | null
  company: string | null
  city: string | null
  state: string | null
  is_remote: boolean | null
  skills_required: string[] | null
  job_description: string | null
  cosine_similarity: number | null
  match_rank: number | null
}

export interface GapDetailNarrative {
  verdict_line: string | null
  narrative_text: string | null
  match_strengths: MatchStrength[]
  match_gaps: MatchGap[]
  match_partial: MatchGap[]
  calibration_label: string | null
  cosine_similarity: number | null
  generated_at: string | null
}

export interface GapDetailGapRow {
  id: string
  target_role: string | null
  gap_score: number | null
  missing_skills: string[] | null
  recommendations: unknown
  analyzed_at: string | null
}

export interface CareerPathwayItem {
  job_id: number
  title: string
  company: string | null
  city: string | null
  state: string | null
  cosine_similarity: number
  match_rank: number | null
  verdict_line: string | null
  calibration_label: string | null
  gap_score: number | null
  missing_skills: string[] | null
}

export interface GapDetailPayload {
  core: GapDetailCore | null
  narrative: GapDetailNarrative | null
  gap_analysis: GapDetailGapRow | null
  career_pathway: CareerPathwayItem[]
}

export function fetchGapDetail(studentId: string, jobId: number | string) {
  return fetchJSON<GapDetailPayload>(
    `${API_BASE}/student/${studentId}/gap-detail/${jobId}`,
  )
}

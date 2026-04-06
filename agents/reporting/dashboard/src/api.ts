const BASE = 'http://localhost:8000/api'

export async function fetchOverview() {
  const r = await fetch(`${BASE}/overview`)
  return r.json()
}

export async function fetchSkills() {
  const r = await fetch(`${BASE}/skills`)
  return r.json()
}

export async function fetchPipeline() {
  const r = await fetch(`${BASE}/pipeline`)
  return r.json()
}

export async function fetchGaps() {
  const r = await fetch(`${BASE}/gaps`)
  return r.json()
}

export async function fetchJobs() {
  const r = await fetch(`${BASE}/jobs`)
  return r.json()
}

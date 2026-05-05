import React, { useEffect, useState } from 'react'
import { fetchOverview, fetchSkills, fetchPipeline, fetchGaps, fetchJobs } from './api'
import QueryInterface from './components/QueryInterface'
import DemandPanel from './panels/DemandPanel'
import PipelinePanel from './panels/PipelinePanel'
import GapPanel from './panels/GapPanel'

export default function App() {
  const [overview, setOverview] = useState<any>(null)
  const [skills, setSkills] = useState<any>(null)
  const [pipeline, setPipeline] = useState<any>(null)
  const [gaps, setGaps] = useState<any>(null)
  const [jobs, setJobs] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadAll() {
      try {
        const [o, s, p, g, j] = await Promise.all([
          fetchOverview(),
          fetchSkills(),
          fetchPipeline(),
          fetchGaps(),
          fetchJobs(),
        ])
        setOverview(o)
        setSkills(s)
        setPipeline(p)
        setGaps(g)
        setJobs(j)
      } catch (err: any) {
          setError(`Failed to load data: ${err.message}. Is the API running on localhost:8011?`)
      } finally {
        setLoading(false)
      }
    }
    loadAll()
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="text-slate-600">Loading dashboard data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100">
        <div className="rounded-lg bg-white p-8 shadow-md">
          <h2 className="mb-2 text-lg font-semibold text-red-600">Connection Error</h2>
          <p className="text-sm text-slate-600">{error}</p>
          <p className="mt-4 text-xs text-slate-400">
            Start the API: <code className="rounded bg-slate-100 px-2 py-1">uvicorn api:app --reload --port 8011</code>
          </p>
        </div>
      </div>
    )
  }

  const lastUpdated = overview?.last_updated
    ? new Date(overview.last_updated).toLocaleString()
    : 'Unknown'

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600 text-xl font-bold text-white">W</div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">Waifinder</h1>
              <p className="text-sm text-slate-500">Borderplex Labor Market Intelligence</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium text-slate-700">Workforce Solutions Borderplex</div>
            <div className="text-xs text-slate-400">Prepared for Alma | Updated {lastUpdated}</div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl space-y-6 px-6 py-6">
        {/* Query Interface */}
        <QueryInterface />

        {/* Panel 1: Labor Market Demand */}
        <DemandPanel skills={skills} jobs={jobs} overview={overview} />

        {/* Panel 2: Talent Pipeline */}
        <PipelinePanel pipeline={pipeline} overview={overview} />

        {/* Panel 3: Skills Gap */}
        <GapPanel gaps={gaps} />
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white py-4">
        <div className="mx-auto max-w-7xl px-6 text-center text-xs text-slate-400">
          Waifinder by Computing for All | JIE Deployment 001 | thewaifinder.com
        </div>
      </footer>
    </div>
  )
}

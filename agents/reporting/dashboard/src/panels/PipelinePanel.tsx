import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts'
import PanelHeader from '../components/PanelHeader'
import MetricCard from '../components/MetricCard'

interface PipelinePanelProps {
  pipeline: any
  overview: any
}

const STAGE_COLORS: Record<string, string> = {
  unknown: '#94A3B8',
  inactive: '#CBD5E1',
  applied: '#60A5FA',
  enrolled: '#34D399',
  completed: '#2563EB',
  dropped: '#F87171',
  placed: '#10B981',
  alumni: '#8B5CF6',
}

export default function PipelinePanel({ pipeline, overview }: PipelinePanelProps) {
  const byStatus = (pipeline?.by_status || []).map((s: any) => ({
    name: s.pipeline_status || 'unknown',
    value: s.n,
    fill: STAGE_COLORS[s.pipeline_status] || '#94A3B8',
  }))

  const completeness = (pipeline?.completeness_distribution || []).map((c: any) => ({
    name: c.band,
    count: c.n,
  }))

  const resumeStats = pipeline?.resume_stats || {}

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <PanelHeader title="Talent Pipeline" subtitle="Student progress through the education-to-work pipeline" />

      <div className="mb-6 grid grid-cols-4 gap-4">
        <MetricCard label="Total Students" value={overview?.total_students || 0} color="blue" />
        <MetricCard label="Resumes Parsed" value={overview?.resumes_parsed || 0} subtitle={`of ${(resumeStats.parsed || 0) + (resumeStats.unparsed || 0) + (resumeStats.no_resume || 0)}`} color="green" />
        <MetricCard label="Showcase Active" value={overview?.showcase_active || 0} color="amber" />
        <MetricCard label="No Resume" value={resumeStats.no_resume || 0} subtitle="Need re-engagement" color="red" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Students by Pipeline Status</h3>
          <BarChart width={440} height={280} data={byStatus} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value: number) => [`${value} students`]} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {byStatus.map((entry: any, i: number) => (
                <Cell key={i} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </div>

        <div>
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Profile Completeness Distribution</h3>
          <BarChart width={440} height={280} data={completeness} margin={{ left: 10, right: 20, top: 5, bottom: 5 }}>
            <XAxis dataKey="name" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={(value: number) => [`${value} students`]} />
            <Bar dataKey="count" fill="#6366F1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </div>
      </div>
    </div>
  )
}

import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts'
import PanelHeader from '../components/PanelHeader'
import MetricCard from '../components/MetricCard'

interface GapPanelProps {
  gaps: any
}

export default function GapPanel({ gaps }: GapPanelProps) {
  const gapData = (gaps?.gap_data || []).slice(0, 12).map((g: any) => ({
    name: g.skill.length > 20 ? g.skill.slice(0, 18) + '..' : g.skill,
    fullName: g.skill,
    demand: g.demand,
    supply: g.supply,
  }))

  const criticalGaps = gaps?.critical_missing_skills || []

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <PanelHeader title="Skills Gap Analysis" subtitle="Employer demand vs student skills supply" />

      <div className="mb-6 grid grid-cols-3 gap-4">
        <MetricCard
          label="Gap Coverage"
          value={`${gaps?.coverage_pct || 0}%`}
          subtitle="Student skills vs market demand"
          color={gaps?.coverage_pct >= 50 ? 'green' : gaps?.coverage_pct >= 20 ? 'amber' : 'red'}
        />
        <MetricCard label="Gap Analyses Run" value={gaps?.total_gap_analyses || 0} subtitle="Students assessed" color="blue" />
        <MetricCard label="Critical Missing Skills" value={criticalGaps.length} subtitle="Top gaps across students" color="red" />
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Demand vs Supply (Top 12 Skills)</h3>
          <BarChart width={580} height={380} data={gapData} layout="vertical" margin={{ left: 110, right: 20, top: 5, bottom: 5 }}>
            <XAxis type="number" tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={105} />
            <Tooltip
              formatter={(value: number, name: string) => [
                `${value}`,
                name === 'demand' ? 'Employer Demand' : 'Student Supply'
              ]}
            />
            <Legend />
            <Bar dataKey="demand" name="Employer Demand" fill="#2563EB" radius={[0, 4, 4, 0]} />
            <Bar dataKey="supply" name="Student Supply" fill="#10B981" radius={[0, 4, 4, 0]} />
          </BarChart>
        </div>

        <div>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Most Critical Missing Skills</h3>
          <div className="space-y-2">
            {criticalGaps.slice(0, 8).map((g: any, i: number) => (
              <div key={i} className="flex items-center justify-between rounded-lg bg-red-50 px-3 py-2">
                <span className="text-sm text-slate-700">{g.skill.length > 25 ? g.skill.slice(0, 23) + '..' : g.skill}</span>
                <span className="rounded-full bg-red-200 px-2 py-0.5 text-xs font-semibold text-red-800">{g.frequency}</span>
              </div>
            ))}
          </div>
          {criticalGaps.length === 0 && (
            <p className="text-sm text-slate-400 italic">Run gap analyses to populate</p>
          )}
        </div>
      </div>
    </div>
  )
}

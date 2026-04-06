import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts'
import PanelHeader from '../components/PanelHeader'
import MetricCard from '../components/MetricCard'

interface DemandPanelProps {
  skills: any
  jobs: any
  overview: any
}

const BLUE = '#2563EB'
const BLUE_LIGHT = '#93C5FD'

export default function DemandPanel({ skills, jobs, overview }: DemandPanelProps) {
  const topSkills = (skills?.top_skills || []).slice(0, 15).map((s: any) => ({
    name: s.skill_name.length > 25 ? s.skill_name.slice(0, 23) + '..' : s.skill_name,
    fullName: s.skill_name,
    count: s.demand_count,
    pct: s.pct_of_jobs,
  }))

  const topTitles = (jobs?.top_titles || []).slice(0, 10).map((j: any) => ({
    name: j.title.length > 30 ? j.title.slice(0, 28) + '..' : j.title,
    fullName: j.title,
    count: j.n,
  }))

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <PanelHeader title="Labor Market Demand" subtitle="Skills and roles employers are hiring for" />

      <div className="mb-6 grid grid-cols-3 gap-4">
        <MetricCard label="Total Job Listings" value={overview?.total_jobs || 0} color="blue" />
        <MetricCard label="Digital Roles" value={`${overview?.digital_role_pct || 0}%`} subtitle="of all listings" color="green" />
        <MetricCard label="Data Sources" value={jobs?.by_source?.length || 0} subtitle="Lightcast + Arbeitnow" color="slate" />
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Top 15 Skills by Employer Demand</h3>
        <BarChart width={900} height={420} data={topSkills} layout="vertical" margin={{ left: 150, right: 30, top: 5, bottom: 5 }}>
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={145} />
          <Tooltip
            formatter={(value: number, name: string, props: any) => [
              `${value} listings (${props.payload.pct}%)`,
              props.payload.fullName
            ]}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {topSkills.map((_: any, i: number) => (
              <Cell key={i} fill={i < 5 ? BLUE : BLUE_LIGHT} />
            ))}
          </Bar>
        </BarChart>
      </div>

      <div className="mt-6">
        <h3 className="mb-2 text-sm font-semibold text-slate-700">Top 10 Job Titles</h3>
        <BarChart width={900} height={300} data={topTitles} layout="vertical" margin={{ left: 200, right: 30, top: 5, bottom: 5 }}>
          <XAxis type="number" tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={195} />
          <Tooltip formatter={(value: number, _: string, props: any) => [`${value} listings`, props.payload.fullName]} />
          <Bar dataKey="count" fill="#10B981" radius={[0, 4, 4, 0]} />
        </BarChart>
      </div>
    </div>
  )
}

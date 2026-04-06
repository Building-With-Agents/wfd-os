import React from 'react'

interface MetricCardProps {
  label: string
  value: string | number
  subtitle?: string
  color?: 'blue' | 'green' | 'amber' | 'red' | 'slate'
}

const colorMap = {
  blue: 'border-blue-500 bg-blue-50',
  green: 'border-green-500 bg-green-50',
  amber: 'border-amber-500 bg-amber-50',
  red: 'border-red-500 bg-red-50',
  slate: 'border-slate-400 bg-slate-50',
}

export default function MetricCard({ label, value, subtitle, color = 'blue' }: MetricCardProps) {
  return (
    <div className={`rounded-lg border-l-4 p-4 shadow-sm ${colorMap[color]}`}>
      <div className="text-sm font-medium text-slate-600">{label}</div>
      <div className="mt-1 text-2xl font-bold text-slate-900">{typeof value === 'number' ? value.toLocaleString() : value}</div>
      {subtitle && <div className="mt-0.5 text-xs text-slate-500">{subtitle}</div>}
    </div>
  )
}

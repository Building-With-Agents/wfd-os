import React from 'react'

interface PanelHeaderProps {
  title: string
  subtitle?: string
  icon?: string
}

export default function PanelHeader({ title, subtitle, icon }: PanelHeaderProps) {
  return (
    <div className="mb-4 border-b border-slate-200 pb-3">
      <h2 className="text-lg font-semibold text-slate-800">
        {icon && <span className="mr-2">{icon}</span>}
        {title}
      </h2>
      {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
    </div>
  )
}

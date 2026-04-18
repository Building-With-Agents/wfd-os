"use client"

export interface TabDef {
  id: string
  label: string
  count?: number
}

export function TabsBar({
  tabs,
  activeId,
  onChange,
}: {
  tabs: TabDef[]
  activeId: string
  onChange: (id: string) => void
}) {
  return (
    <div className="cockpit-tabs-bar">
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          className="cockpit-tab"
          data-active={t.id === activeId ? "true" : "false"}
          onClick={() => onChange(t.id)}
        >
          {t.label}
          {t.count !== undefined && (
            <span className="cockpit-tab-count">{t.count}</span>
          )}
        </button>
      ))}
    </div>
  )
}

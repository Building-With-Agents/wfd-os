export function Topbar({ today }: { today: string }) {
  return (
    <div className="cockpit-topbar">
      <div style={{ display: "flex", gap: 24, alignItems: "baseline" }}>
        <span className="cockpit-topbar-brand">Computing for All</span>
        <span className="cockpit-topbar-meta">
          K8341 · WJI Good Jobs Challenge · Backbone Cockpit
        </span>
      </div>
      <div>
        <span className="cockpit-mockup-tag">Live · {today}</span>
      </div>
    </div>
  )
}

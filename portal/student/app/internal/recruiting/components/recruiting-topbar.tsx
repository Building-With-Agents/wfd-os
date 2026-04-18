// Recruiting topbar — simpler than Finance's. Breadcrumb-style
// rather than a dense K8341 + grant-name strip, because Recruiting
// isn't a single-grant surface the way Finance is. Reuses the
// .cockpit-topbar CSS hook so the shape + dark-green background match.

export function RecruitingTopbar({ leaf = "Workday view" }: { leaf?: string }) {
  return (
    <div className="cockpit-topbar">
      <div style={{ display: "flex", gap: 24, alignItems: "baseline" }}>
        <span className="cockpit-topbar-brand">Computing for All</span>
        <span className="cockpit-topbar-meta">
          internal{" / "}recruiting{" / "}
          <span style={{ color: "#F5F2E8", fontWeight: 500 }}>{leaf.toLowerCase()}</span>
        </span>
      </div>
      <div>
        <span className="cockpit-mockup-tag">Live · dev</span>
      </div>
    </div>
  )
}

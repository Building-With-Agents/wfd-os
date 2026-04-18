"use client"

// Phase 2A scaffold tab content. Each tab renders enough content to
// prove the layout + drill wiring works end-to-end against the
// fixture. Polish + the audit-surfaced patterns (multi-row thead,
// threshold-zone bar chart, wide-table-scroll, grouped-data-table
// subheaders) are picked up in later phases — see deferred_fixes.md.

import { Fragment } from "react"
import type { CockpitFixture } from "../../lib/types"
import { fmtUSD, fmtPct, fmtNum } from "../../lib/format"
import { VerdictBox } from "../cockpit-shell/verdict-box"

function StatCard({
  label,
  value,
  sub,
  valueColor,
}: {
  label: string
  value: React.ReactNode
  sub: React.ReactNode
  valueColor?: string
}) {
  return (
    <div className="cockpit-stat">
      <div className="cockpit-stat-label">{label}</div>
      <div className="cockpit-stat-value cockpit-num" style={{ color: valueColor }}>
        {value}
      </div>
      <div className="cockpit-stat-sub">{sub}</div>
    </div>
  )
}

function DrillableRow({
  drillKey,
  onOpen,
  children,
  style,
}: {
  drillKey: string
  onOpen: (key: string) => void
  children: React.ReactNode
  style?: React.CSSProperties
}) {
  return (
    <tr
      data-drill={drillKey}
      onClick={() => onOpen(drillKey)}
      style={{ cursor: "pointer", ...style }}
    >
      {children}
    </tr>
  )
}

// ---------------- BUDGET TAB ----------------

function BudgetTab({ data, onOpen }: TabProps) {
  const cats = data.summary.categories
  const totalBudget = data.summary.grant_total_budget
  const totalSpent = data.summary.gjc_paid + data.summary.cfa_contractor_paid + data.summary.backbone_qb_paid
  return (
    <div className="cockpit-tab-pane">
      <VerdictBox
        tone="watch"
        headline="Backbone runway lands within ~$3k of the September 30 grant end."
        body={
          <>
            At current burn (~$78k/month across backbone + contractors), the
            four backbone categories run out roughly aligned with grant end.
            CFA Contractors finishes with ~$0 if AI Engage and Pete &amp; Kelly
            stay at current pace. The $700k+ unspent in GJC Contractors is the
            lever — moving even $200k via budget amendment buys substantial
            recovery-work runway.
          </>
        }
      />

      <div className="cockpit-panel">
        <div className="cockpit-panel-head">
          <h3>Budget by category</h3>
          <span className="cockpit-helper">
            Click any category for drill detail
          </span>
        </div>
        <div style={{ padding: 0 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--cockpit-fs-body)" }}>
            <thead>
              <tr>
                <th style={cellHead("left", 20)}>Category</th>
                <th style={cellHead("right")}>Budget</th>
                <th style={cellHead("right")}>Spent</th>
                <th style={cellHead("right")}>Remaining</th>
                <th style={cellHead("right")}>% used</th>
                <th style={cellHead("right", 20, true)}>Monthly runway</th>
              </tr>
            </thead>
            <tbody>
              {cats.map((cat) => (
                <DrillableRow
                  key={cat.name}
                  drillKey={`category:${cat.name}`}
                  onOpen={onOpen}
                >
                  <td style={cell("left", 20)}>
                    {cat.name}
                    {cat.prorated && (
                      <span style={{ fontSize: "var(--cockpit-fs-label)", color: "var(--cockpit-text-3)", marginLeft: 4 }}>
                        · pro-rated*
                      </span>
                    )}
                  </td>
                  <td style={cell("right")} className="cockpit-num">{fmtUSD(cat.budget)}</td>
                  <td style={cell("right")} className="cockpit-num">{fmtUSD(cat.spent)}</td>
                  <td style={cell("right")} className="cockpit-num">{fmtUSD(cat.remaining)}</td>
                  <td style={cell("right")} className="cockpit-num">{fmtPct(cat.pct, 1)}</td>
                  <td style={cell("right", 20)} className="cockpit-num">
                    {fmtUSD(cat.remaining / data.summary.months_remaining)}/mo
                  </td>
                </DrillableRow>
              ))}
              <tr style={{ borderTop: "1px solid var(--cockpit-border-strong)", background: "var(--cockpit-surface-alt)", fontWeight: 600 }}>
                <td style={cell("left", 20)}>Total</td>
                <td style={cell("right")} className="cockpit-num">{fmtUSD(totalBudget)}</td>
                <td style={cell("right")} className="cockpit-num">{fmtUSD(totalSpent)}</td>
                <td style={cell("right")} className="cockpit-num">{fmtUSD(totalBudget - totalSpent)}</td>
                <td style={cell("right")} className="cockpit-num">
                  {fmtPct((totalSpent / totalBudget) * 100, 1)}
                </td>
                <td style={cell("right", 20)} className="cockpit-num">
                  {fmtUSD((totalBudget - totalSpent) / data.summary.months_remaining)}/mo
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ---------------- PLACEMENTS TAB ----------------

function PlacementsTab({ data, onOpen }: TabProps) {
  const p = data.placements
  return (
    <div className="cockpit-tab-pane">
      <VerdictBox
        tone="good"
        headline={`${p.confirmed_total} confirmed of ${fmtNum(p.grant_goal)} — PIP threshold cleared.`}
        body={
          <>
            Coalition reported {p.coalition_reported} placements through Q4 net of
            retractions. CFA verified {p.cfa_verified} additional Good Jobs via
            LinkedIn outreach. {p.q1_provider_actuals} more from Provider Q1 actuals.
            Recovery target Q2-Q3: {p.recovery_target} more to hit the {fmtNum(p.grant_goal)} goal.
          </>
        }
      />

      <div className="cockpit-three-col">
        <StatCard label="Confirmed total" value={p.confirmed_total} sub="Above PIP threshold" />
        <StatCard label="Q1 '26 actuals" value={p.q1_provider_actuals} sub="From provider invoices" />
        <StatCard label="Recovered (CFA)" value={data.recovered.total_validated} sub="Validated via LinkedIn" />
      </div>

      <div className="cockpit-panel">
        <div className="cockpit-panel-head">
          <h3>Quarterly placements by provider</h3>
          <span className="cockpit-helper">Click a row for the full provider drill</span>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--cockpit-fs-helper)" }}>
            <thead>
              <tr>
                <th style={cellHead("left", 20)}>Provider</th>
                {p.quarter_labels.map((q) => (
                  <th key={q} style={cellHead("right")}>{q}</th>
                ))}
                <th style={cellHead("right")}>Net</th>
                <th style={cellHead("right")}>Target</th>
                <th style={cellHead("right", 20)}>%</th>
              </tr>
            </thead>
            <tbody>
              {p.quarterly_placements.map((row) => (
                <DrillableRow
                  key={row.provider}
                  drillKey={`provider:${row.provider}`}
                  onOpen={onOpen}
                >
                  <td style={cell("left", 20)}>{row.provider}</td>
                  {row.q.map((v, i) => (
                    <td key={i} style={cell("right")} className="cockpit-num">
                      {v > 0 ? v : "—"}
                    </td>
                  ))}
                  <td style={cell("right")} className="cockpit-num">{row.net}</td>
                  <td style={cell("right")} className="cockpit-num">{row.target}</td>
                  <td style={cell("right", 20)} className="cockpit-num" data-tone={row.pct_tone}>
                    <span style={{ color: `var(--cockpit-${row.pct_tone})` }}>
                      {fmtPct(row.pct)}
                    </span>
                  </td>
                </DrillableRow>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ---------------- PROVIDERS TAB ----------------

function ProvidersTab({ data, onOpen }: TabProps) {
  const groups = [
    { label: "Active — closing out", rows: data.providers.active },
    { label: "Closed — placement-based", rows: data.providers.closed_with_placements },
    { label: "Closed — support / engagement", rows: data.providers.closed_support },
    { label: "ESD-directed terminations", rows: data.providers.terminated },
    { label: "CFA Contractors — recovery engine", rows: data.providers.cfa_contractors },
  ]
  return (
    <div className="cockpit-tab-pane">
      <div className="cockpit-three-col">
        <StatCard
          label="Total providers"
          value={Object.values(data.providers).flat().length}
          sub="Across all statuses"
        />
        <StatCard
          label="Active — closing out"
          value={data.providers.active.length}
          sub={`Plus ${data.providers.cfa_contractors.length} recovery contractors`}
        />
        <StatCard
          label="Closed or terminated"
          value={
            data.providers.closed_with_placements.length +
            data.providers.closed_support.length +
            data.providers.terminated.length
          }
          sub={`${data.providers.terminated.length} ESD-directed terminations`}
        />
      </div>

      <div className="cockpit-panel">
        <div className="cockpit-panel-head">
          <h3>Provider Reconciliation — v3 (3/27/2026)</h3>
          <span className="cockpit-helper">Amended Budget vs. QB Actual · click a provider for full detail</span>
        </div>
        <div style={{ padding: 0 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--cockpit-fs-body)" }}>
            <thead>
              <tr>
                <th style={cellHead("left", 20)}>Provider</th>
                <th style={cellHead("right")}>Amended Budget</th>
                <th style={cellHead("right")}>QB Actual</th>
                <th style={cellHead("right")}>Balance</th>
                <th style={cellHead("left", 20, true)}>Notes</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <Fragment key={g.label}>
                  <tr style={{ background: "var(--cockpit-surface-alt)" }}>
                    <td colSpan={5} style={{ ...cell("left", 20), fontSize: "var(--cockpit-fs-meta)", letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--cockpit-text-2)", fontWeight: 600 }}>
                      {g.label}
                    </td>
                  </tr>
                  {g.rows.map((p) => (
                    <DrillableRow
                      key={p.name}
                      drillKey={`provider:${canonicalProvider(p.name)}`}
                      onOpen={onOpen}
                    >
                      <td style={cell("left", 20)}>{p.name}</td>
                      <td style={cell("right")} className="cockpit-num">{fmtUSD(p.budget)}</td>
                      <td style={cell("right")} className="cockpit-num">{fmtUSD(p.qb_actual)}</td>
                      <td style={cell("right")} className="cockpit-num">{fmtUSD(p.balance)}</td>
                      <td style={{ ...cell("left", 20), fontSize: "var(--cockpit-fs-label)", color: "var(--cockpit-text-2)" }}>{p.notes}</td>
                    </DrillableRow>
                  ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// Provider name canonicalization for drill keys. Mirrors PROVIDER_CANONICAL
// in agents/finance/design/cockpit_data.py — extracted into a small map
// so React-side rows can resolve drill keys without round-tripping through
// the Python layer.
const PROVIDER_CANONICAL: Record<string, string> = {
  "Vets2Tech / St. Martin University": "Vets2Tech",
  "St Martins - Washington Vets 2 Tech": "Vets2Tech",
  "Year Up Puget Sound": "Year Up",
  "Code Day X Mint": "Code Day",
  "Code Day X MinT": "Code Day",
  "Code Day / MinT": "Code Day",
  "CodeDay/MinT": "Code Day",
  "PNW Cyber Challenge": "PNW CCG",
  "NCESD 171": "NCESD",
  "Riipen / North Seattle College": "Riipen",
  "Ada Developers": "Ada",
  "Ada Developers Academy": "Ada",
  "AI Engage Group LLC": "AI Engage",
  "Pete & Kelly Vargo": "CFA Contractors (Pete & Kelly Vargo)",
}
function canonicalProvider(name: string): string {
  return PROVIDER_CANONICAL[name] ?? name
}

// ---------------- TRANSACTIONS TAB ----------------

function TransactionsTab({ onOpen }: TabProps) {
  const txns = [
    { date: "2026-04-14", type: "Bill", vendor: "AI Engage Group LLC", memo: "March recovery work — 47 candidates reviewed", cat: "CFA Contractors", amt: 12000 },
    { date: "2026-04-12", type: "Purchase", vendor: "Brosnahan Insurance Agency", memo: "Workers comp Q2 2026", cat: "Personnel — Benefits", amt: 1847 },
    { date: "2026-04-10", type: "Purchase", vendor: "Unknown vendor ●", memo: "Office supplies", cat: "Other Direct", amt: 1243, anomaly: true },
    { date: "2026-04-08", type: "Bill", vendor: "Pete & Kelly Vargo", memo: "March outreach contract", cat: "CFA Contractors", amt: 18500 },
    { date: "2026-04-05", type: "JE", vendor: "Payroll Apr 1-15", memo: "K8341 allocation", cat: "Personnel — Salaries", amt: 17184 },
    { date: "2026-04-02", type: "Bill", vendor: "Code Day X MinT", memo: "Q1 final invoice — 8 placements × $3,222", cat: "GJC Contractors", amt: 25776 },
  ]
  return (
    <div className="cockpit-tab-pane">
      <div className="cockpit-three-col">
        <StatCard label="Mirrored from QB" value={53} sub="Sandbox · production sync pending" />
        <StatCard label="Tagged with Class" value="0 / 53" sub="Class tracking status pending Krista" />
        <StatCard label="Anomalies open" value={2} sub="Missing docs · 1 over-threshold CC" valueColor="var(--cockpit-watch)" />
      </div>
      <div className="cockpit-panel">
        <div className="cockpit-panel-head">
          <h3>Recent Transactions</h3>
          <span className="cockpit-helper">Click a vendor to drill into the provider</span>
        </div>
        <div style={{ padding: 0 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--cockpit-fs-body)" }}>
            <thead>
              <tr>
                <th style={cellHead("left", 20)}>Date</th>
                <th style={cellHead("left")}>Type</th>
                <th style={cellHead("left")}>Vendor</th>
                <th style={cellHead("left")}>Memo</th>
                <th style={cellHead("left")}>Category</th>
                <th style={cellHead("right", 20)}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((t, i) => {
                const drillKey = canonicalProvider(t.vendor)
                const isDrillable = !t.anomaly && drillKey !== t.vendor
                return (
                  <tr key={i}>
                    <td style={cell("left", 20)} className="cockpit-num">{t.date}</td>
                    <td style={cell("left")}>{t.type}</td>
                    <td
                      style={{
                        ...cell("left"),
                        cursor: isDrillable ? "pointer" : "default",
                        color: t.anomaly ? "var(--cockpit-watch)" : undefined,
                      }}
                      onClick={isDrillable ? () => onOpen(`provider:${drillKey}`) : undefined}
                    >
                      {t.vendor}
                    </td>
                    <td style={cell("left")}>{t.memo}</td>
                    <td style={cell("left")}>{t.cat}</td>
                    <td
                      style={{ ...cell("right", 20), color: t.anomaly ? "var(--cockpit-watch)" : undefined }}
                      className="cockpit-num"
                    >
                      {fmtUSD(t.amt)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div style={{ padding: "12px 20px", fontSize: "var(--cockpit-fs-helper)", color: "var(--cockpit-text-3)", background: "var(--cockpit-surface-alt)", borderTop: "1px solid var(--cockpit-border)" }}>
          Showing 6 of 53 · production QB sync pending
        </div>
      </div>
    </div>
  )
}

// ---------------- REPORTING TAB ----------------

function ReportingTab() {
  const cycle = [
    { num: "01", name: "March reconciled", date: "Apr 5 · ✓", state: "done" },
    { num: "02", name: "April advance drafted", date: "Apr 17 · today", state: "current" },
    { num: "03", name: "Submit to ESD", date: "Apr 30 · due", state: "" },
    { num: "04", name: "ESD funds advance", date: "~May 21 · est.", state: "" },
    { num: "05", name: "Spend through April", date: "Apr 30 close", state: "" },
    { num: "06", name: "Reconcile vs. actual", date: "May 5 · est.", state: "" },
  ]
  return (
    <div className="cockpit-tab-pane">
      <div className="cockpit-panel">
        <div className="cockpit-panel-head">
          <h3>April 2026 Monthly Advance Cycle</h3>
          <span className="cockpit-helper">First month under new monthly cadence</span>
        </div>
        <div className="cockpit-panel-body">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", border: "1px solid var(--cockpit-border)" }}>
            {cycle.map((step) => (
              <div
                key={step.num}
                style={{
                  padding: "12px 14px",
                  borderRight: "1px solid var(--cockpit-border)",
                  background:
                    step.state === "done"
                      ? "var(--cockpit-good-soft)"
                      : step.state === "current"
                      ? "var(--cockpit-surface-warm)"
                      : "var(--cockpit-surface)",
                  borderBottom:
                    step.state === "current"
                      ? "2px solid var(--cockpit-brand)"
                      : "none",
                }}
              >
                <div className="cockpit-num" style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)", marginBottom: 4 }}>{step.num}</div>
                <div style={{ fontSize: "var(--cockpit-fs-helper)", fontWeight: 500, marginBottom: 4 }}>{step.name}</div>
                <div className="cockpit-num" style={{ fontSize: "var(--cockpit-fs-meta)", color: "var(--cockpit-text-3)" }}>{step.date}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------- AUDIT TAB ----------------

function AuditTab({ onOpen }: TabProps) {
  const dims = [
    { id: "allowable_costs", label: "Allowable costs", what: "Every transaction maps to an allowable category", pct: 96, tone: "good" as const, owner: "Krista" },
    { id: "transaction_documentation", label: "Transaction documentation", what: "Vendor invoices, receipts, approvals on file", pct: 88, tone: "watch" as const, owner: "Krista" },
    { id: "time_effort", label: "Time & effort certifications", what: "Quarterly attestations from federally-funded staff", pct: 0, tone: "critical" as const, owner: "Ritu" },
    { id: "procurement", label: "Procurement & competition", what: "Competitive process or sole-source justification per contract", pct: 92, tone: "good" as const, owner: "Ritu" },
    { id: "subrecipient_monitoring", label: "Subrecipient monitoring", what: "Risk assessment, monitoring, follow-up per provider", pct: 81, tone: "watch" as const, owner: "Ritu · Bethany" },
    { id: "performance_reporting", label: "Performance reporting accuracy", what: "Reported placements reconcilable to source data", pct: 95, tone: "good" as const, owner: "Bethany · Gage" },
  ]
  return (
    <div className="cockpit-tab-pane">
      <VerdictBox
        headline="73% audit-ready. Biggest gap is time & effort certifications."
        body={
          <>
            Single Audit covering K8341 spend will be due roughly September 2027.
            ESD monitoring visits can happen anytime with 2-4 weeks notice. Worth
            closing the documentation gaps now while institutional memory is fresh,
            not in a year when staff may have turned over.
          </>
        }
      />
      <div className="cockpit-three-col">
        <StatCard label="Overall readiness" value="73%" sub="Across 6 audit dimensions" valueColor="var(--cockpit-watch)" />
        <StatCard label="Documentation gap" value={12} sub="Transactions over $2,500 missing invoices" />
        <StatCard label="T&E certifications" value="0 / 9" sub="Quarterly certs since grant start" valueColor="var(--cockpit-critical)" />
      </div>
      <div className="cockpit-panel">
        <div className="cockpit-panel-head">
          <h3>Audit Dimensions</h3>
          <span className="cockpit-helper">Click any dimension for the underlying gap list</span>
        </div>
        <div style={{ padding: 0 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "var(--cockpit-fs-body)" }}>
            <thead>
              <tr>
                <th style={cellHead("left", 20)}>Dimension</th>
                <th style={cellHead("left")}>What auditors look for</th>
                <th style={cellHead("right")}>Readiness</th>
                <th style={cellHead("left", 20)}>Owner</th>
              </tr>
            </thead>
            <tbody>
              {dims.map((d) => (
                <DrillableRow key={d.id} drillKey={`audit:${d.id}`} onOpen={onOpen}>
                  <td style={cell("left", 20)}>{d.label}</td>
                  <td style={{ ...cell("left"), color: "var(--cockpit-text-2)", fontSize: "var(--cockpit-fs-helper)" }}>{d.what}</td>
                  <td style={cell("right")} className="cockpit-num" data-tone={d.tone}>
                    <span style={{ color: `var(--cockpit-${d.tone})`, fontSize: "var(--cockpit-fs-label)" }}>{d.pct}%</span>
                  </td>
                  <td style={cell("left", 20)}>{d.owner}</td>
                </DrillableRow>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ---------------- shared cell-style helpers ----------------

function cellHead(align: "left" | "right", padHoriz = 0, last = false): React.CSSProperties {
  return {
    textAlign: align,
    fontSize: "var(--cockpit-fs-meta)",
    letterSpacing: "0.08em",
    textTransform: "uppercase",
    color: "var(--cockpit-text-3)",
    fontWeight: 600,
    padding: `8px ${last ? padHoriz + "px" : 12 + "px"} 8px ${padHoriz}px`,
    borderBottom: "1px solid var(--cockpit-border)",
  }
}
function cell(align: "left" | "right", padHoriz = 0): React.CSSProperties {
  return {
    textAlign: align,
    padding: `10px ${padHoriz || 12}px 10px ${padHoriz}px`,
    borderBottom: "1px solid var(--cockpit-border)",
    verticalAlign: "middle",
  }
}

// ---------------- dispatch ----------------

interface TabProps {
  data: CockpitFixture
  onOpen: (key: string) => void
}

export function TabContent({ tab, data, onOpen }: { tab: string } & TabProps) {
  switch (tab) {
    case "budget":       return <BudgetTab data={data} onOpen={onOpen} />
    case "placements":   return <PlacementsTab data={data} onOpen={onOpen} />
    case "providers":    return <ProvidersTab data={data} onOpen={onOpen} />
    case "transactions": return <TransactionsTab data={data} onOpen={onOpen} />
    case "reporting":    return <ReportingTab />
    case "audit":        return <AuditTab data={data} onOpen={onOpen} />
    default:             return <BudgetTab data={data} onOpen={onOpen} />
  }
}

"use client"

// Phase 2B tab content. Each tab takes its own typed payload from
// /api/finance/cockpit/tabs/{tab_id}. Dispatch reads the `tab`
// discriminator and renders the right component. Loading + error
// states are owned by cockpit-client.tsx — this module handles
// rendering only.

import { Fragment } from "react"
import type {
  TabPayload,
  BudgetTabPayload,
  PlacementsTabPayload,
  ProvidersTabPayload,
  TransactionsTabPayload,
  ReportingTabPayload,
  AuditTabPayload,
  Tone,
} from "../../lib/types"
import { fmtUSD, fmtPct, fmtNum } from "../../lib/format"
import { VerdictBox } from "../../../_shared/verdict-box"

// ---------- shared cell-style helpers ----------

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

// Mirrors PROVIDER_CANONICAL in agents/finance/design/cockpit_data.py so
// row-level drill keys resolve even when the reconciliation sheet uses a
// long variant name (NCESD 171 → NCESD).
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

// ---------- tab implementations ----------

function BudgetTab({ payload, onOpen }: { payload: BudgetTabPayload; onOpen: (k: string) => void }) {
  const { categories, totals, months_remaining, verdict } = payload
  return (
    <div className="cockpit-tab-pane">
      <VerdictBox tone={verdict.tone} headline={verdict.headline} body={verdict.body} />
      <div className="cockpit-panel">
        <div className="cockpit-panel-head">
          <h3>Budget by category</h3>
          <span className="cockpit-helper">Click any category for drill detail</span>
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
              {categories.map((cat) => (
                <DrillableRow key={cat.name} drillKey={`category:${cat.name}`} onOpen={onOpen}>
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
                    {fmtUSD(cat.remaining / months_remaining)}/mo
                  </td>
                </DrillableRow>
              ))}
              <tr style={{ borderTop: "1px solid var(--cockpit-border-strong)", background: "var(--cockpit-surface-alt)", fontWeight: 600 }}>
                <td style={cell("left", 20)}>Total</td>
                <td style={cell("right")} className="cockpit-num">{fmtUSD(totals.budget)}</td>
                <td style={cell("right")} className="cockpit-num">{fmtUSD(totals.spent)}</td>
                <td style={cell("right")} className="cockpit-num">{fmtUSD(totals.remaining)}</td>
                <td style={cell("right")} className="cockpit-num">{fmtPct(totals.pct, 1)}</td>
                <td style={cell("right", 20)} className="cockpit-num">
                  {fmtUSD(totals.remaining / months_remaining)}/mo
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function PlacementsTab({ payload, onOpen }: { payload: PlacementsTabPayload; onOpen: (k: string) => void }) {
  const { summary, recovered_total, quarterly_placements, quarter_labels, verdict } = payload
  return (
    <div className="cockpit-tab-pane">
      <VerdictBox tone={verdict.tone} headline={verdict.headline} body={verdict.body} />
      <div className="cockpit-three-col">
        <StatCard label="Confirmed total" value={summary.confirmed_total} sub="Above PIP threshold" />
        <StatCard label="Q1 '26 actuals" value={summary.q1_provider_actuals} sub="From provider invoices" />
        <StatCard label="Recovered (CFA)" value={recovered_total} sub="Validated via LinkedIn" />
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
                {quarter_labels.map((q) => (
                  <th key={q} style={cellHead("right")}>{q}</th>
                ))}
                <th style={cellHead("right")}>Net</th>
                <th style={cellHead("right")}>Target</th>
                <th style={cellHead("right", 20)}>%</th>
              </tr>
            </thead>
            <tbody>
              {quarterly_placements.map((row) => (
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

function ProvidersTab({ payload, onOpen }: { payload: ProvidersTabPayload; onOpen: (k: string) => void }) {
  const { stats, groups } = payload
  return (
    <div className="cockpit-tab-pane">
      <div className="cockpit-three-col">
        <StatCard
          label="Total providers"
          value={stats.total_providers}
          sub="Across all statuses"
        />
        <StatCard
          label="Active — closing out"
          value={stats.active}
          sub={`Plus ${stats.cfa_contractors} recovery contractors`}
        />
        <StatCard
          label="Closed or terminated"
          value={stats.closed}
          sub={`${stats.terminated} ESD-directed terminations`}
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
                <Fragment key={g.id}>
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

function TransactionsTab({ payload, onOpen }: { payload: TransactionsTabPayload; onOpen: (k: string) => void }) {
  const { stats, transactions, total_count, note } = payload
  return (
    <div className="cockpit-tab-pane">
      <div className="cockpit-three-col">
        <StatCard label="Mirrored from QB" value={stats.mirrored_from_qb} sub="Sandbox · production sync pending" />
        <StatCard label="Tagged with Class" value={`${stats.tagged_with_class.tagged} / ${stats.tagged_with_class.total}`} sub="Class tracking status pending Krista" />
        <StatCard label="Anomalies open" value={stats.anomalies_open} sub="Missing docs · 1 over-threshold CC" valueColor="var(--cockpit-watch)" />
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
              {transactions.map((t, i) => {
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
                    <td style={cell("left")}>{t.category}</td>
                    <td
                      style={{ ...cell("right", 20), color: t.anomaly ? "var(--cockpit-watch)" : undefined }}
                      className="cockpit-num"
                    >
                      {fmtUSD(t.amount)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div style={{ padding: "12px 20px", fontSize: "var(--cockpit-fs-helper)", color: "var(--cockpit-text-3)", background: "var(--cockpit-surface-alt)", borderTop: "1px solid var(--cockpit-border)" }}>
          Showing {transactions.length} of {total_count} · {note}
        </div>
      </div>
    </div>
  )
}

function ReportingTab({ payload }: { payload: ReportingTabPayload }) {
  const { cycle } = payload
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

// TODO(v1.2 cockpit-side step 3 follow-up): add pytest on this branch
// and cover the stat-card rendering branches (computed value,
// computed-null, placeholder, engine-unreachable). Tests deferred per
// scope; see integration_notes.md on feature/compliance-engine-extract.
function toneForOverallReadiness(
  pct: number | null,
  unreachable: boolean,
): Tone {
  // Mirror _tone_for_dimension in cockpit_api.py — null / unreachable
  // → neutral; otherwise band on the pct value.
  if (unreachable || pct === null) return "neutral"
  if (pct >= 90) return "good"
  if (pct >= 70) return "watch"
  return "critical"
}

const MUTED_COLOR = "var(--cockpit-text-3)"

function AuditTab({ payload, onOpen }: { payload: AuditTabPayload; onOpen: (k: string) => void }) {
  const { stats, dimensions, verdict, engine_status } = payload
  const unreachable = engine_status === "unreachable"

  // --- Overall Readiness card ---
  const overallPct = stats.overall_readiness_pct
  const overallValue = overallPct !== null ? `${overallPct}%` : "—"
  const overallTone = toneForOverallReadiness(overallPct, unreachable)
  const overallValueColor =
    overallTone === "neutral" ? MUTED_COLOR : `var(--cockpit-${overallTone})`
  const overallSub = unreachable
    ? "Engine unreachable"
    : stats.overall_readiness_basis.computed_dimension_count === 0
      ? "No dimensions measured yet"
      : `Across ${stats.overall_readiness_basis.computed_dimension_count} of ${stats.overall_readiness_basis.total_dimension_count} audit dimensions`

  // --- Documentation Gap card ---
  const docGapCount = stats.doc_gap_count
  const docGapValue: React.ReactNode = docGapCount !== null ? docGapCount : "—"
  const docGapValueColor = docGapCount === null ? MUTED_COLOR : undefined
  // Format threshold from cents → "$X,XXX" via fmtUSD; the engine
  // owns the threshold value so the cockpit doesn't duplicate it.
  const docGapThresholdDollars = fmtUSD(stats.doc_gap_threshold_cents / 100)
  const docGapSub = unreachable
    ? "Engine unreachable"
    : docGapCount !== null
      ? `Transactions over ${docGapThresholdDollars} missing invoices`
      : "Documentation gap not measurable"

  // --- T&E Certifications card ---
  // v1.2: always a placeholder value. Subcopy distinguishes
  // "not yet tracked" (roadmap) from "engine unreachable" (operational)
  // via the te_certs_status string per spec §v1.2.6.
  const teCertsValue = "—"
  const teCertsSub =
    unreachable || stats.te_certs_status === "engine_unreachable"
      ? "Engine unreachable"
      : "Not yet tracked — pending Employee↔Grant data"

  return (
    <div className="cockpit-tab-pane">
      <VerdictBox tone={verdict.tone} headline={verdict.headline} body={verdict.body} />
      <div className="cockpit-three-col">
        <StatCard
          label="Overall readiness"
          value={overallValue}
          sub={overallSub}
          valueColor={overallValueColor}
        />
        <StatCard
          label="Documentation gap"
          value={docGapValue}
          sub={docGapSub}
          valueColor={docGapValueColor}
        />
        <StatCard
          label="T&E certifications"
          value={teCertsValue}
          sub={teCertsSub}
          valueColor={MUTED_COLOR}
        />
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
              {dimensions.map((d) => {
                // Three-state readiness rendering per audit_readiness_tab_spec.md §v1.2.4:
                //   computed + pct     → "{pct}%"
                //   computed + null    → "Awaiting scan"
                //   placeholder        → "—"
                const readinessText =
                  d.pct !== null
                    ? `${d.pct}%`
                    : d.status === "computed"
                      ? "Awaiting scan"
                      : "—"
                return (
                  <DrillableRow key={d.id} drillKey={`audit:${d.id}`} onOpen={onOpen}>
                    <td style={cell("left", 20)}>{d.label}</td>
                    <td style={{ ...cell("left"), color: "var(--cockpit-text-2)", fontSize: "var(--cockpit-fs-helper)" }}>{d.what}</td>
                    <td style={cell("right")} className="cockpit-num" data-tone={d.tone}>
                      <span style={{ color: `var(--cockpit-${d.tone})`, fontSize: "var(--cockpit-fs-label)" }}>{readinessText}</span>
                    </td>
                    <td style={cell("left", 20)}>{d.owner}</td>
                  </DrillableRow>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ---------- dispatch ----------

export function TabContent({
  payload,
  onOpen,
}: {
  payload: TabPayload
  onOpen: (key: string) => void
}) {
  switch (payload.tab) {
    case "budget":       return <BudgetTab       payload={payload} onOpen={onOpen} />
    case "placements":   return <PlacementsTab   payload={payload} onOpen={onOpen} />
    case "providers":    return <ProvidersTab    payload={payload} onOpen={onOpen} />
    case "transactions": return <TransactionsTab payload={payload} onOpen={onOpen} />
    case "reporting":    return <ReportingTab    payload={payload} />
    case "audit":        return <AuditTab        payload={payload} onOpen={onOpen} />
    default: {
      const exhaustive: never = payload
      console.warn("Unknown tab payload", exhaustive)
      return null
    }
  }
}

export function TabLoading({ tabId }: { tabId: string }) {
  return (
    <div className="cockpit-tab-pane">
      <div style={{
        padding: 48,
        textAlign: "center",
        color: "var(--cockpit-text-3)",
        fontSize: "var(--cockpit-fs-body)",
      }}>
        Loading {tabId} content…
      </div>
    </div>
  )
}

export function TabError({ tabId, error, onRetry }: { tabId: string; error: string; onRetry: () => void }) {
  return (
    <div className="cockpit-tab-pane">
      <div className="cockpit-panel" style={{ padding: 24 }}>
        <h3 style={{ color: "var(--cockpit-critical)" }}>Couldn&apos;t load {tabId}</h3>
        <p style={{ marginTop: 8, color: "var(--cockpit-text-2)" }}>{error}</p>
        <button
          type="button"
          onClick={onRetry}
          style={{
            marginTop: 16,
            background: "var(--cockpit-brand)",
            color: "white",
            border: "none",
            padding: "8px 16px",
            cursor: "pointer",
            font: "inherit",
          }}
        >
          Retry
        </button>
      </div>
    </div>
  )
}

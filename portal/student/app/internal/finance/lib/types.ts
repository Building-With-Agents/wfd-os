// Polymorphic drill content schema. Mirrors the Python TypedDict shape
// in agents/finance/design/cockpit_data.py exactly.
//
// Section types are discriminated by the `type` field. Each renderer in
// components/drill-sections/ handles one variant. Tone values map to the
// CSS custom properties --good / --watch / --critical / --text-3.

export type Tone = "good" | "watch" | "critical" | "neutral"

export type SectionType =
  | "rows"
  | "table"
  | "chart"
  | "prose"
  | "verdict"
  | "timeline"
  | "action_items"

// ---------- Per-section types ----------

export interface RowsSection {
  type: "rows"
  title: string
  rows: Array<{
    label: string
    value: string | number
    emphasize?: boolean
  }>
  note?: string
}

export interface TableColumn {
  key: string
  label: string
  align?: "left" | "right"
  numeric?: boolean
}

export interface TableSection {
  type: "table"
  title: string
  columns: TableColumn[]
  rows: Array<Record<string, string | number | boolean>>
  note?: string
}

export interface AxisDef {
  key: string
  label?: string
}

export interface ChartReferenceLine {
  value: number
  label?: string
  tone?: Tone
}

export interface ChartSection {
  type: "chart"
  title: string
  chart_type: "bar" | "line" | "area"
  x_axis: AxisDef
  y_axis: AxisDef
  data: Array<Record<string, string | number> & { tone?: Tone }>
  reference_lines?: ChartReferenceLine[]
  note?: string
}

export interface ProseSection {
  type: "prose"
  title?: string
  body: string
}

export interface VerdictSection {
  type: "verdict"
  tone: Tone
  headline: string
  body: string
}

export interface TimelineEvent {
  date: string
  title: string
  tone?: Tone
}

export interface TimelineSection {
  type: "timeline"
  title: string
  events: TimelineEvent[]
}

export interface ActionItem {
  priority: "HIGH" | "MEDIUM" | "LOW"
  owner?: string
  text: string
}

export interface ActionItemsSection {
  type: "action_items"
  title: string
  items: ActionItem[]
}

export type DrillSection =
  | RowsSection
  | TableSection
  | ChartSection
  | ProseSection
  | VerdictSection
  | TimelineSection
  | ActionItemsSection

// ---------- Top-level drill entry ----------

export interface StatusChip {
  label: string
  tone: Tone
}

export interface DrillAction {
  label: string
  intent: "navigate" | "chat" | "export"
  target?: string
  prompt?: string
}

export interface DrillEntry {
  eyebrow: string
  title: string
  summary: string
  status_chip?: StatusChip
  sections: DrillSection[]
  actions?: DrillAction[]
  updated_at?: string
  source?: string
  note?: string
}

export type DrillRegistry = Record<string, DrillEntry>

// ---------- Cockpit-wide data shape (mirrors extract_all output) ----------

export interface SummaryCategory {
  name: string
  budget: number
  spent: number
  remaining: number
  pct: number
  color: string
  note?: string
  prorated?: boolean
}

export interface CockpitSummary {
  today: string
  days_remaining: number
  months_remaining: number
  grant_total_budget: number
  gjc_budget: number
  gjc_paid: number
  gjc_remaining: number
  training_budget: number
  training_paid: number
  training_remaining: number
  strategic_budget: number
  strategic_paid: number
  strategic_remaining: number
  cfa_contractor_budget: number
  cfa_contractor_paid: number
  cfa_contractor_remaining: number
  backbone_budget: number
  backbone_qb_paid: number
  backbone_remaining: number
  backbone_runway_combined: number
  categories: SummaryCategory[]
}

export interface ActionItem_ {
  priority: "HIGH" | "MEDIUM" | "LOW"
  area: string
  action: string
  owner: string
}

export interface ProviderRow {
  name: string
  budget: number
  qb_actual: number
  balance: number
  notes: string
  category: "training" | "strategic" | "cfa_contractor"
}

export interface ProvidersByGroup {
  active: ProviderRow[]
  closed_with_placements: ProviderRow[]
  closed_support: ProviderRow[]
  terminated: ProviderRow[]
  cfa_contractors: ProviderRow[]
}

export interface QuarterlyPlacementsRow {
  provider: string
  q: number[]
  total_through_q4_25: number
  q1_26_actual: number
  q1_26_retraction: number
  target: number
  net: number
  pct: number
  pct_tone: Tone
}

export interface Q1ProviderActual {
  provider: string
  expected: string
  actual: number | null
  rate: number
  invoice: number | null
  variance_color: string
}

export interface CockpitPlacements {
  confirmed_total: number
  pip_threshold: number
  grant_goal: number
  coalition_reported: number
  cfa_verified: number
  q1_provider_actuals: number
  vets2tech_q2_guaranteed: number
  apprenti_expected_low: number
  apprenti_expected_high: number
  recovery_target: number
  total_participants: number
  confirmed_plus_guaranteed: number
  linkedin_unreachable: number
  reachable_pool: number
  live_synced_minutes_ago: number
  q1_provider_actuals_breakdown: Q1ProviderActual[]
  quarterly_placements: QuarterlyPlacementsRow[]
  quarter_labels: string[]
}

export interface FinancialPerformanceRow {
  provider: string
  category: "training" | "recovery" | "cfa_direct"
  quarterly_payments: number[]
  quarterly_placements: number[]
  q1_26_invoice: number | null
  q1_26_placements: number
  q1_26_retraction: number
  total_paid: number
  total_placements_net: number
  recovered: number
  true_placements: number
  cpp: number
  true_cpp: number
  cpp_tone: Tone
  true_cpp_tone: Tone
}

export interface CockpitFixture {
  summary: CockpitSummary
  providers: ProvidersByGroup
  action_items: ActionItem_[]
  placements: CockpitPlacements
  cost_per_placement: {
    providers: Array<{
      name: string
      quarterly: number[]
      total_paid: number
      q1_26_retraction: number
      total_placements: number
      net_placements: number
      cpp: number
    }>
    totals: {
      total_paid: number
      total_placements: number
      net_placements: number
      weighted_cpp: number
    }
  }
  budget: Record<string, number>
  recovered: {
    by_provider: Record<string, number>
    by_status: Record<string, number>
    total_validated: number
    available: boolean
  }
  financial_performance: FinancialPerformanceRow[]
  drills: DrillRegistry
  trailing_q1_total: number
  high_priority_count: number
}

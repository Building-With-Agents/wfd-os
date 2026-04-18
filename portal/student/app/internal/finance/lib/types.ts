// Finance-specific type definitions.
// Cross-agent primitives (Tone, StatusChip, DrillEntry, all DrillSection
// variants, HeroGridCell, VerdictPayload) live in
// portal/student/app/internal/_shared/types.ts — this file imports and
// re-exports the ones Finance components reference, then layers
// Finance-specific API payload shapes on top.

import type {
  Tone,
  StatusChip,
  DrillEntry,
  DrillSection,
  VerdictPayload,
} from "../../_shared/types"

// Re-export cross-agent types so finance/**/*.tsx can keep importing
// from ./lib/types without reaching across the whole tree. New files
// in finance/ can import from _shared/types directly — either works.
export type { Tone, StatusChip, DrillEntry, DrillSection, VerdictPayload } from "../../_shared/types"
export type {
  RowsSection,
  TableSection,
  ChartSection,
  ProseSection,
  VerdictSection,
  TimelineSection,
  ActionItemsSection,
  TableColumn,
  ActionItem,
  TimelineEvent,
  AxisDef,
  ChartReferenceLine,
  DrillAction,
  DrillRegistry,
  SectionType,
  HeroGridCell,
} from "../../_shared/types"


// ---------- Finance domain types (derived from extract_all output) ----------

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

export interface ProviderRow {
  name: string
  budget: number
  qb_actual: number
  balance: number
  notes: string
  category: "training" | "strategic" | "cfa_contractor"
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


// ---------- Finance API payload shapes (cockpit_api.py) ----------

export interface CockpitStatusPayload {
  as_of: string
  months_remaining: number
  days_remaining: number
  last_sync: string | null
  data_sources: Array<{
    type: string
    path?: string
    files?: string[]
    available: boolean
    loaded_at: string | null
    status?: string
  }>
  tab_counts: {
    decisions: number
    providers: number
    transactions: number
    reporting: number
    audit: number
    high_priority: number
  }
}

export interface HeroCellPayload {
  drill_key: string
  label: string
  value: string
  value_suffix?: string
  subtitle: string
  status_chip: StatusChip
  updated_at: string
  source: string
  live_minutes_ago?: number
}

export interface HeroPayload {
  backbone: HeroCellPayload
  placements: HeroCellPayload
  cash: HeroCellPayload
  flags: HeroCellPayload
}

export interface DecisionItem {
  id: string
  drill_key: string
  title: string
  area: string
  action: string
  owner: string
  priority: "HIGH" | "MEDIUM" | "LOW"
  priority_tone: Tone
  status: string
  source: string
  created_at: string
}

export interface DecisionsPayload {
  items: DecisionItem[]
  sorted_by: string
  total: number
}


// ---------- Per-tab payloads ----------

export interface BudgetTabPayload {
  tab: "budget"
  verdict: VerdictPayload
  categories: SummaryCategory[]
  totals: { budget: number; spent: number; remaining: number; pct: number }
  months_remaining: number
}

export interface PlacementsTabPayload {
  tab: "placements"
  summary: {
    confirmed_total: number
    grant_goal: number
    pip_threshold: number
    coalition_reported: number
    cfa_verified: number
    q1_provider_actuals: number
    recovery_target: number
  }
  recovered_total: number
  quarterly_placements: QuarterlyPlacementsRow[]
  quarter_labels: string[]
  verdict: VerdictPayload
}

export interface ProvidersTabPayload {
  tab: "providers"
  stats: {
    total_providers: number
    active: number
    cfa_contractors: number
    closed: number
    terminated: number
  }
  groups: Array<{
    id: string
    label: string
    rows: ProviderRow[]
  }>
}

export interface TransactionRow {
  date: string
  type: string
  vendor: string
  memo: string
  category: string
  amount: number
  anomaly: boolean
}

export interface TransactionsTabPayload {
  tab: "transactions"
  stats: {
    mirrored_from_qb: number
    tagged_with_class: { tagged: number; total: number }
    anomalies_open: number
  }
  transactions: TransactionRow[]
  total_count: number
  note: string
}

export interface ReportingCycleStep {
  num: string
  name: string
  date: string
  state: "done" | "current" | ""
}

export interface ReportingTabPayload {
  tab: "reporting"
  cycle: ReportingCycleStep[]
}

export interface AuditDimension {
  id: string
  label: string
  what: string
  pct: number
  tone: Tone
  owner: string
}

export interface AuditTabPayload {
  tab: "audit"
  verdict: VerdictPayload
  stats: { overall: string; doc_gap: number; te_certs: string }
  dimensions: AuditDimension[]
}

export type TabPayload =
  | BudgetTabPayload
  | PlacementsTabPayload
  | ProvidersTabPayload
  | TransactionsTabPayload
  | ReportingTabPayload
  | AuditTabPayload

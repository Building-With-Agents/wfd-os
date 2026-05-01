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


// ---------- Recent Compliance Activity feed ----------
//
// Served by GET /cockpit/activity. Label translation is Python-side
// (agents/finance/audit_activity_labels.py) so the React component
// just renders strings. See spec §v1.2.9 for the "Recent Compliance
// Activity" panel contract.

export interface ActivityEntry {
  timestamp_label: string
  actor_label: string
  action_text: string
  metadata_text: string | null
  occurred_at: string
}

export interface ActivityPayload {
  entries: ActivityEntry[]
  engine_status: "ok" | "unreachable"
}


// ---------- Per-tab payloads ----------

export interface BudgetTabPayload {
  tab: "budget"
  verdict: VerdictPayload
  categories: SummaryCategory[]
  totals: { budget: number; spent: number; remaining: number; pct: number }
  months_remaining: number
  /** Personnel & Contractors sub-section payload. See
   *  agents/finance/design/personnel_contractors_view_spec.md and
   *  agents/finance/personnel.py::to_dict for the contract. */
  personnel: PersonnelPayload
}

// ---------- Personnel & Contractors sub-section ----------

export type PersonnelEngagementType = "employee" | "contractor" | "subcontractor" | ""
export type PersonnelBudgetLine =
  | "personnel_salaries"
  | "personnel_benefits"
  | "cfa_contractors"
  | "gjc_contractors_strategic"
  | string  // tolerate unknown lines surfaced by the parser

export interface PersonnelQuarterlyActual {
  quarter: string
  amount_paid: number
  source: string
  qb_vendor_name: string | null
}

export interface PersonnelQuarterlyProjection {
  quarter: string
  projected_amount: number
  projection_basis: string
}

export interface PersonnelPerson {
  id: string
  name: string
  role: string
  engagement_type: PersonnelEngagementType
  vendor_legal_entity: string | null
  start_date: string | null
  end_date: string | null
  budget_line: PersonnelBudgetLine
  amended_budget_total: number
  rate_amount: number
  rate_unit: string
  rate_basis: string
  rate_effective_date: string | null
  actuals: PersonnelQuarterlyActual[]
  projections: PersonnelQuarterlyProjection[]
  missing_required_fields: string[]
  projections_missing: boolean
  paid_to_date: number
  projected_total_remaining: number
  total_committed: number
  variance_vs_amended: number
  variance_pct: number
  amended_budget_remaining_periods: number
  documentation_incomplete: boolean
  drill_key: string  // "person:<id>"
}

export interface PersonnelRollup {
  budget_line: string
  label: string
  person_count: number
  amended_budget_total: number
  paid_to_date: number
  projected_total_remaining: number
  total_committed: number
  variance_vs_amended: number
  amendment_1_reference: number | null
  reconciliation_delta: number | null
  reconciles: boolean | null
}

export interface PersonnelReconciliationWarning {
  level: "error" | "warning" | "info"
  budget_line: string | null
  message: string
}

export interface PersonnelPayload {
  people: PersonnelPerson[]
  rollups: PersonnelRollup[]
  distinct_person_count: number
  summary: {
    paid_to_date: number
    total_committed: number
    variance_vs_amended: number
  }
  reconciliation_warnings: PersonnelReconciliationWarning[]
  extracted_at: string | null
  source_workbook: string | null
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
  // null when the dimension is a placeholder (no formula in v1.2) or
  // when it's computed but no data yet (e.g. scanner hasn't run).
  pct: number | null
  // "computed": a real formula exists on the engine side. "placeholder":
  // no formula in v1.2 — deferred to v1.3+ pending data-model additions.
  // See audit_readiness_tab_spec.md §v1.2.4 for the three-state contract.
  status: "computed" | "placeholder"
  tone: Tone
  owner: string
}

// Shape mirrors the compliance engine's /compliance/dimensions `stats`
// block (see agents/grant-compliance docs for v1.2.5). The cockpit
// fetches this once per extract_all refresh; when the engine is
// unreachable the cockpit synthesizes a fallback with null values
// and te_certs_status="engine_unreachable" per spec §v1.2.6.
export interface AuditStats {
  overall_readiness_pct: number | null
  overall_readiness_basis: {
    computed_dimension_count: number
    total_dimension_count: number
  }
  doc_gap_count: number | null
  doc_gap_threshold_cents: number
  te_certs_status: string
}

export type EngineStatus = "ok" | "unreachable"

export interface AuditTabPayload {
  tab: "audit"
  verdict: VerdictPayload
  stats: AuditStats
  // "ok" when the last compliance-engine fetch succeeded,
  // "unreachable" when it failed. Drives visually distinct rendering
  // for the degraded state (engine-offline variants in stat subcopy,
  // static verdict message). See spec §v1.2.6.
  engine_status: EngineStatus
  dimensions: AuditDimension[]
}

// Re-export the Compliance Requirements tab payload from its own module
// (compliance-types.ts) so the union below stays the single TabPayload
// definition without inlining 200+ lines of mirror types here.
export type { ComplianceTabPayload } from "./compliance-types"
import type { ComplianceTabPayload as _ComplianceTabPayloadImport } from "./compliance-types"

export type TabPayload =
  | BudgetTabPayload
  | PlacementsTabPayload
  | ProvidersTabPayload
  | TransactionsTabPayload
  | ReportingTabPayload
  | AuditTabPayload
  | _ComplianceTabPayloadImport

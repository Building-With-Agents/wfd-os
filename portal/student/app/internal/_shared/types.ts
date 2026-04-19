// Cross-agent types shared by every internal/* surface (Finance,
// Recruiting, future agents). Agent-specific payload shapes (Finance's
// HeroPayload, Recruiting's WorkdayStats, etc.) import from here.
//
// The drill content schema mirrors agents/finance/design/cockpit_data.py
// exactly. Recruiting will emit drill entries in the same shape so the
// shared DrillPanel + DrillSectionRenderer can render them unchanged.

export type Tone = "good" | "watch" | "critical" | "neutral"

export type SectionType =
  | "rows"
  | "table"
  | "chart"
  | "prose"
  | "verdict"
  | "timeline"
  | "action_items"

// ---------- per-section content ----------

export interface RowsSection {
  type: "rows"
  title: string
  rows: Array<{
    label: string
    value: string | number
    emphasize?: boolean
    /** When set, the value renders as an external link. Used by the
     *  student drill for LinkedIn / GitHub / portfolio URLs so the
     *  recruiter can click through without leaving keyboard focus. */
    href?: string
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
  /** When set, table rows become clickable. The renderer reads this
   *  key off each row and emits it to the optional onRowClick handler
   *  wired from the page level (Recruiting Workday uses this to open
   *  the student drill when a matched student is clicked). */
  row_click_key?: string
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

// ---------- top-level drill entry ----------

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

// ---------- hero grid (shared, any number of cells) ----------

export interface HeroGridCell {
  drill_key?: string      // optional — undefined = non-clickable stat cell
  label: React.ReactNode
  value: React.ReactNode
  value_suffix?: React.ReactNode
  subtitle?: React.ReactNode
  status_chip?: StatusChip
  live_minutes_ago?: number
}

// ---------- verdict payload (used by tab content + drill sections) ----------

export interface VerdictPayload {
  tone: Tone
  headline: string
  body: string
}

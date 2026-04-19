import type { DrillSection } from "../../types"
import { DrillSectionRows } from "./drill-section-rows"
import { DrillSectionTable } from "./drill-section-table"
import { DrillSectionChart } from "./drill-section-chart"
import { DrillSectionProse } from "./drill-section-prose"
import { DrillSectionVerdict } from "./drill-section-verdict"
import { DrillSectionTimeline } from "./drill-section-timeline"
import { DrillSectionActionItems } from "./drill-section-action-items"

// Polymorphic dispatch — one renderer per section.type. Add a new
// section type = add a renderer + a case here. Defaults to rows on
// unknown types since validate_registry() rejects unknown types at
// build time on the Python side.
//
// onTableRowClick is an optional hook propagated from the page level
// (Recruiting Workday) to enable click-through on table rows that
// declare a `row_click_key`. Other section types ignore it.

export function DrillSectionRenderer({
  section,
  onTableRowClick,
}: {
  section: DrillSection
  onTableRowClick?: (key: string, value: string | number | boolean) => void
}) {
  switch (section.type) {
    case "rows":
      return <DrillSectionRows section={section} />
    case "table":
      return <DrillSectionTable section={section} onRowClick={onTableRowClick} />
    case "chart":
      return <DrillSectionChart section={section} />
    case "prose":
      return <DrillSectionProse section={section} />
    case "verdict":
      return <DrillSectionVerdict section={section} />
    case "timeline":
      return <DrillSectionTimeline section={section} />
    case "action_items":
      return <DrillSectionActionItems section={section} />
    default: {
      const exhaustive: never = section
      console.warn("Unknown drill section type", exhaustive)
      return null
    }
  }
}

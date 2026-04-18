import type { VerdictSection } from "../../lib/types"

export function DrillSectionVerdict({ section }: { section: VerdictSection }) {
  return (
    <div className="cockpit-drill-section">
      <div className="cockpit-drill-verdict" data-tone={section.tone}>
        <div className="cockpit-drill-verdict-headline cockpit-display">
          {section.headline}
        </div>
        <div className="cockpit-drill-verdict-body">{section.body}</div>
      </div>
    </div>
  )
}

import type { ProseSection } from "../../lib/types"

export function DrillSectionProse({ section }: { section: ProseSection }) {
  return (
    <div className="cockpit-drill-section">
      {section.title && (
        <h3 className="cockpit-drill-section-title">{section.title}</h3>
      )}
      <p className="cockpit-drill-prose">{section.body}</p>
    </div>
  )
}

import type { ActionItemsSection } from "../../types"

export function DrillSectionActionItems({
  section,
}: {
  section: ActionItemsSection
}) {
  return (
    <div className="cockpit-drill-section">
      <h3 className="cockpit-drill-section-title">{section.title}</h3>
      <div className="cockpit-drill-action-items">
        {section.items.map((item, i) => (
          <div key={i} className="cockpit-drill-action-item">
            <div
              className="cockpit-drill-action-priority"
              data-priority={item.priority.toLowerCase()}
            >
              {item.priority}
            </div>
            {item.owner && (
              <div className="cockpit-drill-action-owner">{item.owner}</div>
            )}
            {!item.owner && <div />}
            <div className="cockpit-drill-action-text">{item.text}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

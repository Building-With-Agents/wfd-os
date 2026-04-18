import type { TimelineSection } from "../../types"

export function DrillSectionTimeline({ section }: { section: TimelineSection }) {
  return (
    <div className="cockpit-drill-section">
      <h3 className="cockpit-drill-section-title">{section.title}</h3>
      <div className="cockpit-drill-timeline">
        {section.events.map((e, i) => (
          <div key={i} className="cockpit-drill-timeline-event">
            <div className="cockpit-drill-timeline-date cockpit-num">
              {e.date}
            </div>
            <div
              className="cockpit-drill-timeline-title"
              data-tone={e.tone ?? "neutral"}
            >
              {e.title}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

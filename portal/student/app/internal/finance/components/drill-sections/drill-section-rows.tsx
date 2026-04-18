import type { RowsSection } from "../../lib/types"

export function DrillSectionRows({ section }: { section: RowsSection }) {
  return (
    <div className="cockpit-drill-section">
      <h3 className="cockpit-drill-section-title">{section.title}</h3>
      <div className="cockpit-drill-rows">
        {section.rows.map((r, i) => (
          <div key={i} className="cockpit-drill-kv">
            <div className="cockpit-drill-kv-label">{r.label}</div>
            <div
              className="cockpit-drill-kv-value cockpit-num"
              data-emphasize={r.emphasize ? "true" : undefined}
            >
              {r.value}
            </div>
          </div>
        ))}
      </div>
      {section.note && (
        <div className="cockpit-drill-callout">{section.note}</div>
      )}
    </div>
  )
}

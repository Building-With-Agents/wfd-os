import type { TableSection } from "../../types"

export function DrillSectionTable({ section }: { section: TableSection }) {
  return (
    <div className="cockpit-drill-section">
      <h3 className="cockpit-drill-section-title">{section.title}</h3>
      <table className="cockpit-drill-table">
        <thead>
          <tr>
            {section.columns.map((c) => (
              <th
                key={c.key}
                style={{ textAlign: c.align ?? "left" }}
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {section.rows.map((row, i) => {
            const isTotal = !!row.total
            return (
              <tr key={i} data-total={isTotal ? "true" : undefined}>
                {section.columns.map((c) => {
                  const v = row[c.key]
                  return (
                    <td
                      key={c.key}
                      className={c.numeric ? "cockpit-num" : undefined}
                      style={{ textAlign: c.align ?? "left" }}
                    >
                      {String(v ?? "")}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
      {section.note && (
        <div className="cockpit-drill-callout">{section.note}</div>
      )}
    </div>
  )
}

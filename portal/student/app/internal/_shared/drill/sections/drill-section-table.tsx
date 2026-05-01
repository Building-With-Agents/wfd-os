import type { TableSection } from "../../types"

type RowValue = string | number | boolean

/** Props: the polymorphic section; and an optional onRowClick hook
 *  used only when the section declares `row_click_key`. Recruiting's
 *  Workday drill uses this path to open a student drill when a matched
 *  student is clicked; other section renderers (Finance) ignore it. */
export function DrillSectionTable({
  section,
  onRowClick,
}: {
  section: TableSection
  onRowClick?: (key: string, value: RowValue) => void
}) {
  const clickKey = section.row_click_key
  const clickable = Boolean(clickKey && onRowClick)

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
            const handleClick = clickable && clickKey
              ? () => onRowClick!(clickKey, row[clickKey])
              : undefined
            return (
              <tr
                key={i}
                data-total={isTotal ? "true" : undefined}
                data-clickable={clickable ? "true" : undefined}
                onClick={handleClick}
                onKeyDown={handleClick ? (e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    handleClick()
                  }
                } : undefined}
                role={clickable ? "button" : undefined}
                tabIndex={clickable ? 0 : undefined}
              >
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

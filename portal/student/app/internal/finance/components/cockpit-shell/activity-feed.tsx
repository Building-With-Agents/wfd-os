// Static placeholder for Phase 2A. The real feed will read from an
// activity log endpoint in Phase 2B. Content mirrors the HTML
// cockpit's feed section so the visual treatment can be eyeballed.

const FEED = [
  { time: "10:42 AM", who: "Bethany", body: "2 placements verified via LinkedIn · count now 745" },
  { time: "9:42 AM", who: "QB sync", body: "4 new transactions mirrored · 1 anomaly flagged (vendor field empty on $1,243 charge)" },
  { time: "Yesterday", who: "Bethany", body: "Updated WJI TWC tracking · 3 new placements verified via LinkedIn" },
  { time: "Yesterday", who: "Krista", body: "Approved Pete & Kelly March invoice · $18,500 paid" },
  { time: "Apr 15", who: "Agent", body: "Generated April monthly placement dashboard for Andrew & Jenny" },
  { time: "Apr 12", who: "Ritu", body: "Updated CLAUDE.md with monthly advance cycle context" },
]

export function ActivityFeed() {
  return (
    <div className="cockpit-feed">
      <h4>Recent activity</h4>
      {FEED.map((row, i) => (
        <div key={i} className="cockpit-feed-item">
          <div className="cockpit-feed-time cockpit-num">{row.time}</div>
          <div>
            <span className="cockpit-feed-who">{row.who}</span> · {row.body}
          </div>
        </div>
      ))}
    </div>
  )
}

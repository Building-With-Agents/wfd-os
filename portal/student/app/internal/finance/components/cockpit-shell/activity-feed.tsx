// Recent Compliance Activity feed — renders pre-translated audit-log
// entries from the compliance engine via /cockpit/activity. Label
// construction (timestamp formatting, actor display names, per-action
// templates, classifier-action silencing) happens Python-side in
// agents/finance/audit_activity_labels.py so the component stays a
// pure renderer. See spec §v1.2.9.
//
// Three rendering states:
//   - unreachable: engine couldn't be reached; clear operational message.
//   - empty:       no compliance activity in the last 7 days.
//   - populated:   entries rendered newest first.
//
// TODO(v1.2 cockpit-side step 6 follow-up): the React component has
// no test infrastructure on this branch. The Python label module's
// logic is where tests would be most valuable; both deferred per
// scope. See integration_notes.md on feature/compliance-engine-extract.

import type { ActivityPayload } from "../../lib/types"

export function ActivityFeed({ activity }: { activity: ActivityPayload }) {
  if (activity.engine_status === "unreachable") {
    return (
      <div className="cockpit-feed">
        <h4>Recent Compliance Activity</h4>
        <div
          className="cockpit-feed-item"
          style={{ color: "var(--cockpit-text-3)" }}
        >
          Compliance engine unavailable — recent activity not available.
        </div>
      </div>
    )
  }

  if (activity.entries.length === 0) {
    return (
      <div className="cockpit-feed">
        <h4>Recent Compliance Activity</h4>
        <div
          className="cockpit-feed-item"
          style={{ color: "var(--cockpit-text-3)" }}
        >
          No recent compliance activity in the last 7 days.
        </div>
      </div>
    )
  }

  return (
    <div className="cockpit-feed">
      <h4>Recent Compliance Activity</h4>
      {activity.entries.map((entry, i) => (
        <div key={`${entry.occurred_at}-${i}`} className="cockpit-feed-item">
          <div className="cockpit-feed-time cockpit-num">
            {entry.timestamp_label}
          </div>
          <div>
            <span className="cockpit-feed-who">{entry.actor_label}</span> ·{" "}
            {entry.action_text}
            {entry.metadata_text && (
              <div
                style={{
                  fontSize: "var(--cockpit-fs-meta)",
                  color: "var(--cockpit-text-3)",
                  marginTop: 2,
                }}
              >
                {entry.metadata_text}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

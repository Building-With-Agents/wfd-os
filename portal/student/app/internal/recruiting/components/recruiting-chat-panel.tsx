"use client"

// Recruiting-side chat panel. Same visual language as the Finance
// chat-panel (cockpit-chat-col, pills, input row) but with
// Recruiting-shaped "Try asking…" prompts. Actual wiring (send to a
// Recruiting assistant agent) is deferred — this is a scaffold.

const PROMPTS = [
  "Who's a match for the Founding AI Engineer role?",
  "Find senior Python candidates in Seattle",
  "Which jobs have gone >30 days with no applications?",
  "Draft an outreach note for Alma's Borderplex team",
  "What's in flight this week?",
]

export function RecruitingChatPanel({ activeView }: { activeView: string }) {
  return (
    <div className="cockpit-chat-col">
      <div className="cockpit-chat-head">
        <div className="cockpit-chat-head-title">Recruiting Assistant</div>
        <div className="cockpit-chat-head-ctx">Context: {activeView}</div>
      </div>
      <div className="cockpit-chat-body">
        <div className="cockpit-chat-section-head">Try asking</div>
        <div className="cockpit-chat-pills">
          {PROMPTS.map((p, i) => (
            <button key={i} type="button" className="cockpit-chat-pill">
              <span className="cockpit-chat-pill-icon">→</span>
              {p}
            </button>
          ))}
        </div>
        <div className="cockpit-chat-section-head">Matching status</div>
        <div
          style={{
            background: "var(--cockpit-watch-soft)",
            borderLeft: "3px solid var(--cockpit-watch)",
            padding: "12px 14px",
            fontSize: "var(--cockpit-fs-helper)",
            color: "var(--cockpit-text-2)",
            lineHeight: 1.55,
          }}
        >
          <strong>Matching is paused</strong> while student embeddings are
          still being generated. Job embeddings are ready (29 roles).
          When the student side lights up, cosine-match queries will
          populate the &ldquo;matches&rdquo; columns automatically — no UI
          change. Tracking this as Phase 2D.
        </div>
      </div>
      <div className="cockpit-chat-input">
        <div className="cockpit-chat-input-box">
          Ask about jobs, candidates, the pipeline, outreach…
        </div>
        <div className="cockpit-chat-meta">⌘ Enter to send</div>
      </div>
    </div>
  )
}

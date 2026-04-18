"use client"

// Phase 2A scaffold — chat panel renders the same layout as the HTML
// cockpit (Try asking pills + a sample exchange) but doesn't talk to
// finance_agent yet. Phase 2 chat wiring is documented in
// agents/finance/design/chat_spec.md (a Phase 1F item, deferred).

const PROMPTS = [
  "Will we have enough money to pay people through September?",
  "What changed since last month?",
  "Show me the case for a budget amendment",
  "Draft this month's update for Andrew",
  "What's in next month's advance request?",
]

export function ChatPanel({ activeTab }: { activeTab: string }) {
  return (
    <div className="cockpit-chat-col">
      <div className="cockpit-chat-head">
        <div className="cockpit-chat-head-title">Finance Assistant</div>
        <div className="cockpit-chat-head-ctx">Context: {activeTab} tab</div>
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
        <div className="cockpit-chat-section-head">Last asked</div>
        <div
          style={{
            background: "var(--cockpit-brand)",
            color: "#F5F2E8",
            padding: "10px 14px",
            fontSize: "var(--cockpit-fs-body)",
            marginLeft: 32,
            marginBottom: 16,
          }}
        >
          Are we on track to spend the budget by September?
        </div>
        <div
          style={{
            fontSize: "var(--cockpit-fs-body)",
            lineHeight: 1.55,
            color: "var(--cockpit-text-1)",
          }}
        >
          <strong>Mostly yes, with one big asterisk.</strong>
          <br />
          <br />
          Backbone categories will land at roughly $0 on Sept 30 if April&apos;s
          burn matches recent quarters. CFA Contractors finishes around $0 too.
          The asterisk: <strong>GJC Contractors will be ~$700k underspent</strong>{" "}
          because all provider contracts ended March 31.
        </div>
      </div>
      <div className="cockpit-chat-input">
        <div className="cockpit-chat-input-box">
          Ask about runway, anomalies, providers, audit prep…
        </div>
        <div className="cockpit-chat-meta">⌘ Enter to send</div>
      </div>
    </div>
  )
}

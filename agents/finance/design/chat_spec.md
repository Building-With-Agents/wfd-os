# Finance Cockpit — Chat Specification

*Target path in repo: `agents/finance/design/chat_spec.md`*
*Status: Design complete, ready for implementation*
*Owner: Ritu (design) → Claude Code (implementation)*

## What this is

Two chat surfaces in the Finance Cockpit, working together:

1. **Broad chat** — a right-docked panel visible on every cockpit view. Answers cross-cutting questions about CFA's finances, compliance, and operations. This is the workhorse.
2. **Drill chat** — a collapsible section inside each drill panel. Answers questions scoped to the drill's data. This is the deepening layer.

Both call `finance_agent` via the existing `POST /api/assistant/chat` endpoint. The difference is what context is passed.

## Why two surfaces

Krista's known questions skew broad: "which providers haven't been monitored in six months?", "draft the update for Andrew", "what's in the advance request?" A drill-only chat would redirect the majority of her questions elsewhere. A broad-only chat would miss the anchored, in-context explanations that are valuable when she's already looking at a specific drill ("why is Ada in the red?").

The hybrid covers both. Broad chat is the default; drill chat is the specialization.

---

## Surface 1: Broad chat

### Placement

Right-docked column, visible on every tab of `/internal/finance`. This replaces the current `ChatPanel` placeholder in `CockpitShell`. Width: 360px (same as today). Collapsible via a chevron control at the top-left of the column — when collapsed, a narrow rail shows with a chat icon; clicking expands to full width. Collapse state persists in localStorage per user.

### Behavior

Single rolling session across the whole cockpit visit. Krista can ask about any tab, any provider, any timeframe — the agent has access to all cockpit data via its read-only tools (`get_qb_status`, `get_recent_transactions`, `get_open_compliance_flags`, `get_grants`, `get_allocation_queue`).

### Entry points

- The chat panel itself (always visible, right-docked)
- Seeded prompts at the top of the panel (3-5, clickable)
- Drill chat "escalation" — when a drill-scoped question goes out of scope, the user can click "Ask in broad chat" and the question pre-populates the broad chat input with focus

### Header

`Finance Assistant` — left-aligned. No context label (the chat is cockpit-wide, not tab-scoped). A "Clear conversation" link sits top-right, small and muted; clicking it starts a fresh session.

### Seeded prompts

Five prompts, shown above the input when the conversation is empty. Drawn from Krista's known question shapes:

- "Which providers are behind on reporting?"
- "Draft this month's update for Andrew"
- "What's in next month's advance request?"
- "Summarize recent activity on K8341"
- "What do I need to prepare for ESD monitoring?"

Prompts are clickable — clicking fills the input and sends. They're hidden after the first message.

### Input

Single-line text input at the bottom of the panel. `⌘ Enter` to send (`Ctrl+Enter` on Windows — keyboard handling must support both). Character cap: 1000. Placeholder text: `Ask about runway, providers, flags, audit prep…`

### Message rendering

User messages: right-aligned, neutral background.
Agent messages: left-aligned, white card.
Agent messages can include:
- Plain markdown text
- Links to drills in the cockpit (see "Drill linking" below)
- Tool-call indicators (small inline chip: `✓ Checked open compliance flags`) — one per tool call, rendered inline above the text response
- Error state (agent failure): shows the error message with a retry button

No avatars. No timestamps inline (timestamps appear on hover).

### Drill linking

When the agent's response references a specific drill (provider, category, audit dimension, flag), it renders as a clickable link in the message text: `[Ada →]`, `[Audit: Allowable Costs →]`. Clicking opens the drill in the cockpit. The chat conversation persists.

Server-side implementation: the agent is prompted to format drill references as markdown links with a known URL scheme (`/internal/finance#drill=provider:ada`). Client-side, a message renderer intercepts these links and opens the drill via the existing drill-opening mechanism instead of navigating. This requires no new backend work beyond the prompt update.

### Loading / error / empty

- **Empty** (no messages yet): seeded prompts shown, input focused on panel expand
- **Loading** (agent thinking): user message appears immediately; agent row shows three animated dots, left-aligned; input disabled
- **Error**: agent row shows `Couldn't answer that — {error}. Try again?` with retry button; doesn't block further questions
- **Tool in progress**: tool chip renders with a spinner until the tool returns, then the spinner becomes a checkmark

### Session behavior

- Session ID generated once per cockpit visit; persists across tab switches and drill opens
- Stored in React state (not localStorage) — closing the browser tab ends the session
- Server-side: `agent_conversations` row keyed by session ID with `metadata.scope: "cockpit-broad"` and `metadata.user: "krista"` (or whoever)
- "Clear conversation" generates a new session ID and clears the client message list; the old row stays in the DB for forensics

---

## Surface 2: Drill chat

### Placement

Collapsible bottom sheet inside each drill panel. When the drill panel is open, a section at the bottom of the drill (below action items, below the existing footer area) shows a collapsed `Discuss this drill` bar. Clicking expands it upward to ~40% of the drill panel height, pushing the drill content up but keeping the top of it visible (title, summary, first section).

When collapsed: a single-line bar at the bottom of the drill with `💬 Discuss this drill` and a chevron-up icon. Height: 44px.

When expanded: the bottom ~40% of the drill becomes the chat surface; the top 60% shows the drill content with scroll. A chevron-down icon in the chat header collapses it back. Escape collapses if chat is empty; if chat has messages, Escape closes the whole drill (same as today).

### Behavior

Per-drill ephemeral session. Each time the drill opens, a fresh conversation starts. Closing the drill ends the session. Re-opening the drill starts a new one. No cross-drill memory.

The agent receives the full drill payload as context on every turn — sections, verdicts, rows, tables, the works. The agent is explicitly scoped: answer only questions about this drill. Out-of-scope questions get redirected to broad chat.

### Header

When expanded: `Discuss: {drill.title}` on the left. `→ Ask in broad chat` link on the right — clicking copies the current input (if any) into broad chat, opens broad chat panel if collapsed, and collapses drill chat.

### Seeded prompts

Three prompts per drill type, generated server-side and returned as part of the drill payload (new field: `discussion_prompts: string[]`). The prompts are data-aware — wording shifts based on the drill's tone and values. Examples:

- **Provider drill (red band)**: "Why is this in the red band?" / "What's driving the CPP?" / "Which transactions contributed most?"
- **Provider drill (green band)**: "What's keeping this on track?" / "Show me the spend pattern" / "Any concentration risk?"
- **Backbone drill**: "What happens if we don't move the $700k?" / "Where's the burn concentrated?" / "When do we run out?"
- **Audit dimension drill**: "What's the biggest open gap?" / "What closes this fastest?" / "Which providers contribute?"

Prompts hidden after first message.

### Input

Same pattern as broad chat: single-line, `⌘/Ctrl Enter` to send, 500 char cap (shorter than broad chat — drill questions should be focused). Placeholder: `Ask about {drill.title}…`

### Message rendering

Same pattern as broad chat with one addition: **source chips**.

Every agent message includes source chips below the text: small pill buttons like `Source: Contract & Spend` or `Source: Placements by quarter`. Clicking a chip scrolls the drill content (in the visible top portion of the drill panel) to that section and flashes it briefly.

Sources come from the server response: the agent returns `sources: ["section_id"]` and the renderer maps IDs to section titles.

### Scope enforcement

The agent is prompted with the drill payload as a system-level context block appended to the user turn (using Option 1 from the finance_agent report — ~10 lines of change in `api.py`). The system instruction reads:

> You are answering questions about the '{drill_title}' drill in the Finance Cockpit. You have access to the following data about this drill: {drill_payload_json}. Answer only questions that can be answered from this data. If the user asks about something outside this drill (other providers, other categories, general compliance questions), respond with: "That's outside this drill's scope — try the broader chat panel for that." Do not guess or draw on general knowledge beyond this drill's data.

Out-of-scope responses use a consistent format (detected client-side by a magic string or a structured flag — prefer structured):

```json
{ "response": "...", "out_of_scope": true }
```

When `out_of_scope: true`, the message renders with a distinct style (muted background, different icon) and includes an automatic `→ Ask this in broad chat` button that copies the question to broad chat.

### Loading / error / empty

Same patterns as broad chat. One addition: if the drill payload has `sections: []` (shouldn't happen, but), the Discuss bar is disabled with tooltip "No data to discuss."

### Session behavior

- Session ID: `drill-{drill_key}-{timestamp}-{random}`
- Fresh session per drill open
- Stored in React state keyed by drill key; discarded when drill closes
- Server-side: `agent_conversations` row with `metadata.scope: "drill-ephemeral"`, `metadata.drill_key: "provider:ada"`, `metadata.drill_title: "Ada"` — makes the rows filterable later for analysis or pruning

---

## Backend changes

### 1. `POST /api/assistant/chat` — inject context

Currently accepts `context: dict` but doesn't use it. Change: when `context.drill_payload` is present, render it as a formatted block and prepend to the user message. Specifically in `agents/assistant/base.py` or `api.py`:

```python
if context and context.get("drill_payload"):
    drill_context = f"[Context: {context['drill_title']} drill]\n{json.dumps(context['drill_payload'], indent=2)}\n\n"
    user_message_with_context = drill_context + user_message
else:
    user_message_with_context = user_message
```

Plus: when `context.scope == "drill"`, append scope-enforcement instructions to the system prompt dynamically (or pass as part of the user turn; either works with Gemini).

Plus: structured out-of-scope signaling. When the agent response matches a recognizable out-of-scope phrasing, set `out_of_scope: true` in the response. Implementation: prompt the agent to return responses in a structured JSON format when scope-enforced, or detect client-side by pattern-matching the redirect phrase. Prefer structured.

### 2. `GET /cockpit/drills/{key}` — add discussion_prompts

Server generates 3 prompts per drill based on drill type and tone. Returned as `discussion_prompts: string[]`.

### 3. Section IDs on drills

Every section in `drill.sections[]` needs a stable `id: string` field. If sections don't have IDs today, add them — it's a small schema change that unlocks source-chip anchoring.

### 4. Session metadata

`BaseAgent._save_session` needs to respect passed-in `metadata`. Currently it writes session metadata but check whether it merges with passed-in values — we want `scope`, `drill_key`, etc. to land in the DB row.

---

## Frontend changes

### Components to modify

- `CockpitShell` — restore the chat column (currently renders `ChatPanel` placeholder); wire real chat state
- `ChatPanel` — rewrite from placeholder to live chat; lift the pattern from `operations/finance-client.tsx`
- `DrillPanel` — add collapsible bottom sheet for drill chat

### New components

- `BroadChat` (replaces current `ChatPanel` placeholder)
- `DrillChat` — the bottom sheet
- `ChatMessage` — shared message renderer (used by both surfaces); handles user/agent/tool/error/out-of-scope states, renders drill links, renders source chips
- `useBroadChatSession()` — hook for cockpit-wide chat state (session ID, messages, loading state)
- `useDrillChatSession(drillKey)` — hook for ephemeral drill chat state; resets on drillKey change

### Handoff between surfaces

- Drill chat `→ Ask in broad chat` action: imperatively call a broad-chat method to pre-populate the input and focus. Needs a small cross-component bridge (context provider or a zustand store).
- Broad chat drill links: intercept markdown link clicks with href matching `/internal/finance#drill=...`, call the existing drill-opening mechanism instead of navigating.

### Remove

- The current hard-coded 5 "Try asking" pills in `ChatPanel`
- The canned "Last asked" static exchange
- The file-level comment pointing to this spec (which no longer doesn't exist)

---

## Voice and copy

The agent should sound like the cockpit sounds today — executive-audience plain English, specific numbers, no hedging. Krista is the audience. The system prompt should reinforce this explicitly:

> You are the Finance Assistant inside CFA's Finance Cockpit. Your user is Krista, CFA's bookkeeper. Answer in plain English, with specific numbers where relevant. Match the tone of the cockpit's verdicts: direct, factual, and practical. When you don't know something, say so plainly. Don't hedge. Don't apologize for being an AI.

The scope-enforcement phrasing for out-of-scope drill questions should be consistent across all drills:

> That's outside this drill's scope. Try the broader chat panel for cross-cutting questions.

---

## Desktop-only, ≥1280px

The cockpit has no responsive behavior today. This spec inherits that. The broad chat column is 360px fixed; drill chat bottom sheet is constrained by the drill panel width (min(560px, 100vw)). Below 1280px viewport, behavior is undefined. Explicit out-of-scope for v1.

Follow-up: ask Krista what screen she uses. If 1366×768, the broad chat panel squeeze warrants a responsive pass. If 1440px+, no change needed.

---

## Success criteria

Measured over two weeks of Krista using the cockpit daily:

**Broad chat:**
1. Used at least daily
2. Messages average 2+ turns (she's having conversations, not single-shot queries)
3. At least one drill link clicked per session (the linking between chat and cockpit is working)

**Drill chat:**
1. Used in 20%+ of drill opens (proves there's real demand for anchored questions)
2. Source chips clicked in 30%+ of responses (proves the anchoring is valuable, not decorative)
3. Out-of-scope rate under 40% (proves the scoping is well-calibrated; higher means the seeded prompts or scope are miscalibrated)
4. At least 10% of drill-chat messages result in `→ Ask in broad chat` escalation (proves the handoff is used)

**If drill chat fails these criteria, kill it — don't expand it.** The signal is that chat works broadly but anchored questions aren't common enough to justify the surface. Broad chat alone is sufficient.

**If broad chat fails these criteria, reassess the whole product.** It means chat isn't the right affordance and something else (better verdicts, different drafting workflow, a different surface entirely) should replace it.

---

## Out of scope for v1

- Persistence of broad-chat sessions across browser closes
- Chat history UI ("recent conversations" list)
- Cross-drill memory ("compare Ada to Boldly" inside a drill)
- Streaming responses (complete-response for v1; streaming is a polish upgrade)
- Voice input / dictation
- Sharing conversations (links, exports, etc.)
- Per-user preferences (response length, verbosity)
- Multi-user awareness (Krista and Ritu chatting in parallel — v1 assumes single-user)
- Azure OpenAI adapter migration (finance_agent stays on Gemini for v1; adapter migration is a separate ticket per CLAUDE.md)

Each of these is a well-scoped follow-up. They stay out to keep v1 honest.

---

## Implementation sequence

Claude Code should execute in this order, with a commit per step:

1. **Backend: context injection + out-of-scope signaling** (`api.py` + `base.py`) — the 10-line prompt change plus structured response handling. Test via curl before moving on.
2. **Backend: discussion_prompts in drill payload** — generator function per drill type; test via `curl /cockpit/drills/provider:ada`.
3. **Backend: section IDs on drill sections** — schema change + migration path for existing drills.
4. **Frontend: BroadChat component** — rewrite `ChatPanel` using the operations-page pattern, wire session management, add drill-link interception. Ship this alone; it's usable without drill chat.
5. **Frontend: DrillChat component** — collapsible bottom sheet, source chips, escalation handoff. Ship after broad chat is working.
6. **Remove: placeholder code** — old `ChatPanel` hardcoded content, the file comment referencing this spec.

Each step should be a separate PR or commit so review and rollback are clean.

---

## Questions Claude Code should ask Ritu before implementing

1. **Gemini prompt format** — structured JSON responses vs plain text with pattern detection for out-of-scope? (Gemini supports structured output; preference depends on testing.)
2. **Session ID format** — is the proposed `drill-{drill_key}-{timestamp}-{random}` convention fine, or does the team have a UUID convention already?
3. **Seeded prompt generation** — should prompts be hand-authored per drill type (deterministic, copy-reviewable) or LLM-generated (dynamic, adapts to data)? Spec assumes hand-authored; flag if different.
4. **Cross-component state** — preferred pattern for drill-chat → broad-chat handoff? Zustand store? React context? Imperative refs? Pick whatever matches existing patterns in the codebase.

---

## Implementation decisions (answered 2026-04-24)

1. **Gemini response format** — structured JSON output for drill chat only; broad chat stays free-text. Gemini can't combine tool-calling with structured output on the same turn, and drill chat doesn't need tools (payload is injected), so the split is clean.
2. **Session ID format** — keep existing `str(uuid.uuid4())` convention. Put `scope`, `drill_key`, `drill_title`, `user` in `agent_conversations.metadata` (JSONB) for filterability.
3. **Seeded prompt generation** — hand-authored, keyed by drill_key prefix, 3 per type.
4. **Cross-component state** — React Context defined in `CockpitClient`, exposing `{ prepopulateBroadChat(text), openBroadChat() }`. No new dependencies.

---

*End of spec.*

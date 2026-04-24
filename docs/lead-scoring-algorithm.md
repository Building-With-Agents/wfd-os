# WFD OS Lead Scoring Algorithm

**Version:** 0.1 (Design)
**Last updated:** 2026-04-07
**Owner:** Marketing Agent (Agent 12) + Apollo integration
**Status:** Design doc — not yet implemented

---

## Purpose

Route leads to the right outreach path at the right intensity. Specifically:

1. Tell Jason which prospects to prioritize each morning
2. Decide when a lead graduates from sequence-based outreach to personal outreach from Ritu
3. Decide when a lead moves to **Ready to Scope** (triggers the Scoping Agent)
4. Keep low-signal leads in warm-up sequences without burning them with manual outreach
5. Identify leads that should be dropped (unresponsive, bad fit)

**Core principle:** The score is a forecast of *probability of closing a $20-35K engagement*, not engagement volume. A prospect who downloaded 3 reports but works at a 5-person nonprofit scores lower than a prospect who downloaded one report and works at a regional workforce board.

---

## Lead Lifecycle States

Every lead sits in one of these states at any time. Scores move leads between states.

| State | Score Range | Meaning | Apollo Stage | Who Acts |
|---|---|---|---|---|
| `cold` | 0-19 | In Apollo, no engagement yet | Cold | Marketing Agent (automated sequences only) |
| `warming` | 20-39 | Opened 1+ emails or clicked once | Approaching | Marketing Agent (continue sequence) |
| `engaged` | 40-59 | Replied to email OR downloaded 1 asset | Replied / Interested | Jason (personal outreach) |
| `qualified` | 60-79 | Multiple signals, fits ICP | Interested | Jason (scheduling conversation) |
| `ready_to_scope` | 80-100 | Confirmed intent + fit | **Ready to Scope** (new stage) | Scoping Agent auto-fires |
| `dropped` | N/A | Explicit opt-out or 90-day silence | Do Not Contact / Unresponsive | No action |

---

## Data Sources (Signals)

Every scored lead has a `lead_signals` row per signal event. Signals are additive — multiple events compound the score.

### Signal Categories

**A. Content Engagement (via `marketing_leads` + page tracking)**
- Gated PDF download (research report)
- Blog post read (3+ minute dwell time)
- Case study read
- Multiple pages viewed in single session
- Return visit within 7 days

**B. Direct Conversation (via `agent_conversations`)**
- Chat started with Consulting Agent
- Chat reached 5+ exchanges
- `INTAKE_COMPLETE` signal fired
- Contact info volunteered in chat

**C. Form Submission (via `project_inquiries`)**
- Consulting inquiry form submitted
- Free-text problem description provided (not just "exploring")
- Budget range provided
- Timeline provided

**D. Email Engagement (via Apollo webhooks)**
- Email opened (first time)
- Email opened (repeat)
- Link clicked
- Email replied
- Calendar meeting booked

**E. Firmographic Fit (inferred or looked up)**
- Organization type (workforce board, healthcare, professional services = high fit)
- Organization size (mid-market = best fit, under 10 = poor fit, enterprise = partial fit)
- Geographic region (WA + TX = priority, other US = standard, international = low)
- Role seniority of contact (director+ = high, individual contributor = low)

---

## Scoring Weights

Each signal adds points. Weights favor **depth** (replies, forms) over **breadth** (opens, page views). Scores cap at 100.

### Content Engagement

| Signal | Points | Notes |
|---|---|---|
| Gated PDF download | +15 | Email required — strong intent signal |
| Blog post read (3+ min) | +3 | Soft signal |
| Case study read | +8 | Stronger than blog — decision-stage content |
| 3+ pages in single session | +5 | Research behavior |
| Return visit within 7 days | +7 | Sustained interest |
| Downloaded 2+ reports | +10 (additional) | Bonus for multi-asset engagement |

### Direct Conversation

| Signal | Points | Notes |
|---|---|---|
| Started chat with Consulting Agent | +5 | Low commitment |
| Chat reached 5+ exchanges | +15 | Real engagement |
| Chat reached 10+ exchanges | +25 | Serious conversation |
| `INTAKE_COMPLETE` triggered | +35 | Agent qualified them |
| Volunteered contact info in chat | +10 | Ready to be contacted |

### Form Submission

| Signal | Points | Notes |
|---|---|---|
| Consulting inquiry form submitted | +40 | Strongest single signal |
| Problem description 100+ words | +10 (bonus) | Real problem, not curiosity |
| Budget range provided | +10 (bonus) | Qualified buyer |
| Timeline provided | +5 (bonus) | Active timing |

### Email Engagement (from Apollo)

| Signal | Points | Notes |
|---|---|---|
| Email opened (first time) | +2 | Minimal signal |
| Email opened (3+ times same message) | +3 (bonus) | Re-engaged |
| Link clicked | +5 | Active interest |
| Email replied | +20 | Strong signal |
| Calendar meeting booked | +30 | Near-certain conversion |

### Firmographic Fit (multiplier, not additive)

The firmographic fit score is calculated once and applied as a multiplier to the engagement score.

| Fit Factor | Score |
|---|---|
| Perfect fit (WA/TX workforce board, mid-market) | 1.0x |
| Strong fit (healthcare/prof services, mid-market) | 0.9x |
| Partial fit (right type, wrong size) | 0.7x |
| Weak fit (adjacent industry) | 0.5x |
| Poor fit (wrong industry or too small) | 0.3x |
| Anti-fit (enterprise expecting enterprise pricing) | 0.2x |

**Why multiplier:** A prospect can't "earn" their way to a high score through engagement alone if they're a bad fit. Keeps Jason from chasing $2K budget prospects who downloaded every PDF.

### Negative Signals (decay)

| Signal | Points | Notes |
|---|---|---|
| No engagement for 30 days | -10 | Cooling |
| No engagement for 60 days | -20 | Further cooling |
| Unsubscribed from Apollo sequence | -40 | Explicit rejection |
| Bounced email | -25 | Bad data |
| Explicit "not interested" reply | drop to `dropped` state | Respect the no |

---

## Calculation

```
raw_score = sum(all positive signals) - sum(all negative signals)
fit_multiplier = firmographic_fit_score
final_score = min(100, max(0, raw_score * fit_multiplier))
```

Scores recalculated on every new signal event. Stored in `lead_scores` table with history.

---

## State Transitions

Scores recompute when any signal lands. State transitions fire side effects:

| Transition | Side Effect |
|---|---|
| cold → warming | No action (Marketing Agent continues sequence) |
| warming → engaged | Slack/Teams ping to Jason with prospect summary |
| engaged → qualified | Daily digest entry for Jason, suggested email template |
| qualified → ready_to_scope | Apollo stage moved to "Ready to Scope" → webhook fires Scoping Agent → SharePoint workspace created → briefing doc generated → Ritu gets Teams card |
| any → dropped | Removed from all sequences, noted in CRM, no retry for 12 months |

**Manual override:** Jason or Ritu can force-promote or force-demote a lead at any time. The score is a recommendation, not a rule.

---

## Ready to Scope Threshold

The **Ready to Scope** state is the highest-stakes transition — it triggers real work (SharePoint workspace creation, briefing research via Anthropic tokens, meeting scheduling). We need high confidence before firing it.

Required for automatic promotion to Ready to Scope:
1. **Final score ≥ 80** AND
2. **At least one of:**
   - `INTAKE_COMPLETE` fired in chat, OR
   - Consulting inquiry form submitted with problem + budget + timeline, OR
   - Email reply containing keywords: "schedule", "call", "meet", "scope", "proposal", "next step", OR
   - Calendar meeting booked via Apollo

**Why two conditions:** Score alone could be inflated by a very engaged browser who isn't actually ready to buy. The second condition requires explicit buying intent.

---

## Schema Changes Needed

Current state: `marketing_leads` exists but has no scoring logic. Apollo contacts exist but aren't synced to our scoring.

### New table: `lead_scores`
```sql
CREATE TABLE lead_scores (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email TEXT NOT NULL,
    apollo_contact_id TEXT,
    current_score INTEGER NOT NULL DEFAULT 0,
    fit_multiplier NUMERIC(3, 2) DEFAULT 1.0,
    state TEXT NOT NULL DEFAULT 'cold',
    organization_name TEXT,
    organization_type TEXT,
    organization_size TEXT,
    region TEXT,
    last_signal_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX ix_lead_scores_email ON lead_scores(LOWER(email));
```

### New table: `lead_signals`
```sql
CREATE TABLE lead_signals (
    id BIGSERIAL PRIMARY KEY,
    lead_score_id TEXT REFERENCES lead_scores(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,
    points INTEGER NOT NULL,
    source TEXT NOT NULL,             -- 'content_download' / 'chat' / 'form' / 'apollo' / 'pageview'
    source_id TEXT,                    -- ref to marketing_leads.id, project_inquiries.id, etc.
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX ix_lead_signals_lead ON lead_signals(lead_score_id, created_at DESC);
```

### New table: `lead_state_transitions`
```sql
CREATE TABLE lead_state_transitions (
    id BIGSERIAL PRIMARY KEY,
    lead_score_id TEXT REFERENCES lead_scores(id) ON DELETE CASCADE,
    from_state TEXT,
    to_state TEXT NOT NULL,
    trigger_signal_id BIGINT REFERENCES lead_signals(id),
    manual_override_by TEXT,          -- NULL if automatic
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Implementation Plan

### Phase 1: Capture signals (no scoring yet)
- [ ] Add `record_signal(email, type, source, source_id, metadata)` helper in `agents/apollo/client.py`
- [ ] Hook into existing flows:
  - `POST /api/marketing/leads` → signal `pdf_download`
  - `POST /api/consulting/inquire` → signal `form_submitted`
  - `agent_conversations` session end → signal `chat_completed` (with exchange count)
  - Apollo webhook handler → signals `email_opened`, `email_clicked`, `email_replied`
- [ ] Populate `lead_scores` row on first signal per email

### Phase 2: Compute scores
- [ ] Background job (every 5 min) recomputes scores for leads with new signals
- [ ] Firmographic lookup via Apollo's organization enrichment API
- [ ] Fit multiplier applied
- [ ] State transitions detected and logged

### Phase 3: Act on scores
- [ ] Jason morning digest: top 10 leads by score with delta from yesterday
- [ ] Ritu weekly digest: ready_to_scope leads for approval
- [ ] Teams card on every state promotion
- [ ] Auto-fire Scoping Agent on qualified → ready_to_scope transition (behind feature flag initially — Ritu approves first 5 manually)

### Phase 4: Tune
- [ ] Log every state transition + outcome (did they close?)
- [ ] Weekly review: are scores predictive? Adjust weights.
- [ ] Kill signals that don't correlate with closes.

---

## Guardrails

1. **No Scoping Agent auto-fire without human approval** for the first 10 leads that hit `ready_to_scope`. Ritu reviews each one. Adjust thresholds based on false positives.

2. **No outreach escalation above "email reply" without a real person approving.** The score suggests — humans act. This prevents a bug from spamming Ritu into the inbox of a bad-fit lead.

3. **Daily cap on Scoping Agent fires:** maximum 3 per day. Prevents runaway costs from bad signals.

4. **Opt-out is permanent.** Once a lead unsubscribes or says "not interested," they're frozen for 12 months regardless of score changes.

5. **Firmographic data cached 30 days.** Apollo lookups cost money. Re-enrich only if the org name changes or 30 days pass.

---

## Open Questions

1. **Pageview tracking:** We don't currently track page views on the CFA site. Do we add analytics (Plausible/PostHog) to feed signals? Or skip pageview signals for v1?

2. **Score decay rate:** Should a lead who hit score 70 three months ago still be at 70? Proposed: linear decay after 30 days of no engagement (-1 point per inactive day, floor at 20).

3. **Multi-contact accounts:** If two people from the same org download reports, do they score independently or as an account? For v1, independently — merge by org in Phase 2.

4. **Apollo field sync:** Should `current_score` be pushed to a custom field in Apollo so Jason sees it in the CRM? Yes, once Phase 2 is stable.

5. **Gaming:** Nothing prevents someone from refreshing the site to game their score. For v1 accept the risk — sample size is too small for noise to matter. Add rate limiting per email in Phase 3.

---

## Metrics to Track

Once implemented, track these to validate the model:

- **Precision @ ready_to_scope:** Of leads that hit this state, what % convert to a signed engagement within 60 days? Target: 40%+.
- **Recall @ ready_to_scope:** Of closed engagements, what % were flagged by the scoring model before Jason/Ritu reached out manually? Target: 70%+.
- **False positive rate:** How many Scoping Agent fires produced no scoped proposal? Target: <20%.
- **Time-to-scope:** From first signal to ready_to_scope state. Baseline, then optimize.
- **Fit calibration:** Are perfect-fit leads (1.0x multiplier) actually closing at higher rates than partial-fit? If not, the fit model is wrong.

---

## Related Documents

- `CLAUDE.md` — Marketing Agent (Agent 12) description, Apollo integration
- `docs/TODO-apollo-scoping-onboarding.md` — Scoping Agent trigger from Apollo webhook
- `agents/apollo/client.py` — Apollo API wrapper
- `agents/apollo/api.py` — Webhook handler (receives Apollo stage changes)
- `agents/marketing/api.py` — `marketing_leads` table + POST /api/marketing/leads

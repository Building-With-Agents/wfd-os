# Deferred cockpit fixes — cleanup epic checklist

Phase 1 closed early at the end of 1C. The polish + metadata-surface
items originally scoped as 1D / 1E / 1F were deferred so we could
pivot to Phase 2 (Next.js migration). This doc is the checklist for
the cleanup epic that lands alongside or after Phase 2.

For the full spec of each item, follow the section pointer into
[cockpit_design_fixes.md](cockpit_design_fixes.md).

---

## Phase 1D — affordance + state consistency
Spec: cockpit_design_fixes.md §1D

- [ ] **Unified clickable affordance** — every `[data-drill]` element
  gets `cursor: pointer`, subtle hover background, and the hover `↗`
  icon (currently only on hero cells). Single `.drillable` class
  applied wherever `data-drill` appears. (§1D.1)
- [ ] **Priority vs. status differentiation in decisions list** —
  HIGH/MEDIUM/LOW gets the colored tag style (matching the marker
  dot), open/closed stays muted. (§1D.2)
- [ ] **Section dividers in decisions list** — thin divider + small
  label between priority groups for faster scanning. (§1D.3)
- [ ] **Subhead simplification** — change
  "11 items from v3 reconciliation Action Items · prioritized" to
  "11 open · sorted by priority". Move provenance into per-drill
  `source` chips. (§1D.4)
- [ ] **"RECENT" → "LAST ASKED"** in the chat panel. Singular
  matches the singular item shown. (§1D.5)
- [ ] **Category color tokens** — the 7 budget category bars in the
  Budget Allocation chart use raw hex (`#2E4D3E`, `#5C7A6B`,
  `#8B5E3C`, `#B8821B`, `#D4A847`, `#8C8A82`, `#C4B89C`). Promote
  to named tokens (`--cat-training`, `--cat-strategic`, etc.) in
  `:root`. (Audit task 4 finding — not in 1D spec but same family.)
- [ ] **Row background classes** — the two row-level inline
  backgrounds in the Provider Financial Performance table
  (`style="background:var(--surface-alt);"` for CFA Direct,
  `style="background:var(--surface-warm);"` for Recovery Operation)
  → CSS classes `.row-cfa-direct`, `.row-recovery`. (Audit task 7
  finding.)
- [ ] **Dead `.status` cleanup** — `.status` class with 5 variants
  (draft/review/approved/blocked/closed) defined in CSS but never
  instantiated. Either find a use case or delete the block.
  (Audit task 7 finding.)
- [ ] **Hero-cell inline span extraction** — two inline `style=`
  spans inside `.hero-cell` (the live-badge `font-size:9px` and the
  `/ goal` suffix `font-size:18px`) → CSS classes. (Audit task 6
  finding.)

## Phase 1E — metadata surface
Spec: cockpit_design_fixes.md §1E

- [ ] **Per-metric freshness timestamps** — every hero cell renders
  "Updated 3 min ago" below the status badge, sourced from a new
  `updated_at` field per metric. Schema already accepts the field on
  drill entries (validated optional). (§1E.1)
- [ ] **Source chips** — every hero cell renders a small uppercase
  source indicator ("QB sandbox ✓", "WSAC + LinkedIn", "v3
  reconciliation"). Schema already accepts `source` field. (§1E.2)
- [ ] **Data-quality status chips** — pro-rated/estimated/awaiting
  drills surface their state via the existing `status_chip` field
  rather than via a "⚠ Data quality" pseudo-row inside the
  `Current Status` section. Affects the four pro-rated category
  drills (Personnel — Salaries / Benefits / Other Direct /
  Indirect). (§1E.3)
- [ ] **Loading state spec** — drill panel renders a skeleton
  shimmer while content is loading. Currently aesthetic only
  (content is embedded), but ready for Phase 2 API-driven flow.
  (§1E.4)
- [ ] **Error state spec** — drill panel renders a critical-tone
  error with Retry button when load fails. (§1E.4)
- [ ] **Empty state spec** — drill panel renders a friendly "no
  data" state when the registry returns an empty section list, vs.
  a blank panel. (§1E.5)
- [ ] **Domain-term tooltips** — hero metric labels wrapped in a
  tooltip with a `?` icon or dotted underline ("Backbone Runway",
  "PIP threshold", "True CPP"). (§1E.6)

## Phase 1F — chat panel spec
Spec: cockpit_design_fixes.md §1F

- [ ] **Produce `agents/finance/design/chat_spec.md`** covering:
  - Suggested prompts generation (per-tab hardcoded → admin-editable
    upgrade path)
  - Chat message rendering decisions (markdown? embedded
    drill-trigger links? tabular numbers?)
  - Chat error states (timeout, rate limit, context overflow)
  - Wiring to `agents/assistant/finance_agent.py` (Gemini tool-
    calling) — Phase 2 work, spec'd here
  - Chat panel resize / expand affordance
  Spec is a doc, not code — Phase 2 picks it up when the chat
  starts hitting real endpoints.

## Static SVG hex literals (Phase 2 cleanup)

Single-color, non-ternary hex usages still in `cockpit_template.html`
that the Phase 1C color-band consolidation didn't touch (they're
hardcoded fills inside SVG `fill=` / `stroke=` attributes, where
`var(--good)` doesn't work without moving to inline `style=` or
class-based styling). Listed for completeness — none are dynamic
band decisions.

- Cumulative Placements chart (lines ~1066, 1067, 1080, 1086, 1092,
  1093): PIP threshold + grant-goal reference lines, recovery band
  fill, combined-line stroke
- Provider Contribution chart (line ~1236): recovered-portion fill
- CPP Ranking chart (lines ~1481, 1485, 1489, 1492, 1493, 1494):
  threshold-zone background rects + threshold labels
- Budget Allocation chart (line ~918): 1% remaining text tspan
- Legend swatches (lines ~1107, 1254, 1527, 1528): inline color
  squares next to legend labels

Cleanup: introduce CSS classes `.chart-good`, `.chart-watch`,
`.chart-critical` (and `.chart-cat-{training|strategic|...}` for
the budget allocation chart) and use them on SVG elements via
`class=` instead of `fill=`/`stroke=`. Most cleanly tackled during
the Phase 2 Recharts/D3 migration when these charts get rebuilt
from scratch.

---

## Where the cleanup epic plugs in

When this epic gets scheduled:

1. Phase 1D items can land before, during, or after Phase 2 — they
   touch the existing HTML mockup (or its React equivalent in 2A).
2. Phase 1E items naturally land after Phase 2B (API endpoints),
   when freshness timestamps and source chips have a real
   `updated_at` and `source` to render.
3. Phase 1F (chat spec doc) is independent — write any time. The
   spec becomes work for Phase 2 chat wiring.
4. Static SVG hex cleanup naturally rides along with the Phase 2C
   chart rebuild (Recharts/D3 migration).

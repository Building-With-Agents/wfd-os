# Phase 4 exit report — security + auth

**Branch:** `phase-4-exit-gate` (stacked on
`issue-9-credential-rotation-finalize` → `issue-25-tier-decorators` →
`issue-24-wfdos-common-auth` → `phase-3-exit-gate`).

| # | Issue | Branch | PR | Status |
|---|---|---|---|---|
| 1 | #24 — magic-link auth | `issue-24-wfdos-common-auth` | #49 | ✅ |
| 2 | #25 — tier decorators (@public, @read_only, @llm_gated) | `issue-25-tier-decorators` | #50 | ✅ |
| 3 | #9 — credential rotation runbook (code-side closed) | `issue-9-credential-rotation-finalize` | #51 | ✅ |

None merged to master — stacked-branch strategy continues.

## Test + coverage snapshot

| Phase 3 exit | Phase 4 exit |
|---|---|
| 172 tests passing | **210 tests passing** |
| 59.83% coverage | **65.32% coverage** |

Growth by issue:

| After | Tests | Coverage |
|---|---|---|
| Phase 3 exit baseline | 172 | 59.83% |
| #24 (magic-link) | 197 (+25) | 63.90% |
| #25 (tier decorators) | 210 (+13) | 65.32% |
| #9 (runbook, no code) | 210 | 65.32% |

Phase 4 target per plan was 60% coverage; **actual 65.32%** ✅.

## Acceptance-criteria deltas

### #24 — magic-link auth (wfdos_common.auth)

- **`wfdos_common.auth`** has 6 submodules:
  - `tokens.py` — itsdangerous sign/verify for magic-link + session tokens, purpose-salted.
  - `allowlist.py` — env-driven email → role, admin > staff > student precedence, case-insensitive.
  - `middleware.py` — `SessionMiddleware` attaches `request.state.user`.
  - `dependencies.py` — `require_role(*roles)` FastAPI dep (401/403 through #29 envelope).
  - `routes.py` — `build_auth_router()` factory, mountable `/auth/{login,verify,logout,me}`.
  - `__init__.py` — public exports.
- **AuthSettings** added to `wfdos_common.config.settings` with `WFDOS_AUTH_*` env vars.
- **Runtime deps:** `itsdangerous>=2.1`, `slowapi>=0.1.9`, `email-validator>=2.0`.
- **Tests:** 25 (token roundtrip per purpose, expiry, tampered, purpose-misuse rejection, allowlist precedence, middleware accept/reject, end-to-end login → verify → /whoami).
- **Live email dispatch:** deferred to Gary's morning smoke (see consolidated list).

### #25 — tier decorators

- `@public`, `@read_only(roles=...)`, `@llm_gated(roles=...)` decorators in `wfdos_common.auth.tiers`.
- `TierTag` attached via `__wfdos_tier__`; `audit_tier_tags(app.routes)` returns `{tier: [paths]}`.
- **Stripped-`.env` 503 path**: `@llm_gated` with no Azure/Anthropic/Gemini creds returns 503 `service_unavailable` with `error.details.tier == "llm_gated"`.
- **Tests:** 13 (tag attachment, defaults, custom roles, runtime 401/403/503, audit helper).
- **Not landed (deferred to a follow-up PR):** tagging every route in the 9 services + slowapi rate-limit hookup. The `TierTag` carries `rate_limit_per_hour`; the slowapi middleware install is a mechanical pass that belongs in a Phase-5 cleanup branch since it touches all 9 service files.

### #9 — credential rotation finalization

- `docs/ops/credential-rotation.md` — team-secret-store decision (1Password teams), 13-credential inventory, per-credential playbook (generate → stage → deploy → cut → revoke → audit), post-rotation audit checklist.
- Code-side for the original `SuperShivani1` leak already landed in #19 (PR #35).
- **Actual Azure Postgres admin rotation:** Gary's manual step — post rotation date on #9 to close.

## What's deferred (Phase 5 or later)

| Ref | Scope | Why deferred |
|---|---|---|
| Apply `@public`/`@read_only`/`@llm_gated` to every route in the 9 services | 55-route tagging pass | Mechanical; single big PR belongs after Phase 5 or as a cleanup branch |
| Install slowapi rate-limit middleware on the 9 services | Service-side wiring | Depends on route-tagging above |
| Migrate allowlist from env CSV to a `users` table | Schema change + migration | Fine with env CSV for Phase 4; DB migration belongs in Phase 5 product polish |
| Actual Azure Postgres password rotation | Gary's manual step | Cannot execute from agent without Azure console creds |

## Live smoke plan (for Gary's morning pass)

See the consolidated list at the end of the Phase-5 exit report. Phase 4
items:

- `POST /auth/login` to a service with `build_auth_router()` mounted + `WFDOS_AUTH_STAFF_ALLOWLIST=gary.larson@computingforall.org`. Expect a real magic-link email at the inbox within 10–30 s.
- Click the link; expect redirect to `platform.thewaifinder.com` with a session cookie set.
- `GET /auth/me` — expect `{email: "gary.larson@computingforall.org", role: "staff"}`.
- Stripped-env boot: remove every `AZURE_OPENAI_KEY` + `ANTHROPIC_API_KEY` + `GEMINI_API_KEY` from `.env`, restart an `@llm_gated` service; confirm it boots, `@read_only` endpoints respond, `@llm_gated` endpoints return 503.

## Sign-off

- 3 PRs open (#49, #50, #51) stacked correctly per the no-merge-yet strategy.
- 210 tests green, 65.32% coverage (Phase-4 target 60% ✅).
- Next: Phase 5 kicks off from `phase-4-exit-gate` via `issue-26-agent-abc`.

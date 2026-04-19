# `scripts/smoke/` — phase-exit smoke scripts

Python scripts that replace the copy-paste `curl` blocks previously
embedded in `docs/refactor/phase-5-exit-report.md`. Each directory
corresponds to a phase or feature; run the scripts in the order the
exit report references them.

**Cross-platform by design.** Python 3.11+ + `httpx` (already a
`wfdos-common` runtime dep) — works the same on macOS, Linux, and
Windows PowerShell. No `curl`, `jq`, or bash required.

## Directory layout

| Directory       | What it smokes                                          | Exit-report §    |
|-----------------|----------------------------------------------------------|------------------|
| `bootstrap/`    | imports smoke + full pytest suite                        | §0, §1           |
| `errors/`       | Structured error envelope invariants (#29)               | §3               |
| `auth/`         | Magic-link auth (#24), role gates (#25), stripped-env 503 | §4, §5, §6       |
| `tenancy/`      | White-label Host → X-Tenant-Id routing (#16)             | §7               |
| `agent/`        | Agent ABC reference run (#26)                            | §9               |
| `edge/`         | nginx -t syntax check (#30)                              | §10              |
| `cta/`          | Contract-URL walker (#31)                                | §11              |
| `laborpulse/`   | Health, mock-mode query, feedback, JIE-503 path          | §13              |

## Conventions

- **Shebang `#!/usr/bin/env python3`** + `from __future__ import annotations`.
- **Argparse**. Every script accepts `--help`; required positionals
  validated by argparse.
- **Exit codes.** `0` = pass, `1` = assertion failed, `2` = argparse
  misuse.
- **Output format.** `OK: <what>` on stdout on pass, `FAIL: <reason>`
  on stderr on failure, `SKIP: <reason>` on stderr + exit 0 when the
  script isn't applicable (e.g. `nginx` binary missing on Windows).
- **Shared helpers** in `scripts/smoke/_common.py`: `build_parser`,
  `ok`, `fail`, `skip`, `resolve_base_url`.
- **Defaults + overrides.** Each script has a sensible default
  `--base-url` (typically `http://localhost:<port>`); override via
  `--base-url=...` or the `BASE_URL` environment variable.
- **No credentials embedded.** Cookies and emails are passed as
  positional args. Env vars used for configuration only.

## Running them

```powershell
# PowerShell (Windows)
python scripts\smoke\bootstrap\imports.py
python scripts\smoke\laborpulse\health.py
python scripts\smoke\laborpulse\mock_query.py "<wfdos_session cookie>"
```

```bash
# bash / zsh (macOS / Linux / WSL)
python scripts/smoke/bootstrap/imports.py
python scripts/smoke/laborpulse/health.py
python scripts/smoke/laborpulse/mock_query.py "<wfdos_session cookie>"
```

`--help` gives per-script usage:

```
python scripts/smoke/laborpulse/mock_query.py --help
```

As part of the Gary-morning-checklist, follow §13 of
`docs/refactor/phase-5-exit-report.md` — each section points at the
matching Python script.

## Chaining scripts

`mock_query.py` prints the `conversation_id` on its last line so it
can be piped into `feedback.py`:

```powershell
$CONV = python scripts\smoke\laborpulse\mock_query.py "$COOKIE" | Select-Object -Last 1
python scripts\smoke\laborpulse\feedback.py "$COOKIE" $CONV 1
```

```bash
CONV=$(python scripts/smoke/laborpulse/mock_query.py "$COOKIE" | tail -n1)
python scripts/smoke/laborpulse/feedback.py "$COOKIE" "$CONV" 1
```

## Adding a new script

1. Pick (or create) the right subdirectory based on the phase/feature
   the script exercises.
2. Use the template in any existing script; import `ok`/`fail`/`skip`
   + `build_parser` from `_common.py`.
3. Add the reference to `docs/refactor/phase-5-exit-report.md` so
   Gary's checklist stays in sync.
4. Add the subdirectory row to the table in this README if it's new.

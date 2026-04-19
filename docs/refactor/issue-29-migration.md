# Issue #29 — FastAPI endpoint validation + structured error envelope

**Status:** infrastructure + all 9 services wired. Incremental cleanup of
broad `except Exception:` handlers + response_model= annotations continues
as services are touched.

## What changed

### Every service now has

```python
from wfdos_common.errors import install_error_handlers
from wfdos_common.logging import RequestContextMiddleware

app = FastAPI(...)
app.add_middleware(RequestContextMiddleware)
# ...CORS...
install_error_handlers(app)
```

This wires three FastAPI exception handlers:

| Exception class                   | Status | Envelope code          |
|-----------------------------------|--------|------------------------|
| `wfdos_common.errors.APIError` subclasses | 4xx/5xx (per subclass) | matches the subclass     |
| `fastapi.RequestValidationError`  | 422    | `validation_error`     |
| bare `Exception`                  | 500    | `internal_error`       |

All responses follow the `APIEnvelope` shape from
`wfdos_common.models.core`:

```json
{
  "data": null,
  "error": {
    "code": "not_found",
    "message": "student 'abc-123' not found",
    "details": {
      "resource": "student",
      "identifier": "abc-123",
      "request_id": "a1b2c3d4-..."
    }
  },
  "meta": null
}
```

`X-Request-Id` from `RequestContextMiddleware` is echoed into
`error.details.request_id` so clients can quote it when filing a bug.

### Typed errors to raise

Import from `wfdos_common.errors`:

- `NotFoundError("student", student_id)` — 404 with `code: "not_found"`.
- `ValidationFailure("msg", details={...})` — 422 business-rule failure.
- `ConflictError("email already registered")` — 409.
- `UnauthorizedError("missing bearer token")` — 401.
- `ForbiddenError("role 'admin' required")` — 403.
- `ServiceUnavailableError("graph api 503")` — 503.

Services should raise these instead of
`raise HTTPException(status_code=404, detail="X not found")` and instead of
wrapping every route body in `except Exception: raise HTTPException(500, str(e))`.

## Migration status per service

| Service                         | Handlers installed | `HTTPException` count | `except Exception` count |
|---------------------------------|:-:|:-:|:-:|
| `agents/portal/consulting_api.py` | ✅ | 0 | 11 (cleanup pending) |
| `agents/portal/student_api.py`    | ✅ | 0 | 1 (cleanup pending)  |
| `agents/portal/showcase_api.py`   | ✅ | 0 | 3 (cleanup pending)  |
| `agents/portal/wji_api.py`        | ✅ | 0 | 3 (cleanup pending)  |
| `agents/portal/college_api.py`    | ✅ | 0 | 0                    |
| `agents/apollo/api.py`            | ✅ | 0 | 3 (cleanup pending)  |
| `agents/marketing/api.py`         | ✅ | 0 | 0                    |
| `agents/reporting/api.py`         | ✅ | 0 | 0                    |
| `agents/assistant/api.py`         | ✅ | 0 | 0                    |

Every `raise HTTPException(...)` in the 9 FastAPI services was migrated to
typed errors. The remaining `except Exception:` blocks are incremental
cleanup work that each service owner can finish as they touch adjacent
code — the unhandled-exception handler catches anything they don't.

## Response model annotations (next step)

Response model annotations (`@app.get("/...", response_model=StudentProfile)`)
were not added in this PR — the 9 portal services have 55 routes and each
one needs a hand-written response model since the shapes don't yet line up
with the `wfdos_common.models` Pydantic models.

**Plan:** add response models per service in follow-up PRs, one service
per PR. The blocker is that current response bodies ship raw DB rows
(e.g. `RealDictCursor` output) which have keys like `created_at: datetime`
that need Pydantic field ordering decisions. Deferred to a Phase-4-era
follow-up.

## Test coverage

- `packages/wfdos-common/tests/test_errors.py` — 13 unit tests on the
  handlers + envelope shape.
- `packages/wfdos-common/tests/test_service_error_envelopes.py` —
  19 parametrized integration tests (each of the 9 services × 2 envelope
  checks + 1 route-level validation test) proving the middleware + handlers
  are wired on every FastAPI app.

Full suite: **172 passing, 59.83% coverage** (+32 tests, +2 pp coverage
from #27 baseline of 140 / 57.75%).

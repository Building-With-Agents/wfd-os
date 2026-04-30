"""Core cross-cutting Pydantic models used by every service.

Scope of 'core': response envelopes, error shapes, audit events, tool
definitions. Things every service touches regardless of domain.

Domain-specific models (StudentProfile, EmployerProfile, etc.) live in
`wfdos_common.models.domain`. Scoping-pipeline dataclasses in
`wfdos_common.models.scoping`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error shape returned by every FastAPI endpoint.

    Replaces the raw-string / traceback leaks that exist today. See #29 for
    the rollout (Pydantic validators + exception handlers on every endpoint).
    """

    code: str = Field(..., description="Machine-readable error code, e.g. 'validation_error'.")
    message: str = Field(..., description="Human-readable one-line summary.")
    details: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional field-level detail (e.g. Pydantic validation errors).",
    )

    model_config = ConfigDict(extra="forbid")


class APIEnvelope(BaseModel, Generic[T]):
    """Standard response wrapper: either `data` (success) or `error` (failure),
    never both. Services can optionally include `meta` for pagination cursors,
    timing info, tenant context, etc.
    """

    data: Optional[T] = None
    error: Optional[ErrorDetail] = None
    meta: Optional[dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class AuditEvent(BaseModel):
    """One row in an audit log. Used by the services that write to the
    `audit_log` table (market-intelligence ingest pipeline today; more
    services to come as #23 structured logging lands).
    """

    event_type: str = Field(..., description="Machine-readable event type.")
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: Optional[str] = Field(default=None, description="user_id / service name / system")
    tenant_id: Optional[str] = Field(default=None)
    request_id: Optional[str] = Field(default=None)
    subject_type: Optional[str] = Field(default=None, description="Entity kind, e.g. 'student'.")
    subject_id: Optional[str] = Field(default=None, description="Entity primary key.")
    attributes: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class Tool(BaseModel):
    """Tool declaration for agents. Generalized from
    agents/assistant/base.py:Tool so every agent framework (Gemini
    function-calling, Anthropic tool_use, OpenAI tool_calls) can use the
    same Python object and emit provider-specific shapes.

    `parameters` is a JSON-Schema dict (draft 7). Provider adapters in
    #20 + #26 convert to per-provider declaration shapes.
    """

    name: str = Field(..., description="Callable identifier, e.g. 'search_jobs'.")
    description: str = Field(..., description="Natural-language purpose; shown to the model.")
    parameters: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}, "required": []},
        description="JSON Schema for tool input. Empty object if the tool takes no arguments.",
    )
    # The Python callable is excluded from serialization. Pydantic sees Callable
    # fields as plain Any — that's fine; we just never JSON-encode them.
    handler: Optional[Callable[..., Any]] = Field(
        default=None,
        exclude=True,
        description="Python callable invoked when the model selects this tool.",
    )

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

"""Base agent class.

All agents in this system inherit from `Agent`. The base class:
  - Centralizes LLM access (so every agent call is auditable)
  - Enforces the "agents propose, humans dispose" pattern via .propose()
  - Writes audit log entries for every consequential action
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from sqlalchemy.orm import Session

from grant_compliance.audit.log import write_entry
from grant_compliance.utils.llm import LLMResponse, get_llm


class Agent(ABC):
    """Subclass and set `name`. Use `self.llm()` to call the LLM, which
    automatically writes an audit log entry.
    """

    name: str = "base_agent"

    def __init__(self, db: Session):
        self.db = db

    def llm(
        self,
        *,
        system: str,
        user: str,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        extra_inputs: dict[str, Any] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Call the LLM and write an audit entry in one step.

        Both the success and failure paths write to audit_log: a successful
        call records the response preview + served model; a raised
        exception records `failed: True` plus the exception type and
        message before re-raising. Without the failure path, transient
        API errors (auth, credit balance, rate limits) leave no trace
        an attempt was made — violating the engine's "every consequential
        agent action writes to audit_log" discipline.
        """
        client = get_llm()
        try:
            response = client.complete(
                system=system, user=user, max_tokens=max_tokens, temperature=temperature
            )
        except Exception as exc:
            write_entry(
                db=self.db,
                actor=self.name,
                actor_kind="agent",
                action=action,
                target_type=target_type,
                target_id=target_id,
                inputs={"user_prompt_preview": user[:500], **(extra_inputs or {})},
                outputs={
                    "failed": True,
                    "exception_type": type(exc).__name__,
                    "exception_message": str(exc)[:1000],
                },
                model=None,  # no served model on failure
                prompt=user,
                note="LLM call raised; no response received.",
            )
            raise
        write_entry(
            db=self.db,
            actor=self.name,
            actor_kind="agent",
            action=action,
            target_type=target_type,
            target_id=target_id,
            inputs={"user_prompt_preview": user[:500], **(extra_inputs or {})},
            outputs={"text_preview": response.text[:1000]},
            model=response.model,
            prompt=user,
        )
        return response

    def log_action(
        self,
        *,
        action: str,
        target_type: str | None = None,
        target_id: str | None = None,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> None:
        """Log a non-LLM action (e.g., 'compliance.flag_raised')."""
        write_entry(
            db=self.db,
            actor=self.name,
            actor_kind="agent",
            action=action,
            target_type=target_type,
            target_id=target_id,
            inputs=inputs,
            outputs=outputs,
            note=note,
        )

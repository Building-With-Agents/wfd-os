"""LLM-generated Audit Readiness verdict with caching and static fallback.

Implements step 5 of audit_readiness_tab_spec.md §v1.2.8 — cockpit-side
only. The compliance engine stays deterministic; only the editorial
verdict box calls the LLM.

Reuses the same Gemini pattern as agents/llm/client.py and
agents/assistant/base.py: `google.generativeai` SDK, model name from
GEMINI_MODEL env (default gemini-2.5-flash), API key from
GEMINI_API_KEY env, `genai.configure(api_key=...)` at module load.

Three fallback layers in descending preference:
  1. Happy path — LLM returns a structured JSON headline + body.
  2. Data-driven fallback — LLM fails or no API key; build a minimal
     headline + body from stats/dimensions alone. Tone still honest.
  3. Static fallback — engine is unreachable (per spec §v1.2.6); skip
     the LLM entirely and show the canonical "data unavailable" copy.

TODO(v1.2 cockpit-side step 5 follow-up): add pytest infrastructure on
this branch and cover the three fallback layers, cache hit/miss, and
hash-key stability. Tests deferred per the cockpit-side decision; see
integration_notes.md on feature/compliance-engine-extract.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import google.generativeai as genai

from wfdos_common.logging import get_logger

log = get_logger(__name__)

# Repo root on sys.path so `agents.*` imports resolve when this module
# is loaded via uvicorn from various cwds. Mirrors cockpit_api's setup.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_REPO_ROOT, ".env"), override=False)
except ImportError:  # pragma: no cover
    pass


# ---------------------------------------------------------------------------
# LLM configuration (shared convention with agents/llm/client.py)
# ---------------------------------------------------------------------------

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if _GEMINI_API_KEY:
    genai.configure(api_key=_GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# POC-grade in-process cache
# ---------------------------------------------------------------------------
#
# Keyed on a hash of (engine_status, stats, dimensions); TTL 5 minutes
# per spec §v1.2.8. Single-process — does not survive uvicorn restarts
# and doesn't isolate per-tenant. TODO: replace with the shared
# wfdos-common cache when that refactor lands.

_CACHE_TTL_SECONDS: int = 5 * 60
_cache: dict[str, tuple[float, dict]] = {}


def _cache_key(
    engine_status: str, stats: dict, dimensions: list[dict]
) -> str:
    """Stable hash of the inputs that meaningfully change the verdict.

    Only the fields that would move the verdict text are included. We
    deliberately DO NOT include `generated_at` or dimension `what`
    copy — those don't affect the output and including them would
    produce spurious cache misses on unrelated field additions.
    """
    payload = json.dumps(
        {
            "engine_status": engine_status,
            "stats": {
                "overall_readiness_pct": stats.get("overall_readiness_pct"),
                "overall_readiness_basis": stats.get("overall_readiness_basis"),
                "doc_gap_count": stats.get("doc_gap_count"),
                "doc_gap_threshold_cents": stats.get("doc_gap_threshold_cents"),
                "te_certs_status": stats.get("te_certs_status"),
            },
            "dimensions": [
                {
                    "id": d.get("id"),
                    "pct": _dim_pct(d),
                    "status": d.get("status"),
                }
                for d in dimensions
            ],
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> Optional[dict]:
    entry = _cache.get(key)
    if entry is None:
        return None
    stamped_at, value = entry
    if time.time() - stamped_at > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return value


def _cache_put(key: str, value: dict) -> None:
    _cache[key] = (time.time(), value)


# ---------------------------------------------------------------------------
# Tone + dimension helpers
# ---------------------------------------------------------------------------


def _tone_for_pct(pct: Optional[int]) -> str:
    """Mirror of cockpit_api._tone_for_dimension / toneForOverallReadiness.

    Bands match the dimension table: neutral on null, good ≥90,
    watch ≥70, critical below. Keeps the verdict-box tone band
    consistent with the stat card's Overall Readiness tone.
    """
    if pct is None:
        return "neutral"
    if pct >= 90:
        return "good"
    if pct >= 70:
        return "watch"
    return "critical"


def _dim_pct(d: dict) -> Optional[int]:
    """Dimension pct can live under either `pct` (cockpit UI shape) or
    `readiness_pct` (engine shape). Support both."""
    if "pct" in d:
        return d.get("pct")
    return d.get("readiness_pct")


def _dim_label(d: dict) -> str:
    return d.get("label") or d.get("title") or d.get("id") or "unknown"


def _top_gap(dimensions: list[dict]) -> Optional[tuple[int, str]]:
    """Identify the computable dimension with the lowest readiness pct.
    Returns (pct, label) or None if no computed dimension has a pct."""
    candidates: list[tuple[int, str]] = []
    for d in dimensions:
        if d.get("status") != "computed":
            continue
        pct = _dim_pct(d)
        if pct is None:
            continue
        candidates.append((pct, _dim_label(d)))
    if not candidates:
        return None
    return min(candidates, key=lambda x: x[0])


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are the editorial voice for CFA's Audit Readiness tab.

Your job: write a 2-4 sentence verdict summarizing Single Audit posture, \
matching the tone of a concise, honest, auditor-aware briefing. The reader \
is Ritu (Executive Director) or Krista (bookkeeper).

Style:
- Concrete. Name the specific dimension, not generalities.
- Honest. If a top gap is a placeholder dimension (no data model yet), \
  say so — don't inflate or paper over it.
- Audit-aware. Mention the Single Audit or ESD monitoring when relevant.
- No emojis. No preamble like "Based on the data..." — start with the fact.

Output format: a single JSON object with exactly two keys:
  "headline" — one crisp sentence, ideally under 15 words.
  "body"     — 1-3 additional sentences of context and the action that \
              most moves the needle this week.

Do not include any markdown, code fences, or commentary outside the JSON."""


def _format_input_summary(stats: dict, dimensions: list[dict]) -> str:
    """Human-readable block summarizing current state for the LLM input."""
    lines: list[str] = []

    overall = stats.get("overall_readiness_pct")
    basis = stats.get("overall_readiness_basis") or {}
    lines.append(
        f"Overall Readiness: {overall if overall is not None else 'null'}% "
        f"(across {basis.get('computed_dimension_count', 0)} of "
        f"{basis.get('total_dimension_count', 6)} computable dimensions)"
    )
    doc_gap = stats.get("doc_gap_count")
    threshold = (stats.get("doc_gap_threshold_cents") or 250_000) / 100
    lines.append(
        f"Documentation Gap: "
        f"{doc_gap if doc_gap is not None else 'null'} transactions above "
        f"${int(threshold):,} lack linked invoices"
    )
    lines.append(f"T&E Certifications: {stats.get('te_certs_status', '?')}")
    lines.append("")
    lines.append("Six audit dimensions:")
    for d in dimensions:
        pct = _dim_pct(d)
        status = d.get("status", "?")
        label = _dim_label(d)
        if pct is None and status == "computed":
            pct_str = "no data yet"
        elif pct is None:
            pct_str = "placeholder — no formula in v1.2"
        else:
            pct_str = f"{pct}%"
        lines.append(f"  - {label}: {pct_str} (status={status})")

    top = _top_gap(dimensions)
    if top is not None:
        lines.append("")
        lines.append(
            f"Top gap (lowest computable readiness): {top[1]} at {top[0]}%."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM call + response parsing
# ---------------------------------------------------------------------------


def _strip_code_fences(text: str) -> str:
    """Defensive: Gemini usually follows the JSON-only instruction, but
    strip ```json ... ``` fences if they slip in."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop the first line (```json or ```) and any trailing ```.
        lines = stripped.split("\n")
        if len(lines) >= 2:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def _call_llm(prompt_text: str) -> tuple[dict, dict]:
    """Returns (parsed_output, usage_info). Raises on failure."""
    start = time.time()
    model = genai.GenerativeModel(
        model_name=_MODEL_NAME,
        system_instruction=_SYSTEM_PROMPT,
    )
    response = model.generate_content(prompt_text)
    latency_ms = int((time.time() - start) * 1000)

    text = _strip_code_fences(response.text)
    parsed = json.loads(text)

    usage = getattr(response, "usage_metadata", None)
    usage_info = {
        "model": _MODEL_NAME,
        "latency_ms": latency_ms,
        "input_tokens": getattr(usage, "prompt_token_count", None) if usage else None,
        "output_tokens": (
            getattr(usage, "candidates_token_count", None) if usage else None
        ),
    }
    return parsed, usage_info


# ---------------------------------------------------------------------------
# Fallback builders (no LLM)
# ---------------------------------------------------------------------------


def _static_unreachable_verdict(now_iso: str) -> dict:
    """Canonical spec §v1.2.6 fallback when engine_status == 'unreachable'."""
    return {
        "headline": "Audit readiness data is currently unavailable.",
        "body": "Verify the compliance engine is running.",
        "tone": "neutral",
        "generated_at": now_iso,
        "source": "static_fallback",
    }


def _data_driven_fallback(
    stats: dict, dimensions: list[dict], tone: str, now_iso: str
) -> dict:
    """Minimal deterministic fallback when the LLM call fails (missing
    API key, timeout, parse error). Honest but mechanical tone."""
    overall = stats.get("overall_readiness_pct")
    basis = stats.get("overall_readiness_basis") or {}
    computed = basis.get("computed_dimension_count", 0)
    total = basis.get("total_dimension_count", 6)

    if overall is None:
        headline = "Audit readiness metrics are not yet available."
    else:
        headline = (
            f"{overall}% audit-ready across {computed} of {total} "
            f"measured dimensions."
        )

    body_parts: list[str] = []
    doc_gap = stats.get("doc_gap_count")
    threshold = (stats.get("doc_gap_threshold_cents") or 250_000) / 100
    if doc_gap is not None and doc_gap > 0:
        body_parts.append(
            f"{doc_gap} transactions over ${int(threshold):,} lack linked invoices."
        )
    top = _top_gap(dimensions)
    if top is not None and (overall is None or top[0] < overall):
        body_parts.append(f"Lowest readiness: {top[1]} at {top[0]}%.")
    if not body_parts:
        body_parts.append(
            "Run a compliance scan to produce initial readiness data."
        )

    return {
        "headline": headline,
        "body": " ".join(body_parts),
        "tone": tone,
        "generated_at": now_iso,
        "source": "static_fallback",
    }


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def generate_verdict(
    engine_status: str,
    stats: dict,
    dimensions: list[dict],
) -> dict:
    """Generate the Audit Readiness verdict box payload.

    Args:
        engine_status: "ok" or "unreachable" (from extract_all's
            audit_dimensions_from_engine fetch).
        stats: the engine's stats block (or the cockpit's unreachable
            fallback payload with the same shape).
        dimensions: the cockpit's ui_dimensions list (pct/status/label)
            OR the engine's dimensions list (readiness_pct/status/title).
            Both shapes are supported via the _dim_pct / _dim_label
            helpers.

    Returns dict with keys:
        headline, body, tone, generated_at (ISO UTC), source
        ("llm" | "static_fallback" | "cache").
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Spec §v1.2.6: engine-unreachable bypasses the LLM.
    if engine_status == "unreachable":
        return _static_unreachable_verdict(now_iso)

    # Cache lookup before anything expensive.
    key = _cache_key(engine_status, stats, dimensions)
    cached = _cache_get(key)
    if cached is not None:
        return {**cached, "source": "cache"}

    tone = _tone_for_pct(stats.get("overall_readiness_pct"))

    # No API key — skip the LLM call, serve the data-driven fallback.
    if not _GEMINI_API_KEY:
        verdict = _data_driven_fallback(stats, dimensions, tone, now_iso)
        _cache_put(key, verdict)
        return verdict

    prompt_text = (
        "Current Audit Readiness state:\n\n"
        + _format_input_summary(stats, dimensions)
        + "\n\nWrite the verdict."
    )

    try:
        parsed, usage = _call_llm(prompt_text)
        # Cost-awareness log — no prompt text, no verdict text.
        log.info(
            "agents.finance.verdict.llm_call",
            model=usage["model"],
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            latency_ms=usage["latency_ms"],
        )
        headline = str(parsed.get("headline", "")).strip()
        body = str(parsed.get("body", "")).strip()
        if not headline or not body:
            raise ValueError("LLM returned empty headline or body")
        verdict = {
            "headline": headline,
            "body": body,
            "tone": tone,
            "generated_at": now_iso,
            "source": "llm",
        }
    except Exception as exc:  # noqa: BLE001 — intentional catch-all
        log.warning(
            "agents.finance.verdict.llm_failed",
            error=str(exc),
            fallback="data_driven",
        )
        verdict = _data_driven_fallback(stats, dimensions, tone, now_iso)

    _cache_put(key, verdict)
    return verdict

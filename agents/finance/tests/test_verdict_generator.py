"""Coverage for the Audit Readiness verdict generator.

The TODO at verdict_generator.py:19 named the four scope items below;
each section in this file maps to one of them:

  1. Three fallback layers (engine-unreachable / no-API-key / LLM error).
  2. Cache hit + miss behavior.
  3. Hash-key stability across irrelevant field additions.
  4. LLM happy path (with a stubbed Gemini response).
"""
from __future__ import annotations

import json
from typing import Any

import pytest

import agents.finance.verdict_generator as vg


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cache():
    """Cache is a module-level dict — clear between tests so they don't
    bleed cached verdicts into one another."""
    vg._cache.clear()
    yield
    vg._cache.clear()


def _stats(overall_pct: int | None = 78, doc_gap: int | None = 4) -> dict:
    return {
        "overall_readiness_pct": overall_pct,
        "overall_readiness_basis": {
            "computed_dimension_count": 4,
            "total_dimension_count": 6,
        },
        "doc_gap_count": doc_gap,
        "doc_gap_threshold_cents": 250_000,
        "te_certs_status": "current",
    }


def _dimensions() -> list[dict]:
    return [
        {"id": "documentation", "label": "Documentation", "pct": 92, "status": "computed"},
        {"id": "time_effort", "label": "Time & Effort", "pct": 60, "status": "computed"},
        {"id": "procurement", "label": "Procurement", "pct": None, "status": "placeholder"},
    ]


# ---------------------------------------------------------------------------
# Fallback layer 3 — engine unreachable
# ---------------------------------------------------------------------------


class TestEngineUnreachable:
    def test_unreachable_short_circuits_to_static(self, monkeypatch):
        # Even with an API key, unreachable bypasses the LLM.
        monkeypatch.setattr(vg, "_GEMINI_API_KEY", "fake-key")

        called = {"n": 0}
        def _spy(*_a, **_kw):
            called["n"] += 1
            return ({"headline": "x", "body": "y"}, {"model": "m", "input_tokens": 0, "output_tokens": 0, "latency_ms": 0})
        monkeypatch.setattr(vg, "_call_llm", _spy)

        verdict = vg.generate_verdict("unreachable", _stats(), _dimensions())
        assert verdict["source"] == "static_fallback"
        assert verdict["headline"] == "Audit readiness data is currently unavailable."
        assert verdict["tone"] == "neutral"
        assert called["n"] == 0


# ---------------------------------------------------------------------------
# Fallback layer 2 — no API key, data-driven path
# ---------------------------------------------------------------------------


class TestNoApiKeyFallback:
    def test_no_api_key_yields_data_driven_verdict(self, monkeypatch):
        monkeypatch.setattr(vg, "_GEMINI_API_KEY", "")
        verdict = vg.generate_verdict("ok", _stats(overall_pct=78, doc_gap=4), _dimensions())
        assert verdict["source"] == "static_fallback"
        # Tone derived from 78% → "watch" band (>=70).
        assert verdict["tone"] == "watch"
        # Headline names the % so a reader sees the actual readiness.
        assert "78%" in verdict["headline"]
        # Body should mention the doc gap when it's >0.
        assert "4 transactions" in verdict["body"]

    def test_data_driven_handles_missing_overall_pct(self, monkeypatch):
        monkeypatch.setattr(vg, "_GEMINI_API_KEY", "")
        verdict = vg.generate_verdict("ok", _stats(overall_pct=None, doc_gap=0), _dimensions())
        assert "not yet available" in verdict["headline"]


# ---------------------------------------------------------------------------
# Fallback layer 1 — LLM happy path + LLM error
# ---------------------------------------------------------------------------


def _stub_llm_ok(*_a, **_kw) -> tuple[dict, dict]:
    return (
        {
            "headline": "Audit posture holding at 78% across measured dimensions.",
            "body": "Time & Effort lags at 60%; Krista's quarterly batch closes the gap before May 1.",
        },
        {"model": "gemini-2.5-flash", "input_tokens": 412, "output_tokens": 96, "latency_ms": 850},
    )


def _stub_llm_blow_up(*_a, **_kw):
    raise RuntimeError("simulated network failure")


class TestLLMHappyPath:
    def test_llm_success_uses_llm_source(self, monkeypatch):
        monkeypatch.setattr(vg, "_GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr(vg, "_call_llm", _stub_llm_ok)
        verdict = vg.generate_verdict("ok", _stats(), _dimensions())
        assert verdict["source"] == "llm"
        assert "78%" in verdict["headline"]


class TestLLMErrorFallback:
    def test_llm_failure_falls_to_data_driven(self, monkeypatch):
        monkeypatch.setattr(vg, "_GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr(vg, "_call_llm", _stub_llm_blow_up)
        verdict = vg.generate_verdict("ok", _stats(), _dimensions())
        # The data-driven fallback marks itself with source="static_fallback".
        assert verdict["source"] == "static_fallback"
        assert verdict["tone"] == "watch"

    def test_llm_returns_empty_headline_falls_back(self, monkeypatch):
        monkeypatch.setattr(vg, "_GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr(
            vg,
            "_call_llm",
            lambda *_a, **_kw: ({"headline": "", "body": "ok"}, {"model": "m", "input_tokens": 0, "output_tokens": 0, "latency_ms": 0}),
        )
        verdict = vg.generate_verdict("ok", _stats(), _dimensions())
        assert verdict["source"] == "static_fallback"


# ---------------------------------------------------------------------------
# Cache behavior
# ---------------------------------------------------------------------------


class TestCache:
    def test_second_call_returns_cached_source(self, monkeypatch):
        monkeypatch.setattr(vg, "_GEMINI_API_KEY", "fake-key")
        call_count = {"n": 0}

        def _counted_llm(*a, **kw):
            call_count["n"] += 1
            return _stub_llm_ok(*a, **kw)

        monkeypatch.setattr(vg, "_call_llm", _counted_llm)

        first = vg.generate_verdict("ok", _stats(), _dimensions())
        second = vg.generate_verdict("ok", _stats(), _dimensions())

        assert first["source"] == "llm"
        assert second["source"] == "cache"
        # Cached body matches the first (LLM) body.
        assert second["headline"] == first["headline"]
        assert call_count["n"] == 1

    def test_cache_expires_after_ttl(self, monkeypatch):
        monkeypatch.setattr(vg, "_GEMINI_API_KEY", "fake-key")
        monkeypatch.setattr(vg, "_call_llm", _stub_llm_ok)

        first = vg.generate_verdict("ok", _stats(), _dimensions())
        assert first["source"] == "llm"

        # Fast-forward time well past the 5-min TTL.
        original_time = vg.time.time
        monkeypatch.setattr(vg.time, "time", lambda: original_time() + (vg._CACHE_TTL_SECONDS + 60))

        again = vg.generate_verdict("ok", _stats(), _dimensions())
        # Past TTL — should re-call the LLM.
        assert again["source"] == "llm"


# ---------------------------------------------------------------------------
# Hash-key stability
# ---------------------------------------------------------------------------


class TestCacheKeyStability:
    def test_unrelated_field_additions_do_not_change_key(self):
        baseline_stats = _stats()
        baseline_dims = _dimensions()
        baseline_key = vg._cache_key("ok", baseline_stats, baseline_dims)

        # Add fields that the verdict prose doesn't depend on. Cache key
        # should stay the same so we don't get spurious misses when the
        # engine adds metadata.
        noisy_stats = {**baseline_stats, "irrelevant_metric": 42, "another_extra": "noise"}
        noisy_dims = [{**d, "what": "explanatory copy", "as_of": "2026-04-01"} for d in baseline_dims]
        noisy_key = vg._cache_key("ok", noisy_stats, noisy_dims)

        assert baseline_key == noisy_key

    def test_relevant_field_change_changes_key(self):
        baseline_key = vg._cache_key("ok", _stats(overall_pct=78), _dimensions())
        bumped_key = vg._cache_key("ok", _stats(overall_pct=82), _dimensions())
        assert baseline_key != bumped_key

    def test_engine_status_change_changes_key(self):
        ok_key = vg._cache_key("ok", _stats(), _dimensions())
        unreachable_key = vg._cache_key("unreachable", _stats(), _dimensions())
        assert ok_key != unreachable_key


# ---------------------------------------------------------------------------
# _strip_code_fences — small helper that's easy to break
# ---------------------------------------------------------------------------


class TestStripCodeFences:
    def test_strips_json_fence(self):
        assert vg._strip_code_fences('```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_strips_bare_fence(self):
        assert vg._strip_code_fences("```\n{\"a\": 1}\n```") == '{"a": 1}'

    def test_no_fence_passes_through(self):
        assert vg._strip_code_fences('{"a": 1}') == '{"a": 1}'

    def test_loadable_after_strip(self):
        # Round-trip — stripped output must be valid JSON.
        stripped = vg._strip_code_fences('```json\n{"headline": "h", "body": "b"}\n```')
        assert json.loads(stripped) == {"headline": "h", "body": "b"}

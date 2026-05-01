"""Coverage for the Recent Compliance Activity feed label translator.

Exercises every branch the v1.2 cockpit-side step 6 follow-up TODO
named: action templates, unknown-action fallback, actor display
(known + email-local-part + raw), timestamp formatting bands, and
the classifier-silence filter.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agents.finance.audit_activity_labels import (
    display_actor,
    render_entries,
    render_entry,
)


# ---------------------------------------------------------------------------
# Actor display
# ---------------------------------------------------------------------------


class TestDisplayActor:
    def test_known_actor_uses_friendly_name(self):
        assert display_actor("krista@cfa.org") == "Krista"
        assert display_actor("compliance_monitor") == "Compliance Monitor"

    def test_unknown_email_uses_local_part(self):
        assert display_actor("operator@example.com") == "operator"

    def test_unknown_non_email_returns_raw(self):
        assert display_actor("scheduled-job") == "scheduled-job"

    def test_empty_or_none_actor_yields_unknown(self):
        assert display_actor(None) == "Unknown"
        assert display_actor("") == "Unknown"


# ---------------------------------------------------------------------------
# Action templates (render_entry's action_text branch)
# ---------------------------------------------------------------------------


def _entry(action: str, *, target_summary: str | None = None, actor: str | None = None) -> dict:
    return {
        "action": action,
        "target_summary": target_summary,
        "actor": actor or "krista@cfa.org",
        "occurred_at": "2026-04-23T10:42:00+00:00",
    }


class TestActionText:
    def test_template_with_summary_interpolates(self):
        rendered = render_entry(_entry("compliance.flag.resolve", target_summary="Vendor X $1,500 — §200.438"))
        assert rendered["action_text"] == "Resolved flag: Vendor X $1,500 — §200.438"

    def test_template_with_missing_summary_strips_suffix(self):
        rendered = render_entry(_entry("compliance.flag.resolve", target_summary=None))
        assert rendered["action_text"] == "Resolved flag"

    def test_static_template_ignores_summary(self):
        # time_effort.certified has no {target_summary} placeholder.
        rendered = render_entry(_entry("time_effort.certified", target_summary="anything"))
        assert rendered["action_text"] == "Certification signed"

    def test_unknown_action_falls_back_to_actor_performed_action(self):
        rendered = render_entry(_entry("custom.weird.event", actor="krista@cfa.org"))
        assert rendered["action_text"] == "Krista performed custom.weird.event"

    def test_qb_sync_template_interpolates(self):
        rendered = render_entry(_entry("qb.sync.transactions", target_summary="14 added since 2026-04-01"))
        assert rendered["action_text"] == "QB sync — transactions: 14 added since 2026-04-01"


# ---------------------------------------------------------------------------
# Timestamp formatting bands
# ---------------------------------------------------------------------------


class TestTimestampFormatting:
    """`now` is injected so the bands are deterministic across CI clocks."""

    NOW = datetime(2026, 4, 23, 14, 0, 0, tzinfo=timezone.utc)

    def _at(self, delta: timedelta) -> str:
        return (self.NOW - delta).isoformat()

    def test_under_one_minute_is_just_now(self):
        rendered = render_entry({"occurred_at": self._at(timedelta(seconds=20))}, now=self.NOW)
        assert rendered["timestamp_label"] == "just now"

    def test_under_one_hour_is_n_min_ago(self):
        rendered = render_entry({"occurred_at": self._at(timedelta(minutes=23))}, now=self.NOW)
        assert rendered["timestamp_label"] == "23 min ago"

    def test_same_day_is_clock_time(self):
        rendered = render_entry({"occurred_at": self._at(timedelta(hours=3))}, now=self.NOW)
        # 14:00 - 3h = 11:00 UTC; %I:%M %p with leading-zero strip
        assert rendered["timestamp_label"] == "11:00 AM"

    def test_previous_day_prefixes_yesterday(self):
        rendered = render_entry({"occurred_at": self._at(timedelta(days=1, hours=2))}, now=self.NOW)
        assert rendered["timestamp_label"].startswith("Yesterday at ")

    def test_within_year_uses_month_day_at_time(self):
        rendered = render_entry({"occurred_at": self._at(timedelta(days=30))}, now=self.NOW)
        assert " at " in rendered["timestamp_label"]
        assert "Yesterday" not in rendered["timestamp_label"]

    def test_older_than_year_uses_full_date(self):
        rendered = render_entry({"occurred_at": self._at(timedelta(days=400))}, now=self.NOW)
        # No time component for cross-year — just "Mon DD, YYYY"
        assert "," in rendered["timestamp_label"]
        assert " at " not in rendered["timestamp_label"]

    def test_invalid_timestamp_falls_back_to_raw(self):
        rendered = render_entry({"occurred_at": "not-iso-8601"}, now=self.NOW)
        assert rendered["timestamp_label"] == "not-iso-8601"

    def test_missing_timestamp_yields_empty_string(self):
        rendered = render_entry({"occurred_at": ""}, now=self.NOW)
        assert rendered["timestamp_label"] == ""


# ---------------------------------------------------------------------------
# render_entries — silenced-action filter + order preservation
# ---------------------------------------------------------------------------


class TestRenderEntries:
    NOW = datetime(2026, 4, 23, 14, 0, 0, tzinfo=timezone.utc)

    def test_silences_classifier_prefix_actions(self):
        raw = {
            "entries": [
                {"action": "classifier.flag_silent", "occurred_at": self.NOW.isoformat()},
                {"action": "compliance.flag.resolve", "target_summary": "X", "occurred_at": self.NOW.isoformat()},
            ]
        }
        rendered = render_entries(raw, now=self.NOW)
        assert len(rendered) == 1
        assert rendered[0]["action_text"].startswith("Resolved flag")

    def test_preserves_engine_order(self):
        raw = {
            "entries": [
                {"action": "compliance.flag.acknowledge", "target_summary": "A", "occurred_at": self.NOW.isoformat()},
                {"action": "compliance.flag.resolve", "target_summary": "B", "occurred_at": self.NOW.isoformat()},
                {"action": "compliance.flag.waive", "target_summary": "C", "occurred_at": self.NOW.isoformat()},
            ]
        }
        rendered = render_entries(raw, now=self.NOW)
        assert [r["action_text"] for r in rendered] == [
            "Acknowledged flag: A",
            "Resolved flag: B",
            "Waived flag: C",
        ]

    def test_empty_entries_list(self):
        assert render_entries({"entries": []}) == []

    def test_missing_entries_key(self):
        assert render_entries({}) == []

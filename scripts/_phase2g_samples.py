"""
Phase 2G Stage 1 — generate 12 sample match narratives across the
cosine spectrum and print them for review. Does NOT write to the
database. Does NOT commit anything. Read-only apart from the LLM
API calls.

Spectrum:
  Strong   (cosine > 0.60)   → 3 pairs
  Match    (0.50 - 0.60]     → 4 pairs
  Weak     (0.40 - 0.50)     → 3 pairs
  Marginal (< 0.40)          → 2 pairs

Pairs are randomly sampled within each bucket but filtered to Tier-A
students (institution + parsed resume + skills) so there's enough
profile content for the narrative to chew on.

Run:  python scripts/_phase2g_samples.py
"""
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agents.job_board.data_source import PostgresDataSource
from agents.job_board.match_narrative import (
    calibration_label,
    compute_overlap,
    generate_narrative,
    NarrativeError,
)

# Hardcoded pairs from the Phase 2G Stage-1 v1 run — used so v2 gives
# direct before/after narrative comparisons on identical profiles.
# Bucket layout preserved: 3 Strong, 4 Match, 3 Weak, 2 Marginal.
HARDCODED_PAIRS: list[tuple[str, int]] = [
    ("03f1e010-7ddc-4d6c-af44-593e1887582f", 14),  # Jiahui Z.  cos=0.6117 Strong
    ("652561c9-5470-4020-bf3a-f6fda99ad877", 48),  # Christopher M.  0.6162 Strong
    ("a57fe38b-3d6a-437b-8b00-4c226cf1775b", 14),  # Iris Z.  0.6051 Strong
    ("0d8023f1-68fe-42e1-a008-3f80d4566e9e", 42),  # Henos G.  0.5382 Match
    ("9b3b1331-845e-4957-9943-fd233a1b5057", 44),  # Suprita B.  0.5185 Match
    ("5f8abcb3-2f48-4ee8-84ab-5e9122500d2e", 39),  # Ken R.  0.5280 Match
    ("00fa5ace-fb6c-48ae-a90a-1b834bfc1566", 14),  # Michael T.  0.5820 Match
    ("9ec77fac-8afd-463b-92df-7640fbba7d7c", 53),  # Elijah S.  0.4180 Weak
    ("3baf19b2-c158-481c-ab7c-df8936ae6160", 31),  # Michael B.  0.4982 Weak
    ("cf2554cf-46fa-4882-9e2b-3405091b0bb0", 32),  # Emil K.  0.4485 Weak
    ("4b64e0d0-f848-4241-98a9-b27553218a0b", 48),  # Cami L.  0.3431 Marginal
    ("83bc17a7-ef82-4cfd-9138-129699adc071", 28),  # Shubhangi B.  0.3771 Marginal
]


def redact_name(full_name: str | None) -> str:
    """Soft PII redaction — keep first name for readability, last
    initial only. Matches the display convention used in Phase 2D
    validation output."""
    if not full_name:
        return "—"
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0]
    return parts[0] + " " + parts[-1][0] + "."


def format_items(items: list[dict]) -> list[str]:
    out: list[str] = []
    for it in items:
        area = it.get("area", "—")
        detail = it.get("evidence") or it.get("note") or ""
        out.append(f"- {area}: {detail}")
    return out or ["(none)"]


def print_sample(idx: int, total: int, student: dict, job: dict,
                 cosine: float, overlap: dict, narrative: dict | None,
                 error: str | None) -> None:
    label = calibration_label(cosine)
    print()
    print("─" * 78)
    print(f"Sample {idx}/{total}   |   cosine={cosine:.4f}   |   {label}")
    print("─" * 78)
    print(f"STUDENT:  {redact_name(student.get('full_name'))}")
    inst = student.get("institution") or "—"
    fos  = student.get("field_of_study") or "—"
    deg  = student.get("degree") or "—"
    print(f"          {inst} · {fos} · {deg}")
    print(f"JOB:      {job.get('title') or '—'} @ {job.get('company') or '—'}")

    if error is not None:
        print()
        print("VERDICT:  (generation failed)")
        print(f"          {error}")
        return

    v = (narrative or {}).get("verdict_line", "")
    n = (narrative or {}).get("narrative_text", "")

    print()
    print(f"VERDICT:  {v}")
    print()
    print("NARRATIVE:")
    # Respect paragraph breaks (two newlines) then wrap each paragraph
    # to a readable width.
    for para in n.split("\n\n"):
        for line in textwrap.wrap(para.strip(), 74) or [""]:
            print("  " + line)
        print()

    strong = overlap.get("strong_matches") or []
    gaps   = overlap.get("gaps") or []
    print("STRENGTHS:")
    for line in format_items(strong):
        print("  " + line)
    print()
    print("GAPS:")
    for line in format_items(gaps):
        print("  " + line)


def main() -> int:
    source = PostgresDataSource()
    print(f"Regenerating {len(HARDCODED_PAIRS)} hardcoded pairs (Phase 2G v2)…")
    # Recompute cosine per pair so we don't rely on stale expected values.
    all_pairs: list[tuple[str, int, float]] = []
    for s_id, j_id in HARDCODED_PAIRS:
        cos = source.get_cosine_for_pair(s_id, j_id)
        if cos is None:
            print(f"  WARN: ({s_id[:8]}..., {j_id}) missing embedding — skipping")
            continue
        all_pairs.append((s_id, j_id, cos))

    if not all_pairs:
        print("No pairs resolved. Are student and job embeddings present?")
        return 1

    total = len(all_pairs)
    for i, (s_id, j_id, cosine) in enumerate(all_pairs, 1):
        try:
            student = source.get_student(s_id)
            job = source.get_job(j_id)
            if student is None or job is None:
                print_sample(i, total, {}, {}, cosine, {}, None,
                             f"fetch failed (student={student is not None}, "
                             f"job={job is not None})")
                continue
            label = calibration_label(cosine)
            overlap = compute_overlap(student, job)
            try:
                narrative = generate_narrative(student, job, overlap, cosine, label)
                err = None
            except NarrativeError as e:
                narrative = None
                err = f"NarrativeError: {e}"
            print_sample(i, total, student, job, cosine, overlap, narrative, err)
        except Exception as e:  # noqa: BLE001 — never abort the whole run
            print(f"\nSample {i}/{total}: unexpected error {type(e).__name__}: {e}")
    print()
    print("─" * 78)
    print(f"Done. {total} samples printed. Review narrative quality,")
    print("then approve or request prompt iteration.")
    print("─" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())

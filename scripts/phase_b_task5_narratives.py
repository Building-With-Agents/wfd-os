"""Phase B Task 5 — generate match narratives for WSB Cohort 1.

Produces one match_narratives row per (apprentice, top-3 match) pair,
using agents/job_board/match_narrative.py's generate_narrative + the
same compute_overlap methodology Task 4 used for gap analyses.

Reuses Task 4 helpers (fetch_student, fetch_job, lookup_tenant_uuid)
via import — no redefinition, no re-extraction. skills_required on
jobs_enriched is already populated from Task 4's side-effect.

Inputs:
  - Top-3 matches per apprentice from cohort_matches (tenant=WSB)
  - cohort_matches.cosine_similarity used directly (not recomputed)

Tenancy: DELETE-then-INSERT scoped to WHERE tenant_id = WSB.
Per-row error handling: no stub rows on NarrativeError; rollback + continue.
"""
from __future__ import annotations

import json
import sys
import time
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from pgconfig import PG_CONFIG  # noqa: E402

# Reuse Task 4 helpers verbatim — no redefinition, no drift.
import phase_b_task4_gap_analyses as task4  # noqa: E402

# agents/job_board/match_narrative.py (Phase 2G, uncommitted on branch)
sys.path.insert(0, str(SCRIPTS_DIR.parent / "agents" / "job_board"))
import match_narrative as mn  # noqa: E402


WSB_CODE = "WSB"
TOP_N_FOR_NARRATIVE = 3


def _serialize_student_dates(student: dict) -> dict:
    """match_narrative._format_student_for_prompt does `start_date[:7]`, which
    expects ISO strings, not datetime.date objects. Task 4's fetch_student
    returns raw date objects (it never hit this path — compute_overlap reads
    only skills[].name). Convert dates to ISO strings here so generate_narrative
    works without modifying the Phase 2G module or the committed task4 helpers.
    """
    from datetime import date, datetime
    out = dict(student)
    work = []
    for w in student.get("work_experience") or []:
        w2 = dict(w)
        for k in ("start_date", "end_date"):
            v = w2.get(k)
            if isinstance(v, (date, datetime)):
                w2[k] = v.isoformat()
        work.append(w2)
    out["work_experience"] = work
    return out


def main() -> int:
    print("=" * 70)
    print("Phase B Task 5 — Match narratives for WSB Cohort 1 (Phase 2G)")
    print("=" * 70)

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False

    wsb = task4.lookup_tenant_uuid(conn, WSB_CODE)
    cfa = task4.lookup_tenant_uuid(conn, "CFA")
    print(f"WSB tenant_id: {wsb}")
    print()

    cur = conn.cursor()

    # Baseline counts for CFA drift check
    cur.execute("SELECT COUNT(*) FROM match_narratives WHERE tenant_id = %s::uuid", (cfa,))
    cfa_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM match_narratives WHERE tenant_id = %s::uuid", (wsb,))
    wsb_before = cur.fetchone()[0]
    print(f"match_narratives before: CFA={cfa_before}  WSB={wsb_before}")

    # Idempotent reset for WSB scope only
    cur.execute("DELETE FROM match_narratives WHERE tenant_id = %s::uuid", (wsb,))
    deleted_prior = cur.rowcount
    print(f"  deleted {deleted_prior} prior WSB rows (idempotent reset)")
    print()

    # Top-N matches from cohort_matches
    cur.execute(
        """
        SELECT cm.student_id, cm.job_id, cm.match_rank,
               cm.cosine_similarity, s.full_name
        FROM cohort_matches cm
        JOIN students s ON s.id = cm.student_id
        WHERE cm.tenant_id = %s::uuid
          AND cm.match_rank <= %s
        ORDER BY s.full_name, cm.match_rank
        """,
        (wsb, TOP_N_FOR_NARRATIVE),
    )
    top_matches = cur.fetchall()
    print(f"top-{TOP_N_FOR_NARRATIVE} matches to narrate: {len(top_matches)} "
          f"(expected {9 * TOP_N_FOR_NARRATIVE})")
    print()

    # Targeted samples for the report:
    #   - Strong (Fabian rank 1, cosine ~0.638)
    #   - Match  (one of Emilio/Fatima/Nestor rank 1)
    #   - Weak   (Angel rank 1, cosine ~0.410)
    sample_specs = {
        "strong": {"name_prefix": "Fabian", "rank": 1},
        "match":  {"name_prefix": "Emilio", "rank": 1},
        "weak":   {"name_prefix": "Angel",  "rank": 1},
    }
    samples: dict[str, dict] = {}

    inserted = 0
    failed: list[dict] = []
    per_apprentice_counts: dict[str, int] = {}
    per_label_counts: dict[str, int] = {}

    for (student_id, job_id, match_rank, cosine, full_name) in top_matches:
        cosine_f = float(cosine)
        label = mn.calibration_label(cosine_f)
        per_label_counts[label] = per_label_counts.get(label, 0) + 1

        try:
            student = _serialize_student_dates(task4.fetch_student(conn, str(student_id), wsb))
            job = task4.fetch_job(conn, job_id, wsb)

            overlap = mn.compute_overlap(student, job)
            narrative = mn.generate_narrative(student, job, overlap, cosine_f, label)
            input_hash = mn.compute_input_hash(student, job)

            cur.execute(
                """
                INSERT INTO match_narratives (
                    student_id, job_id,
                    verdict_line, narrative_text,
                    match_strengths, match_gaps, match_partial,
                    calibration_label, cosine_similarity, input_hash,
                    tenant_id
                ) VALUES (
                    %s::uuid, %s,
                    %s, %s,
                    %s::jsonb, %s::jsonb, %s::jsonb,
                    %s, %s, %s,
                    %s::uuid
                )
                """,
                (
                    str(student_id), job_id,
                    narrative["verdict_line"], narrative["narrative_text"],
                    json.dumps(overlap.get("strong_matches") or []),
                    json.dumps(overlap.get("gaps") or []),
                    json.dumps(overlap.get("partial_matches") or []),
                    label, cosine_f, input_hash,
                    wsb,
                ),
            )
            conn.commit()
            inserted += 1
            per_apprentice_counts[full_name] = per_apprentice_counts.get(full_name, 0) + 1

            # Capture targeted samples
            for key, spec in sample_specs.items():
                if key in samples:
                    continue
                if full_name.startswith(spec["name_prefix"]) and match_rank == spec["rank"]:
                    samples[key] = {
                        "student": full_name,
                        "job_id": job_id,
                        "job_title": job.get("title"),
                        "job_company": job.get("company"),
                        "match_rank": match_rank,
                        "cosine": cosine_f,
                        "label": label,
                        "verdict_line": narrative["verdict_line"],
                        "narrative_text": narrative["narrative_text"],
                        "strong_matches": overlap.get("strong_matches") or [],
                        "gaps": overlap.get("gaps") or [],
                    }

            safe_title = (job.get("title") or "").encode("ascii", "replace").decode("ascii")[:38]
            print(f"  [{label:<8}] {full_name[:23]:<25} rank {match_rank}  #{job_id:<4} "
                  f"{safe_title:<40} cos={cosine_f:.3f}")
            time.sleep(0.1)
        except mn.NarrativeError as e:
            conn.rollback()
            failed.append({
                "student_id": str(student_id), "job_id": job_id,
                "full_name": full_name, "error": f"NarrativeError: {str(e)[:200]}",
            })
            print(f"  FAIL  {full_name} × #{job_id}: NarrativeError: {str(e)[:200]}")
        except Exception as e:
            conn.rollback()
            failed.append({
                "student_id": str(student_id), "job_id": job_id,
                "full_name": full_name, "error": f"{type(e).__name__}: {str(e)[:200]}",
            })
            print(f"  FAIL  {full_name} × #{job_id}: {type(e).__name__}: {str(e)[:200]}")

    # Verification
    cur.execute("SELECT COUNT(*) FROM match_narratives WHERE tenant_id = %s::uuid", (cfa,))
    cfa_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM match_narratives WHERE tenant_id = %s::uuid", (wsb,))
    wsb_after = cur.fetchone()[0]
    conn.close()

    print()
    print("=" * 70)
    print(f"Inserted: {inserted}  Failed: {len(failed)}")
    print(f"match_narratives after:  CFA={cfa_after}  WSB={wsb_after}")
    cfa_ok = cfa_after == cfa_before
    wsb_ok = wsb_after == inserted
    print(f"  CFA drift: {'NONE' if cfa_ok else 'CHANGED'} (expected {cfa_before}, got {cfa_after})")
    print(f"  WSB count: {'OK' if wsb_ok else 'MISMATCH'} (expected {inserted}, got {wsb_after})")

    print()
    print("Per-label counts:")
    for lbl in ("Strong", "Match", "Weak", "Marginal"):
        print(f"  {lbl:<10}  {per_label_counts.get(lbl, 0)}")

    print()
    print("Per-apprentice narrative counts:")
    for name, n in sorted(per_apprentice_counts.items()):
        tag = "OK" if n == TOP_N_FOR_NARRATIVE else "WARN"
        print(f"  [{tag}] {name:<30} {n} narratives")

    if failed:
        print()
        print("Failures:")
        for f in failed:
            print(f"  - {f['full_name']} × #{f['job_id']}: {f['error']}")

    # Targeted spot-check samples
    for key in ("strong", "match", "weak"):
        s = samples.get(key)
        if not s:
            print(f"\n(no sample captured for tier={key})")
            continue
        print()
        print("=" * 70)
        print(f"SAMPLE — {key.upper()} tier")
        print("=" * 70)
        print(f"  student:     {s['student']}")
        print(f"  job:         #{s['job_id']} {s['job_title']!r} @ {s['job_company']}")
        print(f"  match_rank:  {s['match_rank']}")
        print(f"  cosine:      {s['cosine']:.4f}")
        print(f"  label:       {s['label']}")
        print(f"  strengths ({len(s['strong_matches'])}):")
        for m in s["strong_matches"]:
            area = (m.get("area") or "").encode("ascii", "replace").decode("ascii")
            ev = (m.get("evidence") or "").encode("ascii", "replace").decode("ascii")
            print(f"    • {area} — {ev}")
        print(f"  gaps ({len(s['gaps'])}):")
        for g in s["gaps"]:
            area = (g.get("area") or "").encode("ascii", "replace").decode("ascii")
            note = (g.get("note") or "").encode("ascii", "replace").decode("ascii")
            print(f"    • {area} — {note}")
        print()
        print(f"  VERDICT: {s['verdict_line']}")
        print()
        print("  NARRATIVE:")
        for para in s["narrative_text"].split("\n\n"):
            print(f"    {para}")
            print()

    return 0 if (not failed and cfa_ok and wsb_ok) else 1


if __name__ == "__main__":
    sys.exit(main())

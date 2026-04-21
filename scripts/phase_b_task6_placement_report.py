"""Phase B Task 6 — build the Cohort 1 placement report.

Reads WSB-tenant data from cohort_matches, gap_analyses, match_narratives,
students, jobs_enriched — all tenant-scoped — and emits a single markdown
report at docs/cohort1_placement_report.md.

Mechanical: no editorialization, presentation only.
"""
from __future__ import annotations

import sys
from collections import Counter
from datetime import date
from pathlib import Path

import psycopg2
import psycopg2.extras


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from pgconfig import PG_CONFIG  # noqa: E402


WORKTREE = SCRIPTS_DIR.parent
REPO_ROOT = Path(r"C:\Users\ritub\Projects\wfd-os")
REPORT_PATH = REPO_ROOT / "docs" / "cohort1_placement_report.md"


def lookup_tenant_uuid(conn, code: str) -> str:
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants WHERE code = %s", (code,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"tenant code {code!r} not seeded")
    return str(row[0])


def years_from_work(work_rows: list[dict]) -> str:
    """Rough 'years of experience' derivation from work_experience entries.
    Sum of spans in years, capped and rounded. Returns 'N/A' if no usable dates."""
    total_days = 0
    for w in work_rows:
        s = w.get("start_date")
        e = w.get("end_date") if not w.get("is_current") else date.today()
        if isinstance(s, date) and isinstance(e, date) and e >= s:
            total_days += (e - s).days
    if total_days == 0:
        return "N/A"
    yrs = total_days / 365.25
    if yrs < 1:
        months = round(yrs * 12)
        return f"~{months} months total"
    return f"~{yrs:.1f} years total"


def main() -> int:
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False

    wsb = lookup_tenant_uuid(conn, "WSB")

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # --- Apprentice core records ---
    cur.execute(
        """
        SELECT id::text AS id, full_name, email, phone, city, state,
               institution, degree, field_of_study, graduation_year,
               cohort_id, pipeline_status,
               parse_confidence_score,
               legacy_data->>'career_objective' AS career_objective
        FROM students
        WHERE tenant_id = %s::uuid AND cohort_id = 'cohort-1-feb-2026'
        ORDER BY full_name
        """,
        (wsb,),
    )
    apprentices = [dict(r) for r in cur.fetchall()]

    # --- Per-apprentice top 3 matches with narrative + gap_analysis ---
    apprentice_data: list[dict] = []
    for a in apprentices:
        # Top skills
        cur.execute(
            """
            SELECT sk.skill_name AS name
            FROM student_skills ss
            JOIN skills sk ON sk.skill_id = ss.skill_id
            WHERE ss.student_id = %s::uuid
            ORDER BY sk.skill_name
            """,
            (a["id"],),
        )
        skills = [r["name"] for r in cur.fetchall()]

        # Work experience
        cur.execute(
            """
            SELECT company, title, start_date, end_date, is_current
            FROM student_work_experience
            WHERE student_id = %s::uuid
            ORDER BY is_current DESC NULLS LAST,
                     end_date DESC NULLS FIRST,
                     start_date DESC NULLS LAST
            """,
            (a["id"],),
        )
        work = [dict(r) for r in cur.fetchall()]
        years = years_from_work(work)

        # Top-3 matches with narratives and gap analyses
        cur.execute(
            """
            SELECT cm.match_rank, cm.job_id, cm.cosine_similarity,
                   j.title AS job_title, j.company AS job_company,
                   j.city AS job_city, j.state AS job_state, j.is_remote,
                   mn.verdict_line, mn.narrative_text,
                   mn.match_strengths, mn.match_gaps, mn.calibration_label,
                   ga.gap_score, ga.missing_skills
            FROM cohort_matches cm
            JOIN jobs_enriched j  ON j.id = cm.job_id
            LEFT JOIN match_narratives mn
              ON mn.student_id = cm.student_id
             AND mn.job_id     = cm.job_id
             AND mn.tenant_id  = cm.tenant_id
            LEFT JOIN gap_analyses ga
              ON ga.student_id = cm.student_id
             AND ga.tenant_id  = cm.tenant_id
             AND ga.recommendations ->> 'cohort_match_id' = cm.id::text
            WHERE cm.student_id = %s::uuid
              AND cm.tenant_id  = %s::uuid
              AND cm.match_rank <= 3
            ORDER BY cm.match_rank
            """,
            (a["id"], wsb),
        )
        matches = [dict(r) for r in cur.fetchall()]

        apprentice_data.append({
            "apprentice": a,
            "skills": skills,
            "work": work,
            "years": years,
            "matches": matches,
        })

    # --- Aggregate findings ---

    # Strongest matches across cohort (highest cosines overall)
    cur.execute(
        """
        SELECT s.full_name, cm.match_rank, cm.cosine_similarity,
               j.title, j.company, j.id AS job_id
        FROM cohort_matches cm
        JOIN students s ON s.id = cm.student_id
        JOIN jobs_enriched j ON j.id = cm.job_id
        WHERE cm.tenant_id = %s::uuid
        ORDER BY cm.cosine_similarity DESC
        LIMIT 10
        """,
        (wsb,),
    )
    strongest = [dict(r) for r in cur.fetchall()]

    # Most-matched jobs (appearing in many apprentices' top-3)
    cur.execute(
        """
        SELECT j.id AS job_id, j.title, j.company, COUNT(*) AS n_apprentices
        FROM cohort_matches cm
        JOIN jobs_enriched j ON j.id = cm.job_id
        WHERE cm.tenant_id = %s::uuid
          AND cm.match_rank <= 3
        GROUP BY j.id, j.title, j.company
        ORDER BY n_apprentices DESC, j.id
        LIMIT 10
        """,
        (wsb,),
    )
    hot_jobs = [dict(r) for r in cur.fetchall()]

    # Common skill gaps across cohort (from gap_analyses.missing_skills)
    cur.execute(
        """
        SELECT unnest(missing_skills) AS skill
        FROM gap_analyses
        WHERE tenant_id = %s::uuid
        """,
        (wsb,),
    )
    gap_counter: Counter[str] = Counter()
    for r in cur.fetchall():
        sk = (r["skill"] or "").strip()
        if sk:
            gap_counter[sk] += 1

    # Weakest top-1 matches per apprentice
    cur.execute(
        """
        SELECT s.full_name, cm.cosine_similarity, j.title, j.company
        FROM cohort_matches cm
        JOIN students s ON s.id = cm.student_id
        JOIN jobs_enriched j ON j.id = cm.job_id
        WHERE cm.tenant_id = %s::uuid AND cm.match_rank = 1
        ORDER BY cm.cosine_similarity ASC
        LIMIT 5
        """,
        (wsb,),
    )
    weakest_top1 = [dict(r) for r in cur.fetchall()]

    conn.close()

    # --- Emit markdown ---
    lines: list[str] = []
    p = lines.append
    p("# Cohort 1 Placement Report")
    p("")
    p("*Generated: 2026-04-21 · Source: wfd-os Phase B pipeline · Tenant: WSB (Workforce Solutions Borderplex)*")
    p("")
    p("## What this report is")
    p("")
    p(
        "This report summarizes the Phase B matching output for the 9 Cohort 1 "
        "apprentices against the 40-job WSB El Paso tech pool. It is for Ritu's "
        "internal review only — it is not intended for external sharing with "
        "apprentices or with Alma at Borderplex without further curation."
    )
    p("")
    p(
        "The data backing this report lives in wfd_os PostgreSQL, WSB tenant: "
        "`cohort_matches` (90 rows — top-10 matches per apprentice), "
        "`gap_analyses` (27 rows — top-3 structured gap analyses per apprentice), "
        "`match_narratives` (27 rows — top-3 LLM-generated recruiter notes per "
        "apprentice). Matching used text-embedding-3-small (1536-dim pgvector "
        "cosine). Gap analyses and narratives used the Phase 2G "
        "`compute_overlap` + `generate_narrative` pipeline on `chat-gpt41mini`."
    )
    p("")
    p("---")
    p("")

    # ------------------------------------------------------------------
    # Aggregate findings
    # ------------------------------------------------------------------
    p("## Aggregate findings")
    p("")

    p("### Strongest matches across cohort (top 10 by cosine)")
    p("")
    p("| # | Apprentice | Rank | Cosine | Job | Company |")
    p("|---:|---|---:|---:|---|---|")
    for i, r in enumerate(strongest, 1):
        title = (r["title"] or "").replace("|", "/")
        company = (r["company"] or "").replace("|", "/")
        p(f"| {i} | {r['full_name']} | {r['match_rank']} | {float(r['cosine_similarity']):.4f} | {title} | {company} |")
    p("")

    p("### Most-matched jobs (appearing in apprentices' top-3)")
    p("")
    p("| # | Job | Company | # apprentices |")
    p("|---:|---|---|---:|")
    for i, r in enumerate(hot_jobs, 1):
        title = (r["title"] or "").replace("|", "/")
        company = (r["company"] or "").replace("|", "/")
        p(f"| {i} | {title} | {company} | {r['n_apprentices']} |")
    p("")

    p("### Common skill gaps across cohort")
    p("")
    p("Aggregated from the `gap_analyses.missing_skills` array across all 27 top-3 analyses.")
    p("")
    p("| Skill | # times listed as a gap |")
    p("|---|---:|")
    for sk, n in gap_counter.most_common(15):
        p(f"| {sk} | {n} |")
    p("")

    p("### Apprentices with the weakest top-1 matches")
    p("")
    p("| Apprentice | Top-1 cosine | Top-1 job | Company |")
    p("|---|---:|---|---|")
    for r in weakest_top1:
        title = (r["title"] or "").replace("|", "/")
        company = (r["company"] or "").replace("|", "/")
        p(f"| {r['full_name']} | {float(r['cosine_similarity']):.4f} | {title} | {company} |")
    p("")
    p("---")
    p("")

    # ------------------------------------------------------------------
    # Per-apprentice sections
    # ------------------------------------------------------------------
    p("## Per-apprentice sections")
    p("")

    for entry in apprentice_data:
        a = entry["apprentice"]
        name = a["full_name"]
        p(f"### {name}")
        p("")
        # Profile summary
        p("**Profile summary:**")
        p("")
        loc_bits = [x for x in [a.get("city"), a.get("state")] if x]
        location = ", ".join(loc_bits) if loc_bits else "—"
        edu_bits = [x for x in [a.get("degree"), a.get("field_of_study")] if x]
        edu = ", ".join(edu_bits)
        if a.get("institution"):
            edu = f"{edu} at {a['institution']}" if edu else a["institution"]
        if a.get("graduation_year"):
            edu = f"{edu} ({a['graduation_year']})" if edu else str(a["graduation_year"])
        p(f"- Education: {edu or '—'}")
        p(f"- Location: {location}")
        p(f"- Email: {a.get('email') or '—'}")
        p(f"- Cohort: {a.get('cohort_id')}")
        p(f"- Parse confidence: {float(a['parse_confidence_score']):.2f}" if a.get("parse_confidence_score") is not None else "- Parse confidence: —")
        p(f"- Work experience: {len(entry['work'])} entries, {entry['years']}")
        top_skills = entry["skills"][:12]
        if top_skills:
            p(f"- Skills (first 12 of {len(entry['skills'])}): {', '.join(top_skills)}")
        else:
            p("- Skills: none matched to taxonomy")
        if a.get("career_objective"):
            p(f"- Career objective: {a['career_objective']}")
        p("")

        # Flags — per-apprentice flags from Phase A + Phase B
        flags: list[str] = []
        if name.startswith("Angel"):
            flags.append(
                "**NYC / PhD-track profile**: Phase A extraction parsed his "
                "location as New York, NY and degree as \"PhD Computer Science "
                "at City University of New York (2028)\" — geographically and "
                "academically far from the El Paso entry-level tech pool. "
                "All three top matches fall in the Weak calibration band "
                "(cosine 0.40–0.41). If this is a parsing artifact, re-ingesting "
                "would likely change his matches materially."
            )
        if name.startswith("FATIMA"):
            flags.append(
                "**Georgia Tech MS Cybersecurity**: education field shows "
                "Fatima as an MS-level student at Georgia Institute of "
                "Technology, while her phone number (915 area code) is El Paso. "
                "Likely the GaTech online MS-CS program. Matches include a "
                "Remote AI Security Engineer role (top-1) which aligns with "
                "cyber/security framing."
            )
        if name == "Ricardo Acosta Arambula":
            flags.append(
                "**Not in the original CLAUDE.md Cohort 1 list** — was the 9th "
                "resume in the SharePoint folder. Ritu elected to keep him; "
                "pending confirmation from Alma/Gary that he belongs to this "
                "cohort."
            )
        if name == "Nestor Escobedo":
            flags.append(
                "**Parse confidence 0.90** (slightly below the cohort's 1.00 "
                "mode). Phase A extraction missed city/state — no location "
                "populated. All three top-3 narratives still succeeded."
            )
        if name.startswith("EMILIO"):
            flags.append(
                "**Parse confidence 0.90** (slightly below the cohort's 1.00 "
                "mode). Phase A extraction surfaced \"Da Vinci School For The "
                "Science And The Arts\" as institution (likely his secondary "
                "school) rather than UTEP — worth checking the original PDF "
                "against his actual current program."
            )

        if flags:
            p("**Flags:**")
            p("")
            for f in flags:
                p(f"- {f}")
            p("")

        # Top 3 matches table
        p("**Top 3 matched jobs:**")
        p("")
        p("| Rank | Job | Company | City, State | Cosine | Label |")
        p("|---:|---|---|---|---:|---|")
        for m in entry["matches"]:
            title = (m["job_title"] or "").replace("|", "/")
            company = (m["job_company"] or "").replace("|", "/")
            city = m.get("job_city") or "—"
            state = m.get("job_state") or "—"
            remote_tag = " · **REMOTE**" if m.get("is_remote") else ""
            p(f"| {m['match_rank']} | {title} | {company} | {city}, {state}{remote_tag} | {float(m['cosine_similarity']):.4f} | {m.get('calibration_label') or '—'} |")
        p("")

        # Per-match detail
        for m in entry["matches"]:
            title = m["job_title"] or "(no title)"
            p(f"#### Rank {m['match_rank']} — {title}")
            p("")
            p(f"- Company: {m['job_company'] or '—'}")
            gap_display = f"{float(m['gap_score']):.1f}" if m.get("gap_score") is not None else "—"
            p(f"- gap_score: {gap_display}")
            p(f"- cosine: {float(m['cosine_similarity']):.4f}")
            p(f"- calibration: {m.get('calibration_label') or '—'}")
            p("")

            strengths = m.get("match_strengths") or []
            gaps = m.get("match_gaps") or []
            missing = m.get("missing_skills") or []

            if strengths:
                p(f"**Strengths ({len(strengths)}):**")
                p("")
                for s in strengths:
                    area = s.get("area") or "—"
                    ev = s.get("evidence") or ""
                    p(f"- {area} — {ev}")
                p("")
            else:
                p("**Strengths:** none detected by bidirectional substring match.")
                p("")

            if gaps:
                p(f"**Gaps ({len(gaps)}):**")
                p("")
                for g in gaps:
                    area = g.get("area") or "—"
                    note = g.get("note") or ""
                    p(f"- {area} — {note}")
                p("")

            verdict = m.get("verdict_line")
            narrative = m.get("narrative_text")
            if verdict:
                p(f"**Verdict:** {verdict}")
                p("")
            if narrative:
                p("**Narrative:**")
                p("")
                for para in narrative.split("\n\n"):
                    p(f"> {para.strip()}")
                    p("> ")
                p("")

        p("---")
        p("")

    content = "\n".join(lines)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(content, encoding="utf-8")
    print(f"Wrote {REPORT_PATH}  ({len(content):,} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Phase 2G — match narrative generation.

Given a student profile + a job posting + their cosine similarity,
emit a structured recruiter's note with:
  - a one-sentence verdict
  - a two-paragraph substantive narrative
  - a list of concrete strengths (skills the student has that fit
    the role)
  - a list of gaps (things the job lists as needed that the student
    doesn't visibly have)
  - a calibration label

The module is deliberately stateless: callers (sample scripts today,
a cached endpoint tomorrow) fetch student + job rows however they
like, pass them in, and receive a JSON-serializable dict back.

Uses Azure OpenAI's `chat-gpt41mini` deployment — the same model we
picked in Phase 2D Stage 3b for job-description extraction because
it's cheap and fast enough for interactive UI.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# .env with AZURE_OPENAI_* lives at the wfd-os project root. Matches
# the load pattern used by scripts/backfill_embeddings.py.
_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env", override=False)
# Also try the user-rooted .env used in Phase 2D scripts.
load_dotenv("C:/Users/ritub/Projects/wfd-os/.env", override=False)

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_KEY = os.getenv("AZURE_OPENAI_KEY", "")
CHAT_DEPLOYMENT = "chat-gpt41mini"  # gpt-4.1-mini; same as Phase 2D
API_VERSION = "2024-02-01"

JOB_DESC_MAX_CHARS = 2000           # keep prompt tight
STRONG_CAP = 6
GAPS_CAP = 4
PARTIAL_CAP = 4

# Hard-coded recruiter's-note temperature: low for consistency but
# not 0 — we want minor variety across regenerations.
LLM_TEMPERATURE = 0.3


# ---------------------------------------------------------------------------
# Calibration label — strictly deterministic from cosine.
# ---------------------------------------------------------------------------

def calibration_label(cosine: float) -> str:
    """Categorize a cosine similarity into one of four labels.
    See Phase 2G spec for thresholds."""
    if cosine > 0.60:
        return "Strong"
    if cosine >= 0.50:
        return "Match"
    if cosine >= 0.40:
        return "Weak"
    return "Marginal"


# ---------------------------------------------------------------------------
# Structured overlap — deterministic skill matching between student
# and job. The LLM narrative relies on this as its evidence base;
# keeping it deterministic means every regen lands the same
# strengths/gaps lists even when the prose drifts.
# ---------------------------------------------------------------------------

_WORD_BOUNDARY_CACHE: dict[str, re.Pattern] = {}

def _word_match(phrase: str, text: str) -> bool:
    """Case-insensitive whole-word presence of phrase in text."""
    phrase = (phrase or "").strip()
    if not phrase:
        return False
    pat = _WORD_BOUNDARY_CACHE.get(phrase)
    if pat is None:
        pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        _WORD_BOUNDARY_CACHE[phrase] = pat
    return bool(pat.search(text or ""))


def _substring_either_way(a: str, b: str) -> bool:
    """Bidirectional substring — either a in b or b in a, case-folded.
    Anchors the "close enough" rule for the STRENGTHS matcher so
    'Python' matches 'Python 3.11' AND 'Java' listed in a job req
    matches 'Java' on the student side."""
    if not a or not b:
        return False
    a_l, b_l = a.lower(), b.lower()
    return a_l in b_l or b_l in a_l


def _skill_match(
    student_skill: str,
    reqs_clean: list[str],
    job_desc: str,
) -> tuple[str, str] | None:
    """Return ('required_skills', matched_req) or ('description', '')
    or None. For short skills (<=2 chars — R, C, Go) fall back to
    word-boundary match against the description to avoid false hits
    on letters inside unrelated words. 3+ char skills use bidirectional
    substring matching as specified in Phase 2G iteration (a)."""
    s = (student_skill or "").strip()
    if not s:
        return None
    # Check structured required_skills first — more specific evidence.
    for req in reqs_clean:
        if _substring_either_way(s, req):
            return ("required_skills", req)
    # Then description free-text.
    if len(s) <= 2:
        if _word_match(s, job_desc):
            return ("description", "")
    else:
        if s.lower() in (job_desc or "").lower():
            return ("description", "")
    return None


# Gaps-filter patterns — drop contaminated skills_required entries.
# See Phase 2G iteration (b). The 80-char cutoff in v1 was too weak.
_LABEL_PREFIX_RE = re.compile(r"^[A-Z][A-Za-z][A-Za-z\s\/-]{0,25}:")
_TRACKING_CODE_RE = re.compile(r"#[Jj]-\d+-\w+")
_MARKETING_PHRASES: tuple[str, ...] = (
    "we offer", "we value", "we provide", "we respect", "we are",
    "work-life", "work/life", "pay range", "wages per", "salary",
    "benefits include", "paid time off", "paid holiday",
    "equal opportunity", "competitive", "premium",
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "dependent on role", "relocation assistance",
    "medical, dental",
)


def _is_garbage_requirement(req: str) -> bool:
    """True when the entry looks like scraped boilerplate (pay ranges,
    schedules, EEO language, tracking codes, benefit descriptions)
    rather than a real skill. Err on the side of dropping."""
    s = (req or "").strip()
    if not s:
        return True
    if len(s.split()) > 5:
        return True
    if _LABEL_PREFIX_RE.match(s):
        return True
    if _TRACKING_CODE_RE.search(s):
        return True
    low = s.lower()
    if any(p in low for p in _MARKETING_PHRASES):
        return True
    # Sentence-like punctuation — periods not at the very end suggest
    # "Foo. Bar." style multi-sentence strings.
    if "." in s.rstrip(".").rstrip():
        return True
    # Conjunction-joined clauses in longer strings usually aren't skills.
    if " and " in low and len(s.split()) > 3:
        return True
    return False


def compute_overlap(student: dict, job: dict) -> dict:
    """Match student skills to job text (description + required_skills).

    v2 (Phase 2G iteration):
      - STRENGTHS use bidirectional substring matching (with a safety
        rail for 1-2 char skills like "R" that would substring-match
        everything in a long description).
      - GAPS are filtered through _is_garbage_requirement to drop
        scraped boilerplate. See that helper for the full rule list.

    Returns a dict with three lists, each capped for prompt budget.
    """
    student_skills: list[dict[str, Any]] = student.get("skills") or []
    raw_reqs: list[str] = job.get("skills_required") or []
    job_desc: str = (job.get("job_description") or job.get("description")) or ""

    # Step 1: clean required_skills. Length cutoff + boilerplate rules.
    reqs_clean: list[str] = [
        r for r in raw_reqs
        if r and isinstance(r, str) and len(r) < 80
        and not _is_garbage_requirement(r)
    ]

    # ---- strengths ----
    seen: set[str] = set()
    strong: list[dict[str, str]] = []
    for sk in student_skills:
        name = (sk.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        hit = _skill_match(name, reqs_clean, job_desc)
        if hit is None:
            continue
        seen.add(key)
        source, req = hit
        if source == "required_skills":
            evidence = (
                f'Student skill; matches job requirement "{req}".'
                if req and req.lower() != name.lower()
                else "Student skill; listed in job required skills."
            )
        else:
            evidence = "Student skill; referenced in job description."
        strong.append({"area": name, "evidence": evidence})
        if len(strong) >= STRONG_CAP:
            break

    # ---- gaps ----
    # A cleaned required-skill is a gap iff the student's skills don't
    # match it via the same bidirectional substring rule.
    student_names = [(sk.get("name") or "").strip() for sk in student_skills]
    student_names = [n for n in student_names if n]
    gaps: list[dict[str, str]] = []
    for req in reqs_clean:
        if any(_substring_either_way(req, n) for n in student_names):
            continue
        gaps.append({
            "area": req,
            "note": "Listed in job requirements; not visible in student skills.",
        })
        if len(gaps) >= GAPS_CAP:
            break

    return {
        "strong_matches": strong,
        "partial_matches": [],
        "gaps": gaps,
    }


# ---------------------------------------------------------------------------
# Prompt formatting
# ---------------------------------------------------------------------------

def _format_student_for_prompt(student: dict) -> str:
    lines: list[str] = [f"Name: {student.get('full_name', '—')}"]

    edu_bits: list[str] = []
    if student.get("institution"):
        edu_bits.append(str(student["institution"]))
    if student.get("degree"):
        edu_bits.append(str(student["degree"]))
    if student.get("field_of_study"):
        edu_bits.append(str(student["field_of_study"]))
    if student.get("graduation_year"):
        edu_bits.append(f"expected {student['graduation_year']}")
    if edu_bits:
        lines.append("Education: " + ", ".join(edu_bits))

    work = student.get("work_experience") or []
    if work:
        work_summaries: list[str] = []
        for w in work[:5]:
            title = w.get("title") or "—"
            company = w.get("company") or "—"
            start = (w.get("start_date") or "")[:7]
            end_raw = w.get("end_date") or ""
            end = "present" if w.get("is_current") else (end_raw[:7] or "ongoing")
            resp = (w.get("responsibilities") or "").strip()
            entry = f"{title} @ {company} ({start} to {end})"
            if resp:
                resp_short = resp if len(resp) < 160 else resp[:160].rstrip() + "…"
                entry += f" — {resp_short}"
            work_summaries.append(entry)
        lines.append("Work experience:\n  " + "\n  ".join(work_summaries))

    skills = [s["name"] for s in (student.get("skills") or []) if s.get("name")]
    if skills:
        lines.append("Skills: " + ", ".join(skills))

    if student.get("career_objective"):
        lines.append("Career objective: " + str(student["career_objective"]).strip())

    return "\n".join(lines)


def _format_job_for_prompt(job: dict) -> str:
    lines: list[str] = [
        f"Title: {job.get('title') or '—'}",
        f"Company: {job.get('company') or '—'}",
    ]
    desc = ((job.get("job_description") or job.get("description")) or "").strip()
    if desc:
        if len(desc) > JOB_DESC_MAX_CHARS:
            desc = desc[:JOB_DESC_MAX_CHARS].rstrip() + "…"
        lines.append(f"Description: {desc}")

    reqs = job.get("skills_required") or []
    reqs_clean = [r for r in reqs if r and isinstance(r, str) and len(r) < 80]
    if reqs_clean:
        lines.append("Required skills: " + ", ".join(reqs_clean))
    return "\n".join(lines)


def _format_overlap_for_prompt(overlap: dict) -> dict:
    def fmt(items, empty: str) -> str:
        if not items:
            return empty
        return "\n".join(
            f"- {i.get('area', '—')}: {i.get('evidence') or i.get('note') or ''}"
            for i in items
        )
    return {
        "strong": fmt(overlap.get("strong_matches") or [], "(no direct overlap detected)"),
        "partial": fmt(overlap.get("partial_matches") or [], "(none identified)"),
        "gaps": fmt(overlap.get("gaps") or [],
                    "(required-skills list was empty or contaminated — infer gaps from description)"),
    }


# ---------------------------------------------------------------------------
# Prompts — lifted verbatim from Phase 2G spec, minor formatting.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an experienced technical recruiter at the WA Tech "
    "Workforce Coalition. You're writing brief notes to help Coalition "
    "staff (specifically Jessica) quickly understand whether a "
    "particular student is worth pursuing for a particular job opening.\n\n"
    "Your job: write a recruiter's note that helps the staff member "
    "make a fast, well-informed decision about whether to engage with "
    "this candidate for this role.\n\n"
    "Structure your output as JSON with two fields:\n\n"
    "{\n"
    '  "verdict_line": "<one-sentence bold takeaway>",\n'
    '  "narrative_text": "<two paragraphs separated by a blank line>"\n'
    "}\n\n"
    "Verdict line examples:\n"
    '- "Strong fit — pursue actively."\n'
    '- "Worth a closer look — solid technical foundation, some gaps."\n'
    '- "Stretch fit — pursue if you\'re casting wide for this role."\n'
    '- "Marginal — stronger candidates likely exist in this pool."\n\n'
    "First paragraph (3-4 sentences): The substantive case for the "
    "match. What does the student bring that fits THIS specific role? "
    "Reference concrete things from their profile and the job posting. "
    "Don't generalize — be specific about projects, experience, skills, "
    "education that connect to what the job is asking for.\n\n"
    "Second paragraph (3-5 sentences): Honest assessment of fit "
    "including material gaps, context for the calibration label, and a "
    "concrete sense of how to think about this candidate. If gaps are "
    "real, name them. If the cosine score is high, say what's driving "
    "the strength. If low, be direct about why this is a stretch.\n\n"
    "Total: roughly 7-12 sentences across two paragraphs, plus the "
    "verdict line. Long enough to be substantive, short enough that a "
    "busy recruiter actually reads it.\n\n"
    "Critical principles:\n"
    "- Be honest. If it's a weak match, say so. The recruiter trusts "
    "you to call it straight, not to be encouraging. A misleading "
    "positive note wastes their time and erodes their trust in this "
    "tool.\n"
    "- Be specific. Reference concrete things from the student's "
    "profile and the job posting. Not \"has relevant experience\" but "
    "\"Najib's project work on agentic systems at UW directly "
    "addresses what this role needs.\"\n"
    "- Be calibrated. Strong matches read as confident. Match-range "
    "reads as \"worth a look.\" Weak matches read as \"stretch — pursue "
    "if you're casting wide.\" Marginal reads as \"probably not.\"\n"
    "- Acknowledge gaps when they're real and material. Don't list "
    "every minor missing skill, but flag substantive concerns.\n"
    "- Write like a recruiter's note, not marketing copy. No "
    "\"passionate\" \"innovative\" \"dynamic\" \"leverage\" \"unlock\" or "
    "other empty descriptors. Direct, useful prose.\n"
    "- The structured overlap analysis (strengths, partial matches, "
    "gaps) is your evidence base. Lean on it. Use the cosine score "
    "for calibration only — let the structured overlap drive the "
    "substantive content.\n\n"
    "IMPORTANT: The verdict line tone is determined by the "
    "calibration label, not by your assessment of evidence "
    "sufficiency:\n"
    '- Strong calibration: verdict reads confident ("Strong fit", '
    '"Pursue actively"). If evidence is thin, explain in the '
    "narrative what's driving the high cosine and what to verify "
    "in conversation. Do not downgrade.\n"
    '- Match calibration: verdict reads as "worth a look" or '
    '"worth a closer look".\n'
    "- Weak calibration: verdict acknowledges the stretch.\n"
    "- Marginal calibration: verdict is direct about the poor fit.\n\n"
    "Calibration is the primary signal. Your job is to explain and "
    "contextualize it, not to second-guess it."
)


USER_PROMPT_TEMPLATE = (
    "Student profile:\n"
    "{student_block}\n\n"
    "Job posting:\n"
    "{job_block}\n\n"
    "Match analysis:\n"
    "Cosine similarity: {cosine:.4f}\n"
    "Calibration: {label}\n\n"
    "Strong matches:\n"
    "{strong}\n\n"
    "Partial matches:\n"
    "{partial}\n\n"
    "Gaps:\n"
    "{gaps}\n\n"
    "Write the recruiter's note as JSON."
)


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

class NarrativeError(Exception):
    """Raised when the narrative LLM call fails or returns unparseable
    content. Callers should catch this and surface an 'analysis
    unavailable' fallback rather than propagating a 500."""


def _call_chat_json(system: str, user: str) -> dict:
    if not AZURE_ENDPOINT or not AZURE_KEY:
        raise NarrativeError(
            "AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_KEY not set in .env"
        )
    url = (
        f"{AZURE_ENDPOINT}/openai/deployments/{CHAT_DEPLOYMENT}"
        f"/chat/completions?api-version={API_VERSION}"
    )
    body = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": LLM_TEMPERATURE,
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = requests.post(
            url,
            headers={"api-key": AZURE_KEY, "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
    except requests.RequestException as e:
        raise NarrativeError(f"network: {type(e).__name__}: {e}") from e
    if resp.status_code != 200:
        raise NarrativeError(f"http {resp.status_code}: {resp.text[:200]}")
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, ValueError, IndexError) as e:
        raise NarrativeError(f"malformed response envelope: {e}") from e
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise NarrativeError(f"non-JSON content: {e}; body={content[:200]!r}") from e
    return parsed


def generate_narrative(
    student: dict,
    job: dict,
    overlap: dict,
    cosine: float,
    label: str,
) -> dict:
    """Produce the recruiter's-note JSON for one student-job pair.

    Raises NarrativeError on any failure; caller is expected to
    catch and surface a fallback state to the UI.

    Returned dict shape:
      {
        "verdict_line": str,
        "narrative_text": str,  # two paragraphs separated by "\n\n"
      }
    """
    overlap_fmt = _format_overlap_for_prompt(overlap)
    user = USER_PROMPT_TEMPLATE.format(
        student_block=_format_student_for_prompt(student),
        job_block=_format_job_for_prompt(job),
        cosine=cosine,
        label=label,
        strong=overlap_fmt["strong"],
        partial=overlap_fmt["partial"],
        gaps=overlap_fmt["gaps"],
    )
    parsed = _call_chat_json(SYSTEM_PROMPT, user)
    verdict = parsed.get("verdict_line")
    narrative = parsed.get("narrative_text")
    if not isinstance(verdict, str) or not verdict.strip():
        raise NarrativeError("response missing non-empty verdict_line")
    if not isinstance(narrative, str) or not narrative.strip():
        raise NarrativeError("response missing non-empty narrative_text")
    return {
        "verdict_line": verdict.strip(),
        "narrative_text": narrative.strip(),
    }


# ---------------------------------------------------------------------------
# Input hash — used by the Phase-2 cache to invalidate when either
# side of the input changes.
# ---------------------------------------------------------------------------

def compute_input_hash(student: dict, job: dict) -> str:
    """Stable sha256 over the inputs the narrative actually reads.
    Cache invalidates whenever student skills/profile/objective or
    job description/required_skills change; cosine is re-derived so
    we don't hash it."""
    payload = {
        "student": {
            "full_name": student.get("full_name"),
            "institution": student.get("institution"),
            "degree": student.get("degree"),
            "field_of_study": student.get("field_of_study"),
            "graduation_year": student.get("graduation_year"),
            "career_objective": student.get("career_objective"),
            "skills": sorted(
                (s.get("name") or "") for s in (student.get("skills") or [])
            ),
            "work_experience": [
                {
                    "company": w.get("company"),
                    "title": w.get("title"),
                    "start_date": w.get("start_date"),
                    "end_date": w.get("end_date"),
                    "is_current": w.get("is_current"),
                }
                for w in (student.get("work_experience") or [])
            ],
        },
        "job": {
            "title": job.get("title"),
            "company": job.get("company"),
            # v_jobs_active exposes the column as `description`; jobs_enriched
            # as `job_description`. Hash whichever exists so the cache key is
            # stable regardless of which source the caller used.
            "description": (job.get("job_description") or job.get("description")),
            "skills_required": job.get("skills_required"),
        },
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

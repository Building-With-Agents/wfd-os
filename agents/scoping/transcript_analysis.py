"""Transcript analysis — extract answers to the 5 scoping questions."""

from agents.graph import config
from anthropic import Anthropic
from agents.scoping.models import ScopingRequest, ScopingAnalysis, ScopingAnswer


SCOPING_QUESTIONS = [
    "What problem are they actually trying to solve? Not what they asked for — what is the underlying need.",
    "What data do they have? Where it lives, what shape it's in, whether CFA can access it.",
    "What does success look like to them? How will they know the project worked. Metrics if mentioned.",
    "Who owns this internally? Champion name and title. Decision maker name and title. Are they the same person.",
    "What is their timeline and budget? Any stated expectations. Urgency signals. Budget signals.",
]


async def analyze_transcript(transcript: str, req: ScopingRequest) -> ScopingAnalysis:
    """Analyze a scoping call transcript against the 5 scoping questions."""
    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(SCOPING_QUESTIONS))

    prompt = f"""You are analyzing a scoping call transcript for CFA (Computing for All), an agentic AI engineering firm.

Company: {req.organization.name}
Contact: {req.contact.full_name}, {req.contact.title}
Industry: {req.organization.industry}

TRANSCRIPT:
{transcript}

Analyze this transcript and answer each of the following 5 scoping questions:

{questions_text}

For EACH question, provide:
- ANSWER: What was said (summarized, not verbatim)
- CONFIDENCE: High / Medium / Low / Not Discussed
- DIRECT QUOTE: One short supporting quote from the transcript if available

After answering all 5 questions, provide:

GAP ANALYSIS:
- List any questions where Confidence = Low or Not Discussed
- For each gap, suggest a specific follow-up question Jason should send to the prospect

SUMMARY:
- Problem (1 sentence)
- Champion: Name and title
- Decision Maker: Name and title (or "same as champion")
- Timeline signal: What was said
- Budget signal: What was said (or "Not discussed")

Format your response with clear section headers for each question (Q1, Q2, etc.) and for the Gap Analysis and Summary sections."""

    response = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    return _parse_analysis(response.content[0].text)


def _clean(text: str) -> str:
    """Strip markdown bold/italic markers and leading #."""
    return text.replace("**", "").replace("*", "").strip()


def _extract_value(line: str, key: str) -> str:
    """Extract a value after a key like 'ANSWER:', '**ANSWER:**', '## ANSWER:', etc."""
    import re
    cleaned_line = _clean(line)
    pattern = re.compile(re.escape(key) + r'\s*[:]\s*', re.IGNORECASE)
    match = pattern.search(cleaned_line)
    if match:
        val = cleaned_line[match.end():].strip('"').strip("*").strip()
        # Remove any leading colons left over from markdown
        return val.lstrip(": ").strip()
    return ""


def _parse_analysis(text: str) -> ScopingAnalysis:
    """Parse Claude's transcript analysis into structured ScopingAnalysis."""
    analysis = ScopingAnalysis()
    lines = text.split("\n")

    current_q = None
    current_answer = ""
    current_confidence = ""
    current_quote = ""
    in_gaps = False
    in_summary = False
    gaps = []
    followups = []

    for line in lines:
        stripped = line.strip()
        cleaned = _clean(stripped)
        upper = cleaned.upper()

        # Detect question sections (handles ## Q1, **Q1**, Q1:, etc.)
        if any(upper.startswith(f"Q{n}") or f"QUESTION {n}" in upper for n in [1]):
            _flush_question(analysis, current_q, current_answer, current_confidence, current_quote)
            current_q = 0
            current_answer, current_confidence, current_quote = "", "", ""
            continue
        elif any(upper.startswith(f"Q{n}") or f"QUESTION {n}" in upper for n in [2]):
            _flush_question(analysis, current_q, current_answer, current_confidence, current_quote)
            current_q = 1
            current_answer, current_confidence, current_quote = "", "", ""
            continue
        elif any(upper.startswith(f"Q{n}") or f"QUESTION {n}" in upper for n in [3]):
            _flush_question(analysis, current_q, current_answer, current_confidence, current_quote)
            current_q = 2
            current_answer, current_confidence, current_quote = "", "", ""
            continue
        elif any(upper.startswith(f"Q{n}") or f"QUESTION {n}" in upper for n in [4]):
            _flush_question(analysis, current_q, current_answer, current_confidence, current_quote)
            current_q = 3
            current_answer, current_confidence, current_quote = "", "", ""
            continue
        elif any(upper.startswith(f"Q{n}") or f"QUESTION {n}" in upper for n in [5]):
            _flush_question(analysis, current_q, current_answer, current_confidence, current_quote)
            current_q = 4
            current_answer, current_confidence, current_quote = "", "", ""
            continue
        elif "GAP" in upper and ("ANALYSIS" in upper or "FOLLOW" in upper):
            _flush_question(analysis, current_q, current_answer, current_confidence, current_quote)
            current_q = None
            in_gaps = True
            in_summary = False
            continue
        elif "SUMMARY" in upper and (upper.startswith("SUMMARY") or upper.startswith("#")):
            _flush_question(analysis, current_q, current_answer, current_confidence, current_quote)
            current_q = None
            in_gaps = False
            in_summary = True
            continue

        # Parse content within question sections
        if current_q is not None:
            if "ANSWER" in upper and ":" in cleaned:
                val = _extract_value(stripped, "ANSWER")
                if val:
                    current_answer = val
            elif "CONFIDENCE" in upper and ":" in cleaned:
                val = _extract_value(stripped, "CONFIDENCE")
                if val:
                    current_confidence = val
            elif "DIRECT QUOTE" in upper and ":" in cleaned:
                val = _extract_value(stripped, "DIRECT QUOTE")
                if val:
                    current_quote = val.strip('"').strip("*").strip("_")
            elif cleaned and current_answer and not any(k in upper for k in ["ANSWER", "CONFIDENCE", "DIRECT QUOTE", "---", "Q1", "Q2", "Q3", "Q4", "Q5"]):
                current_answer += " " + cleaned

        # Parse gaps section — handle both bullet lists and tables
        elif in_gaps:
            if stripped.startswith(("-", "|")) or stripped.startswith("*"):
                item = cleaned.lstrip("-|* ").strip()
                if not item or item.startswith("---") or item.upper().startswith("GAP"):
                    continue
                if "?" in item:
                    followups.append(item)
                elif len(item) > 5:
                    gaps.append(item)

        # Parse summary section
        elif in_summary:
            # Extract value from line — try the full key first, then shorter key
            if "PROBLEM" in upper and ":" in cleaned:
                val = _extract_value(stripped, "PROBLEM")
                if val:
                    analysis.problem_summary = val
            elif "CHAMPION" in upper and ":" in cleaned:
                val = _extract_value(stripped, "CHAMPION")
                if val:
                    analysis.champion = val
            elif "DECISION" in upper and ":" in cleaned:
                val = _extract_value(stripped, "DECISION MAKER") or _extract_value(stripped, "DECISION")
                if val:
                    analysis.decision_maker = val
            elif "TIMELINE" in upper and ":" in cleaned:
                val = _extract_value(stripped, "TIMELINE SIGNAL") or _extract_value(stripped, "TIMELINE")
                if val:
                    analysis.timeline_signal = val
            elif "BUDGET" in upper and ":" in cleaned:
                val = _extract_value(stripped, "BUDGET SIGNAL") or _extract_value(stripped, "BUDGET")
                if val:
                    analysis.budget_signal = val

    # Flush last question
    _flush_question(analysis, current_q, current_answer, current_confidence, current_quote)

    analysis.gaps = gaps
    analysis.followup_questions = followups
    return analysis


def _flush_question(
    analysis: ScopingAnalysis,
    q_index: int | None,
    answer: str,
    confidence: str,
    quote: str,
) -> None:
    if q_index is None:
        return
    if q_index < len(SCOPING_QUESTIONS):
        analysis.answers.append(ScopingAnswer(
            question=SCOPING_QUESTIONS[q_index],
            answer=answer.strip(),
            confidence=confidence.strip() or "Not Discussed",
            direct_quote=quote.strip(),
        ))

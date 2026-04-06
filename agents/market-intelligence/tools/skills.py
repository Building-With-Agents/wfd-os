"""
Skills demand tools — what skills employers are asking for.
"""
from dataverse.client import get_all, query


def get_top_skills(
    region: str = "Washington",
    experience_level: str = "0 years - 3 years",
    limit: int = 20,
    skill_category: str = None,
    growth_filter: str = None,
) -> list[dict]:
    """
    Returns skills ranked by posting count with supply/demand gap analysis.
    gap > 0 means employer demand exceeds worker supply (skills shortage).
    """
    records = get_all(
        "cfa_toplightcastskills",
        select=(
            "cfa_skill,cfa_postings,cfa_percentoftotalpostings,"
            "cfa_profiles,cfa_percentoftotalprofiles,"
            "cfa_skillgrowthrelativetomarket,cfa_projectedskillgrowth,"
            "cfa_skilltype,cfa_tabnameinsourceexcelsheet,"
            "cfa_paramregion,cfa_paramtimeframe,cfa_paramminexprequired"
        ),
    )

    results = []
    for r in records:
        # Apply filters
        if region and r.get("cfa_paramregion", "").lower() != region.lower():
            continue
        if experience_level and r.get("cfa_paramminexprequired", "") != experience_level:
            continue
        if skill_category and r.get("cfa_tabnameinsourceexcelsheet", "").lower() != skill_category.lower():
            continue
        if growth_filter and r.get("cfa_skillgrowthrelativetomarket", "").lower() != growth_filter.lower():
            continue

        postings_pct = r.get("cfa_percentoftotalpostings") or 0
        profiles_pct = r.get("cfa_percentoftotalprofiles") or 0

        results.append({
            "skill": r.get("cfa_skill"),
            "postings": r.get("cfa_postings") or 0,
            "percent_of_postings": postings_pct,
            "profiles": r.get("cfa_profiles") or 0,
            "percent_of_profiles": profiles_pct,
            "supply_demand_gap": round(postings_pct - profiles_pct, 1),
            "growth_trend": r.get("cfa_skillgrowthrelativetomarket"),
            "projected_growth_pct": r.get("cfa_projectedskillgrowth"),
            "skill_category": r.get("cfa_tabnameinsourceexcelsheet"),
            "region": r.get("cfa_paramregion"),
            "timeframe": r.get("cfa_paramtimeframe"),
        })

    # Sort by posting count descending
    results.sort(key=lambda x: x["postings"], reverse=True)
    return results[:limit]


def compare_skills_to_market(
    skills: list[str],
    region: str = "Washington",
) -> dict:
    """
    Compares a list of skills (e.g. a student's skills) against market demand.
    Returns matched skills, missing high-demand skills, and a market alignment score.
    """
    all_skills = get_top_skills(region=region, limit=150)
    skill_map = {s["skill"].lower(): s for s in all_skills}

    matched = []
    unmatched_input = []

    for skill in skills:
        key = skill.lower()
        if key in skill_map:
            matched.append(skill_map[key])
        else:
            # Fuzzy match — check if input skill is contained in any market skill
            found = next((v for k, v in skill_map.items() if key in k or k in key), None)
            if found:
                matched.append(found)
            else:
                unmatched_input.append(skill)

    # High demand skills the student is missing
    matched_names = {m["skill"].lower() for m in matched}
    missing_high_demand = [
        s for s in all_skills
        if s["skill"].lower() not in matched_names and s["supply_demand_gap"] > 5
    ][:10]

    # Alignment score: avg(percent_of_postings) for matched skills / 100
    if matched:
        avg_demand = sum(m["percent_of_postings"] for m in matched) / len(matched)
        alignment_score = min(round(avg_demand / 50, 2), 1.0)  # normalize: 50% demand = 1.0
    else:
        alignment_score = 0.0

    return {
        "input_skills": skills,
        "matched_skills": matched,
        "unmatched_skills": unmatched_input,
        "missing_high_demand_skills": missing_high_demand,
        "market_alignment_score": alignment_score,
        "matched_count": len(matched),
        "region": region,
    }

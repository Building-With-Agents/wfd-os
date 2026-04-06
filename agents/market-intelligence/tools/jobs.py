"""
Job search tools — search and filter Lightcast job postings.
"""
from dataverse.client import get_all


def search_jobs(
    query: str = None,
    skills: list[str] = None,
    company: str = None,
    location: str = None,
    onet_code: str = None,
    limit: int = 20,
) -> list[dict]:
    """
    Search Lightcast job postings by title, skills, company, location, or O*NET code.
    Returns structured job summaries.
    """
    records = get_all(
        "cfa_lightcastjobs",
        select=(
            "cfa_name,cfa_company,cfa_location,cfa_skills,"
            "cfa_onetcode,cfa_url,cfa_datestring,cfa_internalnumber,cfa_description"
        ),
    )

    results = []
    query_lower = query.lower() if query else None

    for r in records:
        title = r.get("cfa_name", "") or ""
        company_name = r.get("cfa_company", "") or ""
        loc = r.get("cfa_location", "") or ""
        skill_str = r.get("cfa_skills", "") or ""
        onet = r.get("cfa_onetcode", "") or ""
        desc = r.get("cfa_description", "") or ""

        # Apply filters
        if query_lower:
            if not (query_lower in title.lower() or query_lower in desc.lower()):
                continue
        if company and company.lower() not in company_name.lower():
            continue
        if location and location.lower() not in loc.lower():
            continue
        if onet_code and onet_code not in onet:
            continue
        if skills:
            skill_list_lower = skill_str.lower()
            if not all(s.lower() in skill_list_lower for s in skills):
                continue

        # Parse skills into a list
        parsed_skills = [s.strip() for s in skill_str.split(",") if s.strip()] if skill_str else []

        results.append({
            "title": title,
            "company": company_name,
            "location": loc,
            "skills": parsed_skills,
            "skills_count": len(parsed_skills),
            "onet_code": onet,
            "date": r.get("cfa_datestring"),
            "url": r.get("cfa_url"),
            "internal_id": r.get("cfa_internalnumber"),
            "description_preview": desc[:300] + "..." if len(desc) > 300 else desc,
        })

    return results[:limit]


def get_skills_from_jobs(job_titles: list[str] = None, limit: int = 50) -> dict:
    """
    Extracts the most common skills across job postings,
    optionally filtered to specific job titles.
    """
    records = get_all(
        "cfa_lightcastjobs",
        select="cfa_name,cfa_skills",
    )

    skill_counts = {}
    total_jobs = 0

    for r in records:
        title = r.get("cfa_name", "") or ""
        if job_titles and not any(t.lower() in title.lower() for t in job_titles):
            continue
        skill_str = r.get("cfa_skills", "") or ""
        skills = [s.strip() for s in skill_str.split(",") if s.strip()]
        total_jobs += 1
        for s in skills:
            skill_counts[s] = skill_counts.get(s, 0) + 1

    ranked = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return {
        "total_jobs_analyzed": total_jobs,
        "top_skills": [{"skill": s, "job_count": c, "pct_of_jobs": round(c/total_jobs*100, 1) if total_jobs else 0}
                       for s, c in ranked],
    }

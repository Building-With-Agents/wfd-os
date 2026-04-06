"""
Employer hiring tools — which companies are posting the most jobs.
"""
from dataverse.client import get_all


def get_top_employers(
    region: str = "Washington",
    limit: int = 20,
) -> list[dict]:
    """
    Returns employers ranked by job posting volume with hiring velocity metrics.
    """
    records = get_all(
        "cfa_topcompaniespostings",
        select=(
            "cfa_company,cfa_totalaug2023july2024,cfa_uniqueaug2023july2024,"
            "cfa_medianpostingduration,cfa_paramregion,cfa_paramtimeframe,"
            "cfa_paramminexprequired,cfa_parameducationlevel"
        ),
    )

    results = []
    for r in records:
        if region and r.get("cfa_paramregion", "").lower() != region.lower():
            continue

        # Parse median posting duration to int
        duration_str = r.get("cfa_medianpostingduration") or "n/a"
        try:
            duration_days = int(duration_str.replace(" days", "").strip())
        except (ValueError, AttributeError):
            duration_days = None

        results.append({
            "company": r.get("cfa_company"),
            "total_postings": r.get("cfa_totalaug2023july2024") or 0,
            "unique_postings": r.get("cfa_uniqueaug2023july2024") or 0,
            "median_posting_duration_days": duration_days,
            "region": r.get("cfa_paramregion"),
            "timeframe": r.get("cfa_paramtimeframe"),
            "experience_level": r.get("cfa_paramminexprequired"),
        })

    results.sort(key=lambda x: x["total_postings"], reverse=True)
    return results[:limit]

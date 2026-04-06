"""
Wage trend tools — advertised wages by occupation and region.
"""
from dataverse.client import get_all


def get_wage_trends(
    region: str = "Washington",
    experience_level: str = "0 years - 3 years",
) -> dict:
    """
    Returns monthly advertised wage trend series and summary statistics.
    """
    records = get_all(
        "cfa_advertisedwagetrends",
        select=(
            "cfa_advertisedwage,cfa_monthyear,cfa_jobpostings,"
            "cfa_paramregion,cfa_paramtimeframe,cfa_paramminexprequired,"
            "cfa_parameducationlevel,cfa_parammonthyear"
        ),
        orderby="cfa_monthyear asc",
    )

    filtered = []
    for r in records:
        if region and r.get("cfa_paramregion", "").lower() != region.lower():
            continue
        if experience_level and r.get("cfa_paramminexprequired", "") != experience_level:
            continue
        wage_str = r.get("cfa_advertisedwage") or "0"
        try:
            wage = round(float(wage_str), 2)
        except (ValueError, TypeError):
            wage = 0.0
        filtered.append({
            "month": r.get("cfa_monthyear"),
            "advertised_wage_hourly": wage,
            "job_postings": r.get("cfa_jobpostings") or 0,
            "timeframe": r.get("cfa_paramtimeframe"),
            "region": r.get("cfa_paramregion"),
        })

    if not filtered:
        return {"error": "No wage data found for the specified filters", "region": region}

    wages = [r["advertised_wage_hourly"] for r in filtered if r["advertised_wage_hourly"] > 0]

    # Trend direction
    trend = "stable"
    if len(wages) >= 2:
        if wages[-1] > wages[0] * 1.03:
            trend = "increasing"
        elif wages[-1] < wages[0] * 0.97:
            trend = "decreasing"

    return {
        "region": region,
        "experience_level": experience_level,
        "timeframe": filtered[0]["timeframe"] if filtered else None,
        "median_wage_hourly": round(sorted(wages)[len(wages)//2], 2) if wages else None,
        "min_wage_hourly": round(min(wages), 2) if wages else None,
        "max_wage_hourly": round(max(wages), 2) if wages else None,
        "annual_equivalent_median": round(sorted(wages)[len(wages)//2] * 2080, 0) if wages else None,
        "trend_direction": trend,
        "monthly_series": filtered,
        "data_points": len(filtered),
    }

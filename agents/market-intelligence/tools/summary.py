"""
Market summary tool — high-level snapshot combining all data sources.
"""
from tools.skills import get_top_skills
from tools.jobs import search_jobs
from tools.wages import get_wage_trends
from tools.employers import get_top_employers
from dataverse.client import query


def get_market_summary(region: str = "Washington") -> dict:
    """
    Returns a structured market overview combining all data sources.
    Designed as the opening statement for a Borderplex-style demo.
    """
    # Pull all data in parallel-ish
    top_skills = get_top_skills(region=region, limit=5)
    top_employers = get_top_employers(region=region, limit=5)
    wage_data = get_wage_trends(region=region)

    # Total job postings
    jobs_result = query("cfa_lightcastjobs", select="cfa_lightcastjobid", top=1, count=True)
    total_postings = jobs_result.get("@odata.count", 0)

    # Fastest growing skill
    all_skills = get_top_skills(region=region, limit=150)
    rapidly_growing = [s for s in all_skills if s.get("growth_trend") == "Rapidly Growing"]
    rapidly_growing.sort(key=lambda x: x.get("projected_growth_pct") or 0, reverse=True)
    fastest_growing = rapidly_growing[0] if rapidly_growing else None

    # Biggest supply/demand gap
    gap_skills = sorted(all_skills, key=lambda x: x.get("supply_demand_gap", 0), reverse=True)
    biggest_gap = gap_skills[0] if gap_skills else None

    return {
        "region": region,
        "total_lightcast_job_postings": total_postings,
        "top_5_skills_by_demand": [
            {"skill": s["skill"], "postings": s["postings"], "growth": s["growth_trend"]}
            for s in top_skills
        ],
        "top_5_employers_by_postings": [
            {"company": e["company"], "total_postings": e["total_postings"]}
            for e in top_employers
        ],
        "median_advertised_wage_hourly": wage_data.get("median_wage_hourly"),
        "median_advertised_wage_annual": wage_data.get("annual_equivalent_median"),
        "wage_trend": wage_data.get("trend_direction"),
        "fastest_growing_skill": {
            "skill": fastest_growing["skill"],
            "projected_growth_pct": fastest_growing["projected_growth_pct"],
        } if fastest_growing else None,
        "biggest_supply_demand_gap": {
            "skill": biggest_gap["skill"],
            "gap": biggest_gap["supply_demand_gap"],
            "demand_pct": biggest_gap["percent_of_postings"],
            "supply_pct": biggest_gap["percent_of_profiles"],
        } if biggest_gap else None,
        "data_source": "Lightcast Q3 2024",
        "data_as_of": "Aug 2023 – Jul 2024",
    }

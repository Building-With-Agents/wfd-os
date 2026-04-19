"""
USAJobs API client — federal and government job listings.
https://developer.usajobs.gov/api-reference/

No API key needed for basic search (key increases rate limits).
"""
import requests
import os
from datetime import datetime


BASE_URL = "https://data.usajobs.gov/api/Search"


def fetch_jobs(keyword=None, location_name="El Paso, Texas",
               page=1, results_per_page=50):
    """
    Fetch job listings from USAJobs API.

    Args:
        keyword: Job title or keyword search
        location_name: City, State format
        page: Page number (1-based)
        results_per_page: Max results per page (max 500)

    Returns:
        List of normalized job dicts ready for job_listings table.
    """
    headers = {
        "User-Agent": "ritu@computingforall.org",
        "Host": "data.usajobs.gov",
    }

    # Add API key if available
    api_key = os.getenv("USAJOBS_API_KEY")
    if api_key:
        headers["Authorization-Key"] = api_key

    params = {
        "LocationName": location_name,
        "ResultsPerPage": results_per_page,
        "Page": page,
    }
    if keyword:
        params["Keyword"] = keyword

    response = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    search_result = data.get("SearchResult", {})
    items = search_result.get("SearchResultItems", [])
    total = int(search_result.get("SearchResultCount", 0))

    jobs = []
    for item in items:
        match = item.get("MatchedObjectDescriptor", {})
        position = match.get("PositionLocation", [{}])
        location = position[0] if position else {}

        # Parse salary
        salary_min = None
        salary_max = None
        salary_period = None
        remuneration = match.get("PositionRemuneration", [{}])
        if remuneration:
            rem = remuneration[0]
            try:
                salary_min = float(rem.get("MinimumRange", 0))
                salary_max = float(rem.get("MaximumRange", 0))
                rate = rem.get("RateIntervalCode", "")
                salary_period = {
                    "PA": "annual",
                    "PH": "hourly",
                    "PM": "monthly",
                }.get(rate, rate.lower())
            except (ValueError, TypeError):
                pass

        # Parse dates
        posted_date = None
        expires_date = None
        pub_date = match.get("PublicationStartDate")
        close_date = match.get("ApplicationCloseDate")
        if pub_date:
            try:
                posted_date = datetime.fromisoformat(pub_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except Exception:
                pass
        if close_date:
            try:
                expires_date = datetime.fromisoformat(close_date.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            except Exception:
                pass

        # Employment type
        schedule = match.get("PositionSchedule", [{}])
        emp_type = "full_time"
        if schedule:
            sched_name = schedule[0].get("Name", "").lower()
            if "part" in sched_name:
                emp_type = "part_time"
            elif "intermittent" in sched_name:
                emp_type = "contract"

        # Remote
        telework = match.get("TeleworkEligible", "")
        remote_option = None
        if telework:
            if "yes" in str(telework).lower():
                remote_option = "hybrid"

        job = {
            "source": "usajobs",
            "source_id": match.get("PositionID"),
            "title": match.get("PositionTitle", "Untitled"),
            "description": match.get("QualificationSummary", ""),
            "company": match.get("OrganizationName", "U.S. Government"),
            "city": location.get("CityName"),
            "state": location.get("CountrySubDivisionCode"),
            "zipcode": None,
            "remote_option": remote_option,
            "employment_type": emp_type,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_period": salary_period,
            "soc_code": None,
            "posted_date": posted_date,
            "expires_date": expires_date,
            "url": match.get("PositionURI"),
            "legacy_data": {
                "department": match.get("DepartmentName"),
                "job_category": match.get("JobCategory", []),
                "job_grade": match.get("JobGrade", []),
                "who_may_apply": match.get("UserArea", {}).get("Details", {}).get("WhoMayApply", {}).get("Name"),
            },
        }
        jobs.append(job)

    print(f"  USAJobs: fetched {len(jobs)} of {total} total for '{location_name}'")
    return jobs, total

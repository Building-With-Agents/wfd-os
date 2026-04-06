"""
JSearch API client (via RapidAPI) -- aggregates Indeed, LinkedIn,
Glassdoor, ZipRecruiter.
https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch

Requires RAPIDAPI_KEY in .env. Free tier: 50 requests.
"""
import requests
import os
from datetime import datetime


BASE_URL = "https://jsearch.p.rapidapi.com/search"


def fetch_jobs(query="tech jobs", location="El Paso, TX",
               page=1, num_pages=1, date_posted="month"):
    """
    Fetch job listings from JSearch API.

    Args:
        query: Search query (job title or keywords)
        location: City, State format
        page: Starting page number (1-based)
        num_pages: Number of pages to fetch
        date_posted: 'today', '3days', 'week', 'month', 'all'

    Returns:
        List of normalized job dicts ready for job_listings table.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("  ERROR: RAPIDAPI_KEY not set in .env")
        return [], 0

    headers = {
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        "X-RapidAPI-Key": api_key,
    }

    full_query = f"{query} in {location}" if location else query

    all_jobs = []
    total = 0

    for p in range(page, page + num_pages):
        params = {
            "query": full_query,
            "page": str(p),
            "num_pages": "1",
            "date_posted": date_posted,
        }

        response = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        raw_jobs = data.get("data", [])
        total = data.get("parameters", {}).get("num_pages", 0) * 10  # estimate

        for item in raw_jobs:
            # Parse salary
            salary_min = item.get("job_min_salary")
            salary_max = item.get("job_max_salary")
            salary_period = item.get("job_salary_period")
            if salary_period:
                salary_period = salary_period.lower()

            # Remote
            remote = item.get("job_is_remote", False)
            remote_option = "fully_remote" if remote else None

            # Employment type
            emp_type = item.get("job_employment_type", "")
            emp_map = {
                "FULLTIME": "full_time",
                "PARTTIME": "part_time",
                "CONTRACTOR": "contract",
                "INTERN": "internship",
            }
            employment_type = emp_map.get(emp_type, emp_type.lower() if emp_type else "full_time")

            # Posted date
            posted_date = None
            posted_ts = item.get("job_posted_at_datetime_utc")
            if posted_ts:
                try:
                    posted_date = datetime.fromisoformat(posted_ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
                except:
                    pass

            # SOC/ONET code
            onet = item.get("job_onet_soc")

            job = {
                "source": "jsearch",
                "source_id": item.get("job_id"),
                "title": item.get("job_title", "Untitled"),
                "description": item.get("job_description", ""),
                "company": item.get("employer_name", ""),
                "city": item.get("job_city"),
                "state": item.get("job_state"),
                "zipcode": None,
                "remote_option": remote_option,
                "employment_type": employment_type,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_period": salary_period,
                "soc_code": onet,
                "posted_date": posted_date,
                "expires_date": None,
                "url": item.get("job_apply_link"),
                "legacy_data": {
                    "employer_logo": item.get("employer_logo"),
                    "employer_website": item.get("employer_website"),
                    "job_publisher": item.get("job_publisher"),
                    "job_highlights": item.get("job_highlights"),
                    "job_required_experience": item.get("job_required_experience"),
                    "job_required_education": item.get("job_required_education"),
                },
            }
            all_jobs.append(job)

        print(f"  JSearch: fetched {len(raw_jobs)} jobs from page {p}")

    print(f"  JSearch total: {len(all_jobs)} jobs for '{full_query}'")
    return all_jobs, total

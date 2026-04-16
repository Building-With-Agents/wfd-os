"""
Arbeitnow API client -- tech job listings.
https://www.arbeitnow.com/api/job-board-api

No authentication needed. Returns 100 jobs per page.
NOTE: Primarily European tech jobs. US coverage is limited.
We filter for US-based jobs in post-processing.
"""
import requests


BASE_URL = "https://www.arbeitnow.com/api/job-board-api"


def _parse_date(val):
    """Convert various date formats to YYYY-MM-DD string."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        from datetime import datetime
        try:
            return datetime.fromtimestamp(val).strftime("%Y-%m-%d")
        except Exception:
            return None
    if isinstance(val, str):
        return val[:10] if len(val) >= 10 else val
    return None


def fetch_jobs(page=1, us_only=True):
    """
    Fetch job listings from Arbeitnow API.

    Args:
        page: Page number (1-based)
        us_only: If True, filter for US-based jobs only

    Returns:
        List of normalized job dicts ready for job_listings table.
    """
    params = {"page": page}

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    raw_jobs = data.get("data", [])
    meta = data.get("meta", {})
    if isinstance(meta, dict):
        info = meta.get("info", {})
        total = info.get("total", len(raw_jobs)) if isinstance(info, dict) else len(raw_jobs)
    else:
        total = len(raw_jobs)

    jobs = []
    skipped_non_us = 0

    for item in raw_jobs:
        location = item.get("location", "")

        # Filter for US jobs if requested
        if us_only:
            location_lower = location.lower()
            us_indicators = [
                "united states", "usa", ", us", "remote (us",
                "texas", "california", "new york", "washington",
                "el paso", "san francisco", "seattle", "austin",
                "new jersey", "virginia", "maryland", "colorado",
                "florida", "georgia", "illinois", "massachusetts",
            ]
            is_us = any(ind in location_lower for ind in us_indicators)
            # Also include fully remote jobs
            is_remote = item.get("remote", False)
            if not is_us and not is_remote:
                skipped_non_us += 1
                continue

        # Parse location into city/state
        city = None
        state = None
        if location:
            parts = [p.strip() for p in location.split(",")]
            if len(parts) >= 2:
                city = parts[0]
                state = parts[-1] if len(parts[-1]) <= 3 else parts[-1]
            else:
                city = location

        # Remote option
        remote_option = None
        if item.get("remote"):
            remote_option = "fully_remote"

        # Tags as skills hint (stored in legacy_data)
        tags = item.get("tags", [])

        job = {
            "source": "arbeitnow",
            "source_id": str(item.get("slug", "")),
            "title": item.get("title", "Untitled"),
            "description": item.get("description", ""),
            "company": item.get("company_name", ""),
            "city": city,
            "state": state,
            "zipcode": None,
            "remote_option": remote_option,
            "employment_type": item.get("job_types", ["full_time"])[0] if item.get("job_types") else "full_time",
            "salary_min": None,
            "salary_max": None,
            "salary_period": None,
            "soc_code": None,
            "posted_date": _parse_date(item.get("created_at")),
            "expires_date": None,
            "url": item.get("url"),
            "legacy_data": {
                "tags": tags,
                "visa_sponsorship": item.get("visa_sponsorship"),
                "original_location": location,
            },
        }
        jobs.append(job)

    print(f"  Arbeitnow: fetched {len(jobs)} US/remote jobs "
          f"(skipped {skipped_non_us} non-US) from page {page}, "
          f"{total} total in API")
    return jobs, total

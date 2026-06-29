# scrapers/yej_scraper.py
"""
Scrapes YourEnglishJob.com (yourenglishjob.com) via their public REST API.
This site lists English-only jobs in Germany where German is NOT required —
a unique signal not available on LinkedIn/Indeed.

Key endpoints (no auth required):
  POST /api/search  — paginated search with keyword + location filters
  GET  /api/jobs/latest — newest 50 jobs
"""
import hashlib
import logging
import requests
from config import SEARCH_TERMS

logger = logging.getLogger(__name__)

BASE_URL = "https://yourenglishjob.com/api"

# YEJ is Germany-only — always Germany country display
COUNTRY_DISPLAY = "Germany"
COUNTRY_CODE = "germany"

# Only use the most relevant terms — YEJ is a smaller board
YEJ_TERMS = [
    "Cloud Security",
    "DevSecOps",
    "Cloud Engineer",
    "DevOps",
    "Platform Engineer",
    "Kubernetes",
]


def _make_id(job_id: str) -> str:
    return hashlib.md5(f"yej:{job_id}".encode()).hexdigest()


def _normalize(job: dict) -> dict:
    """Convert a YEJ API job object to our internal job dict schema."""
    job_id = str(job.get("id", ""))
    company = job.get("company_name") or job.get("company", {})
    if isinstance(company, dict):
        company = company.get("name", "Unknown Company")

    return {
        "id":           _make_id(job_id),
        "title":        str(job.get("title", "Unknown Title")),
        "company":      str(company),
        "location":     str(job.get("location", "Germany")),
        "country_code": COUNTRY_CODE,
        "country":      COUNTRY_DISPLAY,
        "url":          f"https://yourenglishjob.com/jobs/{job.get('slug', job_id)}",
        "source":       "yourenglishjob",
        "description":  str(job.get("description", ""))[:4000],
        "date_posted":  str(job.get("created_at", "")[:10] if job.get("created_at") else ""),
        "is_remote":    bool(job.get("remote") or "remote" in str(job.get("location", "")).lower()),
    }


def _search(keyword: str, page: int = 1) -> list[dict]:
    """Run one search query via POST /api/search."""
    try:
        resp = requests.post(
            f"{BASE_URL}/search",
            json={
                "query": keyword,
                "page": page,
                "page_size": 50,
            },
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("jobs", data.get("results", []))
    except Exception as e:
        logger.warning(f"YEJ search error for '{keyword}': {e}")
        return []


def _latest() -> list[dict]:
    """Fetch the 50 most recent jobs regardless of keyword."""
    try:
        resp = requests.get(
            f"{BASE_URL}/jobs/latest",
            params={"limit": 50},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("jobs", [])
    except Exception as e:
        logger.warning(f"YEJ latest jobs error: {e}")
        return []


def fetch_jobs() -> list[dict]:
    """
    Fetch jobs from YourEnglishJob.com using:
    1. Keyword searches for relevant terms
    2. Latest jobs sweep to catch anything missed

    Returns deduplicated list of normalized job dicts.
    """
    seen_ids: set[str] = set()
    all_jobs: list[dict] = []

    # Keyword searches
    for term in YEJ_TERMS:
        logger.info(f"YEJ search: '{term}'")
        results = _search(term)
        for job in results:
            job_id = str(job.get("id", ""))
            if job_id and job_id not in seen_ids:
                seen_ids.add(job_id)
                all_jobs.append(_normalize(job))

    # Latest sweep — catches recent postings not in keyword results
    logger.info("YEJ latest sweep")
    for job in _latest():
        job_id = str(job.get("id", ""))
        if job_id and job_id not in seen_ids:
            seen_ids.add(job_id)
            all_jobs.append(_normalize(job))

    logger.info(f"YEJ fetched {len(all_jobs)} unique jobs")
    return all_jobs

# scrapers/jobspy_scraper.py
"""
Scrapes LinkedIn, Indeed, and Glassdoor using the JobSpy library.
Returns a list of normalized job dicts ready for scoring.
"""
import hashlib
import logging
from jobspy import scrape_jobs
from config import SEARCH_TERMS, SEARCH_LOCATIONS

logger = logging.getLogger(__name__)


def _make_id(site: str, url: str) -> str:
    """Stable unique ID from site + URL so dedup works across runs."""
    return hashlib.md5(f"{site}:{url}".encode()).hexdigest()


def _normalize(row: dict, country_code: str, country_display: str) -> dict:
    """Convert a JobSpy DataFrame row into our internal job dict schema."""
    url = str(row.get("job_url", ""))
    return {
        "id":           _make_id(str(row.get("site", "")), url),
        "title":        str(row.get("title", "Unknown Title")),
        "company":      str(row.get("company", "Unknown Company")),
        "location":     str(row.get("location", "")),
        "country_code": country_code,
        "country":      country_display,
        "url":          url,
        "source":       str(row.get("site", "unknown")),
        "description":  str(row.get("description", ""))[:4000],
        "date_posted":  str(row.get("date_posted", "")),
        "is_remote":    bool(row.get("is_remote", False)),
    }


def fetch_jobs(max_per_query: int = 25) -> list[dict]:
    """
    Run JobSpy for every combination of search term x location.
    Returns deduplicated list of normalized job dicts.
    """
    seen_urls: set[str] = set()
    all_jobs: list[dict] = []

    for term in SEARCH_TERMS:
        for country_code, country_display, cities in SEARCH_LOCATIONS:
            for city in cities[:2]:  # top 2 cities per country to limit API load
                try:
                    logger.info(f"Scraping: '{term}' in {city} ({country_code})")
                    df = scrape_jobs(
                        site_name=["linkedin", "indeed", "glassdoor"],
                        search_term=term,
                        location=city,
                        results_wanted=max_per_query,
                        hours_old=72,  # last 3 days — we run every 2 days
                        country_indeed=country_code,
                        linkedin_fetch_description=True,
                    )
                    if df is None or df.empty:
                        continue

                    for _, row in df.iterrows():
                        url = str(row.get("job_url", ""))
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_jobs.append(
                                _normalize(row.to_dict(), country_code, country_display)
                            )

                except Exception as e:
                    logger.warning(f"JobSpy error for '{term}' in {city}: {e}")
                    continue

    logger.info(f"JobSpy fetched {len(all_jobs)} unique jobs total")
    return all_jobs

# scrapers/jobspy_scraper.py
"""
Scrapes LinkedIn and Indeed using the JobSpy library.
Parallelises at the (term × city) level using ThreadPoolExecutor —
each query runs in its own thread, all cities fire simultaneously.

LinkedIn rate-limits per IP but doesn't block parallel threads from the same
machine as long as we stay under ~10 concurrent connections.
"""
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from jobspy import scrape_jobs
from config import SEARCH_TERMS, SEARCH_LOCATIONS

logger = logging.getLogger(__name__)

# Max concurrent scrape threads — stay low enough LinkedIn doesn't throttle
MAX_SCRAPE_WORKERS = 6

TIER_1 = {"germany", "netherlands", "ireland"}
# Tier 1: 3 cities × all terms
# Tier 2/3: 1 city × all terms


def _make_id(site: str, url: str) -> str:
    return hashlib.md5(f"{site}:{url}".encode()).hexdigest()


def _normalize(row: dict, country_code: str, country_display: str) -> dict:
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


def _scrape_one(term: str, city: str, country_code: str,
                country_display: str, max_per_query: int) -> list[dict]:
    """Run a single (term × city) query. Returns list of normalized jobs."""
    try:
        df = scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term=term,
            location=city,
            results_wanted=max_per_query,
            hours_old=48,
            country_indeed=country_code,
            linkedin_fetch_description=False,
        )
        if df is None or df.empty:
            return []
        results = []
        for _, row in df.iterrows():
            url = str(row.get("job_url", ""))
            if url:
                results.append(_normalize(row.to_dict(), country_code, country_display))
        return results
    except Exception as e:
        logger.warning(f"JobSpy error for '{term}' in {city}: {e}")
        return []


def fetch_jobs(max_per_query: int = 20) -> list[dict]:
    """
    Build the full list of (term, city, country) queries then fire them all
    in parallel via a thread pool. Deduplicates by URL across all results.
    Returns deduplicated list of normalized job dicts.
    """
    # Build query list
    queries = []
    for country_code, country_display, cities in SEARCH_LOCATIONS:
        city_limit = 3 if country_code in TIER_1 else 1
        for term in SEARCH_TERMS:
            for city in cities[:city_limit]:
                queries.append((term, city, country_code, country_display))

    total = len(queries)
    logger.info(f"Scraping {total} queries across {len(SEARCH_LOCATIONS)} countries "
                f"({MAX_SCRAPE_WORKERS} parallel workers)")

    # Execute in parallel
    seen_urls: set[str] = set()
    all_jobs: list[dict] = []
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_SCRAPE_WORKERS) as executor:
        future_to_query = {
            executor.submit(_scrape_one, term, city, cc, cd, max_per_query): (term, city)
            for term, city, cc, cd in queries
        }
        for future in as_completed(future_to_query):
            term, city = future_to_query[future]
            completed += 1
            try:
                results = future.result()
                new = 0
                for job in results:
                    if job["url"] and job["url"] not in seen_urls:
                        seen_urls.add(job["url"])
                        all_jobs.append(job)
                        new += 1
                if new:
                    logger.info(f"[{completed}/{total}] '{term}' in {city} → {new} new jobs")
                else:
                    logger.debug(f"[{completed}/{total}] '{term}' in {city} → 0 new")
            except Exception as e:
                logger.warning(f"[{completed}/{total}] '{term}' in {city} failed: {e}")

    logger.info(f"JobSpy fetched {len(all_jobs)} unique jobs total")
    return all_jobs

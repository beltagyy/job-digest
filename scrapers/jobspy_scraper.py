# scrapers/jobspy_scraper.py
"""
Scrapes LinkedIn and Indeed using the JobSpy library.
Two strategies run in parallel:
  1. Term-based:    standard job title searches across all locations
  2. Company-based: "Cloud Security Engineer at <company>" for known relocation-friendly companies

Tiers:
  Tier 1 (DE, NL, IE, CH, BE): 2 cities × all terms
  Tier 2 (CZ, PL, AT, ES, EE): 1 city × all terms
  Tier 3 (HU, HR, BG):         1 city × top 5 terms only
"""
import hashlib
import logging
from jobspy import scrape_jobs
from config import SEARCH_TERMS, SEARCH_LOCATIONS, COMPANY_TARGETS

logger = logging.getLogger(__name__)

TIER_1 = {"germany", "netherlands", "ireland", "switzerland", "belgium"}
TIER_3 = {"hungary", "croatia", "bulgaria"}

# Top terms used for company-targeted searches (keep it focused)
COMPANY_SEARCH_TERMS = [
    "Cloud Security Engineer",
    "DevSecOps Engineer",
    "Cloud Engineer",
    "DevOps Engineer",
    "Platform Engineer",
    "Site Reliability Engineer",
]


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


def _scrape_one(term: str, city: str, country_code: str, country_display: str,
                seen_urls: set, all_jobs: list, max_per_query: int):
    """Run one JobSpy query and append new results to all_jobs."""
    try:
        df = scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term=term,
            location=city,
            results_wanted=max_per_query,
            hours_old=72,
            country_indeed=country_code,
            linkedin_fetch_description=True,
        )
        if df is None or df.empty:
            return
        for _, row in df.iterrows():
            url = str(row.get("job_url", ""))
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_jobs.append(_normalize(row.to_dict(), country_code, country_display))
    except Exception as e:
        logger.warning(f"JobSpy error for '{term}' in {city}: {e}")


def fetch_jobs(max_per_query: int = 20) -> list[dict]:
    """
    Run term-based + company-targeted searches across all configured locations.
    Returns deduplicated list of normalized job dicts.
    """
    seen_urls: set[str] = set()
    all_jobs: list[dict] = []

    # ── Strategy 1: Standard term × location searches ────────────────────────
    logger.info("=== Strategy 1: Term-based search ===")
    for country_code, country_display, cities in SEARCH_LOCATIONS:
        if country_code in TIER_1:
            city_limit = 2
            terms = SEARCH_TERMS
        elif country_code in TIER_3:
            city_limit = 1
            terms = SEARCH_TERMS[:5]
        else:
            city_limit = 1
            terms = SEARCH_TERMS

        for term in terms:
            for city in cities[:city_limit]:
                logger.info(f"  '{term}' in {city}")
                _scrape_one(term, city, country_code, country_display,
                            seen_urls, all_jobs, max_per_query)

    logger.info(f"After term search: {len(all_jobs)} unique jobs")

    # ── Strategy 2: Company-targeted searches (Tier 1 cities only) ───────────
    logger.info("=== Strategy 2: Company-targeted search ===")
    tier1_locations = [(cc, cd, cities) for cc, cd, cities in SEARCH_LOCATIONS
                       if cc in TIER_1]

    for company in COMPANY_TARGETS:
        for role in COMPANY_SEARCH_TERMS[:3]:   # top 3 roles per company
            query = f"{role} {company}"
            # Search in top Tier 1 city only to keep query count manageable
            for country_code, country_display, cities in tier1_locations:
                city = cities[0]
                logger.info(f"  '{query}' in {city}")
                _scrape_one(query, city, country_code, country_display,
                            seen_urls, all_jobs, max_per_query)

    logger.info(f"JobSpy fetched {len(all_jobs)} unique jobs total")
    return all_jobs

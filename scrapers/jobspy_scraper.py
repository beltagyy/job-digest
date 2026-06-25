# scrapers/jobspy_scraper.py
"""
Scrapes LinkedIn and Indeed using the JobSpy library.
Returns a list of normalized job dicts ready for scoring.

Strategy:
- Tier 1 countries (DE, NL, IE, CH, BE): 2 cities × all terms
- Tier 2 countries (CZ, PL, AT, ES, EE): 1 city × all terms
- Tier 3 countries (HU, HR, BG): 1 city × top 3 terms only
"""
import hashlib
import logging
from jobspy import scrape_jobs
from config import SEARCH_TERMS, SEARCH_LOCATIONS

logger = logging.getLogger(__name__)

# Tier 1 — search 2 cities, all terms (highest job density)
TIER_1 = {"germany", "netherlands", "ireland", "switzerland", "belgium"}

# Tier 3 — search 1 city, top 3 terms only (emerging markets)
TIER_3 = {"hungary", "croatia", "bulgaria"}


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


def fetch_jobs(max_per_query: int = 20) -> list[dict]:
    """
    Scrape jobs across all configured locations using tiered strategy.
    Returns deduplicated list of normalized job dicts.
    """
    seen_urls: set[str] = set()
    all_jobs: list[dict] = []

    for country_code, country_display, cities in SEARCH_LOCATIONS:

        # Determine tier settings
        if country_code in TIER_1:
            city_limit = 2
            terms = SEARCH_TERMS
        elif country_code in TIER_3:
            city_limit = 1
            terms = SEARCH_TERMS[:3]   # top 3 terms only for Tier 3
        else:
            city_limit = 1
            terms = SEARCH_TERMS

        for term in terms:
            for city in cities[:city_limit]:
                try:
                    logger.info(f"Scraping: '{term}' in {city} ({country_code})")
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

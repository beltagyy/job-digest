# scrapers/xing_scraper.py
"""
Scrapes Xing job search using Playwright (headless Chromium).
Xing is dominant in Germany/Austria/Czech — worth the extra effort.
"""
import hashlib
import logging
import time
import random
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from config import SEARCH_TERMS, SEARCH_LOCATIONS

logger = logging.getLogger(__name__)

XING_SEARCH_URL = (
    "https://www.xing.com/jobs/search"
    "?keywords={keywords}&location={location}&radius=50&sort=date"
)

# Countries where Xing has meaningful coverage
XING_COUNTRIES = {"DE", "AT", "CZ", "HU"}


def _make_id(url: str) -> str:
    return hashlib.md5(f"xing:{url}".encode()).hexdigest()


def _scrape_search_page(page, term: str, city: str) -> list[dict]:
    """Scrape one Xing search results page. Returns list of partial job dicts."""
    url = XING_SEARCH_URL.format(
        keywords=term.replace(" ", "+"),
        location=city.replace(" ", "+"),
    )
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(random.uniform(2, 4))

        # Accept cookies if banner appears
        try:
            page.click("[data-testid='cookie-consent-accept-all']", timeout=5000)
        except PlaywrightTimeout:
            pass

        page.wait_for_selector("[data-testid='job-listing-item']", timeout=15000)
        cards = page.query_selector_all("[data-testid='job-listing-item']")

        jobs = []
        for card in cards[:15]:
            try:
                title_el   = card.query_selector("[data-testid='job-title']")
                company_el = card.query_selector("[data-testid='company-name']")
                loc_el     = card.query_selector("[data-testid='job-location']")
                link_el    = card.query_selector("a[href*='/jobs/']")

                title   = title_el.inner_text().strip()   if title_el   else ""
                company = company_el.inner_text().strip() if company_el else ""
                loc     = loc_el.inner_text().strip()     if loc_el     else city
                href    = link_el.get_attribute("href")   if link_el    else ""
                if not href.startswith("http"):
                    href = "https://www.xing.com" + href

                if title and href:
                    jobs.append({"title": title, "company": company, "location": loc, "url": href})
            except Exception:
                continue

        return jobs

    except PlaywrightTimeout:
        logger.warning(f"Xing timeout for '{term}' in {city}")
        return []
    except Exception as e:
        logger.warning(f"Xing error for '{term}' in {city}: {e}")
        return []


def _fetch_description(page, url: str) -> str:
    """Visit a Xing job detail page and extract the description text."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(random.uniform(1, 2))
        desc_el = page.query_selector("[data-testid='job-description']")
        if desc_el:
            return desc_el.inner_text().strip()[:4000]
    except Exception:
        pass
    return ""


def fetch_jobs() -> list[dict]:
    """Run Xing scraping for all XING_COUNTRIES x top search terms."""
    seen_urls: set[str] = set()
    all_jobs: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )
        page = context.new_page()

        for term in SEARCH_TERMS[:3]:  # top 3 terms to limit Xing requests
            for country_code, country_display, cities in SEARCH_LOCATIONS:
                if country_code not in XING_COUNTRIES:
                    continue
                city = cities[0]
                logger.info(f"Xing scraping: '{term}' in {city}")

                raw = _scrape_search_page(page, term, city)
                for r in raw:
                    url = r["url"]
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    desc = _fetch_description(page, url)
                    time.sleep(random.uniform(1, 3))
                    all_jobs.append({
                        "id":           _make_id(url),
                        "title":        r["title"],
                        "company":      r["company"],
                        "location":     r["location"],
                        "country_code": country_code,
                        "country":      country_display,
                        "url":          url,
                        "source":       "xing",
                        "description":  desc,
                        "date_posted":  "",
                        "is_remote":    False,
                    })

        browser.close()

    logger.info(f"Xing fetched {len(all_jobs)} jobs")
    return all_jobs

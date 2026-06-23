#!/usr/bin/env python3
# run.py
"""
Job Digest Bot - main entry point.
Run this script manually or via cron to scrape, score, and email job matches.

Usage:
    python run.py                   # Full run
    python run.py --dry-run         # Scrape + score but don't send email
    python run.py --no-xing         # Skip Xing (faster, for testing)
"""
import os
import sys
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("digest_run.log"),
    ],
)
logger = logging.getLogger("run")

from scrapers.jobspy_scraper import fetch_jobs as fetch_jobspy
from scrapers.xing_scraper import fetch_jobs as fetch_xing
from matching.scorer import enrich_jobs
from storage.db import JobDatabase
from email_digest.renderer import render_digest
from email_digest.sender import send_digest


def main():
    parser = argparse.ArgumentParser(description="Job Digest Bot")
    parser.add_argument("--dry-run", action="store_true", help="Skip sending email")
    parser.add_argument("--no-xing", action="store_true", help="Skip Xing scraping")
    args = parser.parse_args()

    run_date = datetime.utcnow().strftime("%Y-%m-%d")
    logger.info(f"=== Job Digest Bot starting - {run_date} ===")

    # 1. Scrape
    all_jobs = fetch_jobspy()
    if not args.no_xing:
        all_jobs.extend(fetch_xing())
    else:
        logger.info("Skipping Xing (--no-xing flag set)")
    logger.info(f"Total scraped: {len(all_jobs)} jobs")

    # 2. Deduplicate
    db = JobDatabase("jobs.db")
    new_jobs = db.filter_new(all_jobs)
    logger.info(f"New (not seen before): {len(new_jobs)} jobs")

    # 3. Score with Claude Haiku
    enriched = enrich_jobs(new_jobs) if new_jobs else []
    logger.info(f"Above threshold: {len(enriched)} jobs")

    # 4. Mark ALL new jobs as seen (even ones below threshold)
    db.mark_seen_batch(new_jobs)
    db.close()

    # 5. Render HTML
    html = render_digest(enriched, run_date=run_date)

    # 6. Send (unless --dry-run)
    if args.dry_run:
        dry_path = f"digest_preview_{run_date}.html"
        with open(dry_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"DRY RUN: email not sent. Preview saved to {dry_path}")
    else:
        if not send_digest(html, job_count=len(enriched), run_date=run_date):
            logger.error("Email failed to send!")
            sys.exit(1)

    logger.info(f"=== Done. {len(enriched)} jobs in digest. ===")


if __name__ == "__main__":
    main()

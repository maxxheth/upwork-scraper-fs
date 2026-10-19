"""Scrape the latest 50 WordPress jobs sorted by recency from UpWork via FlareSolverr."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from src.flaresolverr_client import FlareSolverrClient
from src.models import UpWorkJob
from src.parser import parse_job_listings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scrape_50_wordpress")

TARGET_JOBS = 50
DELAY_BETWEEN_PAGES = 5.0
OUTPUT_DIR = Path("/var/www/upwork-scraper-fs/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main() -> None:
    client = FlareSolverrClient(proxies=[], max_timeout=60000)
    all_jobs: list[UpWorkJob] = []
    seen_urls: set[str] = set()
    page = 1
    max_pages = 10

    logger.info("Starting scrape for 50 latest WordPress jobs on UpWork...")

    while len(all_jobs) < TARGET_JOBS and page <= max_pages:
        url = f"https://www.upwork.com/nx/search/jobs/?q=wordpress&sort=recency&page={page}"
        logger.info("Fetching Page %d: %s", page, url)

        try:
            resp = client.request(url)
            if resp.status != 200 or not resp.html:
                logger.error("Failed to fetch page %d: HTTP %d", page, resp.status)
                time.sleep(DELAY_BETWEEN_PAGES)
                page += 1
                continue

            jobs = parse_job_listings(resp.html)
            logger.info("Page %d returned %d raw jobs", page, len(jobs))

            new_on_page = 0
            for j in jobs:
                if j.url not in seen_urls:
                    seen_urls.add(j.url)
                    all_jobs.append(j)
                    new_on_page += 1
                    if len(all_jobs) >= TARGET_JOBS:
                        break

            logger.info("Added %d new jobs from page %d (Total: %d/%d)", new_on_page, page, len(all_jobs), TARGET_JOBS)

            if len(all_jobs) >= TARGET_JOBS:
                logger.info("Reached target of %d jobs!", TARGET_JOBS)
                break

            page += 1
            time.sleep(DELAY_BETWEEN_PAGES)

        except Exception as e:
            logger.exception("Error on page %d: %s", page, e)
            time.sleep(DELAY_BETWEEN_PAGES)
            page += 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"wordpress_latest_50_{timestamp}.json"

    data = [asdict(j) for j in all_jobs]
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Successfully scraped %d jobs and saved to %s", len(all_jobs), out_file)
    print(f"DONE:{len(all_jobs)}:{out_file}")

if __name__ == "__main__":
    main()

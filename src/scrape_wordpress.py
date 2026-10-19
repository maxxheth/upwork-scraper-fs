"""Scrape multiple pages of WordPress jobs from UpWork.

Usage:
    uv run python -m src.scrape_wordpress --pages 10
    uv run python -m src.scrape_wordpress --pages 10 --min-jobs 200
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from src.config import load_config
from src.orchestrator import UpWorkScraper

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape multiple pages of WordPress jobs")
    parser.add_argument("--pages", "-p", type=int, default=10, help="Number of pages to scrape")
    parser.add_argument("--min-jobs", type=int, default=200, help="Minimum jobs to collect")
    parser.add_argument("--delay", type=float, default=15.0, help="Delay between pages (seconds)")
    parser.add_argument("--query", "-q", type=str, default="wordpress", help="Search query")
    parser.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config()
    output_dir = Path(str(config["output_dir"]))

    scraper = UpWorkScraper(
        flaresolverr_url=str(config["flaresolverr_url"]),
        proxy_file=str(config["proxy_file"]),
        output_dir=str(config["output_dir"]),
    )

    all_jobs: list = []
    total_start = time.time()

    try:
        for page in range(1, args.pages + 1):
            print(f"\n{'='*60}")
            print(f"📄 Page {page}/{args.pages}")
            print(f"{'='*60}")

            result = scraper.search(
                query=args.query,
                page=page,
                max_retries=3,
            )

            if result.errors:
                print(f"  ❌ Error: {result.errors[0]}")
                continue

            jobs = result.jobs
            all_jobs.extend(jobs)
            elapsed = time.time() - total_start

            print(f"  ✅ Found {len(jobs)} jobs on page {page}")
            print(f"  📊 Running total: {len(all_jobs)} jobs in {elapsed:.0f}s")

            if len(all_jobs) >= args.min_jobs:
                print(f"\n🎯 Reached minimum {args.min_jobs} jobs — stopping early")
                break

            if page < args.pages:
                print(f"  ⏳ Waiting {args.delay}s before next page...")
                time.sleep(args.delay)

        total_elapsed = time.time() - total_start
        print(f"\n{'='*60}")
        print("📊 FINAL RESULTS")
        print(f"{'='*60}")
        print(f"  Query: '{args.query}'")
        print(f"  Pages scraped: {page}")
        print(f"  Total jobs: {len(all_jobs)}")
        print(f"  Time: {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")

        # Save combined results
        if all_jobs:
            from src.output import save_jobs
            combined_path = save_jobs(
                jobs=all_jobs,
                output_dir=output_dir,
                query=f"{args.query}_all_pages",
                page=1,
            )
            print(f"  💾 Saved: {combined_path}")

        return 0

    finally:
        scraper.close()


if __name__ == "__main__":
    sys.exit(main())

"""Scrape multiple pages of WordPress jobs from UpWork via ConfigurableScraper.

Usage:
    uv run python -m src.scrape_wordpress --pages 10
    uv run python -m src.scrape_wordpress --pages 10 --min-jobs 200
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.config_schema import load_profile_config
from src.orchestrator import ConfigurableScraper

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

    profile = load_profile_config("configs/profiles/wordpress_multi_page.yaml")
    profile.search.query = args.query
    profile.search.max_pages = args.pages
    profile.search.target_jobs = args.min_jobs
    profile.search.delay_between_pages_seconds = args.delay

    with ConfigurableScraper(profile) as scraper:
        result = scraper.run()

    if result.errors and not result.jobs:
        print(f"\n❌ Error: {result.errors[0]}")
        return 1

    print(f"\n{'='*60}")
    print("📊 FINAL RESULTS")
    print(f"{'='*60}")
    print(f"  Query: '{profile.search.query}'")
    print(f"  Total jobs: {result.total_found}")
    print(f"  Time: {result.elapsed_seconds:.0f}s ({result.elapsed_seconds/60:.1f} min)")
    if result.output_path:
        print(f"  💾 Saved: {result.output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

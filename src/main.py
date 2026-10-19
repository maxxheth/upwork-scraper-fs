"""UpWork scraper — FlareSolverr + Decodo proxies + Scrapling parsing.

Usage:
    uv run python -m src.main --query "golang developer"
    uv run python -m src.main --query "python" --page 2
    uv run python -m src.main --query "rust" --with-details
    uv run python -m src.main --query "python" --with-details --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.config import load_config
from src.orchestrator import UpWorkScraper


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="UpWork scraper — FlareSolverr + Decodo proxies + Scrapling",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default="golang developer",
        help="Search query (default: 'golang developer')",
    )
    parser.add_argument(
        "--page",
        "-p",
        type=int,
        default=1,
        help="Page number (default: 1)",
    )
    parser.add_argument(
        "--with-details",
        "-d",
        action="store_true",
        help="Scrape each job's detail page for full description + client info",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retries per request (default: 3)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def _print_job(i: int, job: object) -> None:
    """Print a single job's summary."""
    title = getattr(job, "title", "?")
    rate = getattr(job, "hourly_rate", None) or getattr(job, "budget", None)
    skills = getattr(job, "skills", [])
    exp = getattr(job, "experience_level", None)
    proposals = getattr(job, "proposals", None)
    client_spent = getattr(job, "client_spent", None)
    desc = getattr(job, "description", "")

    print(f"  {i}. {title}")
    if rate:
        print(f"     Rate: {rate}")
    if exp:
        print(f"     Exp: {exp}")
    if proposals:
        print(f"     Proposals: {proposals}")
    if client_spent:
        print(f"     Client spent: {client_spent}")
    if skills:
        print(f"     Skills: {', '.join(skills[:5])}")
    if desc:
        # Show first 120 chars of description
        desc_short = desc[:120].replace("\n", " ")
        print(f"     {desc_short}...")
    print()


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)
    setup_logging(args.verbose)

    config = load_config()

    scraper = UpWorkScraper(
        flaresolverr_url=str(config["flaresolverr_url"]),
        proxy_file=str(config["proxy_file"]),
        output_dir=str(config["output_dir"]),
    )

    try:
        if args.with_details:
            result = scraper.search_with_details(
                query=args.query,
                page=args.page,
                max_retries=args.max_retries,
            )
        else:
            result = scraper.search(
                query=args.query,
                page=args.page,
                max_retries=args.max_retries,
            )

        if result.errors:
            print(f"\n❌ Failed: {result.errors[0]}")
            return 1

        print(f"\n✅ Found {result.total_found} jobs for '{args.query}'")
        print(f"   Time: {result.elapsed_seconds:.1f}s")
        if result.output_path:
            print(f"   Saved: {result.output_path}")

        if result.jobs:
            print(f"\n--- Jobs ({len(result.jobs)}) ---")
            for i, job in enumerate(result.jobs[:10], 1):
                _print_job(i, job)

        return 0

    finally:
        scraper.close()


if __name__ == "__main__":
    sys.exit(main())

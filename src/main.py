"""UpWork scraper — YAML profile-driven execution with CLI flag overrides.

Usage:
    # Run a named profile directly
    uv run python -m src.main --config configs/profiles/wordpress_latest_50.yaml

    # Run default search with CLI query
    uv run python -m src.main --query "golang developer"
    uv run python -m src.main --query "python" --page 2
    uv run python -m src.main --query "rust" --with-details
    uv run python -m src.main --query "wordpress" --max-proposals 15
    uv run python -m src.main --adapter stealthy_session --query "wordpress" --max-proposals 10
"""

from __future__ import annotations

import argparse
import logging
import sys

from src.config_schema import load_profile_config
from src.orchestrator import ConfigurableScraper, UpWorkScraper

logger = logging.getLogger(__name__)


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
        description="UpWork scraper — YAML profile-driven scraper with adapter support",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to YAML scraping profile (e.g. configs/profiles/wordpress_latest_50.yaml)",
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default=None,
        help="Search query override",
    )
    parser.add_argument(
        "--page",
        "-p",
        type=int,
        default=None,
        help="Start page number override",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to scrape",
    )
    parser.add_argument(
        "--target-jobs",
        type=int,
        default=None,
        help="Stop pagination early after collecting this many jobs",
    )
    parser.add_argument(
        "--sort",
        type=str,
        choices=["recency", "relevance"],
        default=None,
        help="Sort order on UpWork search results",
    )
    parser.add_argument(
        "--adapter",
        type=str,
        choices=["flaresolverr", "stealthy_session"],
        default=None,
        help="Override transport adapter",
    )
    parser.add_argument(
        "--with-details",
        "-d",
        action="store_true",
        help="Enrich jobs with detail pages (full description + client info)",
    )
    parser.add_argument(
        "--max-proposals",
        type=int,
        default=None,
        help=(
            "Maximum allowed proposals upper-bound (e.g. 15 keeps 'Less than 5', '5 to 10', '10 to 15'). "
            "Automatically enables detail-page enrichment if search cards lack proposal counts."
        ),
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Max retries per request",
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
        desc_short = desc[:120].replace("\n", " ")
        print(f"     {desc_short}...")
    print()


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = parse_args(argv)
    setup_logging(args.verbose)

    # 1. Determine profile path
    profile_path = args.config
    if not profile_path:
        profile_path = "configs/profiles/default_search.yaml"

    try:
        profile = load_profile_config(profile_path)
    except FileNotFoundError:
        # Fall back to legacy UpWorkScraper if config not found
        logger.warning("Profile %s not found, falling back to legacy orchestrator", profile_path)
        return _run_legacy(args)

    # 2. Apply CLI overrides to profile
    if args.query is not None:
        profile.search.query = args.query
    if args.page is not None:
        profile.search.start_page = args.page
    if args.max_pages is not None:
        profile.search.max_pages = args.max_pages
    if args.target_jobs is not None:
        profile.search.target_jobs = args.target_jobs
    if args.sort is not None:
        profile.search.sort = args.sort
    if args.adapter is not None:
        profile.transport.adapter = args.adapter
    if args.with_details:
        profile.enrichment.enabled = True
    if args.max_proposals is not None:
        profile.filters.max_proposals = args.max_proposals
    if args.max_retries is not None:
        profile.transport.max_retries = args.max_retries

    # 3. Execute through ConfigurableScraper
    runner = ConfigurableScraper(profile)
    try:
        result = runner.run()

        if result.errors:
            print(f"\n❌ Error during scrape: {result.errors[0]}")
            if not result.jobs:
                return 1

        print(f"\n✅ Found {result.total_found} jobs for '{profile.search.query}'")
        print(f"   Time: {result.elapsed_seconds:.1f}s")
        if result.output_path:
            print(f"   Saved: {result.output_path}")

        if result.jobs:
            print(f"\n--- Jobs ({len(result.jobs)}) ---")
            for i, job in enumerate(result.jobs[:10], 1):
                _print_job(i, job)

        return 0

    finally:
        runner.close()


def _run_legacy(args: argparse.Namespace) -> int:
    """Legacy execution path for backward compatibility."""
    from src.config import load_config

    config = load_config()
    scraper = UpWorkScraper(
        flaresolverr_url=str(config["flaresolverr_url"]),
        proxy_file=str(config["proxy_file"]),
        output_dir=str(config["output_dir"]),
    )
    query = args.query or "golang developer"
    page = args.page or 1
    max_retries = args.max_retries or 3
    max_proposals = args.max_proposals

    try:
        if args.with_details or max_proposals is not None:
            result = scraper.search_with_details(
                query=query,
                page=page,
                max_retries=max_retries,
                max_proposals=max_proposals,
            )
        else:
            result = scraper.search(query=query, page=page, max_retries=max_retries)

        if result.errors:
            print(f"\n❌ Failed: {result.errors[0]}")
            return 1

        print(f"\n✅ Found {result.total_found} jobs for '{query}'")
        return 0
    finally:
        scraper.close()


if __name__ == "__main__":
    sys.exit(main())

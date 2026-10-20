"""Scrape the latest 50 WordPress jobs sorted by recency from UpWork via ConfigurableScraper."""

from __future__ import annotations

import logging

from src.config_schema import load_profile_config
from src.orchestrator import ConfigurableScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scrape_50_wordpress")


def main() -> None:
    profile = load_profile_config("configs/profiles/wordpress_latest_50.yaml")
    logger.info("Starting scrape for 50 latest WordPress jobs on UpWork via profile %s...", profile.name)

    with ConfigurableScraper(profile) as scraper:
        result = scraper.run()

    if result.output_path:
        logger.info("Successfully scraped %d jobs and saved to %s", result.total_found, result.output_path)
        print(f"DONE:{result.total_found}:{result.output_path}")
    else:
        logger.warning("Scrape completed with 0 saved jobs. Errors: %s", result.errors)


if __name__ == "__main__":
    main()

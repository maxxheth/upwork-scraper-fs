"""Scrape detail pages for top WordPress jobs to get full client info + scores via ConfigurableScraper.

Usage:
    uv run python -m src.scrape_top_details
"""

from __future__ import annotations

import logging
import sys

from src.config_schema import load_profile_config
from src.orchestrator import ConfigurableScraper
from src.proposal_engine import score_job

logger = logging.getLogger(__name__)


def format_score_label(score: int) -> str:
    """Return an emoji label for a proposal match score."""
    if score >= 80:
        return "🔥 HOT"
    if score >= 60:
        return "👍 WARM"
    if score >= 40:
        return "👎 LUKEWARM"
    return "❌ SKIP"


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    profile = load_profile_config("configs/profiles/wordpress_top20_enriched.yaml")
    logger.info("Running top 20 enrichment via profile: %s", profile.name)

    with ConfigurableScraper(profile) as scraper:
        result = scraper.run()

    if result.errors and not result.jobs:
        logger.error("Enrichment failed: %s", result.errors)
        return 1

    print(f"\n✅ Enriched {result.total_found} jobs in {result.elapsed_seconds:.0f}s")
    if result.output_path:
        print(f"💾 Saved: {result.output_path}")

    # Print summary
    print(f"\n{'='*60}")
    print("📊 ENRICHED RESULTS")
    print(f"{'='*60}")
    for i, job in enumerate(result.jobs, 1):
        job_dict = job.__dict__
        score = score_job(job_dict)
        label = format_score_label(score)
        title = job.title[:70]
        rate = job.hourly_rate or job.budget or "?"
        spend = job.client_spent or "?"
        hires = job.client_hires or "?"
        proposals = job.proposals or "?"
        posted = job.posted or "?"
        print(f"  {i}. {label} ({score}/100) — {title}")
        print(f"     Rate: {rate} | Proposals: {proposals} | Spend: ${spend} | Hires: {hires} | Posted: {posted}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())

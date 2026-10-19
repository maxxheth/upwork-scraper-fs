"""Scrape detail pages for the top 20 WordPress jobs to get full client info + scores.

Usage:
    uv run python -m src.scrape_top_details
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import UTC
from pathlib import Path

from src.config import load_config
from src.orchestrator import UpWorkScraper
from src.proposal_engine import load_jobs, parse_posted_age, score_job

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    config = load_config()

    # Load and filter top 20
    all_jobs = load_jobs()
    q = "wordpress"
    jobs = [j for j in all_jobs if q in j.get("title", "").lower() or q in j.get("_query", "").lower()]
    jobs.sort(key=lambda j: j.get("_score", 0), reverse=True)
    jobs = [j for j in jobs if j.get("_score", 0) >= 40]
    jobs = [j for j in jobs if (age := parse_posted_age(j.get("posted"))) is None or age <= 21]
    top20 = jobs[:20]

    print(f"📄 Scraping detail pages for {len(top20)} jobs...\n")

    scraper = UpWorkScraper(
        flaresolverr_url=str(config["flaresolverr_url"]),
        proxy_file=str(config["proxy_file"]),
        output_dir=str(config["output_dir"]),
    )

    enriched = []
    start = time.time()

    try:
        for i, job in enumerate(top20, 1):
            url = job.get("url", "")
            if not url:
                enriched.append(job)
                continue

            # Clean URL: remove referrer_url_path param
            clean_url = url.split("?referrer")[0]
            print(f"  [{i}/{len(top20)}] {job['title'][:60]}...", end=" ", flush=True)

            result = scraper.scrape_job_detail(url=clean_url, max_retries=2)

            if result.jobs:
                detail = result.jobs[0]
                # Merge detail fields into the job dict
                for key in ["description", "hourly_rate", "experience_level", "duration",
                            "skills", "posted", "country", "proposals",
                            "client_rating", "client_reviews", "client_hires", "client_spent"]:
                    val = getattr(detail, key, None)
                    if val:
                        job[key] = val
                job["_source"] = "enriched"
                print(f"✅ (proposals: {job.get('proposals', '?')}, spend: {job.get('client_spent', '?')})")
            else:
                print("⚠️  (failed, keeping search data)")

            # Re-score with enriched data
            job["_score"] = score_job(job)
            enriched.append(job)

            # Small delay between detail pages
            if i < len(top20):
                time.sleep(2)

        total = time.time() - start
        print(f"\n✅ Enriched {len(enriched)} jobs in {total:.0f}s")

        # Sort by new score
        enriched.sort(key=lambda j: j.get("_score", 0), reverse=True)

        # Save enriched results
        output_dir = Path(str(config["output_dir"]))
        output_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"upwork_wordpress_enriched_top20_{ts}.json"
        with open(out_path, "w") as f:
            json.dump({"query": "wordpress_enriched", "total_jobs": len(enriched), "jobs": enriched}, f, indent=2, default=str)
        print(f"💾 Saved: {out_path}")

        # Print summary
        print("\n📊 ENRICHED RESULTS")
        print(f"{'='*60}")
        for i, j in enumerate(enriched, 1):
            score = j.get("_score", 0)
            label = "🔥 HOT" if score >= 80 else "👍 WARM" if score >= 60 else "👎 LUKEWARM" if score >= 40 else "❌ SKIP"
            title = j.get("title", "?")[:70]
            rate = j.get("hourly_rate") or j.get("budget") or "?"
            spend = j.get("client_spent") or "?"
            hires = j.get("client_hires") or "?"
            proposals = j.get("proposals") or "?"
            posted = j.get("posted") or "?"
            print(f"  {i}. {label} ({score}/100) — {title}")
            print(f"     Rate: {rate} | Proposals: {proposals} | Spend: ${spend} | Hires: {hires} | Posted: {posted}")
            print()

        return 0

    finally:
        scraper.close()


if __name__ == "__main__":
    sys.exit(main())

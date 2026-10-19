"""Orchestrator — coordinates FlareSolverr sessions, proxy rotation, and parsing."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.config import load_proxies
from src.flaresolverr_client import FlareSolverrClient
from src.models import UpWorkJob
from src.output import save_jobs
from src.parser import parse_job_detail, parse_job_listings

logger = logging.getLogger(__name__)


@dataclass
class ScrapeResult:
    """Result of a scrape operation."""

    query: str
    jobs: list[UpWorkJob] = field(default_factory=list)
    total_found: int = 0
    errors: list[str] = field(default_factory=list)
    output_path: Path | None = None
    elapsed_seconds: float = 0.0


class UpWorkScraper:
    """Orchestrator for UpWork scraping with FlareSolverr + proxy rotation."""

    def __init__(
        self,
        flaresolverr_url: str = "http://localhost:8193",
        proxy_file: str | None = None,
        output_dir: str | Path = "output",
        max_timeout: int = 60000,
    ) -> None:
        self.output_dir = Path(output_dir)

        # Load proxies
        proxies: list[str] = []
        if proxy_file:
            proxies = load_proxies(proxy_file)
            logger.info("Loaded %d proxies from %s", len(proxies), proxy_file)

        self.client = FlareSolverrClient(
            base_url=flaresolverr_url,
            proxies=proxies,
            max_timeout=max_timeout,
        )

    def search(
        self,
        query: str,
        page: int = 1,
        max_retries: int = 3,
    ) -> ScrapeResult:
        """Search UpWork for jobs matching the query.

        Uses FlareSolverr with proxy rotation to bypass Cloudflare
        and render the Nuxt page.
        """
        start = time.time()
        result = ScrapeResult(query=query)

        # Build search URL
        safe_query = query.replace(" ", "+")
        url = f"https://www.upwork.com/nx/search/jobs/?q={safe_query}&page={page}"

        logger.info("Searching: %s (page %d)", url, page)

        last_error: str | None = None
        for attempt in range(1, max_retries + 1):
            try:
                fs_resp = self.client.request_with_rotation(
                    url=url,
                    return_raw_html=True,
                )

                if fs_resp.error:
                    last_error = fs_resp.error
                    logger.warning(
                        "Attempt %d/%d failed: %s",
                        attempt,
                        max_retries,
                        fs_resp.error,
                    )
                    time.sleep(2 * attempt)
                    continue

                if fs_resp.status != 200:
                    last_error = f"HTTP {fs_resp.status}"
                    logger.warning(
                        "Attempt %d/%d: status %d",
                        attempt,
                        max_retries,
                        fs_resp.status,
                    )
                    time.sleep(2 * attempt)
                    continue

                # Parse the rendered HTML
                jobs = parse_job_listings(
                    html=fs_resp.html,
                    session_id=fs_resp.session_id,
                )

                result.jobs = jobs
                result.total_found = len(jobs)
                result.elapsed_seconds = time.time() - start

                logger.info(
                    "Found %d jobs in %.1fs (session=%s)",
                    len(jobs),
                    result.elapsed_seconds,
                    fs_resp.session_id,
                )

                # Save results
                result.output_path = save_jobs(
                    jobs=jobs,
                    output_dir=self.output_dir,
                    query=query,
                    page=page,
                )

                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Attempt %d/%d error: %s",
                    attempt,
                    max_retries,
                    e,
                )
                time.sleep(2 * attempt)

        result.errors.append(last_error or "Unknown error")
        result.elapsed_seconds = time.time() - start
        logger.error("All %d attempts failed for query: %s", max_retries, query)
        return result

    def close(self) -> None:
        """Clean up FlareSolverr sessions."""
        self.client.close()

    def search_with_details(
        self,
        query: str,
        page: int = 1,
        max_retries: int = 3,
        detail_retries: int = 2,
    ) -> ScrapeResult:
        """Search UpWork and then scrape each job's detail page.

        Two-phase approach:
          1. Search results page (fast, ~14s) — gets titles, rates, skills
          2. Each job's detail page (~14s each) — gets full description + client info

        Args:
            query: Search query.
            page: Page number.
            max_retries: Max retries for the search request.
            detail_retries: Max retries per job detail request.

        Returns:
            ScrapeResult with all jobs enriched with full details.
        """
        start = time.time()

        # Phase 1: Search
        search_result = self.search(query=query, page=page, max_retries=max_retries)
        if search_result.errors or not search_result.jobs:
            return search_result

        # Phase 2: Scrape each job's detail page
        logger.info(
            "Scraping details for %d jobs...",
            len(search_result.jobs),
        )

        enriched: list[UpWorkJob] = []
        for i, job in enumerate(search_result.jobs, 1):
            if not job.url:
                enriched.append(job)
                continue

            logger.info("[%d/%d] Scraping detail: %s", i, len(search_result.jobs), job.title[:60])

            detail_result = self.scrape_job_detail(
                url=job.url,
                max_retries=detail_retries,
            )

            if detail_result.jobs:
                detail = detail_result.jobs[0]
                # Merge: detail page has full description + client info,
                # search page has the correct URL
                detail.url = job.url
                enriched.append(detail)
            else:
                # Fall back to search result
                enriched.append(job)

        result = ScrapeResult(
            query=query,
            jobs=enriched,
            total_found=len(enriched),
            elapsed_seconds=time.time() - start,
        )

        # Save enriched results
        result.output_path = save_jobs(
            jobs=enriched,
            output_dir=self.output_dir,
            query=query,
            page=page,
        )

        logger.info(
            "Search + details complete: %d jobs in %.1fs",
            len(enriched),
            result.elapsed_seconds,
        )
        return result

    def scrape_job_detail(
        self,
        url: str,
        max_retries: int = 3,
    ) -> ScrapeResult:
        """Scrape a single UpWork job detail page for the full description.

        Args:
            url: Full URL to the job detail page.
            max_retries: Max retry attempts.

        Returns:
            ScrapeResult with a single job (with full description).
        """
        start = time.time()
        result = ScrapeResult(query=url)

        logger.info("Scraping job detail: %s", url)

        last_error: str | None = None
        for attempt in range(1, max_retries + 1):
            try:
                fs_resp = self.client.request_with_rotation(
                    url=url,
                    return_raw_html=True,
                )

                if fs_resp.error:
                    last_error = fs_resp.error
                    logger.warning(
                        "Attempt %d/%d failed: %s",
                        attempt,
                        max_retries,
                        fs_resp.error,
                    )
                    time.sleep(2 * attempt)
                    continue

                if fs_resp.status != 200:
                    last_error = f"HTTP {fs_resp.status}"
                    logger.warning(
                        "Attempt %d/%d: status %d",
                        attempt,
                        max_retries,
                        fs_resp.status,
                    )
                    time.sleep(2 * attempt)
                    continue

                # Parse the job detail page
                job = parse_job_detail(
                    html=fs_resp.html,
                    session_id=fs_resp.session_id,
                )

                if job:
                    job.url = url
                    result.jobs = [job]
                    result.total_found = 1
                else:
                    last_error = "Failed to parse job detail"
                    logger.warning("Attempt %d/%d: %s", attempt, max_retries, last_error)
                    time.sleep(2 * attempt)
                    continue

                result.elapsed_seconds = time.time() - start

                logger.info(
                    "Scraped job detail in %.1fs (session=%s)",
                    result.elapsed_seconds,
                    fs_resp.session_id,
                )

                # Save
                result.output_path = save_jobs(
                    jobs=result.jobs,
                    output_dir=self.output_dir,
                    query=job.title[:40] if job.title else "job_detail",
                    page=1,
                )

                return result

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Attempt %d/%d error: %s",
                    attempt,
                    max_retries,
                    e,
                )
                time.sleep(2 * attempt)

        result.errors.append(last_error or "Unknown error")
        result.elapsed_seconds = time.time() - start
        logger.error("All %d attempts failed for job detail: %s", max_retries, url)
        return result

"""Orchestrator — YAML profile-driven scraping pipeline and adapter coordination."""

from __future__ import annotations

import logging
import time
import urllib.parse
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.adapters import FetchRequest, TransportAdapter, create_adapter
from src.config import load_config
from src.config_schema import ScrapeProfileConfig, load_profile_config
from src.flaresolverr_client import FlareSolverrClient
from src.models import UpWorkJob
from src.output import save_jobs, save_jobs_with_prefix
from src.parser import ConfigurableDomParser, parse_job_detail, parse_job_listings
from src.proposal_engine import (
    job_meets_proposal_threshold,
     parse_posted_age,
    parse_proposal_count,
    score_job,
)
from src.proposal_engine import load_jobs as pe_load_jobs

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


class ConfigurableScraper:
    """YAML profile-driven pipeline runner for UpWork scraping."""

    def __init__(
        self,
        profile: ScrapeProfileConfig,
        adapter: TransportAdapter | None = None,
        parser: ConfigurableDomParser | None = None,
        base_config: dict[str, Any] | None = None,
    ) -> None:
        self.profile = profile
        self.env = base_config or load_config()
        self.adapter = adapter or create_adapter(profile.transport, self.env)
        self.parser = parser or ConfigurableDomParser(config_path=profile.selectors_file)
        self.output_dir = Path(profile.output.directory)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_profile_file(
        cls,
        profile_path: str | Path,
        adapter: TransportAdapter | None = None,
        parser: ConfigurableDomParser | None = None,
        base_config: dict[str, Any] | None = None,
    ) -> ConfigurableScraper:
        """Instantiate runner from a YAML profile file path."""
        cfg = load_profile_config(profile_path)
        return cls(profile=cfg, adapter=adapter, parser=parser, base_config=base_config)

    def run(self) -> ScrapeResult:
        """Execute the 4-stage scraping pipeline defined by the profile."""
        start_time = time.time()
        result = ScrapeResult(query=self.profile.search.query)
        collected_jobs: list[UpWorkJob] = []

        # -------------------------------------------------------------------
        # Stage 1: Acquisition (live_search or from_saved_output)
        # -------------------------------------------------------------------
        if self.profile.search.mode == "live_search":
            collected_jobs = self._run_live_search(result)
        elif self.profile.search.mode == "from_saved_output":
            collected_jobs = self._run_from_saved_output()
        else:
            result.errors.append(f"Unknown search mode: {self.profile.search.mode}")
            result.elapsed_seconds = time.time() - start_time
            return result

        # -------------------------------------------------------------------
        # Stage 2: Filtering & Pre-Enrichment Sorting
        # -------------------------------------------------------------------
        filtered_jobs = self._apply_filters(collected_jobs)

        # -------------------------------------------------------------------
        # Stage 3: Detail Page Enrichment (explicit or auto-enabled for max_proposals)
        # -------------------------------------------------------------------
        max_proposals = self.profile.filters.max_proposals
        needs_proposal_enrichment = (
            max_proposals is not None
            and any(j.proposals is None for j in filtered_jobs)
        )
        should_enrich = self.profile.enrichment.enabled or needs_proposal_enrichment

        final_jobs = filtered_jobs
        if should_enrich and filtered_jobs:
            if needs_proposal_enrichment and not self.profile.enrichment.enabled:
                logger.info(
                    "Auto-enabling detail enrichment to resolve proposal counts for max_proposals=%d",
                    max_proposals,
                )
            final_jobs = self._run_enrichment(filtered_jobs)

        # Enforce final upper-bound proposal threshold after enrichment
        if max_proposals is not None:
            before_count = len(final_jobs)
            final_jobs = [
                j
                for j in final_jobs
                if job_meets_proposal_threshold(
                    j.proposals,
                    max_proposals,
                    include_unknown=False,
                )
            ]
            dropped = before_count - len(final_jobs)
            if dropped:
                logger.info(
                    "Filtered out %d jobs exceeding max_proposals=%d (or missing proposals)",
                    dropped,
                    max_proposals,
                )

        result.jobs = final_jobs
        result.total_found = len(final_jobs)
        result.elapsed_seconds = time.time() - start_time

        # -------------------------------------------------------------------
        # Stage 4: Output Persistence (Standard SearchResult envelope)
        # -------------------------------------------------------------------
        if self.profile.output.save_combined and final_jobs:
            out_path = save_jobs_with_prefix(
                jobs=final_jobs,
                output_dir=self.output_dir,
                filename_prefix=self.profile.output.filename_prefix,
                query=self.profile.search.query,
                page=1,
            )
            result.output_path = out_path
            logger.info("Saved combined results (%d jobs) to %s", len(final_jobs), out_path)

        return result

    def _run_live_search(self, result: ScrapeResult) -> list[UpWorkJob]:
        """Iterate search result pages and extract job listings."""
        seen_urls: set[str] = set()
        jobs: list[UpWorkJob] = []

        query = self.profile.search.query
        safe_query = urllib.parse.quote_plus(query)
        start_page = self.profile.search.start_page
        max_pages = self.profile.search.max_pages
        target = self.profile.search.target_jobs

        for page in range(start_page, max_pages + 1):
            url = f"https://www.upwork.com/nx/search/jobs/?q={safe_query}"
            if self.profile.search.sort:
                url += f"&sort={self.profile.search.sort}"
            url += f"&page={page}"

            logger.info("Fetching search page %d: %s", page, url)

            fetch_req = FetchRequest(
                url=url,
                auto_scroll=self.profile.transport.auto_scroll,
                max_scrolls=self.profile.transport.max_scrolls,
                scroll_delay_ms=self.profile.transport.scroll_delay_ms,
                timeout_ms=self.profile.transport.max_timeout_ms,
                max_retries=self.profile.transport.max_retries,
            )

            resp = self.adapter.fetch(fetch_req)
            if not resp.ok:
                err_msg = resp.error or f"HTTP {resp.status}"
                logger.warning("Search page %d failed: %s", page, err_msg)
                result.errors.append(f"Page {page}: {err_msg}")
                time.sleep(self.profile.search.delay_between_pages_seconds)
                continue

            page_jobs = self.parser.parse_job_listings(resp.html, session_id=resp.session_id)
            logger.info("Page %d parsed %d job cards", page, len(page_jobs))

            new_on_page = 0
            for j in page_jobs:
                if self.profile.search.deduplicate_by_url:
                    if j.url and j.url in seen_urls:
                        continue
                    if j.url:
                        seen_urls.add(j.url)

                jobs.append(j)
                new_on_page += 1

                if target and len(jobs) >= target:
                    break

            if self.profile.output.save_per_page and page_jobs:
                save_jobs_with_prefix(
                    jobs=page_jobs,
                    output_dir=self.output_dir,
                    filename_prefix=f"{self.profile.output.filename_prefix}_p{page}",
                    query=query,
                    page=page,
                )

            if target and len(jobs) >= target:
                logger.info("Reached target of %d jobs — stopping early", target)
                break

            if page < max_pages and self.profile.search.delay_between_pages_seconds > 0:
                time.sleep(self.profile.search.delay_between_pages_seconds)

        return jobs

    def _run_from_saved_output(self) -> list[UpWorkJob]:
        """Load jobs from saved JSON file or output directory."""
        source = (
            self.profile.search.input_saved_file
            if self.profile.search.input_saved_file
            else self.output_dir
        )
        raw_jobs = pe_load_jobs(source)
        jobs: list[UpWorkJob] = []
        for r in raw_jobs:
            proposals_val = r.get("proposals")
            jobs.append(
                UpWorkJob(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    description=r.get("description", ""),
                    budget=r.get("budget"),
                    experience_level=r.get("experience_level"),
                    duration=r.get("duration"),
                    hourly_rate=r.get("hourly_rate"),
                    skills=r.get("skills", []),
                    posted=r.get("posted"),
                    country=r.get("country"),
                    proposals=proposals_val,
                    proposals_count=(
                        r.get("proposals_count")
                        if r.get("proposals_count") is not None
                        else parse_proposal_count(proposals_val)
                    ),
                    client_rating=r.get("client_rating"),
                    client_reviews=r.get("client_reviews"),
                    client_hires=r.get("client_hires"),
                    client_spent=r.get("client_spent"),
                    session_id=r.get("session_id"),
                )
            )
        return jobs

    def _apply_filters(self, jobs: list[UpWorkJob]) -> list[UpWorkJob]:
        """Apply keyword, proposal, score, and age filters, sorting by proposal score when appropriate."""
        filtered = jobs

        # Required keywords
        if self.profile.filters.required_keywords:
            keywords = [k.lower() for k in self.profile.filters.required_keywords]
            filtered = [
                j
                for j in filtered
                if any(k in j.title.lower() or k in j.description.lower() for k in keywords)
            ]

        # Max posted age days
        if self.profile.filters.max_posted_age_days is not None:
            max_days = self.profile.filters.max_posted_age_days
            filtered = [
                j
                for j in filtered
                if (age := parse_posted_age(j.posted)) is None or age <= max_days
            ]

        # Pre-enrichment proposal count filter (drop cards already known to exceed max_proposals;
        # keep unknown cards so Stage 3 detail enrichment can inspect their proposal count)
        if self.profile.filters.max_proposals is not None:
            max_p = self.profile.filters.max_proposals
            filtered = [
                j
                for j in filtered
                if job_meets_proposal_threshold(j.proposals, max_p, include_unknown=True)
            ]

        # Min score filtering & score sorting
        should_score = (
            self.profile.filters.min_score is not None
            or self.profile.enrichment.compute_proposal_scores
        )
        if should_score:
            scored: list[tuple[int, UpWorkJob]] = []
            for j in filtered:
                sc = score_job(asdict(j))
                if self.profile.filters.min_score is None or sc >= self.profile.filters.min_score:
                    scored.append((sc, j))

            # Sort descending by score
            scored.sort(key=lambda item: item[0], reverse=True)
            filtered = [item[1] for item in scored]

        return filtered

    def _run_enrichment(self, jobs: list[UpWorkJob]) -> list[UpWorkJob]:
        """Scrape full detail pages, merge attributes, and optionally re-score and re-sort."""
        max_enrich = self.profile.enrichment.max_jobs_to_enrich
        targets = jobs[:max_enrich] if max_enrich is not None else jobs
        remaining = jobs[max_enrich:] if max_enrich is not None else []

        enriched_list: list[UpWorkJob] = []
        for i, job in enumerate(targets, 1):
            if not job.url:
                enriched_list.append(job)
                continue

            clean_url = job.url.split("?")[0]
            logger.info("[%d/%d] Enriching detail: %s", i, len(targets), job.title[:60])

            fetch_req = FetchRequest(
                url=clean_url,
                timeout_ms=self.profile.transport.max_timeout_ms,
                max_retries=self.profile.enrichment.detail_retries,
            )
            resp = self.adapter.fetch(fetch_req)
            if resp.ok:
                detail = self.parser.parse_job_detail(resp.html, session_id=resp.session_id)
                if detail:
                    # Merge full details
                    if detail.description:
                        job.description = detail.description
                    if detail.hourly_rate:
                        job.hourly_rate = detail.hourly_rate
                    if detail.budget:
                        job.budget = detail.budget
                    if detail.experience_level:
                        job.experience_level = detail.experience_level
                    if detail.duration:
                        job.duration = detail.duration
                    if detail.skills:
                        job.skills = detail.skills
                    if detail.posted:
                        job.posted = detail.posted
                    if detail.country:
                        job.country = detail.country
                    if detail.proposals:
                        job.proposals = detail.proposals
                        job.proposals_count = detail.proposals_count
                    if detail.client_rating is not None:
                        job.client_rating = detail.client_rating
                    if detail.client_hires is not None:
                        job.client_hires = detail.client_hires
                    if detail.client_spent is not None:
                        job.client_spent = detail.client_spent

            enriched_list.append(job)
            if i < len(targets) and self.profile.enrichment.delay_between_details_seconds > 0:
                time.sleep(self.profile.enrichment.delay_between_details_seconds)

        total_list = enriched_list + remaining

        # Re-score and re-sort if proposal scores are requested
        if self.profile.enrichment.compute_proposal_scores:
            total_list.sort(key=lambda j: score_job(asdict(j)), reverse=True)

        return total_list

    def close(self) -> None:
        """Release adapter resources."""
        self.adapter.close()

    def __enter__(self) -> ConfigurableScraper:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Backward-Compatible UpWorkScraper Wrapper
# ---------------------------------------------------------------------------


class UpWorkScraper:
    """Backward-compatible facade delegating to FlareSolverrClient."""

    def __init__(
        self,
        flaresolverr_url: str = "http://localhost:8193",
        proxy_file: str | None = None,
        output_dir: str | Path = "output",
        max_timeout: int = 60000,
    ) -> None:
        self.output_dir = Path(output_dir)

        from src.config import load_proxies

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
        max_proposals: int | None = None,
    ) -> ScrapeResult:
        """Search UpWork for jobs matching query."""
        if max_proposals is not None:
            return self.search_with_details(
                query=query,
                page=page,
                max_retries=max_retries,
                max_proposals=max_proposals,
            )

        start = time.time()
        result = ScrapeResult(query=query)

        safe_query = urllib.parse.quote_plus(query)
        url = f"https://www.upwork.com/nx/search/jobs/?q={safe_query}&page={page}"
        logger.info("Searching: %s (page %d)", url, page)

        last_error: str | None = None
        for attempt in range(1, max_retries + 1):
            try:
                fs_resp = self.client.request_with_rotation(url=url, return_raw_html=True)
                if fs_resp.error:
                    last_error = fs_resp.error
                    time.sleep(2 * attempt)
                    continue

                if fs_resp.status != 200:
                    last_error = f"HTTP {fs_resp.status}"
                    time.sleep(2 * attempt)
                    continue

                jobs = parse_job_listings(html=fs_resp.html, session_id=fs_resp.session_id)
                result.jobs = jobs
                result.total_found = len(jobs)
                result.elapsed_seconds = time.time() - start

                result.output_path = save_jobs(
                    jobs=jobs,
                    output_dir=self.output_dir,
                    query=query,
                    page=page,
                )
                return result

            except Exception as e:
                last_error = str(e)
                time.sleep(2 * attempt)

        result.errors.append(last_error or "Unknown error")
        result.elapsed_seconds = time.time() - start
        return result

    def scrape_job_detail(
        self,
        url: str,
        max_retries: int = 3,
    ) -> ScrapeResult:
        """Scrape a single UpWork job detail page."""
        start = time.time()
        result = ScrapeResult(query=url)
        last_error: str | None = None

        for attempt in range(1, max_retries + 1):
            try:
                fs_resp = self.client.request_with_rotation(url=url, return_raw_html=True)
                if fs_resp.error:
                    last_error = fs_resp.error
                    time.sleep(2 * attempt)
                    continue

                if fs_resp.status != 200:
                    last_error = f"HTTP {fs_resp.status}"
                    time.sleep(2 * attempt)
                    continue

                job = parse_job_detail(html=fs_resp.html, session_id=fs_resp.session_id)
                if job:
                    job.url = url
                    result.jobs = [job]
                    result.total_found = 1
                    result.elapsed_seconds = time.time() - start
                    result.output_path = save_jobs(
                        jobs=result.jobs,
                        output_dir=self.output_dir,
                        query=job.title[:40] if job.title else "job_detail",
                        page=1,
                    )
                    return result

                last_error = "Failed to parse job detail"
                time.sleep(2 * attempt)

            except Exception as e:
                last_error = str(e)
                time.sleep(2 * attempt)

        result.errors.append(last_error or "Unknown error")
        result.elapsed_seconds = time.time() - start
        return result

    def search_with_details(
        self,
        query: str,
        page: int = 1,
        max_retries: int = 3,
        detail_retries: int = 2,
        max_proposals: int | None = None,
    ) -> ScrapeResult:
        """Search and enrich detail pages, optionally filtering by max_proposals."""
        search_result = self.search(query=query, page=page, max_retries=max_retries)
        if search_result.errors or not search_result.jobs:
            return search_result

        enriched: list[UpWorkJob] = []
        for job in search_result.jobs:
            if max_proposals is not None and not job_meets_proposal_threshold(
                job.proposals, max_proposals, include_unknown=True
            ):
                continue
            if not job.url:
                enriched.append(job)
                continue
            detail_res = self.scrape_job_detail(url=job.url, max_retries=detail_retries)
            if detail_res.jobs:
                detail = detail_res.jobs[0]
                detail.url = job.url
                enriched.append(detail)
            else:
                enriched.append(job)

        if max_proposals is not None:
            enriched = [
                j
                for j in enriched
                if job_meets_proposal_threshold(
                    j.proposals,
                    max_proposals,
                    include_unknown=False,
                )
            ]

        search_result.jobs = enriched
        search_result.total_found = len(enriched)
        return search_result

    def close(self) -> None:
        self.client.close()

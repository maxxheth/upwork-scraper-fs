"""Unit tests for YAML selector configs, profile configs, TransportAdapters, and ConfigurableScraper."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.adapters import FetchRequest, FetchResponse, TransportAdapter, create_adapter
from src.adapters.flaresolverr_adapter import FlareSolverrAdapter
from src.adapters.stealthy_adapter import StealthySessionAdapter
from src.config_schema import (
    ScrapeProfileConfig,
    TransportConfig,
    load_profile_config,
    load_selector_config,
)
from src.models import UpWorkJob
from src.orchestrator import ConfigurableScraper
from src.parser import ConfigurableDomParser
from src.proposal_engine import load_jobs
from src.ui_inspector.selector_registry import CORE_PARSER_REGISTRY

SAMPLE_SEARCH_PAGE_HTML = """
<!DOCTYPE html>
<html>
<body>
  <main>
    <article class="job-tile" data-test="JobTile">
      <a data-test="job-tile-title-link" href="/jobs/Python-Engineer-span-class-highlight-FastAPI-span_~022111887415567641941/?referrer_url_path=/nx/search/jobs/">
        Python Engineer FastAPI
      </a>
      <div data-test="JobDescription"><p>Build scalable REST APIs using FastAPI and PostgreSQL.</p></div>
      <div data-test="job-type-label">Hourly: <strong>$50.00 - $75.00</strong></div>
      <div data-test="experience-level"><strong>Expert</strong></div>
      <div data-test="duration-label">Est. time:3 to 6 months</div>
      <div data-test="token"><span>Python</span></div>
      <div data-test="token"><span>FastAPI</span></div>
      <div data-test="job-pubilshed-date"><span>Posted 2 hours ago</span></div>
      <div data-qa="client-location">United States</div>
      <div data-test="proposals-tier">5 to 10</div>
      <div data-qa="client-rating">4.9 of 5</div>
    </article>
    <article class="job-tile" data-test="JobTile">
      <a data-test="job-tile-title-link" href="/jobs/WordPress-Elementor-Fix_~022111887415567641942/">
        WordPress Elementor Fix
      </a>
      <div data-test="JobDescription"><p>Fix broken layout on Elementor header.</p></div>
      <div data-test="is-fixed-price">Est. budget: $150.00</div>
      <div data-test="experience-level"><strong>Intermediate</strong></div>
      <div data-test="token"><span>WordPress</span></div>
      <div data-test="job-published-date"><span>Posted 1 day ago</span></div>
    </article>
  </main>
</body>
</html>
"""

SAMPLE_DETAIL_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Python Engineer FastAPI - UpWork</title></head>
<body>
  <h1>Python Engineer FastAPI</h1>
  <div data-test="Description">
    <p class="multiline-text">Summary We need an expert Python FastAPI developer to architect high-performance microservices.</p>
  </div>
  <li class="ca-item"><span class="title">Proposals:</span><span class="value">Less than 5</span></li>
  <li><div data-cy="clock-timelog">icon</div><strong>$60.00 - $80.00</strong></li>
  <li><div data-cy="expertise">icon</div><strong>Expert</strong></li>
  <li><div data-cy="duration2">icon</div><strong>More than 6 months</strong></li>
  <div class="skills-list"><span class="air3-line-clamp">Python</span><span class="air3-line-clamp">Docker</span></div>
  <div data-qa="client-spend">10k total spent</div>
  <div data-qa="client-hires">12 hires</div>
</body>
</html>
"""


class MockTransportAdapter:
    """Mock transport adapter for deterministic pipeline testing."""

    adapter_name: str = "mock"

    def __init__(self, canned_html: str = SAMPLE_SEARCH_PAGE_HTML) -> None:
        self.canned_html = canned_html
        self.fetch_calls: list[FetchRequest] = []
        self.closed: bool = False

    def fetch(self, request: FetchRequest) -> FetchResponse:
        self.fetch_calls.append(request)
        if "/nx/search/" in request.url:
            html = self.canned_html
        elif "/jobs/" in request.url:
            html = SAMPLE_DETAIL_PAGE_HTML
        else:
            html = self.canned_html

        return FetchResponse(
            url=request.url,
            status=200,
            html=html,
            elapsed_seconds=0.01,
            adapter_name=self.adapter_name,
        )

    def close(self) -> None:
        self.closed = True


def test_load_selector_config_valid() -> None:
    config = load_selector_config()
    assert config.site == "upwork"
    assert "search_listings" in config.views
    assert "job_detail" in config.views

    search_fields = config.views["search_listings"].fields
    assert "title" in search_fields
    assert "url" in search_fields
    assert "normalize_job_url" in search_fields["url"].transforms

    detail_fields = config.views["job_detail"].fields
    assert "title" in detail_fields
    assert "description" in detail_fields
    assert "strip_summary_prefix" in detail_fields["description"].transforms


def test_load_all_profile_configs() -> None:
    profiles = [
        "configs/profiles/default_search.yaml",
        "configs/profiles/wordpress_latest_50.yaml",
        "configs/profiles/wordpress_multi_page.yaml",
        "configs/profiles/wordpress_top20_enriched.yaml",
        "configs/profiles/laravel_latest_50.yaml",
        "configs/profiles/laravel_multi_page.yaml",
        "configs/profiles/laravel_top20_enriched.yaml",
        "configs/profiles/dotnet_latest_50.yaml",
        "configs/profiles/dotnet_multi_page.yaml",
        "configs/profiles/dotnet_top20_enriched.yaml",
        "configs/profiles/react_latest_50.yaml",
        "configs/profiles/react_multi_page.yaml",
        "configs/profiles/react_top20_enriched.yaml",
        "configs/profiles/angular_latest_50.yaml",
        "configs/profiles/angular_multi_page.yaml",
        "configs/profiles/angular_top20_enriched.yaml",
        "configs/profiles/authenticated_search.yaml",
    ]
    for p in profiles:
        cfg = load_profile_config(p)
        assert isinstance(cfg, ScrapeProfileConfig)
        assert cfg.name


def test_transport_adapter_instances() -> None:
    fs_cfg = TransportConfig(adapter="flaresolverr", proxy_mode="direct")
    fs_adapter = create_adapter(fs_cfg)
    assert isinstance(fs_adapter, FlareSolverrAdapter)
    assert isinstance(fs_adapter, TransportAdapter)
    fs_adapter.close()

    ss_cfg = TransportConfig(adapter="stealthy_session", proxy_mode="direct")
    ss_adapter = create_adapter(ss_cfg)
    assert isinstance(ss_adapter, StealthySessionAdapter)
    assert isinstance(ss_adapter, TransportAdapter)
    ss_adapter.close()


def test_configurable_dom_parser_search_listings() -> None:
    parser = ConfigurableDomParser()
    jobs = parser.parse_job_listings(SAMPLE_SEARCH_PAGE_HTML, session_id="test_session")

    assert len(jobs) == 2

    job1 = jobs[0]
    assert job1.title == "Python Engineer FastAPI"
    # Highlight span and referrer should be stripped
    assert job1.url == "https://www.upwork.com/jobs/Python-Engineer-FastAPI_~022111887415567641941/"
    assert job1.hourly_rate == "$50.00 - $75.00"
    assert job1.budget is None
    assert job1.experience_level == "Expert"
    assert job1.duration == "3 to 6 months"
    assert job1.skills == ["Python", "FastAPI"]
    assert job1.country == "United States"
    assert job1.client_rating == 4.9

    job2 = jobs[1]
    assert job2.title == "WordPress Elementor Fix"
    assert job2.budget == "$150.00"
    assert job2.hourly_rate is None
    assert job2.experience_level == "Intermediate"
    assert job2.posted == "Posted 1 day ago"


def test_configurable_dom_parser_job_detail() -> None:
    parser = ConfigurableDomParser()
    detail = parser.parse_job_detail(SAMPLE_DETAIL_PAGE_HTML)
    assert detail is not None
    assert detail.title == "Python Engineer FastAPI"
    # Leading "Summary" prefix stripped
    assert detail.description == "We need an expert Python FastAPI developer to architect high-performance microservices."
    assert detail.hourly_rate == "$60.00 - $80.00"
    assert detail.proposals == "Less than 5"
    assert detail.client_spent == "10k"
    assert detail.client_hires == 12
    assert "Python" in detail.skills
    assert "Docker" in detail.skills


def test_configurable_scraper_pipeline_target_jobs(tmp_path: Path) -> None:
    profile = load_profile_config("configs/profiles/wordpress_latest_50.yaml")
    profile.output.directory = str(tmp_path)
    profile.search.target_jobs = 1  # Stop after 1 job
    profile.search.max_pages = 3
    profile.search.delay_between_pages_seconds = 0.0

    mock_adapter = MockTransportAdapter(SAMPLE_SEARCH_PAGE_HTML)
    scraper = ConfigurableScraper(profile, adapter=mock_adapter)

    result = scraper.run()
    assert result.total_found == 1
    assert len(result.jobs) == 1
    # Only 1 page should have been fetched because target_jobs=1 was satisfied on page 1
    assert len(mock_adapter.fetch_calls) == 1
    assert result.output_path is not None
    assert result.output_path.is_file()

    # Verify output can be read by proposal_engine.load_jobs
    loaded = load_jobs(result.output_path)
    assert len(loaded) == 1
    assert loaded[0]["title"] == "Python Engineer FastAPI"


def test_configurable_scraper_pipeline_with_enrichment(tmp_path: Path) -> None:
    profile = load_profile_config("configs/profiles/default_search.yaml")
    profile.output.directory = str(tmp_path)
    profile.search.query = "python & fastapi"
    profile.search.delay_between_pages_seconds = 0.0
    profile.enrichment.enabled = True
    profile.enrichment.max_jobs_to_enrich = 1
    profile.enrichment.detail_retries = 2
    profile.enrichment.delay_between_details_seconds = 0.0

    mock_adapter = MockTransportAdapter(SAMPLE_SEARCH_PAGE_HTML)
    scraper = ConfigurableScraper(profile, adapter=mock_adapter)

    result = scraper.run()
    assert result.total_found == 2
    # Check that URL encoding was used for query
    assert "python+%26+fastapi" in mock_adapter.fetch_calls[0].url

    # Check detail request retries override was passed
    detail_call = next(c for c in mock_adapter.fetch_calls if c.url.startswith("https://www.upwork.com/jobs/"))
    assert detail_call.max_retries == 2

    # First job should have enriched full detail values
    enriched_job = result.jobs[0]
    assert "high-performance microservices" in enriched_job.description
    assert enriched_job.client_spent == "10k"
    assert enriched_job.client_hires == 12

    # Second job should keep search data
    second_job = result.jobs[1]
    assert second_job.client_spent is None


def test_configurable_scraper_from_saved_output(tmp_path: Path) -> None:
    # Seed a saved file with raw list format
    seed_jobs = [
        UpWorkJob(
            title="Senior WordPress Developer",
            url="https://www.upwork.com/jobs/Senior-WordPress-Developer_~011111111111111111111/",
            description="Build custom Gutenberg blocks",
            hourly_rate="$80.00",
            skills=["wordpress", "php", "gutenberg"],
            posted="Posted 2 days ago",
        ),
        UpWorkJob(
            title="Junior WordPress Helper",
            url="https://www.upwork.com/jobs/Junior-WordPress-Helper_~022222222222222222222/",
            description="Install plugins",
            hourly_rate="$15.00",
            skills=["data entry"],
            posted="Posted 1 day ago",
        ),
    ]
    seed_file = tmp_path / "upwork_wordpress_seed.json"
    seed_file.write_text(json.dumps([asdict(j) for j in seed_jobs]))

    profile = load_profile_config("configs/profiles/wordpress_top20_enriched.yaml")
    profile.output.directory = str(tmp_path)
    profile.search.input_saved_file = str(seed_file)
    profile.filters.min_score = 40
    profile.enrichment.enabled = False

    scraper = ConfigurableScraper(profile, adapter=MockTransportAdapter())
    result = scraper.run()

    # The $80.00 job gets >= 40 pts, the $15.00 job does not
    assert result.total_found == 1
    assert result.jobs[0].title == "Senior WordPress Developer"


def test_core_parser_registry_dynamic_population() -> None:
    assert len(CORE_PARSER_REGISTRY) > 0
    search_fields = [r.target_field for r in CORE_PARSER_REGISTRY if r.view == "search_listings"]
    assert "job_cards_container" in search_fields
    assert "title_and_url" in search_fields
    assert "description" in search_fields
    assert "hourly_rate" in search_fields

    fragile_regs = [r for r in CORE_PARSER_REGISTRY if r.is_fragile]
    assert any(r.target_field == "posted" for r in fragile_regs)

    # Check fallbacks are captured
    container_reg = next(r for r in CORE_PARSER_REGISTRY if r.target_field == "job_cards_container")
    assert len(container_reg.fallback_selectors) > 0

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
    SearchWorkflowConfig,
    TransportConfig,
    load_profile_config,
    load_selector_config,
)
from src.main import main
from src.main import parse_args as main_parse_args
from src.models import UpWorkJob
from src.orchestrator import ConfigurableScraper, ScrapeResult
from src.parser import ConfigurableDomParser
from src.proposal_engine import (
    generate_proposal,
    job_meets_proposal_threshold,
    keyword_matches,
    load_jobs,
    match_portfolio_references,
    parse_posted_age,
    parse_proposal_count,
    score_job,
)
from src.proposal_engine import (
    parse_args as pe_parse_args,
)
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
  <li><div data-cy=\"clock-timelog\">icon</div><strong>$60.00 - $80.00</strong></li>
  <li><div data-cy=\"expertise\">icon</div><strong>Expert</strong></li>
  <li><div data-cy=\"duration2\">icon</div><strong>More than 6 months</strong></li>
  <div class=\"skills-list\"><span class=\"air3-line-clamp\">Python</span><span class=\"air3-line-clamp\">Docker</span></div>
  <div data-qa=\"client-spend\">10k total spent</div>
  <div data-qa=\"client-hires\">12 hires</div>
</body>
</html>
"""

SAMPLE_DETAIL_HIGH_PROPOSALS_HTML = """
<!DOCTYPE html>
<html>
<head><title>WordPress Elementor Fix - UpWork</title></head>
<body>
  <h1>WordPress Elementor Fix</h1>
  <div data-test=\"Description\">
    <p class=\"multiline-text\">Summary Fix broken layout on Elementor header.</p>
  </div>
  <ul class=\"visitor client-activity-items list-unstyled\">
    <li class=\"ca-item\">
      <span class=\"title\">Proposals:</span>
      <span class=\"help-icon\"><span data-test=\"popper\">Close the tooltipThis range includes relevant proposals</span></span>
      <span class=\"value\">20 to 50</span>
    </li>
  </ul>
  <li><div data-cy=\"fixed-price\">icon</div><strong>$150.00</strong></li>
  <li><div data-cy=\"expertise\">icon</div><strong>Intermediate</strong></li>
  <div class=\"skills-list\"><span class=\"air3-line-clamp\">WordPress</span></div>
</body>
</html>
"""


class MockTransportAdapter:
    """Mock transport adapter for deterministic pipeline testing."""

    adapter_name: str = "mock"

    def __init__(
        self,
        canned_html: str = SAMPLE_SEARCH_PAGE_HTML,
        detail_map: dict[str, str] | None = None,
    ) -> None:
        self.canned_html = canned_html
        self.detail_map = detail_map or {}
        self.fetch_calls: list[FetchRequest] = []
        self.closed: bool = False

    def fetch(self, request: FetchRequest) -> FetchResponse:
        self.fetch_calls.append(request)
        if "/nx/search/" in request.url:
            html = self.canned_html
        elif "/jobs/" in request.url:
            matched_detail = None
            for key, val in self.detail_map.items():
                if key in request.url:
                    matched_detail = val
                    break
            html = matched_detail if matched_detail is not None else SAMPLE_DETAIL_PAGE_HTML
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
    profile_dir = Path("configs/profiles")
    profile_files = sorted(profile_dir.glob("*.yaml"))
    assert len(profile_files) >= 30
    for p in profile_files:
        cfg = load_profile_config(p)
        assert isinstance(cfg, ScrapeProfileConfig)
        assert cfg.name


def test_search_workflow_effective_queries() -> None:
    cfg1 = SearchWorkflowConfig(query="python developer")
    assert cfg1.effective_queries() == ["python developer"]

    cfg2 = SearchWorkflowConfig(
        query="fallback",
        queries=["python developer", "fastapi", "python developer", "  playwright  ", ""],
    )
    assert cfg2.effective_queries() == ["python developer", "fastapi", "playwright"]


def test_build_search_url_facets() -> None:
    profile = load_profile_config("configs/profiles/default_search.yaml")
    profile.search.query = "python developer"
    profile.search.sort = "recency"
    profile.search.per_page = 50
    profile.search.contractor_tier = [2, 3]
    profile.search.contract_type = "hourly"
    profile.search.proposal_tiers = ["0-4", "5-9"]
    profile.transport.adapter = "flaresolverr"

    scraper_fs = ConfigurableScraper(profile, adapter=MockTransportAdapter())
    url_fs = scraper_fs.build_search_url("python developer", page=2)

    assert "https://www.upwork.com/nx/search/jobs/?q=python+developer" in url_fs
    assert "sort=recency" in url_fs
    assert "per_page=50" in url_fs
    assert "contractor_tier=2%2C3" in url_fs or "contractor_tier=2,3" in url_fs
    assert "t=0" in url_fs
    assert "page=2" in url_fs
    # In flaresolverr adapter, &proposals= must be suppressed to avoid login redirects
    assert "proposals=" not in url_fs

    # With stealthy_session, proposals filter must be included
    profile.transport.adapter = "stealthy_session"
    scraper_ss = ConfigurableScraper(profile, adapter=MockTransportAdapter())
    url_ss = scraper_ss.build_search_url("python developer", page=1)
    assert "proposals=0-4%2C5-9" in url_ss or "proposals=0-4,5-9" in url_ss

    # Fixed price contract type
    profile.search.contract_type = "fixed"
    url_fixed = scraper_ss.build_search_url("python developer", page=1)
    assert "t=1" in url_fixed


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
    assert job1.proposals == "5 to 10"
    assert job1.proposals_count == 10
    assert job1.client_rating == 4.9

    job2 = jobs[1]
    assert job2.title == "WordPress Elementor Fix"
    assert job2.budget == "$150.00"
    assert job2.hourly_rate is None
    assert job2.experience_level == "Intermediate"
    assert job2.posted == "Posted 1 day ago"
    assert job2.proposals is None
    assert job2.proposals_count is None


def test_configurable_dom_parser_job_detail() -> None:
    parser = ConfigurableDomParser()
    detail = parser.parse_job_detail(SAMPLE_DETAIL_PAGE_HTML)
    assert detail is not None
    assert detail.title == "Python Engineer FastAPI"
    # Leading "Summary" prefix stripped
    assert detail.description == "We need an expert Python FastAPI developer to architect high-performance microservices."
    assert detail.hourly_rate == "$60.00 - $80.00"
    assert detail.proposals == "Less than 5"
    assert detail.proposals_count == 4
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


def test_multi_query_search_deduplication(tmp_path: Path) -> None:
    profile = load_profile_config("configs/profiles/default_search.yaml")
    profile.output.directory = str(tmp_path)
    profile.search.queries = ["python", "django"]
    profile.search.max_pages = 1
    profile.search.delay_between_pages_seconds = 0.0

    mock_adapter = MockTransportAdapter(SAMPLE_SEARCH_PAGE_HTML)
    scraper = ConfigurableScraper(profile, adapter=mock_adapter)
    result = scraper.run()

    # Both queries were searched (2 search calls)
    assert len(mock_adapter.fetch_calls) == 2
    assert "q=python" in mock_adapter.fetch_calls[0].url
    assert "q=django" in mock_adapter.fetch_calls[1].url

    # Result has 2 jobs total because duplicates across queries were deduplicated by URL
    assert result.total_found == 2
    assert len(result.jobs) == 2


def test_exclude_keywords_filtering(tmp_path: Path) -> None:
    profile = load_profile_config("configs/profiles/default_search.yaml")
    profile.output.directory = str(tmp_path)
    profile.search.delay_between_pages_seconds = 0.0
    profile.filters.exclude_keywords = ["fastapi", "homework"]

    mock_adapter = MockTransportAdapter(SAMPLE_SEARCH_PAGE_HTML)
    scraper = ConfigurableScraper(profile, adapter=mock_adapter)
    result = scraper.run()

    # Job 1 has FastAPI in title/skills/desc -> excluded
    # Job 2 is WordPress Elementor Fix -> retained
    assert result.total_found == 1
    assert result.jobs[0].title == "WordPress Elementor Fix"


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


def test_parse_proposal_count_and_upper_bound_thresholds() -> None:
    assert parse_proposal_count("Less than 5") == 4
    assert parse_proposal_count("Proposals: Less than 5") == 4
    assert parse_proposal_count("5 to 10") == 10
    assert parse_proposal_count("10 to 15") == 15
    assert parse_proposal_count("15 to 20") == 20
    assert parse_proposal_count("20 to 50") == 50
    assert parse_proposal_count("50+") == 999
    assert parse_proposal_count("12") == 12
    assert parse_proposal_count(None) is None
    assert parse_proposal_count("") is None

    # Upper-bound threshold = 15
    assert job_meets_proposal_threshold("Less than 5", 15) is True
    assert job_meets_proposal_threshold("5 to 10", 15) is True
    assert job_meets_proposal_threshold("10 to 15", 15) is True
    assert job_meets_proposal_threshold("15 to 20", 15) is False
    assert job_meets_proposal_threshold("20 to 50", 15) is False
    assert job_meets_proposal_threshold("50+", 15) is False

    # Upper-bound threshold = 50 includes "20 to 50" but excludes "50+"
    assert job_meets_proposal_threshold("20 to 50", 50) is True
    assert job_meets_proposal_threshold("50+", 50) is False

    # Unknown handling
    assert job_meets_proposal_threshold(None, 15, include_unknown=True) is True
    assert job_meets_proposal_threshold(None, 15, include_unknown=False) is False

    # Score job rewards "Less than 5" (10 pts) and "15 to 20" (7 pts)
    assert score_job({"proposals": "Less than 5"}) == 10
    assert score_job({"proposals": "10 to 15"}) == 10
    assert score_job({"proposals": "15 to 20"}) == 7
    assert score_job({"proposals": "20 to 50"}) == 5
    assert score_job({"proposals": "50+"}) == 2


def test_max_proposals_auto_enrichment_and_filtering(tmp_path: Path) -> None:
    """When max_proposals is set and search cards lack proposals, Option B auto-enables detail enrichment
    and filters out jobs whose detail page exceeds max_proposals."""
    profile = load_profile_config("configs/profiles/default_search.yaml")
    profile.output.directory = str(tmp_path)
    profile.search.delay_between_pages_seconds = 0.0
    profile.enrichment.enabled = False  # Starts disabled!
    profile.enrichment.delay_between_details_seconds = 0.0
    profile.filters.max_proposals = 15

    # In SAMPLE_SEARCH_PAGE_HTML:
    # - Job 1 ("Python Engineer FastAPI") has proposals="5 to 10" on card, detail has "Less than 5"
    # - Job 2 ("WordPress Elementor Fix") has proposals=None on card, detail has "20 to 50"
    mock_adapter = MockTransportAdapter(
        canned_html=SAMPLE_SEARCH_PAGE_HTML,
        detail_map={
            "Python-Engineer-FastAPI": SAMPLE_DETAIL_PAGE_HTML,
            "WordPress-Elementor-Fix": SAMPLE_DETAIL_HIGH_PROPOSALS_HTML,
        },
    )

    scraper = ConfigurableScraper(profile, adapter=mock_adapter)
    result = scraper.run()

    # Auto-enrichment should have fetched detail pages (1 search + 2 detail calls = 3 calls)
    assert len(mock_adapter.fetch_calls) == 3

    # Job 2 ("20 to 50" proposals, upper bound 50 > 15) must be filtered out; Job 1 kept
    assert result.total_found == 1
    assert len(result.jobs) == 1
    assert result.jobs[0].title == "Python Engineer FastAPI"
    assert result.jobs[0].proposals == "Less than 5"
    assert result.jobs[0].proposals_count == 4


def test_cli_max_proposals_flags() -> None:
    main_args = main_parse_args(["--query", "wordpress", "--max-proposals", "15"])
    assert main_args.query == "wordpress"
    assert main_args.max_proposals == 15

    pe_args = pe_parse_args(["--query", "wordpress", "--max-proposals", "10", "--score-only"])
    assert pe_args.query == "wordpress"
    assert pe_args.max_proposals == 10
    assert pe_args.score_only is True


def test_cli_wide_net_flags() -> None:
    args = main_parse_args([
        "--queries", "python scraper,fastapi,playwright",
        "--per-page", "50",
        "--exclude-keywords", "unpaid,homework",
    ])
    assert args.queries == "python scraper,fastapi,playwright"
    assert args.per_page == 50
    assert args.exclude_keywords == "unpaid,homework"


def test_proposal_engine_expanded_stacks() -> None:
    # DevOps job
    devops_job = {
        "title": "Senior AWS Infrastructure & Terraform Engineer",
        "description": "We need someone to automate our AWS ECS clusters with Terraform and setup GitHub Actions.",
        "skills": ["AWS", "Terraform", "Docker", "CI/CD"],
        "hourly_rate": "$85.00/hr",
        "client_spent": "$50K",
    }
    proposal_devops = generate_proposal(devops_job)
    assert "DevOps & Cloud Infrastructure Engineer" in proposal_devops
    assert "Terraform" in proposal_devops

    refs_devops = match_portfolio_references(devops_job)
    assert any("Cloud Infrastructure" in r["title"] for r in refs_devops)

    # AI integration job
    ai_job = {
        "title": "Python AI Agent Developer with Claude and OpenAI",
        "description": "Build an autonomous LLM agent workflow with RAG and LangChain in Python.",
        "skills": ["Python", "OpenAI", "Claude", "RAG"],
        "hourly_rate": "$75.00/hr",
        "client_spent": "$20K",
    }
    proposal_ai = generate_proposal(ai_job)
    assert "AI & LLM Integration Engineer" in proposal_ai
    assert "Claude" in proposal_ai or "LLM" in proposal_ai

    refs_ai = match_portfolio_references(ai_job)
    assert any("AI Workflow Automation" in r["title"] for r in refs_ai)


def test_keyword_matches_boundaries() -> None:
    # Substring false positives avoided
    assert keyword_matches("go", "Go backend developer needed") is True
    assert keyword_matches("go", "Looking for Golang or Go engineers") is True
    assert keyword_matches("go", "Django and PostgreSQL developer") is False
    assert keyword_matches("go", "Good communication skills and Google Cloud experience") is False

    assert keyword_matches("ai", "Building an AI agent") is True
    assert keyword_matches("ai", "Send email and maintain codebase") is False
    assert keyword_matches("ai", "Tailwind CSS styling") is False

    # Punctuation / language symbols
    assert keyword_matches("c#", "Senior C# backend engineer") is True
    assert keyword_matches("c#", "C#/ASP.NET developer") is True
    assert keyword_matches(".net", "Experienced in .NET 8 and C#") is True
    assert keyword_matches(".net", "ASP.NET Core developer") is True
    assert keyword_matches(".net", "Computer networking technician") is False

    assert keyword_matches("ci/cd", "Setup CI/CD pipelines") is True
    assert keyword_matches("next.js", "Build frontend with Next.js") is True


def test_parse_posted_age_units() -> None:
    assert parse_posted_age("Posted 15 minutes ago") == 0
    assert parse_posted_age("Posted 45 mins ago") == 0
    assert parse_posted_age("Just now") == 0
    assert parse_posted_age("Today") == 0
    assert parse_posted_age("Posted 2 hours ago") == 0
    assert parse_posted_age("Posted 23 hours ago") == 0
    assert parse_posted_age("Posted 25 hours ago") == 1
    assert parse_posted_age("Yesterday") == 1
    assert parse_posted_age("Posted 2 days ago") == 2
    assert parse_posted_age("Posted 1 week ago") == 7
    assert parse_posted_age("Posted 2 weeks ago") == 14
    assert parse_posted_age("Posted 1 month ago") == 30
    assert parse_posted_age(None) is None
    assert parse_posted_age("") is None


def test_score_job_fixed_price_budget() -> None:
    # Fixed-price budget scoring tiers (includes +8 default proposals baseline when proposals missing)
    assert score_job({"budget": "$2,500"}) == 28
    assert score_job({"budget": "$1,000"}) == 28
    assert score_job({"budget": "$750"}) == 23
    assert score_job({"budget": "$500"}) == 23
    assert score_job({"budget": "$300"}) == 18
    assert score_job({"budget": "$200"}) == 18
    assert score_job({"budget": "$100"}) == 13
    assert score_job({"budget": "$50"}) == 13
    # Explicit proposals upper bounds
    assert score_job({"budget": "$1,000", "proposals": "Less than 5"}) == 30
    assert score_job({"budget": "$500", "proposals": "15 to 20"}) == 22
    assert score_job({"budget": "$200", "proposals": "50+"}) == 12
    # Hourly rates remain intact
    assert score_job({"hourly_rate": "$80.00/hr"}) == 33
    assert score_job({"hourly_rate": "$100.00/hr"}) == 28
    assert score_job({"hourly_rate": "$30.00/hr"}) == 18


def test_exclude_and_required_keywords_with_skills(tmp_path: Path) -> None:
    profile = load_profile_config("configs/profiles/default_search.yaml")
    profile.output.directory = str(tmp_path)
    profile.search.delay_between_pages_seconds = 0.0

    # Test that required_keywords matches skills
    profile.filters.required_keywords = ["fastapi"]
    scraper = ConfigurableScraper(profile, adapter=MockTransportAdapter(SAMPLE_SEARCH_PAGE_HTML))
    result = scraper.run()
    # Job 1 has FastAPI in skills; Job 2 does not
    assert result.total_found == 1
    assert result.jobs[0].title == "Python Engineer FastAPI"

    # Test that exclude_keywords filters out based on skills
    profile.filters.required_keywords = []
    profile.filters.exclude_keywords = ["wordpress"]
    scraper2 = ConfigurableScraper(profile, adapter=MockTransportAdapter(SAMPLE_SEARCH_PAGE_HTML))
    result2 = scraper2.run()
    # Job 2 has WordPress in skills; Job 1 does not
    assert result2.total_found == 1
    assert result2.jobs[0].title == "Python Engineer FastAPI"


def test_cli_query_override_clears_queries(monkeypatch: object, tmp_path: Path) -> None:
    profile_file = tmp_path / "test_profile.yaml"
    profile_file.write_text(
        "name: test_profile\nsearch:\n  query: legacy_query\n  queries:\n    - python\n    - django\n"
    )
    captured_profile: ScrapeProfileConfig | None = None

    class DummyScraper:
        def __init__(self, profile: ScrapeProfileConfig, **_kwargs: object) -> None:
            nonlocal captured_profile
            captured_profile = profile

        def run(self) -> ScrapeResult:
            return ScrapeResult(query="fastapi", jobs=[], total_found=0, errors=[], output_path=None, elapsed_seconds=0.1)

        def close(self) -> None:
            pass

    monkeypatch.setattr("src.main.ConfigurableScraper", DummyScraper)  # type: ignore[attr-defined]
    ret = main(["--config", str(profile_file), "--query", "fastapi"])
    assert ret == 0
    assert captured_profile is not None
    assert captured_profile.search.query == "fastapi"
    assert captured_profile.search.queries == []


def test_load_jobs_metadata_richness_merge(tmp_path: Path) -> None:
    url = "https://www.upwork.com/jobs/Python-Engineer-FastAPI_~022111887415567641941/"
    unenriched_job = {
        "title": "Python Engineer FastAPI",
        "url": url,
        "description": "Short description",
        "hourly_rate": "$50.00 - $75.00",
    }
    enriched_job = {
        "title": "Python Engineer FastAPI",
        "url": url,
        "description": "We need an expert Python FastAPI developer to architect high-performance microservices.",
        "hourly_rate": "$60.00 - $80.00",
        "proposals": "Less than 5",
        "proposals_count": 4,
        "client_spent": "10k",
        "client_hires": 12,
        "skills": ["Python", "Docker", "FastAPI"],
    }

    file1 = tmp_path / "upwork_search_unenriched.json"
    file1.write_text(json.dumps({"jobs": [unenriched_job], "query": "python"}))

    file2 = tmp_path / "upwork_search_enriched.json"
    file2.write_text(json.dumps({"jobs": [enriched_job], "query": "python"}))

    loaded = load_jobs(tmp_path)
    assert len(loaded) == 1
    # Richer enriched job took precedence
    assert loaded[0]["client_spent"] == "10k"
    assert loaded[0]["proposals_count"] == 4
    assert len(loaded[0]["skills"]) == 3

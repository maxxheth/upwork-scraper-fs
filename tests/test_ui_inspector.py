"""Unit tests for UpWork UI Inspector: DOM Blueprinting, Drift Auditor, and Proxy Pinning."""

from __future__ import annotations

from src.ui_inspector.dom_blueprint import build_page_blueprint
from src.ui_inspector.drift_auditor import DriftAuditor
from src.ui_inspector.models import AttributeHook, UpWorkPageBlueprint
from src.ui_inspector.proxy_pinning import redact_proxy_url, resolve_pinned_proxy

SAMPLE_SEARCH_HTML = """
<!DOCTYPE html>
<html>
<head><title>WordPress Jobs - UpWork</title></head>
<body>
<nav class="air3-nav-freelancer">
    <div data-test="nav-user-menu">User Menu</div>
</nav>
<main>
    <article class="job-tile">
        <a data-test="job-tile-title-link" href="/jobs/~01abc123">Senior WordPress Developer</a>
        <div data-test="JobDescription">
            <p>Looking for a WordPress / ACF expert to optimize performance.</p>
        </div>
        <div data-test="job-type-label">
            <strong>$50 - $75</strong>
        </div>
        <div data-test="experience-level">
            <strong>Expert</strong>
        </div>
        <div data-test="duration-label">1 to 3 months</div>
        <div class="skills-list">
            <button data-test="token"><span>WordPress</span></button>
            <button data-test="token"><span>PHP</span></button>
        </div>
        <small data-test="job-pubilshed-date"><span>Posted 2 hours ago</span></small>
        <!-- Authenticated UI extra fields -->
        <span data-qa="payment-verified">Payment Verified</span>
        <span data-qa="client-rating">4.9 of 5 stars</span>
        <span data-test="proposals-tier"><strong>5 to 10</strong></span>
    </article>
</main>
</body>
</html>
"""

SAMPLE_MUTATED_HTML = """
<!DOCTYPE html>
<html>
<head><title>WordPress Jobs - UpWork</title></head>
<body>
<main>
    <article class="job-tile">
        <a data-test="job-tile-title-link" href="/jobs/~01abc123">Senior WordPress Developer</a>
        <!-- UpWork fixed the typo from job-pubilshed-date to job-published-date -->
        <small data-test="job-published-date"><span>Posted 2 hours ago</span></small>
    </article>
</main>
</body>
</html>
"""

SAMPLE_JOB_DETAIL_HTML = """
<!DOCTYPE html>
<html>
<head><title>Job Details - Senior WordPress Engineer</title></head>
<body>
<main>
    <h1>Senior WordPress Engineer</h1>
    <div data-test="Description">
        <p class="multiline-text">We need a developer to refactor our WooCommerce checkout.</p>
    </div>
    <div class="posted-on-line"><span>Posted 1 day ago</span></div>
    <ul>
        <li>
            <div data-cy="clock-timelog"></div>
            <div><strong>$45</strong> - <strong>$65</strong></div>
        </li>
        <li>
            <div data-cy="expertise"></div>
            <strong>Intermediate</strong>
        </li>
        <li>
            <div data-cy="duration2"></div>
            <strong>Less than 1 month</strong>
        </li>
        <li>
            <div data-cy="clock-hourly"></div>
            <strong>30+ hrs/week</strong>
        </li>
    </ul>
    <section data-v-3b2c2248>
        <div class="skills-list">
            <div class="air3-line-clamp">WordPress</div>
            <div class="air3-line-clamp">WooCommerce</div>
        </div>
    </section>
    <ul>
        <li class="ca-item">
            <span class="title">Proposals:</span>
            <span class="help-icon"><span data-test="popper">Close the tooltipThis range includes relevant proposals</span></span>
            <span class="value">10 to 15</span>
        </li>
    </ul>
    <li data-qa="client-location">United States</li>
    <strong data-qa="client-spend">$25.5K total spent</strong>
    <div data-qa="client-hires">14 hires</div>
</main>
</body>
</html>
"""


def test_build_page_blueprint_search() -> None:
    blueprint = build_page_blueprint(
        html_content=SAMPLE_SEARCH_HTML,
        url="https://www.upwork.com/nx/search/jobs/?q=wordpress",
        title="WordPress Jobs - UpWork",
        is_authenticated=True,
    )

    assert blueprint.view_type == "search_results"
    assert blueprint.is_authenticated is True
    assert blueprint.job_card_blueprint is not None
    assert blueprint.job_card_blueprint.total_cards_detected == 1
    assert blueprint.job_card_blueprint.sample_card_data.get("title") == "Senior WordPress Developer"
    assert blueprint.job_card_blueprint.sample_card_data.get("proposals") == "5 to 10"

    hook_names = [h.name for h in blueprint.all_hooks]
    assert "job-tile-title-link" in hook_names
    assert "JobDescription" in hook_names
    assert "job-pubilshed-date" in hook_names
    assert "payment-verified" in hook_names


def test_drift_auditor_healthy_and_fragile() -> None:
    blueprint = build_page_blueprint(
        html_content=SAMPLE_SEARCH_HTML,
        url="https://www.upwork.com/nx/search/jobs/?q=wordpress",
        is_authenticated=True,
    )
    auditor = DriftAuditor(blueprint, SAMPLE_SEARCH_HTML)
    report = auditor.audit()

    fragile_fields = [a.target_field for a in report.audits if a.status == "FRAGILE"]
    assert "posted" in fragile_fields

    healthy_fields = [a.target_field for a in report.audits if a.status == "HEALTHY"]
    assert "title_and_url" in healthy_fields
    assert "description" in healthy_fields
    assert "hourly_rate" in healthy_fields
    assert "proposals" in healthy_fields

    proposals_audit = next(a for a in report.audits if a.target_field == "proposals")
    assert proposals_audit.sample_extracted_value == "5 to 10"

    candidate_names = [c.hook_name for c in report.discovered_candidates]
    assert "payment-verified" in candidate_names or "client-rating" in candidate_names


def test_drift_auditor_detects_broken_typo_fix() -> None:
    blueprint = build_page_blueprint(
        html_content=SAMPLE_MUTATED_HTML,
        url="https://www.upwork.com/nx/search/jobs/?q=wordpress",
        is_authenticated=False,
    )
    auditor = DriftAuditor(blueprint, SAMPLE_MUTATED_HTML)
    report = auditor.audit()

    posted_audit = next(a for a in report.audits if a.target_field == "posted")
    assert posted_audit.status == "BROKEN"
    assert posted_audit.suggested_replacement is not None
    assert "job-published-date" in posted_audit.suggested_replacement


def test_job_detail_blueprint_and_sibling_resolution() -> None:
    blueprint = build_page_blueprint(
        html_content=SAMPLE_JOB_DETAIL_HTML,
        url="https://www.upwork.com/jobs/~01def456",
        title="Job Details - Senior WordPress Engineer",
        is_authenticated=True,
    )

    assert blueprint.view_type == "job_detail"
    auditor = DriftAuditor(blueprint, SAMPLE_JOB_DETAIL_HTML)
    report = auditor.audit()

    # Rate should be extracted via sibling child resolution
    rate_audit = next(a for a in report.audits if a.target_field == "hourly_rate")
    assert rate_audit.status == "HEALTHY"
    assert "$45 - $65" in str(rate_audit.sample_extracted_value)

    # Proposals should be extracted cleanly via ca_item_value without tooltip text
    proposals_audit = next(a for a in report.audits if a.target_field == "proposals")
    assert proposals_audit.status == "HEALTHY"
    assert proposals_audit.sample_extracted_value == "10 to 15"

    # Skills should be flagged as FRAGILE because of data-v-3b2c2248
    skills_audit = next(a for a in report.audits if a.target_field == "skills")
    assert skills_audit.status == "FRAGILE"
    assert isinstance(skills_audit.sample_extracted_value, list)
    assert "WordPress" in skills_audit.sample_extracted_value


def test_baseline_diff_detection() -> None:
    # Baseline has old hooks with frequency 5
    baseline = UpWorkPageBlueprint(
        view_type="search_results",
        url="https://www.upwork.com/nx/search/jobs",
        title="Baseline",
        timestamp="2026-10-01T00:00:00Z",
        all_hooks=[
            AttributeHook(hook_type="data-test", name="old-job-badge", tag="span", frequency=5),
            AttributeHook(hook_type="data-test", name="shared-hook", tag="div", frequency=10),
        ],
    )

    # Current has dropped frequency on shared-hook (10 -> 2) and removed old-job-badge
    current = UpWorkPageBlueprint(
        view_type="search_results",
        url="https://www.upwork.com/nx/search/jobs",
        title="Current",
        timestamp="2026-10-19T00:00:00Z",
        all_hooks=[
            AttributeHook(hook_type="data-test", name="shared-hook", tag="div", frequency=2),
            AttributeHook(hook_type="data-test", name="brand-new-hook", tag="div", frequency=3),
        ],
    )

    auditor = DriftAuditor(current, "<div></div>", baseline_blueprint=baseline)
    report = auditor.audit()

    removed = [d for d in report.baseline_diffs if d.change_type == "REMOVED"]
    dropped = [d for d in report.baseline_diffs if d.change_type == "FREQUENCY_DROPPED"]
    added = [d for d in report.baseline_diffs if d.change_type == "ADDED"]

    assert any(r.hook_name == "old-job-badge" for r in removed)
    assert any(dr.hook_name == "shared-hook" for dr in dropped)
    assert any(a.hook_name == "brand-new-hook" for a in added)


def test_proxy_pinning_redaction() -> None:
    raw_url = "http://user99:supersecret123@isp.decodo.com:10001"
    redacted = redact_proxy_url(raw_url)
    assert "supersecret123" not in redacted
    assert "user99:***@isp.decodo.com:10001" in redacted

    direct_cfg = resolve_pinned_proxy(direct=True)
    assert not direct_cfg.has_proxy
    assert direct_cfg.get_display_summary() == "Direct (No Proxy)"


def test_normalize_job_url_strips_highlight_spans_and_referrer() -> None:
    from src.parser import normalize_job_url

    dirty = (
        "/jobs/Cloudflare-Pages-Developer-Move-Website-Assets-Off-"
        "span-class-highlight-WordPress-span-amp-Host-New-Static-Site-Fixed-Price_"
        "~022112225892746435112/?referrer_url_path=/nx/search/jobs/"
    )
    cleaned = normalize_job_url(dirty)
    assert cleaned == (
        "https://www.upwork.com/jobs/Cloudflare-Pages-Developer-Move-Website-Assets-Off-"
        "WordPress-Host-New-Static-Site-Fixed-Price_~022112225892746435112/"
    )
    assert "span-class-highlight" not in cleaned
    assert "referrer_url_path" not in cleaned


def test_parse_job_detail_rejects_404_and_not_found_pages() -> None:
    from src.parser import is_job_not_found_html, parse_job_detail

    html_404_heading = """
    <!DOCTYPE html>
    <html>
    <head><title>Job Not Found - Upwork</title></head>
    <body><main><h1>This job is no longer available</h1></main></body>
    </html>
    """
    assert is_job_not_found_html(html_404_heading) is True
    assert parse_job_detail(html_404_heading) is None

    # Generic UpWork 404 shell without job signals
    html_404_shell = """
    <!DOCTYPE html>
    <html>
    <head><title>Upwork</title></head>
    <body><main><h1>Find the best freelance jobs</h1></main></body>
    </html>
    """
    assert parse_job_detail(html_404_shell) is None

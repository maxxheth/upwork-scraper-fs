"""UpWork job listing parser using Scrapling.

Takes rendered HTML from FlareSolverr / Scrapling and extracts structured job data
using Scrapling's CSS selector engine.

NOTE: Scrapling's `.text` returns a `TextHandler` object, not a string.
Use `.text.strip` (method) to get the stripped text content.
"""

from __future__ import annotations

import logging
import re
from contextlib import suppress

from scrapling import Selector

from src.models import UpWorkJob

logger = logging.getLogger(__name__)

# Patterns indicating a 404, expired, or private UpWork job page
NOT_FOUND_HEADINGS: tuple[str, ...] = (
    "job not found",
    "this job is no longer available",
    "this job is private",
    "page not found",
    "we can't find the page",
    "access denied",
)


def _text(el: Selector) -> str:
    """Safely get stripped text from a Scrapling element."""
    return el.text.strip()


def _full_text(el: Selector) -> str:
    """Get full text including child elements, with whitespace normalized."""
    return re.sub(r"\s+", " ", el.get_all_text().strip())


def normalize_job_url(href_or_url: str) -> str:
    """Sanitize UpWork job URLs by stripping leaked search-highlight span tokens and referrer params.

    UpWork's Nuxt search page injects `span-class-highlight-...-span` into the URL slug
    when search keywords match the title, and appends `?referrer_url_path=/nx/search/jobs/`.
    """
    if not href_or_url:
        return ""

    url = f"https://www.upwork.com{href_or_url}" if href_or_url.startswith("/") else href_or_url

    # Strip ?referrer_url_path=... query string
    if "?referrer_url_path=" in url:
        url = url.split("?referrer_url_path=")[0]

    # Strip leaked `span-class-highlight-<word>-span` tokens from the URL slug while keeping `<word>`
    url = re.sub(r"span-class-highlight-([A-Za-z0-9_-]+?)-span", r"\1", url)
    # Clean up any residual `-amp-` HTML entity artifacts in slugs
    url = re.sub(r"-amp-", "-", url)
    # Collapse multiple consecutive hyphens inside the slug (before `_~`)
    if "_~" in url:
        prefix, job_id_part = url.split("_~", 1)
        prefix = re.sub(r"-{2,}", "-", prefix)
        url = f"{prefix}_~{job_id_part}"

    return url


def is_job_not_found_html(html: str) -> bool:
    """Detect whether an UpWork detail page HTML represents a 404 / 'Job not found' / private job."""
    if not html or not html.strip():
        return True

    sel = Selector(html)
    title_el = sel.css("title")
    page_title = _full_text(title_el[0]).lower() if title_el else ""
    if any(phrase in page_title for phrase in NOT_FOUND_HEADINGS):
        return True

    for h_el in sel.css("h1, h2, [data-test='error-title'], .air3-alert"):
        h_text = _full_text(h_el).lower()
        if any(phrase in h_text for phrase in NOT_FOUND_HEADINGS):
            return True

    return False


def _extract_sibling_text(
    sel: Selector,
    data_cy: str,
    child_tag: str,
    join_with: str | None = None,
) -> str | None:
    """Extract text from sibling elements of a data-cy icon.

    Pattern: <li><div data-cy="...">icon</div><strong>value</strong></li>
    """
    icon = sel.css(f"[data-cy='{data_cy}']")
    if not icon:
        return None
    parent = icon[0].parent
    if not parent:
        return None
    values = parent.css(child_tag)
    if not values:
        return None
    texts = [_text(v) for v in values if _text(v)]
    if not texts:
        return None
    if join_with and len(texts) > 1:
        return join_with.join(texts)
    return texts[0]


def parse_job_listings(html: str, session_id: str | None = None) -> list[UpWorkJob]:
    """Parse UpWork job listings from rendered HTML.

    Args:
        html: Fully rendered HTML from Scrapling / FlareSolverr.
        session_id: Optional session ID for provenance.

    Returns:
        List of parsed UpWorkJob objects.
    """
    sel = Selector(html)
    jobs: list[UpWorkJob] = []

    # UpWork's job card container on the /nx/search/jobs/ and find-work pages
    job_cards = sel.css("article.job-tile, article[data-test*='JobTile']")

    if not job_cards:
        logger.warning("No job cards found in HTML — page structure may have changed")
        return []

    for card in job_cards:
        try:
            job = _parse_single_job(card, session_id)
            if job:
                jobs.append(job)
        except Exception:
            logger.warning("Failed to parse job card", exc_info=True)
            continue

    return jobs


def _parse_single_job(
    card: Selector, session_id: str | None = None
) -> UpWorkJob | None:
    """Parse a single job card element."""
    # Title and URL
    title_el = card.css("a[data-test*='job-tile-title-link']")
    if not title_el:
        return None

    title = _full_text(title_el[0])
    href = title_el[0].attrib.get("href", "")
    url = normalize_job_url(href)

    # Description snippet
    desc_el = card.css("[data-test*='JobDescription'] p")
    if not desc_el:
        # Fallback to direct container text if <p> is absent
        desc_el = card.css("[data-test*='JobDescription']")
    description = _text(desc_el[0]) if desc_el else ""

    # Hourly rate vs Fixed price budget
    # UpWork separates fixed price budget into [data-test='is-fixed-price'] (e.g. "Est. budget:$250.00")
    # and hourly rate into [data-test='job-type-label'] (e.g. "Hourly: $20.00 - $40.00")
    hourly_rate: str | None = None
    budget: str | None = None

    fixed_price_el = card.css("[data-test='is-fixed-price']")
    if fixed_price_el:
        budget_raw = _text(fixed_price_el[0])
        # Clean "Est. budget:$250.00" -> "$250.00"
        budget = budget_raw.replace("Est. budget:", "").strip()

    rate_el = card.css("[data-test='job-type-label']")
    if rate_el:
        rate_raw = _text(rate_el[0])
        if "Hourly" in rate_raw:
            strong_el = rate_el[0].css("strong")
            hourly_rate = _text(strong_el[0]) if strong_el else rate_raw.replace("Hourly:", "").strip()
        elif "Fixed" in rate_raw and not budget:
            budget = "Fixed price"

    # Experience level
    exp_el = card.css("[data-test='experience-level'] strong")
    if not exp_el:
        exp_el = card.css("[data-test='experience-level']")
    experience_level = _text(exp_el[0]) if exp_el else None

    # Duration & Hours per week (e.g. "Est. time:3 to 6 months, Less than 30 hrs/week")
    dur_el = card.css("[data-test='duration-label']")
    duration = None
    if dur_el:
        dur_raw = _text(dur_el[0])
        duration = dur_raw.replace("Est. time:", "").strip()

    # Skills / tags — in <span> inside <button data-test="token"> or .air3-token
    skill_els = card.css("[data-test='token'] span, .air3-token span")
    skills = [_text(s) for s in skill_els if s.text.strip()]

    # Posted time — checks both the legacy typo "job-pubilshed-date" and the corrected "job-published-date"
    posted_el = card.css("[data-test='job-pubilshed-date'] span, [data-test='job-published-date'] span")
    posted = _text(posted_el[0]) if posted_el else None

    # Country & Client info (available on authenticated views)
    country_el = card.css("[data-qa='client-location'], [data-test='client-country']")
    country = _text(country_el[0]) if country_el else None

    proposals_el = card.css("[data-test='proposals-tier'], [data-test='proposals']")
    proposals = _text(proposals_el[0]) if proposals_el else None

    rating_el = card.css("[data-qa='client-rating'], [data-test='client-rating']")
    client_rating = None
    if rating_el:
        with suppress(ValueError, IndexError):
            client_rating = float(_text(rating_el[0]).split()[0])

    return UpWorkJob(
        title=title,
        url=url,
        description=description,
        budget=budget,
        experience_level=experience_level,
        duration=duration,
        hourly_rate=hourly_rate,
        skills=skills,
        posted=posted,
        country=country,
        proposals=proposals,
        client_rating=client_rating,
        session_id=session_id,
    )


def parse_job_detail(html: str, session_id: str | None = None) -> UpWorkJob | None:
    """Parse a full UpWork job detail page.

    Extracts the full description, all skills (mandatory + nice-to-have),
    client info, proposals, and other details not available on the search page.

    Args:
        html: Fully rendered HTML from FlareSolverr / Scrapling.
        session_id: Optional session ID for provenance.

    Returns:
        UpWorkJob with full description, or None if parsing fails or job is not found.
    """
    if is_job_not_found_html(html):
        logger.warning("Job detail page returned 'Job not found' or unavailable state")
        return None

    sel = Selector(html)

    # Title
    title_el = sel.css("h1, .air3-card-section h4")
    if not title_el:
        return None
    title = _full_text(title_el[0])
    if any(phrase in title.lower() for phrase in NOT_FOUND_HEADINGS):
        return None

    # Full description — strip leading "Summary" header if concatenated by public visitor view
    desc_el = sel.css("[data-test='Description'] p.multiline-text")
    if not desc_el:
        desc_el = sel.css("[data-test='Description']")
    description = _full_text(desc_el[0]) if desc_el else ""
    if description.startswith("Summary") and len(description) > 7 and description[7].isupper():
        description = description[7:].strip()

    # Reject if neither a description nor job metadata exists (e.g. generic UpWork 404 landing shell)
    has_job_signals = bool(
        description
        or sel.css("[data-cy='clock-timelog'], [data-cy='fixed-price'], [data-cy='expertise'], [data-qa='client-location']")
    )
    if not has_job_signals:
        logger.warning("No job description or metadata signals found on detail page (title=%r)", title)
        return None

    # Posted time
    posted_el = sel.css(".posted-on-line span, [data-test='posted-on']")
    posted = _text(posted_el[0]) if posted_el else None

    # Hourly rate vs Fixed price budget on detail page
    hourly_rate = _extract_sibling_text(sel, "clock-timelog", "strong", join_with=" - ")
    budget = _extract_sibling_text(sel, "fixed-price", "strong")

    # Experience level
    experience_level = _extract_sibling_text(sel, "expertise", "strong")

    # Duration
    duration = _extract_sibling_text(sel, "duration2", "strong")

    # Hours per week
    _hours_per_week = _extract_sibling_text(sel, "clock-hourly", "strong")

    # Skills — handles generic .skills-list, air3-badge, and scoped sections
    skills: list[str] = []
    skill_items = sel.css(
        ".skills-list .air3-line-clamp, [data-test='Skill'] span, .air3-badge-highlight .air3-line-clamp, section[data-v-3b2c2248] .skills-list .air3-line-clamp"
    )
    for s in skill_items:
        text = s.text.strip()
        if text and text not in skills:
            skills.append(text)

    # Proposals
    proposals = None
    for li in sel.css("li.ca-item"):
        title_span = li.css("span.title")
        if title_span and "Proposals" in _text(title_span[0]):
            value_span = li.css("span.value")
            if value_span:
                proposals = _text(value_span[0])
            break

    # Client info
    client_rating = None
    client_reviews = None
    client_hires = None
    client_spent = None
    country = None

    # Client rating (e.g. "Rating is 4.9 out of 5.")
    rating_el = sel.css(".air3-rating-background, [data-qa='client-rating']")
    if rating_el:
        rating_text = _full_text(rating_el[0])
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:out of|of)\s*5", rating_text)
        if m:
            with suppress(ValueError):
                client_rating = float(m.group(1))

    # Client country
    country_el = sel.css("li[data-qa='client-location'], [data-test='client-country']")
    if country_el:
        country = _text(country_el[0])

    # Client spend
    spend_el = sel.css("[data-qa='client-spend'], [data-test='client-spend']")
    if spend_el:
        spend_text = _full_text(spend_el[0])
        if spend_text:
            client_spent = spend_text.split(" total")[0] if " total" in spend_text else spend_text

        hires_el = sel.css("[data-qa='client-hires'], [data-test='client-hires']")
        if hires_el:
            hires_text = _text(hires_el[0])
            if hires_text:
                with suppress(ValueError, IndexError):
                    client_hires = int(hires_text.split()[0])

    return UpWorkJob(
        title=title,
        url="",
        description=description,
        budget=budget,
        experience_level=experience_level,
        duration=duration,
        hourly_rate=hourly_rate,
        skills=skills,
        posted=posted,
        country=country,
        proposals=proposals,
        client_rating=client_rating,
        client_reviews=client_reviews,
        client_hires=client_hires,
        client_spent=client_spent,
        session_id=session_id,
    )

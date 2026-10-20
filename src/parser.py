"""UpWork job listing and detail parser driven by declarative YAML selector contracts.

Takes rendered HTML from FlareSolverr / Scrapling and extracts structured job data
using Scrapling's CSS selector engine guided by configs/selectors/upwork.yaml.

NOTE: Scrapling's `.text` returns a `TextHandler` object, not a string.
Use `.text.strip` (method) to get stripped text content.
"""

from __future__ import annotations

import logging
import re
from contextlib import suppress
from pathlib import Path
from typing import Any

from scrapling import Selector

from src.config_schema import (
    FieldSelectorRule,
    UpWorkSelectorConfig,
    load_selector_config,
)
from src.models import UpWorkJob

logger = logging.getLogger(__name__)

# Default fallback headings if selector config is not yet initialized
DEFAULT_NOT_FOUND_HEADINGS: tuple[str, ...] = (
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

    # Strip any query string (e.g. ?referrer_url_path=..., ?source=...)
    if "?" in url:
        url = url.split("?", 1)[0]

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


def is_job_not_found_html(
    html: str,
    selector_config: UpWorkSelectorConfig | None = None,
) -> bool:
    """Detect whether an UpWork detail page HTML represents a 404 / 'Job not found' / private job."""
    if not html or not html.strip():
        return True

    cfg = selector_config or _get_default_config()
    headings = tuple(h.lower() for h in cfg.page_guards.not_found_headings)

    sel = Selector(html)
    title_el = sel.css("title")
    page_title = _full_text(title_el[0]).lower() if title_el else ""
    if any(phrase in page_title for phrase in headings):
        return True

    css_error_selectors = ", ".join(cfg.page_guards.error_heading_selectors)
    for h_el in sel.css(css_error_selectors):
        h_text = _full_text(h_el).lower()
        if any(phrase in h_text for phrase in headings):
            return True

    return False


class ConfigurableDomParser:
    """Extracts UpWork job models guided by declarative YAML selector rules."""

    def __init__(
        self,
        config: UpWorkSelectorConfig | None = None,
        config_path: str | Path | None = None,
    ) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = load_selector_config(config_path)

    def extract_field(
        self,
        root: Selector,
        rule: FieldSelectorRule,
    ) -> Any:
        """Extract a single field according to rule definitions and transforms."""
        # Find first matching selector in fallback chain
        matched_elements: list[Selector] = []
        for selector in rule.selectors:
            elements = root.css(selector)
            if elements:
                matched_elements = elements
                break

        if not matched_elements:
            return None

        # Mode-based extraction
        raw_val: Any = None
        if rule.extract == "text":
            raw_val = _text(matched_elements[0])
        elif rule.extract == "full_text":
            raw_val = _full_text(matched_elements[0])
        elif rule.extract == "attribute":
            attr = rule.attribute or "href"
            raw_val = matched_elements[0].attrib.get(attr, "")
        elif rule.extract == "list":
            raw_val = [_text(el) for el in matched_elements if _text(el)]
        elif rule.extract == "sibling_text":
            icon_el = matched_elements[0]
            parent = icon_el.parent
            if parent and rule.sibling_child_tag:
                siblings = parent.css(rule.sibling_child_tag)
                texts = [_text(s) for s in siblings if _text(s)]
                if texts:
                    joiner = rule.join_with or " "
                    raw_val = joiner.join(texts)
        elif rule.extract == "hourly_or_fixed_label":
            rate_raw = _full_text(matched_elements[0])
            if "Hourly" in rate_raw:
                strong_el = matched_elements[0].css("strong")
                raw_val = (
                    _full_text(strong_el[0])
                    if strong_el
                    else re.sub(r"^Hourly:\s*", "", rate_raw, flags=re.IGNORECASE).strip()
                )
            elif "Fixed" in rate_raw:
                raw_val = "Fixed price"
            else:
                raw_val = rate_raw
        elif rule.extract == "ca_item_value":
            # Detail page activity list item (e.g. Proposals)
            for li in matched_elements:
                title_span = li.css("span.title")
                label_req = rule.label_contains or ""
                if title_span and label_req in _text(title_span[0]):
                    val_span = li.css("span.value")
                    if val_span:
                        raw_val = _text(val_span[0])
                        break

        if raw_val is None:
            return None

        # Apply transforms sequentially
        return self._apply_transforms(raw_val, rule.transforms)

    def _apply_transforms(self, val: Any, transforms: list[str]) -> Any:
        """Apply named data transforms."""
        result = val
        for tr in transforms:
            if tr == "normalize_job_url" and isinstance(result, str):
                result = normalize_job_url(result)
            elif tr == "strip_est_budget_prefix" and isinstance(result, str):
                result = re.sub(r"^Est\.\s*budget:\s*", "", result, flags=re.IGNORECASE).strip()
            elif tr == "strip_est_time_prefix" and isinstance(result, str):
                result = result.replace("Est. time:", "").strip()
            elif tr == "strip_summary_prefix" and isinstance(result, str):
                result = re.sub(r"^Summary\s*", "", result)
            elif tr == "strip_total_suffix" and isinstance(result, str):
                result = result.split(" total")[0] if " total" in result else result
            elif tr == "first_token_float" and isinstance(result, str):
                with suppress(ValueError, IndexError):
                    result = float(result.split()[0])
            elif tr == "first_token_int" and isinstance(result, str):
                with suppress(ValueError, IndexError):
                    result = int(result.split()[0])
            elif tr == "rating_out_of_5_float" and isinstance(result, str):
                m = re.search(r"(\d+(?:\.\d+)?)\s*(?:out of|of)\s*5", result)
                if m:
                    with suppress(ValueError):
                        result = float(m.group(1))
        return result

    def parse_job_listings(
        self,
        html: str,
        session_id: str | None = None,
    ) -> list[UpWorkJob]:
        """Parse search listings page into UpWorkJob objects."""
        sel = Selector(html)
        view_cfg = self.config.views.get("search_listings")
        if not view_cfg:
            logger.warning("No search_listings view config defined")
            return []

        # Find job card containers
        job_cards: list[Selector] = []
        for container_sel in view_cfg.container_selectors:
            cards = sel.css(container_sel)
            if cards:
                job_cards = cards
                break

        if not job_cards:
            logger.warning("No job cards found in HTML — page structure may have changed")
            return []

        jobs: list[UpWorkJob] = []
        fields = view_cfg.fields

        for card in job_cards:
            try:
                # Required title & URL
                title_rule = fields.get("title")
                url_rule = fields.get("url")

                title = self.extract_field(card, title_rule) if title_rule else None
                url = self.extract_field(card, url_rule) if url_rule else ""

                if not title:
                    continue

                desc_rule = fields.get("description")
                description = self.extract_field(card, desc_rule) if desc_rule else ""

                budget_rule = fields.get("budget")
                budget = self.extract_field(card, budget_rule) if budget_rule else None

                hourly_rule = fields.get("hourly_rate")
                hourly_rate = self.extract_field(card, hourly_rule) if hourly_rule else None
                if hourly_rate == "Fixed price" and not budget:
                    budget = "Fixed price"
                    hourly_rate = None

                exp_rule = fields.get("experience_level")
                experience_level = self.extract_field(card, exp_rule) if exp_rule else None

                dur_rule = fields.get("duration")
                duration = self.extract_field(card, dur_rule) if dur_rule else None

                skills_rule = fields.get("skills")
                skills = self.extract_field(card, skills_rule) if skills_rule else []

                posted_rule = fields.get("posted")
                posted = self.extract_field(card, posted_rule) if posted_rule else None

                country_rule = fields.get("country")
                country = self.extract_field(card, country_rule) if country_rule else None

                proposals_rule = fields.get("proposals")
                proposals = self.extract_field(card, proposals_rule) if proposals_rule else None

                rating_rule = fields.get("client_rating")
                client_rating = self.extract_field(card, rating_rule) if rating_rule else None
                if not isinstance(client_rating, (int, float)):
                    client_rating = None

                jobs.append(
                    UpWorkJob(
                        title=str(title),
                        url=str(url),
                        description=str(description or ""),
                        budget=budget if isinstance(budget, str) else None,
                        experience_level=experience_level if isinstance(experience_level, str) else None,
                        duration=duration if isinstance(duration, str) else None,
                        hourly_rate=hourly_rate if isinstance(hourly_rate, str) else None,
                        skills=skills if isinstance(skills, list) else [],
                        posted=posted if isinstance(posted, str) else None,
                        country=country if isinstance(country, str) else None,
                        proposals=proposals if isinstance(proposals, str) else None,
                        client_rating=float(client_rating) if client_rating is not None else None,
                        session_id=session_id,
                    )
                )
            except Exception:
                logger.warning("Failed to parse job card", exc_info=True)
                continue

        return jobs

    def parse_job_detail(
        self,
        html: str,
        session_id: str | None = None,
    ) -> UpWorkJob | None:
        """Parse full job detail page into an UpWorkJob object."""
        if is_job_not_found_html(html, self.config):
            logger.warning("Job detail page returned 'Job not found' or unavailable state")
            return None

        sel = Selector(html)
        view_cfg = self.config.views.get("job_detail")
        if not view_cfg:
            logger.warning("No job_detail view config defined")
            return None

        fields = view_cfg.fields

        # Title
        title_rule = fields.get("title")
        title = self.extract_field(sel, title_rule) if title_rule else None
        if not title:
            return None

        headings = tuple(h.lower() for h in self.config.page_guards.not_found_headings)
        if any(phrase in str(title).lower() for phrase in headings):
            return None

        # Full description
        desc_rule = fields.get("description")
        description = self.extract_field(sel, desc_rule) if desc_rule else ""

        # Validate job content signals
        signal_selectors = ", ".join(self.config.page_guards.detail_signal_selectors)
        has_signals = bool(description or sel.css(signal_selectors))
        if not has_signals:
            logger.warning("No job description or metadata signals found on detail page (title=%r)", title)
            return None

        # Posted
        posted_rule = fields.get("posted")
        posted = self.extract_field(sel, posted_rule) if posted_rule else None

        # Hourly rate & Budget
        hourly_rule = fields.get("hourly_rate")
        hourly_rate = self.extract_field(sel, hourly_rule) if hourly_rule else None

        budget_rule = fields.get("budget")
        budget = self.extract_field(sel, budget_rule) if budget_rule else None

        # Experience & Duration
        exp_rule = fields.get("experience_level")
        experience_level = self.extract_field(sel, exp_rule) if exp_rule else None

        dur_rule = fields.get("duration")
        duration = self.extract_field(sel, dur_rule) if dur_rule else None

        # Skills
        skills_rule = fields.get("skills")
        skills_raw = self.extract_field(sel, skills_rule) if skills_rule else []
        skills: list[str] = []
        if isinstance(skills_raw, list):
            for s in skills_raw:
                if s and s not in skills:
                    skills.append(s)

        # Proposals
        proposals_rule = fields.get("proposals")
        proposals = self.extract_field(sel, proposals_rule) if proposals_rule else None

        # Client info
        rating_rule = fields.get("client_rating")
        client_rating = self.extract_field(sel, rating_rule) if rating_rule else None
        if not isinstance(client_rating, (int, float)):
            client_rating = None

        country_rule = fields.get("country")
        country = self.extract_field(sel, country_rule) if country_rule else None

        spent_rule = fields.get("client_spent")
        client_spent = self.extract_field(sel, spent_rule) if spent_rule else None

        hires_rule = fields.get("client_hires")
        client_hires = self.extract_field(sel, hires_rule) if hires_rule else None
        if not isinstance(client_hires, int):
            client_hires = None

        return UpWorkJob(
            title=str(title),
            url="",
            description=str(description or ""),
            budget=str(budget) if budget else None,
            experience_level=str(experience_level) if experience_level else None,
            duration=str(duration) if duration else None,
            hourly_rate=str(hourly_rate) if hourly_rate else None,
            skills=skills,
            posted=str(posted) if posted else None,
            country=str(country) if country else None,
            proposals=str(proposals) if proposals else None,
            client_rating=float(client_rating) if client_rating is not None else None,
            client_hires=client_hires,
            client_spent=str(client_spent) if client_spent else None,
            session_id=session_id,
        )


# Cached singleton parser for standard calls
_default_parser_instance: ConfigurableDomParser | None = None


def _get_default_parser() -> ConfigurableDomParser:
    global _default_parser_instance
    if _default_parser_instance is None:
        _default_parser_instance = ConfigurableDomParser()
    return _default_parser_instance


def _get_default_config() -> UpWorkSelectorConfig:
    return _get_default_parser().config


def parse_job_listings(html: str, session_id: str | None = None) -> list[UpWorkJob]:
    """Parse UpWork job listings from rendered HTML (delegates to ConfigurableDomParser)."""
    return _get_default_parser().parse_job_listings(html, session_id)


def parse_job_detail(html: str, session_id: str | None = None) -> UpWorkJob | None:
    """Parse full job detail page into UpWorkJob (delegates to ConfigurableDomParser)."""
    return _get_default_parser().parse_job_detail(html, session_id)

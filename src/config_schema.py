"""Pydantic schemas and loaders for YAML selector contracts and scraping workflow profiles."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Selector Contract Schemas
# ---------------------------------------------------------------------------


class PageGuardConfig(BaseModel):
    """Rules for detecting 404, expired, private, or invalid page shells."""

    not_found_headings: list[str] = Field(
        default_factory=lambda: [
            "job not found",
            "this job is no longer available",
            "this job is private",
            "page not found",
            "we can't find the page",
            "access denied",
        ]
    )
    error_heading_selectors: list[str] = Field(
        default_factory=lambda: [
            "h1",
            "h2",
            "[data-test='error-title']",
            ".air3-alert",
        ]
    )
    detail_signal_selectors: list[str] = Field(
        default_factory=lambda: [
            "[data-cy='clock-timelog']",
            "[data-cy='fixed-price']",
            "[data-cy='expertise']",
            "[data-qa='client-location']",
        ]
    )


class FieldSelectorRule(BaseModel):
    """Declarative extraction contract for a single field."""

    selectors: list[str] = Field(default_factory=list)
    extract: Literal[
        "text",
        "full_text",
        "attribute",
        "list",
        "sibling_text",
        "hourly_or_fixed_label",
        "ca_item_value",
    ] = "text"
    attribute: str | None = None
    transforms: list[str] = Field(default_factory=list)
    sibling_child_tag: str | None = None
    join_with: str | None = None
    label_contains: str | None = None
    required: bool = False
    is_fragile: bool = False
    fragile_reason: str = ""
    auth_only: bool = False
    description: str = ""


class ViewSelectorConfig(BaseModel):
    """Selector configuration for a specific page view (e.g. search_listings or job_detail)."""

    container_selectors: list[str] = Field(default_factory=list)
    fields: dict[str, FieldSelectorRule] = Field(default_factory=dict)


class UpWorkSelectorConfig(BaseModel):
    """Root selector contract definition loaded from configs/selectors/upwork.yaml."""

    version: str = "1.0"
    site: str = "upwork"
    base_url: str = "https://www.upwork.com"
    page_guards: PageGuardConfig = Field(default_factory=PageGuardConfig)
    views: dict[str, ViewSelectorConfig] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scraping Profile Schemas
# ---------------------------------------------------------------------------


class TransportConfig(BaseModel):
    """Transport backend and connection settings."""

    adapter: Literal["flaresolverr", "stealthy_session"] = "flaresolverr"
    proxy_mode: Literal["rotation", "pinned", "direct"] = "rotation"
    proxy_index: int = 0
    proxy_url: str | None = None
    max_timeout_ms: int = 60000
    max_retries: int = 3
    retry_backoff_seconds: float = 2.0
    auto_scroll: bool = False
    max_scrolls: int = 4
    scroll_delay_ms: int = 1200


class SearchWorkflowConfig(BaseModel):
    """Search, pagination, and data-source parameters."""

    mode: Literal["live_search", "from_saved_output"] = "live_search"
    query: str = "golang developer"
    queries: list[str] = Field(default_factory=list)
    sort: Literal["recency", "relevance"] | None = None
    per_page: Literal[10, 20, 50] | None = None
    contractor_tier: list[Literal[1, 2, 3]] = Field(default_factory=list)
    contract_type: Literal["hourly", "fixed"] | None = None
    proposal_tiers: list[str] = Field(default_factory=list)
    start_page: int = 1
    max_pages: int = 1
    target_jobs: int | None = None
    delay_between_pages_seconds: float = 5.0
    deduplicate_by_url: bool = True
    input_saved_file: str | None = None

    def effective_queries(self) -> list[str]:
        """Return deduplicated list of search queries to execute."""
        if self.queries:
            return list(dict.fromkeys(q.strip() for q in self.queries if q.strip()))
        return [self.query] if self.query else []


class FilterWorkflowConfig(BaseModel):
    """Pre- or post-scoring candidate filters."""

    required_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    min_score: int | None = None
    max_posted_age_days: int | None = None
    max_proposals: int | None = None


class EnrichmentWorkflowConfig(BaseModel):
    """Two-phase detail-page enrichment configuration."""

    enabled: bool = False
    max_jobs_to_enrich: int | None = None
    detail_retries: int = 2
    delay_between_details_seconds: float = 2.0
    compute_proposal_scores: bool = False


class OutputWorkflowConfig(BaseModel):
    """File persistence options."""

    directory: str = "output"
    filename_prefix: str = "upwork_jobs"
    save_per_page: bool = False
    save_combined: bool = True


class ScrapeProfileConfig(BaseModel):
    """Complete declarative specification of a scraping run."""

    name: str = "default_search"
    description: str = ""
    selectors_file: str = "configs/selectors/upwork.yaml"
    transport: TransportConfig = Field(default_factory=TransportConfig)
    search: SearchWorkflowConfig = Field(default_factory=SearchWorkflowConfig)
    filters: FilterWorkflowConfig = Field(default_factory=FilterWorkflowConfig)
    enrichment: EnrichmentWorkflowConfig = Field(default_factory=EnrichmentWorkflowConfig)
    output: OutputWorkflowConfig = Field(default_factory=OutputWorkflowConfig)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _resolve_path(path_str: str | Path) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        project_root = Path(__file__).resolve().parent.parent
        p = project_root / p
    return p


@lru_cache(maxsize=8)
def _load_raw_yaml(target_path_str: str) -> dict[str, Any]:
    """Cache raw parsed YAML dict from disk."""
    target_path = Path(target_path_str)
    if not target_path.is_file():
        raise FileNotFoundError(f"Configuration file not found at: {target_path}")

    with open(target_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_selector_config(path: str | Path | None = None) -> UpWorkSelectorConfig:
    """Load and validate selector configuration from YAML, returning a fresh model instance."""
    target_path = _resolve_path(path or "configs/selectors/upwork.yaml")
    data = _load_raw_yaml(str(target_path))
    return UpWorkSelectorConfig.model_validate(data)


def load_profile_config(path: str | Path) -> ScrapeProfileConfig:
    """Load and validate a scraping profile from YAML, returning a fresh model instance."""
    target_path = _resolve_path(path)
    data = _load_raw_yaml(str(target_path))
    return ScrapeProfileConfig.model_validate(data)

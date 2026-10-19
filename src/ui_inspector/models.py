"""Pydantic data models for UpWork UI blueprints, attribute hooks, and drift audits."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AttributeHook(BaseModel):
    """A semantic or test identifier found in the DOM."""

    hook_type: Literal["data-test", "data-qa", "data-cy", "data-v", "air3-class", "id"]
    name: str
    tag: str
    sample_text: str | None = None
    frequency: int = 1
    sample_values: list[str] = Field(default_factory=list)


class JobCardUIBlueprint(BaseModel):
    """Aggregated blueprint of UpWork job listing cards."""

    container_selector: str = "article.job-tile"
    total_cards_detected: int = 0
    discovered_hooks: dict[str, AttributeHook] = Field(default_factory=dict)
    sample_card_data: dict[str, Any] = Field(default_factory=dict)


class UpWorkPageBlueprint(BaseModel):
    """Complete structural blueprint of an UpWork view."""

    view_type: Literal["search_results", "best_matches", "job_detail", "unknown"]
    url: str
    title: str
    timestamp: str
    is_authenticated: bool = False
    status_code: int = 200
    proxy_used: str = "Direct"
    screenshot_path: str | None = None
    job_card_blueprint: JobCardUIBlueprint | None = None
    all_hooks: list[AttributeHook] = Field(default_factory=list)
    section_landmarks: list[dict[str, Any]] = Field(default_factory=list)
    captured_xhr_endpoints: list[str] = Field(default_factory=list)


class SelectorAuditEntry(BaseModel):
    """Audit result for a single selector used in the core parser."""

    target_field: str
    view: str
    registered_selector: str
    status: Literal["HEALTHY", "DEGRADED", "BROKEN", "FRAGILE"]
    matched_count: int
    sample_extracted_value: Any = None
    notes: str = ""
    suggested_replacement: str | None = None


class DiscoveredFieldCandidate(BaseModel):
    """A newly detected UI element on authenticated pages not yet mapped in src/parser.py."""

    hook_name: str
    suggested_selector: str
    sample_text: str
    element_tag: str
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    notes: str = ""


class BaselineHookDiff(BaseModel):
    """Diff for an attribute hook compared to a baseline blueprint."""

    hook_name: str
    hook_type: str
    change_type: Literal["REMOVED", "FREQUENCY_DROPPED", "ADDED"]
    baseline_frequency: int = 0
    current_frequency: int = 0
    notes: str = ""


class DriftAuditReport(BaseModel):
    """Comprehensive drift and selector health audit report."""

    timestamp: str
    url: str
    view_type: str
    is_authenticated: bool
    healthy_selectors_count: int = 0
    degraded_selectors_count: int = 0
    broken_selectors_count: int = 0
    fragile_selectors_count: int = 0
    audits: list[SelectorAuditEntry] = Field(default_factory=list)
    discovered_candidates: list[DiscoveredFieldCandidate] = Field(default_factory=list)
    breaking_changes_detected: list[str] = Field(default_factory=list)
    baseline_diffs: list[BaselineHookDiff] = Field(default_factory=list)

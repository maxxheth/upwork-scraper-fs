"""Declarative registry of selectors loaded from configs/selectors/upwork.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from src.config_schema import UpWorkSelectorConfig, load_selector_config


@dataclass(frozen=True)
class RegisteredSelector:
    """A registered selector contract used for drift auditing."""

    view: Literal["search_listings", "job_detail"]
    target_field: str
    css_selector: str
    description: str
    fallback_selectors: tuple[str, ...] = field(default_factory=tuple)
    is_fragile: bool = False
    fragile_reason: str = ""
    auth_only: bool = False
    expected_type: Literal["text", "list", "number", "element"] = "text"
    sibling_child_tag: str | None = None  # If text lives in a sibling's child (e.g. icon container + sibling <strong>)
    join_with: str | None = None  # Join multi-element values (e.g. "$25 - $50")


def build_registry_from_yaml(
    config: UpWorkSelectorConfig | None = None,
) -> list[RegisteredSelector]:
    """Build RegisteredSelector list dynamically from YAML selector configuration."""
    cfg = config or load_selector_config()
    registry: list[RegisteredSelector] = []

    # 1. Search Listings View
    search_cfg = cfg.views.get("search_listings")
    if search_cfg:
        if search_cfg.container_selectors:
            container_primary = search_cfg.container_selectors[0]
            container_fallbacks = tuple(search_cfg.container_selectors[1:])
            registry.append(
                RegisteredSelector(
                    view="search_listings",
                    target_field="job_cards_container",
                    css_selector=container_primary,
                    fallback_selectors=container_fallbacks,
                    description="Container element for each job card in search results",
                    expected_type="element",
                )
            )

        for field_name, rule in search_cfg.fields.items():
            if not rule.selectors:
                continue
            tf = "title_and_url" if field_name in ("title", "url") else field_name
            if any(r.view == "search_listings" and r.target_field == tf for r in registry):
                continue

            exp_type = "list" if rule.extract == "list" else "text"
            chosen_selector = rule.selectors[0]
            fallbacks = tuple(rule.selectors[1:])

            registry.append(
                RegisteredSelector(
                    view="search_listings",
                    target_field=tf,
                    css_selector=chosen_selector,
                    fallback_selectors=fallbacks,
                    description=rule.description or field_name,
                    is_fragile=rule.is_fragile,
                    fragile_reason=rule.fragile_reason,
                    auth_only=rule.auth_only,
                    expected_type=exp_type,
                    sibling_child_tag=rule.sibling_child_tag,
                    join_with=rule.join_with,
                )
            )

    # 2. Job Detail Page View
    detail_cfg = cfg.views.get("job_detail")
    if detail_cfg:
        for field_name, rule in detail_cfg.fields.items():
            if not rule.selectors:
                continue

            exp_type = "list" if rule.extract == "list" else "text"
            chosen_selector = rule.selectors[0]
            fallbacks = tuple(rule.selectors[1:])

            registry.append(
                RegisteredSelector(
                    view="job_detail",
                    target_field=field_name,
                    css_selector=chosen_selector,
                    fallback_selectors=fallbacks,
                    description=rule.description or field_name,
                    is_fragile=rule.is_fragile,
                    fragile_reason=rule.fragile_reason,
                    auth_only=rule.auth_only,
                    expected_type=exp_type,
                    sibling_child_tag=rule.sibling_child_tag,
                    join_with=rule.join_with,
                )
            )

    return registry


# Global registry populated from configs/selectors/upwork.yaml
CORE_PARSER_REGISTRY: list[RegisteredSelector] = build_registry_from_yaml()

"""UpWork-specific DOM pruning, semantic landmark extraction, and attribute indexing."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from lxml import html
from lxml.html import HtmlElement

from src.ui_inspector.models import (
    AttributeHook,
    JobCardUIBlueprint,
    UpWorkPageBlueprint,
)

logger = logging.getLogger(__name__)

STRIP_TAGS: set[str] = {
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "canvas",
    "embed",
    "object",
}


def clean_dom_tree(root: HtmlElement) -> None:
    """Remove scripts, styles, and non-content elements in place."""
    for tag_name in STRIP_TAGS:
        for node in list(root.iter(tag_name)):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)


def harvest_attribute_hooks(root: HtmlElement) -> list[AttributeHook]:
    """Discover and tally every data-test, data-qa, data-cy, and air3-* attribute."""
    hooks_map: dict[str, AttributeHook] = {}

    for el in root.iter():
        if not isinstance(el, HtmlElement):
            continue
        tag = el.tag.lower() if isinstance(el.tag, str) else "div"
        text = " ".join("".join(el.itertext()).split())[:100]

        # 1. data-test
        data_test = el.get("data-test")
        if data_test:
            key = f"data-test:{data_test}"
            if key not in hooks_map:
                hooks_map[key] = AttributeHook(
                    hook_type="data-test",
                    name=data_test,
                    tag=tag,
                    sample_text=text or None,
                    frequency=1,
                    sample_values=[text] if text else [],
                )
            else:
                hooks_map[key].frequency += 1
                if text and len(hooks_map[key].sample_values) < 5 and text not in hooks_map[key].sample_values:
                    hooks_map[key].sample_values.append(text)

        # 2. data-qa
        data_qa = el.get("data-qa")
        if data_qa:
            key = f"data-qa:{data_qa}"
            if key not in hooks_map:
                hooks_map[key] = AttributeHook(
                    hook_type="data-qa",
                    name=data_qa,
                    tag=tag,
                    sample_text=text or None,
                    frequency=1,
                    sample_values=[text] if text else [],
                )
            else:
                hooks_map[key].frequency += 1
                if text and len(hooks_map[key].sample_values) < 5 and text not in hooks_map[key].sample_values:
                    hooks_map[key].sample_values.append(text)

        # 3. data-cy
        data_cy = el.get("data-cy")
        if data_cy:
            key = f"data-cy:{data_cy}"
            if key not in hooks_map:
                hooks_map[key] = AttributeHook(
                    hook_type="data-cy",
                    name=data_cy,
                    tag=tag,
                    sample_text=text or None,
                    frequency=1,
                    sample_values=[text] if text else [],
                )
            else:
                hooks_map[key].frequency += 1
                if text and len(hooks_map[key].sample_values) < 5 and text not in hooks_map[key].sample_values:
                    hooks_map[key].sample_values.append(text)

        # 4. Scoped Vue hashes (e.g. data-v-3b2c2248)
        for attr in el.attrib:
            if attr.startswith("data-v-"):
                key = f"data-v:{attr}"
                if key not in hooks_map:
                    hooks_map[key] = AttributeHook(
                        hook_type="data-v",
                        name=attr,
                        tag=tag,
                        sample_text=text or None,
                        frequency=1,
                    )
                else:
                    hooks_map[key].frequency += 1

        # 5. air3 semantic component classes
        cls_str = el.get("class", "")
        if "air3-" in cls_str:
            for c in cls_str.split():
                if c.startswith("air3-"):
                    key = f"air3-class:{c}"
                    if key not in hooks_map:
                        hooks_map[key] = AttributeHook(
                            hook_type="air3-class",
                            name=c,
                            tag=tag,
                            sample_text=text or None,
                            frequency=1,
                        )
                    else:
                        hooks_map[key].frequency += 1

    return sorted(hooks_map.values(), key=lambda h: h.frequency, reverse=True)


def extract_job_card_blueprint(root: HtmlElement) -> JobCardUIBlueprint | None:
    """Find and synthesize repetitive job tile card structures."""
    cards = root.xpath(
        ".//article[contains(concat(' ', normalize-space(@class), ' '), ' job-tile ')] | "
        ".//*[(translate(@data-test, 'JOBTILE', 'jobtile') = 'jobtile' or translate(@data-test, 'JOB_TILE', 'job-tile') = 'job-tile') and not(self::a)]"
    )
    if not isinstance(cards, list) or not cards:
        cards = root.xpath(".//main//article")

    if not isinstance(cards, list) or not cards:
        return None

    card_elements: list[HtmlElement] = []
    for c in cards:
        if isinstance(c, HtmlElement) and not any(parent in card_elements for parent in c.iterancestors()):
            card_elements.append(c)

    total_cards = len(card_elements)
    if total_cards == 0:
        return None

    card_hooks: dict[str, AttributeHook] = {}
    sample_data: dict[str, Any] = {}

    for i, card in enumerate(card_elements):
        hooks = harvest_attribute_hooks(card)
        for h in hooks:
            key = f"{h.hook_type}:{h.name}"
            if key not in card_hooks:
                card_hooks[key] = h
            else:
                card_hooks[key].frequency += 1
                for v in h.sample_values:
                    if len(card_hooks[key].sample_values) < 5 and v not in card_hooks[key].sample_values:
                        card_hooks[key].sample_values.append(v)

        # Extract structured sample from the first card
        if i == 0:
            title_nodes = card.xpath(".//a[contains(@data-test, 'job-tile-title-link')]")
            if title_nodes and isinstance(title_nodes[0], HtmlElement):
                sample_data["title"] = " ".join("".join(title_nodes[0].itertext()).split())
                sample_data["href"] = title_nodes[0].get("href", "")

            desc_nodes = card.xpath(
                ".//*[contains(@data-test, 'JobDescription')]//p | .//*[contains(@data-test, 'JobDescription')]"
            )
            if desc_nodes and isinstance(desc_nodes[0], HtmlElement):
                sample_data["description"] = " ".join("".join(desc_nodes[0].itertext()).split())[:140]

            rate_nodes = card.xpath(".//*[@data-test='job-type-label']//strong | .//*[@data-test='is-fixed-price']")
            if rate_nodes and isinstance(rate_nodes[0], HtmlElement):
                sample_data["rate"] = " ".join("".join(rate_nodes[0].itertext()).split())

            skill_nodes = card.xpath(".//*[@data-test='token']//span")
            if skill_nodes:
                sample_data["skills"] = [
                    " ".join("".join(s.itertext()).split())
                    for s in skill_nodes
                    if isinstance(s, HtmlElement)
                ]

    return JobCardUIBlueprint(
        container_selector="article.job-tile",
        total_cards_detected=total_cards,
        discovered_hooks=card_hooks,
        sample_card_data=sample_data,
    )


def extract_landmarks(root: HtmlElement) -> list[dict[str, Any]]:
    """Extract high-level page landmarks."""
    landmarks: list[dict[str, Any]] = []
    for tag in ["header", "nav", "main", "aside", "footer"]:
        nodes = root.xpath(f".//{tag}")
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, HtmlElement):
                    landmarks.append({
                        "tag": tag,
                        "id": n.get("id"),
                        "class": n.get("class", ""),
                        "data_test": n.get("data-test"),
                    })
    return landmarks


def build_page_blueprint(
    html_content: str,
    url: str,
    title: str = "",
    status_code: int = 200,
    is_authenticated: bool = False,
    proxy_used: str = "Direct",
    screenshot_path: str | None = None,
    captured_xhr: list[str] | None = None,
) -> UpWorkPageBlueprint:
    """Build a complete UpWorkPageBlueprint from raw rendered HTML."""
    if not html_content.strip():
        return UpWorkPageBlueprint(
            view_type="unknown",
            url=url,
            title=title,
            timestamp=datetime.now(UTC).isoformat(),
            status_code=status_code,
            is_authenticated=is_authenticated,
            proxy_used=proxy_used,
        )

    root = html.fromstring(html_content)
    clean_dom_tree(root)

    # Infer view type
    view_type: Any = "unknown"
    if "/search/jobs" in url or "q=" in url:
        view_type = "search_results"
    elif "best-matches" in url or "/nx/find-work" in url:
        view_type = "best_matches"
    elif "/jobs/" in url or "/freelance-jobs/apply/" in url or "nx/job-details" in url or "_~" in url:
        view_type = "job_detail"

    all_hooks = harvest_attribute_hooks(root)
    card_blueprint = extract_job_card_blueprint(root)
    landmarks = extract_landmarks(root)

    return UpWorkPageBlueprint(
        view_type=view_type,
        url=url,
        title=title or (root.findtext(".//title") or "").strip(),
        timestamp=datetime.now(UTC).isoformat(),
        is_authenticated=is_authenticated,
        status_code=status_code,
        proxy_used=proxy_used,
        screenshot_path=screenshot_path,
        job_card_blueprint=card_blueprint,
        all_hooks=all_hooks,
        section_landmarks=landmarks,
        captured_xhr_endpoints=captured_xhr or [],
    )

"""Evaluates parser selector contracts against rendered DOM and diffs baselines."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scrapling import Selector

from src.ui_inspector.models import (
    BaselineHookDiff,
    DiscoveredFieldCandidate,
    DriftAuditReport,
    SelectorAuditEntry,
    UpWorkPageBlueprint,
)
from src.ui_inspector.selector_registry import CORE_PARSER_REGISTRY, RegisteredSelector

logger = logging.getLogger(__name__)


class DriftAuditor:
    """Audits live UpWork HTML against registered parser selectors and discovers drift."""

    def __init__(
        self,
        page_blueprint: UpWorkPageBlueprint,
        raw_html: str,
        baseline_blueprint: UpWorkPageBlueprint | None = None,
    ) -> None:
        self.blueprint = page_blueprint
        self.raw_html = raw_html
        self.baseline_blueprint = baseline_blueprint or self._load_default_baseline(page_blueprint.view_type)
        self.selector = Selector(raw_html)

    @staticmethod
    def _load_default_baseline(view_type: str) -> UpWorkPageBlueprint | None:
        """Attempt to load a baseline blueprint from baselines/{view_type}_baseline.json."""
        baseline_file = Path("baselines") / f"{view_type}_baseline.json"
        if baseline_file.is_file():
            try:
                with open(baseline_file, encoding="utf-8") as f:
                    data = json.load(f)
                return UpWorkPageBlueprint(**data)
            except Exception as e:
                logger.debug("Could not parse baseline file %s: %s", baseline_file, e)
        return None

    def audit(self) -> DriftAuditReport:
        """Run complete selector contract evaluation, baseline diffing, and new field discovery."""
        audits: list[SelectorAuditEntry] = []
        breaking_changes: list[str] = []

        is_search_view = self.blueprint.view_type in ("search_results", "best_matches")
        relevant_view = "search_listings" if is_search_view else "job_detail"

        # 1. Audit every registered selector for this view
        for reg in CORE_PARSER_REGISTRY:
            if reg.view != relevant_view:
                continue

            entry = self._audit_single_selector(reg)
            audits.append(entry)

            if entry.status == "BROKEN":
                breaking_changes.append(
                    f"BROKEN: Field '{entry.target_field}' using '{entry.registered_selector}' matched 0 elements."
                )
            elif entry.status == "FRAGILE":
                breaking_changes.append(
                    f"FRAGILE: Field '{entry.target_field}' using '{entry.registered_selector}'. Reason: {entry.notes}"
                )

        # 2. Discover unmapped fields from authenticated DOM
        discovered_candidates = self._discover_unmapped_fields(relevant_view)

        # 3. Diff against baseline if available
        baseline_diffs = self._diff_against_baseline()
        for diff in baseline_diffs:
            if diff.change_type in ("REMOVED", "FREQUENCY_DROPPED"):
                breaking_changes.append(
                    f"BASELINE DRIFT: Hook '{diff.hook_name}' {diff.notes}"
                )

        # Tally counts
        healthy = sum(1 for a in audits if a.status == "HEALTHY")
        degraded = sum(1 for a in audits if a.status == "DEGRADED")
        broken = sum(1 for a in audits if a.status == "BROKEN")
        fragile = sum(1 for a in audits if a.status == "FRAGILE")

        return DriftAuditReport(
            timestamp=datetime.now(UTC).isoformat(),
            url=self.blueprint.url,
            view_type=self.blueprint.view_type,
            is_authenticated=self.blueprint.is_authenticated,
            healthy_selectors_count=healthy,
            degraded_selectors_count=degraded,
            broken_selectors_count=broken,
            fragile_selectors_count=fragile,
            audits=audits,
            discovered_candidates=discovered_candidates,
            breaking_changes_detected=breaking_changes,
            baseline_diffs=baseline_diffs,
        )

    def _diff_against_baseline(self) -> list[BaselineHookDiff]:
        """Compare current blueprint hooks against baseline blueprint."""
        if not self.baseline_blueprint:
            return []

        diffs: list[BaselineHookDiff] = []
        current_hooks = {f"{h.hook_type}:{h.name}": h for h in self.blueprint.all_hooks}
        baseline_hooks = {f"{h.hook_type}:{h.name}": h for h in self.baseline_blueprint.all_hooks}

        # Check for removed or degraded hooks from baseline
        for key, base_h in baseline_hooks.items():
            if key not in current_hooks:
                diffs.append(
                    BaselineHookDiff(
                        hook_name=base_h.name,
                        hook_type=base_h.hook_type,
                        change_type="REMOVED",
                        baseline_frequency=base_h.frequency,
                        current_frequency=0,
                        notes=f"Hook existed {base_h.frequency}x in baseline but was removed in current UI",
                    )
                )
            else:
                curr_h = current_hooks[key]
                if base_h.frequency >= 4 and curr_h.frequency < (base_h.frequency // 2):
                    diffs.append(
                        BaselineHookDiff(
                            hook_name=base_h.name,
                            hook_type=base_h.hook_type,
                            change_type="FREQUENCY_DROPPED",
                            baseline_frequency=base_h.frequency,
                            current_frequency=curr_h.frequency,
                            notes=f"Frequency dropped significantly: {base_h.frequency}x -> {curr_h.frequency}x",
                        )
                    )

        # Check for newly added hooks (limit to top 5)
        for key, curr_h in current_hooks.items():
            if key not in baseline_hooks and curr_h.frequency >= 2:
                diffs.append(
                    BaselineHookDiff(
                        hook_name=curr_h.name,
                        hook_type=curr_h.hook_type,
                        change_type="ADDED",
                        baseline_frequency=0,
                        current_frequency=curr_h.frequency,
                        notes="Newly appeared in current UI",
                    )
                )

        return diffs[:10]

    def _audit_single_selector(self, reg: RegisteredSelector) -> SelectorAuditEntry:
        """Evaluate a single selector against the DOM."""
        matches = self.selector.css(reg.css_selector)
        count = len(matches)

        suggested_replacement: str | None = None
        notes = ""

        # Check fragility flag
        if reg.is_fragile:
            notes = reg.fragile_reason

        # If zero matches
        if count == 0:
            status = "BROKEN"
            suggested_replacement = self._find_replacement_for_broken(reg)
            return SelectorAuditEntry(
                target_field=reg.target_field,
                view=reg.view,
                registered_selector=reg.css_selector,
                status=status,
                matched_count=0,
                notes=notes or "Selector matched 0 elements in live DOM",
                suggested_replacement=suggested_replacement,
            )

        # Evaluate sample text (including sibling resolution if defined)
        sample_val = self._extract_sample_value(matches, reg)

        # If fragile (even if matching)
        if reg.is_fragile:
            return SelectorAuditEntry(
                target_field=reg.target_field,
                view=reg.view,
                registered_selector=reg.css_selector,
                status="FRAGILE",
                matched_count=count,
                sample_extracted_value=sample_val,
                notes=notes,
                suggested_replacement=self._find_replacement_for_broken(reg),
            )

        # If matched element exists but text is completely empty on a text field
        if reg.expected_type in ("text", "list") and not sample_val:
            return SelectorAuditEntry(
                target_field=reg.target_field,
                view=reg.view,
                registered_selector=reg.css_selector,
                status="DEGRADED",
                matched_count=count,
                sample_extracted_value="",
                notes="Matched elements produced empty text",
                suggested_replacement=self._find_replacement_for_broken(reg),
            )

        # Check for degradation (e.g. fewer than 50% of cards have it)
        card_blueprint = self.blueprint.job_card_blueprint
        if card_blueprint and card_blueprint.total_cards_detected > 0:
            total_cards = card_blueprint.total_cards_detected
            if reg.target_field in ("title_and_url", "description", "hourly_rate") and count < total_cards // 2:
                return SelectorAuditEntry(
                    target_field=reg.target_field,
                    view=reg.view,
                    registered_selector=reg.css_selector,
                    status="DEGRADED",
                    matched_count=count,
                    sample_extracted_value=sample_val,
                    notes=f"Low match rate ({count}/{total_cards} cards)",
                    suggested_replacement=self._find_replacement_for_broken(reg),
                )

        return SelectorAuditEntry(
            target_field=reg.target_field,
            view=reg.view,
            registered_selector=reg.css_selector,
            status="HEALTHY",
            matched_count=count,
            sample_extracted_value=sample_val,
            notes=notes,
        )

    def _extract_sample_value(self, matches: list[Selector], reg: RegisteredSelector) -> Any:
        """Extract multi-element values or handle parent-sibling resolution for icon containers."""
        if not matches:
            return ""

        try:
            # Handle sibling child resolution (used in src/parser.py for [data-cy] icon tags)
            if reg.sibling_child_tag:
                icon_el = matches[0]
                parent = icon_el.parent
                if parent:
                    sibling_values = parent.css(reg.sibling_child_tag)
                    texts = [s.text.strip() for s in sibling_values if s.text and s.text.strip()]
                    if texts:
                        joiner = reg.join_with or " "
                        return joiner.join(texts)

            if reg.expected_type == "list":
                texts = [m.text.strip() for m in matches[:5] if m.text and m.text.strip()]
                return texts

            if reg.expected_type == "element":
                first = matches[0]
                cls_val = first.attrib.get("class", "element")
                return f"<{cls_val}>"

            first_text = matches[0].text.strip() if matches[0].text else ""
            return first_text[:100]
        except Exception:
            return ""

    def _find_replacement_for_broken(self, reg: RegisteredSelector) -> str | None:
        """Heuristic search in discovered attribute hooks for safer replacement."""
        # 1. Look for typo fix in published date
        if "pubilshed" in reg.css_selector:
            for hook in self.blueprint.all_hooks:
                if hook.hook_type == "data-test" and "publish" in hook.name:
                    return f"[data-test='{hook.name}'] span"

        # 2. Look for scoped Vue hash removal in skills
        if "data-v-" in reg.css_selector:
            skills_matches = self.selector.css(".skills-list .air3-line-clamp, [data-test='Skill'] span")
            if skills_matches:
                return ".skills-list .air3-line-clamp"

        # 3. Look for matching data-test / data-qa / data-cy by field name
        field_slug = reg.target_field.replace("_", "-")
        for hook in self.blueprint.all_hooks:
            if field_slug in hook.name.lower():
                return f"[{hook.hook_type}='{hook.name}']"

        return None

    def _discover_unmapped_fields(self, view: str) -> list[DiscoveredFieldCandidate]:
        """Scan hooks to discover new UI elements present in authenticated sessions."""
        candidates: list[DiscoveredFieldCandidate] = []

        # Extract registered attribute values precisely
        registered_hook_names: set[str] = set()
        for r in CORE_PARSER_REGISTRY:
            # Match data-* attributes inside selector
            for match in re.findall(r"\[(data-[a-zA-Z0-9_-]+)[*^$]?=['\"]([^'\"]+)['\"]\]", r.css_selector):
                registered_hook_names.add(match[1])

        keywords = [
            "verified", "payment", "rating", "review", "hire", "spent",
            "connect", "badge", "score", "tier", "proposals", "interview", "invites"
        ]

        hooks_to_scan = []
        if view == "search_listings" and self.blueprint.job_card_blueprint:
            hooks_to_scan = list(self.blueprint.job_card_blueprint.discovered_hooks.values())
        else:
            hooks_to_scan = self.blueprint.all_hooks

        for hook in hooks_to_scan:
            # Skip if explicitly registered
            if hook.name in registered_hook_names:
                continue

            name_lower = hook.name.lower()
            if any(k in name_lower for k in keywords):
                css = f"[{hook.hook_type}='{hook.name}']"
                sample = hook.sample_text or (hook.sample_values[0] if hook.sample_values else "")
                candidates.append(
                    DiscoveredFieldCandidate(
                        hook_name=hook.name,
                        suggested_selector=css,
                        sample_text=sample[:100],
                        element_tag=hook.tag,
                        confidence="HIGH" if hook.sample_text else "MEDIUM",
                        notes=f"Detected {hook.frequency} times with type '{hook.hook_type}'",
                    )
                )

        return candidates[:15]

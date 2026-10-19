"""Multi-format exporter for UI blueprints, drift reports, and baseline diffs."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.ui_inspector.models import (
    DriftAuditReport,
    UpWorkPageBlueprint,
)

logger = logging.getLogger(__name__)
console = Console()


def save_blueprint_json(blueprint: UpWorkPageBlueprint, output_dir: Path) -> Path:
    """Save an UpWorkPageBlueprint to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = blueprint.view_type
    timestamp = blueprint.timestamp.replace(":", "-").replace(".", "_")
    filename = f"blueprint_{slug}_{timestamp}.json"
    file_path = output_dir / filename

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(blueprint.model_dump(), f, indent=2, ensure_ascii=False)

    logger.info("Saved UI Blueprint to %s", file_path)
    return file_path


def save_drift_report_markdown(report: DriftAuditReport, output_dir: Path) -> Path:
    """Generate and save an actionable Markdown drift report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = report.view_type
    timestamp = report.timestamp.replace(":", "-").replace(".", "_")
    filename = f"drift_report_{slug}_{timestamp}.md"
    file_path = output_dir / filename

    lines = [
        "# UpWork UI Drift & Selector Audit Report",
        "",
        f"- **Target URL:** {report.url}",
        f"- **View Type:** `{report.view_type}`",
        f"- **Authenticated Session:** {'✅ Yes' if report.is_authenticated else '❌ No (Public View)'}",
        f"- **Audited At:** {report.timestamp}",
        "",
        "## Summary",
        "",
        f"- **Healthy Selectors:** {report.healthy_selectors_count}",
        f"- **Degraded Selectors:** {report.degraded_selectors_count}",
        f"- **Broken Selectors:** {report.broken_selectors_count}",
        f"- **Fragile Selectors:** {report.fragile_selectors_count}",
        "",
    ]

    if report.breaking_changes_detected:
        lines.extend([
            "## 🚨 Breaking & High-Risk Changes Detected",
            "",
        ])
        for b in report.breaking_changes_detected:
            lines.append(f"- ⚠️ {b}")
        lines.append("")

    if report.baseline_diffs:
        lines.extend([
            "## 🔄 Baseline Structural Diffs",
            "",
            "| Hook Name | Hook Type | Change Type | Baseline Freq | Current Freq | Notes |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for d in report.baseline_diffs:
            change_badge = {
                "REMOVED": "❌ REMOVED",
                "FREQUENCY_DROPPED": "⚠️ DROPPED",
                "ADDED": "✨ ADDED",
            }.get(d.change_type, d.change_type)
            notes = d.notes.replace("|", "\\|")
            lines.append(
                f"| `{d.hook_name}` | `{d.hook_type}` | {change_badge} | {d.baseline_frequency} | {d.current_frequency} | {notes} |"
            )
        lines.append("")

    lines.extend([
        "## Selector Contract Status (src/parser.py)",
        "",
        "| Target Field | Current Selector in `src/parser.py` | Status | Matches | Sample Extracted | Replacement / Notes |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for a in report.audits:
        status_badge = {
            "HEALTHY": "✅ HEALTHY",
            "DEGRADED": "⚠️ DEGRADED",
            "BROKEN": "❌ BROKEN",
            "FRAGILE": "⚡ FRAGILE",
        }.get(a.status, a.status)
        sample = str(a.sample_extracted_value or "").replace("|", "\\|")[:40]
        notes = (a.suggested_replacement or a.notes or "").replace("|", "\\|")
        lines.append(
            f"| `{a.target_field}` | `{a.registered_selector}` | {status_badge} | {a.matched_count} | `{sample}` | {notes} |"
        )

    lines.append("")

    if report.discovered_candidates:
        lines.extend([
            "## 💡 Newly Discovered Authenticated UI Fields",
            "",
            "These elements are present in the authenticated session but currently unmapped in `src/parser.py` and `src/models.py`:",
            "",
            "| Hook Name | Suggested CSS Selector | Element Tag | Sample Value | Confidence | Notes |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for c in report.discovered_candidates:
            sample = c.sample_text.replace("|", "\\|")[:50]
            lines.append(
                f"| `{c.hook_name}` | `{c.suggested_selector}` | `<{c.element_tag}>` | `{sample}` | {c.confidence} | {c.notes} |"
            )
        lines.append("")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info("Saved Drift Report to %s", file_path)
    return file_path


def render_rich_audit_summary(report: DriftAuditReport) -> None:
    """Print an interactive Rich CLI summary of the audit."""
    table = Table(title=f"Selector Health Contract — {report.view_type.upper()}", show_header=True)
    table.add_column("Target Field", style="cyan")
    table.add_column("Current Selector", style="white")
    table.add_column("Status", style="bold")
    table.add_column("Matches", justify="right")
    table.add_column("Sample Extracted", style="green")
    table.add_column("Action / Replacement", style="yellow")

    for a in report.audits:
        status_color = {
            "HEALTHY": "green",
            "DEGRADED": "yellow",
            "BROKEN": "bold red",
            "FRAGILE": "bold magenta",
        }.get(a.status, "white")
        sample = str(a.sample_extracted_value or "")[:35]
        action = a.suggested_replacement or a.notes or "OK"
        table.add_row(
            a.target_field,
            a.registered_selector,
            f"[{status_color}]{a.status}[/{status_color}]",
            str(a.matched_count),
            sample,
            action,
        )

    console.print(table)

    if report.baseline_diffs:
        diff_table = Table(title="Baseline Structural Diffs", show_header=True)
        diff_table.add_column("Hook", style="cyan")
        diff_table.add_column("Change", style="bold")
        diff_table.add_column("Baseline -> Current Freq", justify="center")
        diff_table.add_column("Notes", style="yellow")
        for d in report.baseline_diffs:
            c_color = "red" if d.change_type == "REMOVED" else "yellow" if d.change_type == "FREQUENCY_DROPPED" else "green"
            diff_table.add_row(
                f"{d.hook_type}:{d.hook_name}",
                f"[{c_color}]{d.change_type}[/{c_color}]",
                f"{d.baseline_frequency} -> {d.current_frequency}",
                d.notes,
            )
        console.print(diff_table)

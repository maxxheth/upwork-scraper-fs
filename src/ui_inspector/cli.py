"""Command-line interface for UpWork UI Inspector & Drift Auditor."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import quote_plus

import typer
from rich.console import Console
from rich.panel import Panel

from src.config import load_config
from src.ui_inspector.drift_auditor import DriftAuditor
from src.ui_inspector.engine import UpWorkUIEngine
from src.ui_inspector.exporter import (
    render_rich_audit_summary,
    save_blueprint_json,
    save_drift_report_markdown,
)
from src.ui_inspector.proxy_pinning import resolve_pinned_proxy
from src.ui_inspector.session_manager import UpWorkSessionManager

app = typer.Typer(
    name="upwork-ui-inspector",
    help="UpWork UI Scraper & Selector Drift Auditor using Scrapling persistent sessions.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _init_session_manager(
    proxy_index: int | None = None,
    direct: bool = False,
) -> tuple[UpWorkSessionManager, dict[str, str | int | None]]:
    """Helper to initialize UpWorkSessionManager with sticky proxy settings or saved metadata."""
    config = load_config()

    # Create dummy manager first to check saved metadata
    temp_mgr = UpWorkSessionManager(
        user_data_dir=str(config["user_data_dir"]),
        storage_state_file=str(config["storage_state_file"]),
    )
    saved_meta = temp_mgr.load_session_meta()

    # Determine effective direct/proxy_index
    is_direct = direct
    p_idx = proxy_index

    if not direct and proxy_index is None and saved_meta is not None:
        is_direct = bool(saved_meta.get("direct", False))
        p_idx = saved_meta.get("proxy_index")

    if p_idx is None:
        p_idx = int(config.get("session_proxy_index") or 0)

    proxy_cfg = resolve_pinned_proxy(
        explicit_proxy=str(config["session_proxy_url"]) if config.get("session_proxy_url") else None,
        proxy_index=p_idx,
        proxy_file=str(config["proxy_file"]),
        direct=is_direct,
    )

    manager = UpWorkSessionManager(
        user_data_dir=str(config["user_data_dir"]),
        storage_state_file=str(config["storage_state_file"]),
        proxy_config=proxy_cfg,
        cdp_url=str(config["cdp_url"]) if config.get("cdp_url") else None,
    )

    return manager, config


@app.command()
def auth_login(
    proxy_index: Annotated[
        int | None,
        typer.Option("--proxy-index", "-p", help="Proxy index from proxies.txt to pin session to"),
    ] = None,
    direct: Annotated[
        bool,
        typer.Option("--direct", help="Bypass proxies and log in directly using local IP"),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option("--timeout", "-t", help="Timeout in seconds for interactive login"),
    ] = 180,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose debug logs")] = False,
) -> None:
    """Launch interactive visible browser to log into UpWork and persist session cookies/profile."""
    setup_logging(verbose)
    session_mgr, _ = _init_session_manager(proxy_index=proxy_index, direct=direct)

    # Save session metadata for subsequent inspect/audit runs
    session_mgr.save_session_meta(direct=direct, proxy_index=proxy_index)

    console.print(
        Panel.fit(
            f"[bold cyan]UpWork Interactive Session Login[/bold cyan]\n"
            f"Profile: [yellow]{session_mgr.user_data_dir}[/yellow]\n"
            f"Proxy: [magenta]{session_mgr.proxy_config.get_display_summary()}[/magenta]\n\n"
            f"[green]A Chrome window will now open.[/green]\n"
            f"Please log into UpWork (including 2FA / Google SSO if prompted).\n"
            f"Once you reach the UpWork feed or search page, press Enter in this terminal.",
            title="Session Bootstrap",
        )
    )

    session = session_mgr.create_session(headless=False, timeout=timeout * 1000)
    login_url = "https://www.upwork.com/ab/account-security/login"

    with session:
        def on_action(page: object) -> None:
            input("\n👉 Press ENTER here after you have successfully logged into UpWork in Chrome... ")
            try:
                ctx = getattr(page, "context", None)
                if ctx:
                    session_mgr.backup_storage_state(ctx)
            except Exception as e:
                console.print(f"[yellow]Warning backing up state: {e}[/yellow]")

        session.fetch(
            login_url,
            page_action=on_action,
            load_dom=True,
            solve_cloudflare=True,
        )

    console.print("[bold green]✅ Login routine completed! Session profile saved.[/bold green]")


@app.command()
def auth_status(
    proxy_index: Annotated[int | None, typer.Option("--proxy-index", "-p", help="Proxy index")] = None,
    direct: Annotated[bool, typer.Option("--direct", help="Bypass proxies")] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Debug logging")] = False,
) -> None:
    """Check whether the persisted Scrapling session is currently authenticated on UpWork."""
    setup_logging(verbose)
    session_mgr, _ = _init_session_manager(proxy_index=proxy_index, direct=direct)

    engine = UpWorkUIEngine(session_manager=session_mgr, capture_screenshot=False, auto_scroll=False)
    test_url = "https://www.upwork.com/nx/search/jobs/?q=wordpress"

    with console.status("[bold green]Probing UpWork authentication state...[/bold green]"):
        blueprint, _ = engine.fetch_blueprint(test_url, headless=True)

    if blueprint.is_authenticated:
        console.print("[bold green]✅ Session is AUTHENTICATED on UpWork![/bold green]")
        console.print(f"Proxy used: {blueprint.proxy_used}")
    else:
        console.print("[bold yellow]⚠️ Session is PUBLIC / UNAUTHENTICATED on UpWork.[/bold yellow]")
        console.print("Run `uv run python -m src.ui_inspector auth-login` to authenticate.")


@app.command()
def inspect(
    target: Annotated[
        str,
        typer.Option("--target", "-t", help="Target view: 'search', 'best-matches', or custom URL"),
    ] = "search",
    query: Annotated[str, typer.Option("--query", "-q", help="Search query")] = "wordpress",
    url: Annotated[str | None, typer.Option("--url", "-u", help="Explicit target URL")] = None,
    proxy_index: Annotated[int | None, typer.Option("--proxy-index", "-p", help="Proxy index")] = None,
    direct: Annotated[bool, typer.Option("--direct", help="Bypass proxies")] = False,
    screenshot: Annotated[bool, typer.Option("--screenshot", "-s", help="Save screenshot")] = True,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("output/ui_reports"),
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Debug logging")] = False,
) -> None:
    """Capture live UpWork UI blueprint and XHR endpoints via persisted Scrapling session."""
    setup_logging(verbose)
    session_mgr, _ = _init_session_manager(proxy_index=proxy_index, direct=direct)

    target_url = url
    if not target_url:
        if target == "best-matches":
            target_url = "https://www.upwork.com/nx/find-work/best-matches"
        else:
            safe_q = quote_plus(query)
            target_url = f"https://www.upwork.com/nx/search/jobs/?q={safe_q}&sort=recency"

    engine = UpWorkUIEngine(
        session_manager=session_mgr,
        output_dir=output,
        capture_screenshot=screenshot,
        auto_scroll=True,
    )

    console.print(f"[bold cyan]Inspecting UI for:[/bold cyan] {target_url}")
    blueprint, _ = engine.fetch_blueprint(target_url, headless=True)

    json_path = save_blueprint_json(blueprint, output)
    console.print(f"[bold green]Blueprint saved to:[/bold green] {json_path}")
    if blueprint.job_card_blueprint:
        console.print(
            f"Detected [bold yellow]{blueprint.job_card_blueprint.total_cards_detected}[/bold yellow] job cards on page."
        )


@app.command()
def audit(
    target: Annotated[
        str,
        typer.Option("--target", "-t", help="Target view: 'search', 'best-matches', or custom URL"),
    ] = "search",
    query: Annotated[str, typer.Option("--query", "-q", help="Search query")] = "wordpress",
    url: Annotated[str | None, typer.Option("--url", "-u", help="Explicit target URL")] = None,
    proxy_index: Annotated[int | None, typer.Option("--proxy-index", "-p", help="Proxy index")] = None,
    direct: Annotated[bool, typer.Option("--direct", help="Bypass proxies")] = False,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("output/ui_reports"),
    update_baseline: Annotated[
        bool,
        typer.Option("--update-baseline", help="Save captured blueprint as baseline in baselines/"),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Debug logging")] = False,
) -> None:
    """Audit src/parser.py selectors against live UpWork UI and generate a drift report."""
    setup_logging(verbose)
    session_mgr, _ = _init_session_manager(proxy_index=proxy_index, direct=direct)

    target_url = url
    if not target_url:
        if target == "best-matches":
            target_url = "https://www.upwork.com/nx/find-work/best-matches"
        else:
            safe_q = quote_plus(query)
            target_url = f"https://www.upwork.com/nx/search/jobs/?q={safe_q}&sort=recency"

    engine = UpWorkUIEngine(
        session_manager=session_mgr,
        output_dir=output,
        capture_screenshot=True,
        auto_scroll=True,
    )

    console.print(f"[bold cyan]Running UI Drift Audit against:[/bold cyan] {target_url}")
    blueprint, raw_html = engine.fetch_blueprint(target_url, headless=True)

    auditor = DriftAuditor(blueprint, raw_html)
    report = auditor.audit()

    render_rich_audit_summary(report)

    # Save reports
    md_path = save_drift_report_markdown(report, output)
    save_blueprint_json(blueprint, output)
    console.print(f"\n[bold green]Drift Report saved to:[/bold green] {md_path}")

    if update_baseline:
        baseline_dir = Path("baselines")
        baseline_dir.mkdir(parents=True, exist_ok=True)
        baseline_file = baseline_dir / f"{blueprint.view_type}_baseline.json"
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump(blueprint.model_dump(), f, indent=2)
        console.print(f"[bold yellow]Updated baseline file:[/bold yellow] {baseline_file}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()

"""Scrapling execution engine for hydrating and blueprinting UpWork UI views."""

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.ui_inspector.dom_blueprint import build_page_blueprint
from src.ui_inspector.models import UpWorkPageBlueprint
from src.ui_inspector.session_manager import UpWorkSessionManager

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from playwright.sync_api import Response as PlaywrightResponse

logger = logging.getLogger(__name__)

HYDRATE_PAGE_JS = """
async () => {
    // 1. Force eager loading on images
    document.querySelectorAll('img').forEach(img => {
        if (img.loading === 'lazy') img.loading = 'eager';
        if (img.dataset.src && !img.src) img.src = img.dataset.src;
        if (img.dataset.srcset && !img.srcset) img.srcset = img.dataset.srcset;
    });

    // 2. Progressive scroll down to trigger Nuxt/Vue Virtual Scroller & lazy cards
    const getScrollHeight = () => Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.offsetHeight
    );

    const viewportHeight = window.innerHeight || 900;
    const step = Math.max(Math.floor(viewportHeight * 0.75), 500);
    let currentY = 0;
    let maxScroll = getScrollHeight();

    while (currentY < maxScroll) {
        currentY = Math.min(currentY + step, maxScroll);
        window.scrollTo(0, currentY);
        await new Promise(r => setTimeout(r, 60));
        maxScroll = getScrollHeight();
    }

    // Scroll back to top
    window.scrollTo(0, 0);
    await new Promise(r => setTimeout(r, 100));
}
"""


class UpWorkUIEngine:
    """Navigates to UpWork views using a persistent Scrapling session, captures UI blueprints."""

    def __init__(
        self,
        session_manager: UpWorkSessionManager,
        output_dir: Path | str = "./output/ui_reports",
        capture_screenshot: bool = True,
        auto_scroll: bool = True,
        delay: float = 2.0,
    ) -> None:
        self.session_manager = session_manager
        self.output_dir = Path(output_dir)
        self.capture_screenshot = capture_screenshot
        self.auto_scroll = auto_scroll
        self.delay = delay
        self._action_data: dict[str, Any] = {}
        self._captured_xhr: list[str] = []
        self._response_handler: Any = None

    def _page_setup(self, page: Page) -> None:
        """Pre-navigation setup: configure viewport & listen to network responses."""
        try:
            page.set_viewport_size({"width": 1440, "height": 900})

            # Clean up any existing handler if retrying
            if self._response_handler is not None:
                with contextlib.suppress(Exception):
                    page.remove_listener("response", self._response_handler)

            def handle_response(resp: PlaywrightResponse) -> None:
                try:
                    # Filter only actual XHR / fetch responses
                    if resp.request.resource_type in ("xhr", "fetch"):
                        url = resp.url
                        if any(x in url for x in ["/api/graphql", "/nx/search/jobs", "/ab/find-work/api"]):
                            self._captured_xhr.append(url)
                except Exception:
                    pass

            self._response_handler = handle_response
            page.on("response", handle_response)
        except Exception as e:
            logger.warning("Error in page_setup hook: %s", e)

    def _page_action(self, page: Page) -> None:
        """Post-navigation hook: hydration, auth check, screenshot, storage state backup."""
        try:
            # Clean up response listener once navigation is settled
            if self._response_handler is not None:
                with contextlib.suppress(Exception):
                    page.remove_listener("response", self._response_handler)
                self._response_handler = None

            # 1. Check authentication state
            is_auth = self.session_manager.check_auth_indicators(page)
            self._action_data["is_authenticated"] = is_auth
            logger.info("Session authentication state: %s", "Authenticated" if is_auth else "Public/Unauthenticated")

            # 2. Backup storage state ONLY if affirmatively authenticated
            if is_auth and page.context:
                self.session_manager.backup_storage_state(page.context)

            # 3. Progressive auto-scroll hydration
            if self.auto_scroll:
                try:
                    logger.debug("Executing progressive auto-scroll page hydration...")
                    page.evaluate(HYDRATE_PAGE_JS)
                except Exception as e:
                    logger.debug("Page hydration evaluation encountered error: %s", e)

            # 4. Stabilization delay
            if self.delay > 0:
                page.wait_for_timeout(int(self.delay * 1000))

            # 5. Capture screenshot if requested
            if self.capture_screenshot:
                ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
                ss_dir = self.output_dir / "screenshots"
                ss_dir.mkdir(parents=True, exist_ok=True)
                ss_path = ss_dir / f"upwork_{ts}.png"
                page.screenshot(path=str(ss_path), full_page=True)
                self._action_data["screenshot_path"] = str(ss_path)
                logger.info("Captured screenshot: %s", ss_path)

            self._action_data["page_title"] = page.title()

        except Exception as e:
            logger.warning("Error in page_action hook: %s", e)

    def fetch_blueprint(
        self,
        url: str,
        headless: bool = True,
        timeout: int = 45000,
    ) -> tuple[UpWorkPageBlueprint, str]:
        """Fetch UpWork page via Scrapling StealthySession and return its UI blueprint and raw HTML."""
        self._action_data.clear()
        self._captured_xhr.clear()
        self._response_handler = None

        session = self.session_manager.create_session(headless=headless, timeout=timeout)
        with session:
            logger.info("Navigating to %s (headless=%s)...", url, headless)
            response = session.fetch(
                url,
                page_setup=self._page_setup,
                page_action=self._page_action,
                network_idle=True,
                load_dom=True,
                solve_cloudflare=True,
            )

            status_code = getattr(response, "status", 200)
            raw_body = getattr(response, "body", b"")
            html_text = (
                raw_body.decode("utf-8", errors="replace")
                if isinstance(raw_body, bytes)
                else str(raw_body)
            )

            blueprint = build_page_blueprint(
                html_content=html_text,
                url=url,
                title=self._action_data.get("page_title", ""),
                status_code=status_code,
                is_authenticated=self._action_data.get("is_authenticated", False),
                proxy_used=self.session_manager.proxy_config.get_display_summary(),
                screenshot_path=self._action_data.get("screenshot_path"),
                captured_xhr=list(dict.fromkeys(self._captured_xhr)),
            )

            return blueprint, html_text

"""Scrapling StealthySession transport adapter with persistent browser context and sticky proxies."""

from __future__ import annotations

import contextlib
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.adapters.base import FetchRequest, FetchResponse
from src.ui_inspector.engine import HYDRATE_PAGE_JS
from src.ui_inspector.proxy_pinning import PinnedProxyConfig, resolve_pinned_proxy
from src.ui_inspector.session_manager import UpWorkSessionManager

if TYPE_CHECKING:
    from playwright.sync_api import Page
    from scrapling.fetchers import StealthySession

logger = logging.getLogger(__name__)


class StealthySessionAdapter:
    """Transport adapter executing fetches through Scrapling StealthySession with persistent context."""

    adapter_name: str = "stealthy_session"

    def __init__(
        self,
        user_data_dir: str | Path = "./.session/chrome_profile",
        storage_state_file: str | Path = "./.session/storage_state.json",
        proxy_file: str | Path | None = None,
        proxy_mode: str = "pinned",
        proxy_index: int = 0,
        proxy_url: str | None = None,
        cdp_url: str | None = None,
        max_timeout_ms: int = 60000,
        max_retries: int = 2,
        retry_backoff_seconds: float = 3.0,
        headless: bool = True,
    ) -> None:
        self.user_data_dir = Path(user_data_dir)
        self.storage_state_file = Path(storage_state_file)
        self.max_timeout_ms = max_timeout_ms
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.headless = headless

        # Check existing session_meta.json to honor previously saved connection mode
        meta_file = self.user_data_dir.parent / "session_meta.json"
        is_direct = proxy_mode == "direct"
        if not is_direct and meta_file.is_file() and not proxy_url:
            try:
                import json
                with open(meta_file, encoding="utf-8") as f:
                    meta = json.load(f)
                if meta.get("direct") is True:
                    logger.info("Found direct:true in session_meta.json; honoring direct connection mode")
                    is_direct = True
            except Exception:
                pass

        if is_direct:
            proxy_cfg = PinnedProxyConfig(proxy_url=None)
        elif proxy_url:
            proxy_cfg = PinnedProxyConfig(proxy_url=proxy_url, proxy_index=proxy_index)
        else:
            proxy_cfg = resolve_pinned_proxy(
                proxy_file=str(proxy_file) if proxy_file else None,
                proxy_index=proxy_index,
                direct=False,
            )

        self.session_manager = UpWorkSessionManager(
            user_data_dir=self.user_data_dir,
            storage_state_file=self.storage_state_file,
            proxy_config=proxy_cfg,
            cdp_url=cdp_url,
        )

        self._session: StealthySession | None = None

    def _get_or_create_session(self) -> StealthySession:
        """Lazily initialize and enter the persistent Scrapling session."""
        if self._session is None:
            session = self.session_manager.create_session(
                headless=self.headless,
                timeout=self.max_timeout_ms,
            )
            # Enter the session context manager
            self._session = session.__enter__()
        return self._session

    def fetch(self, request: FetchRequest) -> FetchResponse:
        """Fetch URL using persistent StealthySession and return FetchResponse."""
        start_time = time.time()
        last_error: str | None = None
        last_status: int = 0

        effective_retries = (
            request.max_retries if request.max_retries is not None else self.max_retries
        )

        for attempt in range(1, effective_retries + 1):
            try:
                session = self._get_or_create_session()

                def _page_action(page: Page) -> None:
                    # Check auth and backup state if needed
                    is_auth = self.session_manager.check_auth_indicators(page)
                    if is_auth and page.context:
                        self.session_manager.backup_storage_state(page.context)

                    # Progressive hydration if requested
                    if request.auto_scroll:
                        with contextlib.suppress(Exception):
                            page.evaluate(HYDRATE_PAGE_JS)

                    if request.wait_selector:
                        with contextlib.suppress(Exception):
                            page.wait_for_selector(request.wait_selector, timeout=10000)

                logger.info(
                    "[%s] Navigating to %s (attempt %d/%d)...",
                    self.adapter_name,
                    request.url,
                    attempt,
                    effective_retries,
                )

                fetch_kwargs: dict[str, Any] = {
                    "network_idle": True,
                    "load_dom": True,
                    "solve_cloudflare": True,
                }
                if request.auto_scroll or request.wait_selector:
                    fetch_kwargs["page_action"] = _page_action

                response = session.fetch(request.url, **fetch_kwargs)

                status_code = getattr(response, "status", 200)
                raw_body = getattr(response, "body", b"")
                html_text = (
                    raw_body.decode("utf-8", errors="replace")
                    if isinstance(raw_body, bytes)
                    else str(raw_body)
                )

                last_status = status_code
                if status_code != 200 or not html_text.strip():
                    last_error = f"HTTP {status_code} or empty response"
                    logger.warning(
                        "[%s] Attempt %d/%d returned status %d",
                        self.adapter_name,
                        attempt,
                        effective_retries,
                        status_code,
                    )
                    time.sleep(self.retry_backoff_seconds * attempt)
                    continue

                elapsed = time.time() - start_time
                return FetchResponse(
                    url=request.url,
                    status=status_code,
                    html=html_text,
                    error=None,
                    session_id=str(self.user_data_dir),
                    elapsed_seconds=elapsed,
                    adapter_name=self.adapter_name,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "[%s] Attempt %d/%d exception for %s: %s",
                    self.adapter_name,
                    attempt,
                    effective_retries,
                    request.url,
                    e,
                )
                # If session crashed or broke, reset it so next attempt recreates
                self.close()
                time.sleep(self.retry_backoff_seconds * attempt)

        elapsed = time.time() - start_time
        return FetchResponse(
            url=request.url,
            status=last_status,
            html="",
            error=last_error or "All fetch attempts failed",
            elapsed_seconds=elapsed,
            adapter_name=self.adapter_name,
        )

    def close(self) -> None:
        """Close active session and release browser resources."""
        if self._session is not None:
            try:
                self._session.__exit__(None, None, None)
            except Exception as e:
                logger.debug("Error while closing StealthySession: %s", e)
            finally:
                self._session = None

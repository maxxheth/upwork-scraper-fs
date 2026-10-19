"""Persistent user session lifecycle manager for UpWork via Scrapling."""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

from scrapling.fetchers import StealthySession

from src.ui_inspector.proxy_pinning import PinnedProxyConfig

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

logger = logging.getLogger(__name__)


def is_chrome_installed() -> bool:
    """Check if real Chrome/Chromium executable is available."""
    return bool(shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chrome"))


class UpWorkSessionManager:
    """Manages persistent browser profiles, login authentication, and cookie backups."""

    def __init__(
        self,
        user_data_dir: str | Path = "./.session/chrome_profile",
        storage_state_file: str | Path = "./.session/storage_state.json",
        proxy_config: PinnedProxyConfig | None = None,
        cdp_url: str | None = None,
    ) -> None:
        self.user_data_dir = Path(user_data_dir).resolve()
        self.storage_state_file = Path(storage_state_file).resolve()
        self.meta_file = self.user_data_dir.parent / "session_meta.json"
        self.proxy_config = proxy_config or PinnedProxyConfig()
        self.cdp_url = cdp_url
        self.real_chrome = is_chrome_installed()

        # Ensure directory structure exists
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.storage_state_file.parent.mkdir(parents=True, exist_ok=True)

    def save_session_meta(self, direct: bool = False, proxy_index: int | None = None) -> None:
        """Persist last-used connection mode so subsequent runs match automatically."""
        meta = {
            "direct": direct,
            "proxy_index": proxy_index,
            "proxy_url": self.proxy_config.proxy_url,
        }
        try:
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            os.chmod(self.meta_file, 0o600)
        except Exception as e:
            logger.debug("Could not write session metadata: %s", e)

    def load_session_meta(self) -> dict[str, Any] | None:
        """Load last-used connection mode if present."""
        if not self.meta_file.is_file():
            return None
        try:
            with open(self.meta_file, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def create_session(
        self,
        headless: bool = True,
        timeout: int = 45000,
    ) -> StealthySession:
        """Create a Scrapling StealthySession configured with user_data_dir and sticky proxy."""
        session_kwargs: dict[str, Any] = {
            "headless": headless,
            "real_chrome": self.real_chrome,
            "solve_cloudflare": True,
            "timeout": timeout,
        }

        if self.cdp_url:
            session_kwargs["cdp_url"] = self.cdp_url
            logger.info("Connecting to existing browser via CDP: %s", self.cdp_url)
        else:
            # Persistent context mode in Scrapling
            session_kwargs["user_data_dir"] = str(self.user_data_dir)
            logger.info("Using persistent Chrome user_data_dir: %s", self.user_data_dir)

        if self.proxy_config.has_proxy and self.proxy_config.proxy_url:
            session_kwargs["proxy"] = self.proxy_config.proxy_url
            logger.info("Using %s", self.proxy_config.get_display_summary())

        # If backup cookies exist, seed session with them
        if self.storage_state_file.is_file():
            try:
                with open(self.storage_state_file, encoding="utf-8") as f:
                    state = json.load(f)
                cookies = state.get("cookies", [])
                if cookies and not self.cdp_url:
                    session_kwargs["cookies"] = cookies
                    logger.debug("Seeded session with %d cookies from %s", len(cookies), self.storage_state_file)
            except Exception as e:
                logger.debug("Could not read cookies from storage state: %s", e)

        return StealthySession(**session_kwargs)

    def backup_storage_state(self, context: BrowserContext) -> None:
        """Export browser storage state (cookies + localStorage) to disk with restricted permissions."""
        try:
            state = context.storage_state()
            with open(self.storage_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            os.chmod(self.storage_state_file, 0o600)
            logger.info("Saved storage state backup to %s", self.storage_state_file)
        except Exception as e:
            logger.warning("Could not backup storage state: %s", e)

    def check_auth_indicators(self, page: Page) -> bool:
        """Check whether the current page indicates an authenticated user session.

        Requires affirmative evidence of a logged-in freelancer account rather than
        assuming authentication from the absence of a login button.
        """
        try:
            url = page.url
            if "/ab/account-security/login" in url or "/login" in url:
                return False

            # Positive selector checks for logged-in UI elements
            auth_selectors = [
                "[data-test='nav-user-menu']",
                ".air3-avatar",
                "[data-test='find-work-home']",
                "button[aria-label*='User menu']",
                "nav.air3-nav-freelancer",
                "[data-cy='user-menu']",
                "#nav-right .air3-dropdown",
            ]
            for sel in auth_selectors:
                if page.locator(sel).count() > 0:
                    return True

            # Positive cookie check for UpWork session tokens
            try:
                cookies = page.context.cookies(["https://www.upwork.com"])
                auth_cookie_names = {
                    "oauth2_global_js_token",
                    "master_access_token",
                    "user_uid",
                    "XSRF-TOKEN",
                }
                found = {c["name"] for c in cookies if "name" in c and c["name"] in auth_cookie_names}
                # Must have at least user_uid or oauth2 token
                if "user_uid" in found or "oauth2_global_js_token" in found or "master_access_token" in found:
                    return True
            except Exception:
                pass

            return False
        except Exception:
            return False

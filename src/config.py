"""Configuration loading from .env and environment."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_config() -> dict[str, str | int | None]:
    """Load configuration from .env file and environment variables.

    Returns a flat dict of config keys.
    """
    # Find .env — look in project root first, then cwd
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # fallback to cwd

    flaresolverr_url = os.getenv("FLARESOLVERR_URL", "http://localhost:8193")
    proxy_file = os.getenv("PROXY_FILE", str(project_root / "proxies.txt"))
    output_dir = os.getenv("OUTPUT_DIR", str(project_root / "output"))

    user_data_dir = os.getenv("UPWORK_USER_DATA_DIR", str(project_root / ".session" / "chrome_profile"))
    storage_state_file = os.getenv("UPWORK_STORAGE_STATE", str(project_root / ".session" / "storage_state.json"))
    proxy_index_str = os.getenv("UPWORK_SESSION_PROXY_INDEX", "0")
    try:
        session_proxy_index = int(proxy_index_str)
    except ValueError:
        session_proxy_index = 0
    session_proxy_url = os.getenv("UPWORK_SESSION_PROXY_URL")
    cdp_url = os.getenv("UPWORK_CDP_URL")
    ui_report_dir = os.getenv("UI_REPORT_DIR", str(project_root / "output" / "ui_reports"))

    return {
        "flaresolverr_url": flaresolverr_url.rstrip("/"),
        "proxy_file": proxy_file,
        "output_dir": output_dir,
        "user_data_dir": user_data_dir,
        "storage_state_file": storage_state_file,
        "session_proxy_index": session_proxy_index,
        "session_proxy_url": session_proxy_url,
        "cdp_url": cdp_url,
        "ui_report_dir": ui_report_dir,
    }


def load_proxies(proxy_file: str) -> list[str]:
    """Load proxy URLs from a file (one per line, blank lines ignored)."""
    path = Path(proxy_file)
    if not path.exists():
        return []

    proxies: list[str] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                proxies.append(line)
    return proxies

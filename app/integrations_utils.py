"""
Post-download integrations (e.g., Jellyfin refresh hooks).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import requests

from app.config import get_settings


DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class JellyfinScanResult:
    """Result of a Jellyfin library refresh attempt."""

    success: bool
    message: str
    status_code: Optional[int] = None


def trigger_jellyfin_library_scan(
    base_url: str,
    api_key: str,
    session: Optional[requests.Session] = None,
    log: Optional[Callable[[str], None]] = None,
) -> JellyfinScanResult:
    """
    Trigger a Jellyfin library scan (all libraries).

    Args:
        base_url: Base URL of the Jellyfin server (e.g., https://jellyfin.local:8096).
        api_key: Jellyfin API key (X-Emby-Token).
        session: Optional pre-configured requests Session (helps testing).
        log: Optional callable used for diagnostic logging.

    Returns:
        JellyfinScanResult indicating success or failure.
    """
    if not base_url or not api_key:
        return JellyfinScanResult(
            success=False,
            message="Missing Jellyfin base URL or API key.",
        )

    logger = log or (lambda _: None)
    client = session or requests.Session()
    normalized_url = base_url.rstrip("/")
    headers = {
        "X-Emby-Token": api_key.strip(),
    }

    refresh_endpoint = f"{normalized_url}/Library/Refresh"
    try:
        logger(f"POST {refresh_endpoint} (full library scan)")
        response = client.post(
            refresh_endpoint,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as exc:
        error_message = f"Jellyfin refresh request failed: {exc}"
        logger(error_message)
        return JellyfinScanResult(
            success=False,
            message=error_message,
        )

    if 200 <= response.status_code < 300:
        return JellyfinScanResult(
            success=True,
            message="Jellyfin library refresh triggered successfully.",
            status_code=response.status_code,
        )

    try:
        response_text = response.text.strip()
    except Exception:  # noqa: BLE001
        response_text = ""

    failure_message = (
        f"Jellyfin refresh failed with status {response.status_code}. {response_text}"
    ).strip()
    logger(failure_message)
    return JellyfinScanResult(
        success=False,
        message=failure_message,
        status_code=response.status_code,
    )


def post_download_actions(
    log: Callable[[str], None],
    log_title: Callable[[str], None],
) -> None:
    """
    Execute media server integrations after a successful download.

    Currently triggers a Jellyfin full-library refresh when configured.
    """
    settings = get_settings()
    base_url = (settings.JELLYFIN_BASE_URL or "").strip()
    api_key = (settings.JELLYFIN_API_KEY or "").strip()

    if not (base_url and api_key):
        return

    log("")
    log_title("📡 Jellyfin Integration")

    result = trigger_jellyfin_library_scan(
        base_url=base_url,
        api_key=api_key,
        log=log,
    )

    if result.success:
        log(result.message)
    else:
        log(f"⚠️ {result.message}")

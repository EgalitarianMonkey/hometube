"""Optional hand-offs to external media services once a download completes.

Every integration here is inert until it is configured, and none of them may
turn a successful download into a failed one. The file is already on disk by
the time any of this runs; a media server that is asleep, unreachable or
misconfigured is a footnote, not an error. So each helper swallows its own
transport failures, reports them through the caller's logger and returns a
boolean rather than raising.
"""

import requests

from app.config import get_settings

# Jellyfin's public API: an authenticated POST asking the server to rescan its
# libraries. The token travels in a header rather than the query string so it
# does not end up in the server's access log.
JELLYFIN_REFRESH_PATH = "/Library/Refresh"
JELLYFIN_AUTH_HEADER = "X-Emby-Token"
JELLYFIN_TIMEOUT_SECONDS = 5


def jellyfin_is_configured() -> bool:
    """True when both a server URL and an API key are set."""
    settings = get_settings()
    return bool(
        (settings.JELLYFIN_BASE_URL or "").strip()
        and (settings.JELLYFIN_API_KEY or "").strip()
    )


def trigger_jellyfin_library_scan(log_fn=None) -> bool:
    """Ask Jellyfin to rescan its libraries so a new file is picked up.

    Returns True only when the server accepted the request. Returns False when
    the integration is not configured or the call did not succeed; it never
    raises, deliberately — see the module docstring.
    """
    settings = get_settings()
    base_url = (settings.JELLYFIN_BASE_URL or "").strip().rstrip("/")
    api_key = (settings.JELLYFIN_API_KEY or "").strip()

    if not base_url or not api_key:
        return False

    try:
        response = requests.post(
            f"{base_url}{JELLYFIN_REFRESH_PATH}",
            headers={JELLYFIN_AUTH_HEADER: api_key},
            timeout=JELLYFIN_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        if log_fn:
            log_fn(f"⚠️ Jellyfin library scan could not be requested: {error}")
        return False

    if log_fn:
        log_fn("✅ Jellyfin library scan requested")
    return True


def post_download_actions(log_fn=None, title_fn=None) -> None:
    """Run whatever should happen once a download has finished.

    Stays silent when nothing is configured, so users who run no media server
    never see a section about one.
    """
    if not jellyfin_is_configured():
        return

    if title_fn:
        title_fn("Post-download actions")

    trigger_jellyfin_library_scan(log_fn)

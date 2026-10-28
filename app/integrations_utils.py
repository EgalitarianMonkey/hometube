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
# Modern auth: the key travels in an Authorization header using the MediaBrowser
# scheme — what the official clients send. Jellyfin 12.4 rejects the legacy
# `X-Emby-Token` header with 401; the MediaBrowser form is accepted by both
# current and older servers, so it is tried first.
JELLYFIN_AUTHORIZATION_HEADER = "Authorization"
# Legacy header, kept only as a fallback for old servers or forks that predate
# the MediaBrowser Authorization scheme.
JELLYFIN_AUTH_HEADER = "X-Emby-Token"
JELLYFIN_TIMEOUT_SECONDS = 5


def _jellyfin_authorization_value(api_key: str) -> str:
    """Build the ``Authorization: MediaBrowser Token="<key>"`` header value."""
    return f'MediaBrowser Token="{api_key}"'


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

    url = f"{base_url}{JELLYFIN_REFRESH_PATH}"
    # Modern header first; the legacy one is only worth retrying when the server
    # rejected the credentials (401/403). Any other status (404, 5xx) will not
    # change with a different header, so there is no point trying twice.
    header_attempts = [
        {JELLYFIN_AUTHORIZATION_HEADER: _jellyfin_authorization_value(api_key)},
        {JELLYFIN_AUTH_HEADER: api_key},
    ]

    last_status = None
    for headers in header_attempts:
        try:
            response = requests.post(
                url, headers=headers, timeout=JELLYFIN_TIMEOUT_SECONDS
            )
        except requests.RequestException as error:
            if log_fn:
                log_fn(f"⚠️ Jellyfin library scan could not be requested: {error}")
            return False

        if response.status_code < 400:
            if log_fn:
                log_fn("✅ Jellyfin library scan requested")
            return True

        last_status = response.status_code
        if response.status_code not in (401, 403):
            break

    # A configured-but-refused integration must not look identical to one that
    # is simply not configured: say so, once.
    if log_fn:
        log_fn(
            f"⚠️ Jellyfin library scan was refused (HTTP {last_status}); "
            "check JELLYFIN_BASE_URL and JELLYFIN_API_KEY"
        )
    return False


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

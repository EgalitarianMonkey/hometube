"""
Version Checking Module for HomeTube

Handles version checking for both yt-dlp and HomeTube itself.
Provides functionality to check current versions, fetch latest versions,
and display update information in the UI.
"""

import json
import os
import subprocess

import requests
import streamlit as st

from app.translations import t

# === CONSTANTS ===
HOMETUBE_GITHUB_REPO = "EgalitarianMonkey/hometube"  # GitHub repository for HomeTube

# `UNKNOWN_VERSION` is the placeholder the update panel substitutes for a
# lookup that came back None, and the three statuses are everything it can
# report about a pair of versions.
UNKNOWN_VERSION = "unknown"
STATUS_UP_TO_DATE = "✅ Up to date"
STATUS_UPDATE_AVAILABLE = "🔄 Update available"
STATUS_UNKNOWN = "❓ Could not compare"


# === YT-DLP VERSION CHECK ===


def get_current_ytdlp_version() -> str | None:
    """Get the currently installed yt-dlp version."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None


def get_latest_ytdlp_version() -> str | None:
    """Get the latest yt-dlp version from GitHub API."""
    # Environment variable for testing
    test_version = os.getenv("TEST_LATEST_YTDLP_VERSION")
    if test_version:
        return test_version

    try:
        response = requests.get(
            "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest", timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("tag_name", "").lstrip("v")  # Remove 'v' prefix if present
    except (requests.RequestException, json.JSONDecodeError, Exception):
        pass
    return None


# === HOMETUBE VERSION CHECK ===


def get_current_hometube_version() -> str | None:
    """Get the current HomeTube version from pyproject.toml."""
    try:
        import tomllib

        pyproject_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "pyproject.toml"
        )
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version")
    except (FileNotFoundError, ImportError, Exception):
        # Fallback for Python < 3.11 or if tomllib not available
        try:
            pyproject_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "pyproject.toml"
            )
            with open(pyproject_path, "r") as f:
                for line in f:
                    if line.strip().startswith("version = "):
                        # Extract version from line like: version = "0.7.1"
                        return line.split('"')[1]
        except (FileNotFoundError, IndexError, Exception):
            pass
    return None


def get_latest_hometube_version() -> str | None:
    """Get the latest HomeTube version from GitHub API."""
    # Environment variable for testing
    test_version = os.getenv("TEST_LATEST_HOMETUBE_VERSION")
    if test_version:
        return test_version

    try:
        response = requests.get(
            f"https://api.github.com/repos/{HOMETUBE_GITHUB_REPO}/releases/latest",
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("tag_name", "").lstrip("v")  # Remove 'v' prefix if present
        elif response.status_code == 404:
            # Repository might not have releases yet, try tags
            response = requests.get(
                f"https://api.github.com/repos/{HOMETUBE_GITHUB_REPO}/tags", timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return data[0].get("name", "").lstrip("v")
    except (requests.RequestException, json.JSONDecodeError, Exception):
        pass
    return None


# === VERSION COMPARISON ===


def _comparable_version(value: str | None) -> tuple | None:
    """Parse a version into a comparable tuple, or None when there is none.

    Returns None for a missing version, for the `unknown` placeholder, and for
    anything `parse_version` cannot read — it answers `(0, 0, 0)` in that case,
    and neither HomeTube nor yt-dlp has ever published a `0.0.0`, so that value
    means "unparseable" here rather than a real version.
    """
    if not value or value == UNKNOWN_VERSION:
        return None

    # Imported lazily, mirroring `notifications.get_latest_version()`, which
    # imports this module the same way: the two modules reference each other.
    from app.notifications import parse_version

    parsed = parse_version(value)
    return None if parsed == (0, 0, 0) else parsed


def describe_version_status(current: str | None, latest: str | None) -> str:
    """Say whether `latest` is actually newer than `current`.

    Compares parsed `(major, minor, patch)` tuples rather than the two strings.
    Equality is the wrong test in three ways, all of them observed:

    * **Running ahead of the latest release.** A published release can lag the
      running build — a release left in draft is invisible to
      `/releases/latest`, which is exactly the state 2.13.3 shipped in — and an
      inequality then told the user to "update" to a version *older* than
      theirs.
    * **A failed lookup.** Both sides fall back to `unknown`, and
      `"unknown" == "unknown"` reported ✅ *Up to date*: a check that reached
      nothing claimed success, while a half-failed one offered an update to
      `unknown`.
    * **Dotted dates don't compare as strings.** yt-dlp numbers its releases
      `2026.9.1`, `2026.10.26`; `"2026.9.1" > "2026.10.26"` lexically, so the
      newer release reads as older.
    """
    current_tuple = _comparable_version(current)
    latest_tuple = _comparable_version(latest)

    if current_tuple is None or latest_tuple is None:
        return STATUS_UNKNOWN

    return (
        STATUS_UPDATE_AVAILABLE if latest_tuple > current_tuple else STATUS_UP_TO_DATE
    )


# === UI DISPLAY FUNCTIONS ===


def check_and_show_updates() -> None:
    """
    Simplified function to check and display update information
    Called when user clicks the update check button in sidebar
    """
    try:
        # Get current versions
        ytdlp_current = get_current_ytdlp_version() or UNKNOWN_VERSION
        ytdlp_latest = get_latest_ytdlp_version() or UNKNOWN_VERSION
        hometube_current = get_current_hometube_version() or UNKNOWN_VERSION
        hometube_latest = get_latest_hometube_version() or UNKNOWN_VERSION

        # Build information message
        update_info_markdown = f"""
**🔄 Update Information**

**HomeTube:**

**{t('update_current_version')}:** {hometube_current}  
**{t('update_latest_version')}:** {hometube_latest}  
**Status:** {describe_version_status(hometube_current, hometube_latest)}

**yt-dlp:**

**{t('update_current_version')}:** {ytdlp_current}  
**{t('update_latest_version')}:** {ytdlp_latest}  
**Status:** {describe_version_status(ytdlp_current, ytdlp_latest)}

**{t('update_docker_title')}:**

{t('update_docker_instruction')}

{t('update_docker_command')}

**{t('update_local_title')} (yt-dlp):**

{t('update_local_instruction')}

**{t('update_git_title')} (HomeTube):**

{t('update_git_instruction')}
            """
        st.info(update_info_markdown)

    except Exception as e:
        # Never break the app, but show a friendly error
        st.error(f"⚠️ Could not check for updates: {str(e)}")
        st.info("Please check for updates manually using the commands above.")


def display_version_check_button() -> None:
    """Display the version check button in the sidebar."""
    if st.button("🔄 Check for updates", use_container_width=True):
        check_and_show_updates()

"""
Version Checking Module for HomeTube

Handles version checking for both yt-dlp and HomeTube itself.
Provides functionality to check current versions, fetch latest versions,
and display update information in the UI.
"""

import json
import os
import subprocess
from typing import Optional

import requests
import streamlit as st

try:
    from .translations import t
except ImportError:
    from translations import t


# === CONSTANTS ===
HOMETUBE_GITHUB_REPO = "EgalitarianMonkey/hometube"  # GitHub repository for HomeTube


# === YT-DLP VERSION CHECK ===


def get_current_ytdlp_version() -> Optional[str]:
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


def get_latest_ytdlp_version() -> Optional[str]:
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


def get_current_hometube_version() -> Optional[str]:
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


def get_latest_hometube_version() -> Optional[str]:
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


# === UI DISPLAY FUNCTIONS ===


def check_and_show_updates() -> None:
    """
    Simplified function to check and display update information
    Called when user clicks the update check button in sidebar
    """
    try:
        # Get current versions
        ytdlp_current = get_current_ytdlp_version() or "unknown"
        ytdlp_latest = get_latest_ytdlp_version() or "unknown"
        hometube_current = get_current_hometube_version() or "unknown"
        hometube_latest = get_latest_hometube_version() or "unknown"

        # Build information message
        update_info_markdown = f"""
**🔄 Update Information**

**HomeTube:**

**{t('update_current_version')}:** {hometube_current}  
**{t('update_latest_version')}:** {hometube_latest}  
**Status:** {"✅ Up to date" if hometube_current == hometube_latest else "🔄 Update available"}

**yt-dlp:**

**{t('update_current_version')}:** {ytdlp_current}  
**{t('update_latest_version')}:** {ytdlp_latest}  
**Status:** {"✅ Up to date" if ytdlp_current == ytdlp_latest else "🔄 Update available"}

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

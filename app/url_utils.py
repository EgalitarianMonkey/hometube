"""
URL analysis utilities for HomeTube.

This module provides pure functions for URL analysis logic,
without Streamlit dependencies, making them easy to test.
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Tuple

from app.logs_utils import safe_push_log


# === URL MANIPULATION ===


def sanitize_url(url: str) -> str:
    """
    Clean and validate URL, removing YouTube timestamp parameters.

    Args:
        url: URL to sanitize

    Returns:
        Cleaned URL
    """
    if not url:
        return ""

    url = url.strip()

    # Add protocol if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Remove YouTube timestamp parameters (HomeTube specific)
    url = url.split("&t=")[0]
    url = url.split("?t=")[0]

    return url


def video_id_from_url(url: str) -> str:
    """
    Extract video ID from YouTube URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID or empty string if not found
    """
    if not url:
        return ""

    # Standard YouTube URL patterns
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",  # Support for Shorts
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return ""


# === URL INFO FILE OPERATIONS ===


def load_url_info_from_file(file_path: Path) -> Optional[Dict]:
    """
    Load URL info from a JSON file.

    Args:
        file_path: Path to the JSON file (e.g., tmp/url_info.json)

    Returns:
        Dictionary with URL info or None if error
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error loading URL info from {file_path}: {e}")
        return None


def save_url_info(json_path: Path, url_info: Dict) -> bool:
    """
    Save URL info to JSON file.

    Args:
        json_path: Path where to save the JSON file
        url_info: Dictionary with URL information

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Ensure parent directory exists
        json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(url_info, f, indent=2, ensure_ascii=False)

        safe_push_log(f"💾 URL info saved to {json_path}")
        return True

    except Exception as e:
        safe_push_log(f"⚠️ Could not save URL info to file: {e}")
        return False


def check_url_info_integrity(url_info: Dict) -> bool:
    """
    Check if url_info contains premium formats (AV1 or VP9).

    Sometimes YouTube returns limited format information (only h264),
    even when premium formats are available. This function detects
    incomplete responses that should be retried.

    Args:
        url_info: Dictionary from yt-dlp JSON output

    Returns:
        bool: True if premium formats (AV1/VP9) are present, False if only h264
    """
    if not url_info or "error" in url_info:
        return False

    formats = url_info.get("formats", [])
    if not formats:
        return False

    # Check for premium codecs in video formats
    for fmt in formats:
        vcodec = fmt.get("vcodec", "").lower()

        # Skip audio-only formats
        if vcodec == "none":
            continue

        # Check for AV1 codec
        if "av01" in vcodec or "av1" in vcodec:
            return True

        # Check for VP9 codec
        if "vp9" in vcodec or "vp09" in vcodec:
            return True

    # If we only found h264/avc formats, this might be incomplete
    return False


# === INTELLIGENT CACHING ===


def should_reuse_url_info(json_path: Path) -> Tuple[bool, Optional[Dict]]:
    """
    Check if existing url_info.json should be reused based on integrity.

    Strategy:
    1. If file doesn't exist → download needed (False, None)
    2. If file is corrupted → download needed (False, None)
    3. If it's a playlist → always reuse (True, data)
    4. If it's a video:
       - Has premium formats (AV1/VP9) → reuse (True, data)
       - Only h264 formats → download needed (False, None)

    Args:
        json_path: Path to url_info.json file

    Returns:
        Tuple[bool, Optional[Dict]]:
        - bool: True if should reuse, False if should download
        - Optional[Dict]: The loaded data if reusable, None otherwise
    """
    # Check if file exists
    if not json_path.exists():
        safe_push_log(f"📋 No existing url_info.json at {json_path}")
        return False, None

    # Try to load and parse the file
    try:
        safe_push_log("📋 Found existing url_info.json, checking integrity...")
        with open(json_path, "r", encoding="utf-8") as f:
            existing_info = json.load(f)

        # Check if it's a video or playlist
        is_video = existing_info.get("_type") == "video" or "duration" in existing_info
        is_playlist = existing_info.get("_type") == "playlist"

        # For playlists, always reuse
        if is_playlist:
            safe_push_log("✅ Existing url_info.json (playlist) - reusing it")
            return True, existing_info

        # For videos, check integrity (premium formats presence)
        if is_video:
            has_premium = check_url_info_integrity(existing_info)

            if has_premium:
                safe_push_log(
                    "✅ Existing url_info.json has premium formats - reusing it"
                )
                return True, existing_info
            else:
                safe_push_log(
                    "⚠️ Existing url_info.json has limited formats (h264 only) - will re-download"
                )
                return False, None

        # Unknown type, be safe and re-download
        safe_push_log(
            f"⚠️ Unknown content type in url_info.json: {existing_info.get('_type')} - will re-download"
        )
        return False, None

    except json.JSONDecodeError as e:
        safe_push_log(f"⚠️ Corrupted url_info.json: {e} - will re-download")
        return False, None
    except KeyError as e:
        safe_push_log(f"⚠️ Invalid url_info.json structure: {e} - will re-download")
        return False, None
    except Exception as e:
        safe_push_log(f"⚠️ Could not read url_info.json: {e} - will re-download")
        return False, None

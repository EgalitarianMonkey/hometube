"""
URL analysis utilities for HomeTube.

This module provides pure functions for URL analysis logic,
without Streamlit dependencies, making them easy to test.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Tuple

from app.medias_utils import check_url_info_integrity
from app.logs_utils import safe_push_log


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

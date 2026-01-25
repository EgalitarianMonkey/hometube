"""
Playlist management utilities for HomeTube.

This module provides functions for handling YouTube playlists:
- Detection and analysis of playlist URLs
- Checking existing videos in destination folder
- Progress tracking for playlist downloads
- Creating folder structure for playlist videos
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.file_system_utils import (
    sanitize_filename,
    ensure_dir,
    move_final_to_destination,
)
from app.logs_utils import safe_push_log
from app.text_utils import render_title

# === PLAYLIST DETECTION ===


def is_playlist_url(url: str) -> bool:
    """
    Check if URL is a YouTube playlist URL.

    Args:
        url: URL to check

    Returns:
        bool: True if URL is a playlist URL
    """
    if not url:
        return False

    # YouTube playlist patterns
    patterns = [
        r"youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)",
    ]

    for pattern in patterns:
        if re.search(pattern, url):
            return True

    return False


def extract_playlist_id(url: str) -> Optional[str]:
    """
    Extract playlist ID from YouTube playlist URL.

    Args:
        url: YouTube playlist URL

    Returns:
        str: Playlist ID or None if not found
    """
    if not url:
        return None

    match = re.search(r"youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)", url)
    if match:
        return match.group(1)

    return None


def is_playlist_info(url_info: Dict) -> bool:
    """
    Check if url_info represents a playlist.

    Args:
        url_info: Dict from yt-dlp JSON output

    Returns:
        bool: True if this is a playlist
    """
    if not url_info:
        return False

    return url_info.get("_type") == "playlist" or (
        "entries" in url_info and "playlist_count" in url_info
    )


# === PLAYLIST ENTRIES ===


def get_playlist_entries(url_info: Dict) -> List[Dict]:
    """
    Get list of video entries from playlist info.

    Args:
        url_info: Dict from yt-dlp JSON output

    Returns:
        List of video entry dicts with id, title, url, etc.
    """
    if not url_info or not is_playlist_info(url_info):
        return []

    entries = url_info.get("entries", [])
    result = []
    for idx, e in enumerate(entries, 1):  # 1-based index
        if e is not None and isinstance(e, dict):
            # Add playlist_index to each entry for pattern rendering
            entry_with_index = e.copy()
            entry_with_index["playlist_index"] = idx
            result.append(entry_with_index)
    return result


def get_playlist_video_count(url_info: Dict) -> int:
    """
    Get total video count from playlist info.

    Args:
        url_info: Dict from yt-dlp JSON output

    Returns:
        int: Total number of videos in playlist
    """
    if not url_info:
        return 0

    # Use playlist_count if available (more accurate)
    playlist_count = url_info.get("playlist_count")
    if playlist_count is not None:
        return int(playlist_count)

    # Fallback to counting entries
    entries = get_playlist_entries(url_info)
    return len(entries)


# === DESTINATION FOLDER CHECKING ===


def check_existing_videos_in_destination(
    dest_dir: Path,
    playlist_entries: List[Dict],
    video_extensions: List[str] = None,
    playlist_workspace: Optional[Path] = None,
    title_pattern: Optional[str] = None,
) -> Tuple[List[Dict], List[Dict], int]:
    """
    Check which playlist videos already exist in destination folder.

    Uses multiple strategies:
    1. Check status.json in playlist workspace for "completed" status with resolved_title
    2. Check filesystem for files matching the title pattern (if provided)
    3. Check filesystem for existing video files by title or video ID

    Args:
        dest_dir: Destination directory to check
        playlist_entries: List of video entries from get_playlist_entries()
        video_extensions: List of video extensions to check (default: [".mkv", ".mp4", ".webm"])
        playlist_workspace: Optional path to playlist workspace to check status.json
        title_pattern: Optional title pattern for filename matching

    Returns:
        Tuple of:
        - List of entries that exist in destination (already downloaded)
        - List of entries that need to be downloaded
        - Total count for ratio display
    """
    if video_extensions is None:
        video_extensions = [".mkv", ".mp4", ".webm", ".avi", ".mov"]

    # First, check status.json if playlist workspace is provided
    status_completed_videos = {}  # video_id -> video_data (for resolved_title)
    if playlist_workspace:
        status_data = load_playlist_status(playlist_workspace)
        if status_data:
            videos = status_data.get("videos", {})
            for video_id, video_data in videos.items():
                if video_data.get("status") == "completed":
                    status_completed_videos[video_id] = video_data

    # Build set of existing filenames in destination
    existing_files_set = set()
    if dest_dir.exists():
        for ext in video_extensions:
            for f in dest_dir.glob(f"*{ext}"):
                existing_files_set.add(f.name)

    # Normalize filenames for comparison (legacy method)
    existing_names = set()
    existing_video_ids = set()
    for filename in existing_files_set:
        # Store normalized name (without extension)
        name_without_ext = Path(filename).stem
        normalized = _normalize_for_comparison(name_without_ext)
        existing_names.add(normalized)
        # Also check if any video ID is in the filename
        for entry in playlist_entries:
            video_id = entry.get("id", "")
            if video_id and video_id in name_without_ext:
                existing_video_ids.add(video_id)

    already_downloaded = []
    to_download = []

    for entry in playlist_entries:
        video_title = entry.get("title", "")
        video_id = entry.get("id", "")
        playlist_index = entry.get("playlist_index", 1)

        if not video_title and not video_id:
            to_download.append(entry)
            continue

        # Check if video exists by priority:
        # 1. status.json shows "completed" status with resolved_title in filesystem
        # 2. Pattern-based filename match in filesystem (if pattern provided)
        # 3. Normalized title match in filesystem
        # 4. Video ID in filename

        found = False

        # Priority 1: Check status.json with resolved_title
        if video_id and video_id in status_completed_videos:
            video_data = status_completed_videos[video_id]
            resolved_title = video_data.get("resolved_title")
            if resolved_title and resolved_title in existing_files_set:
                found = True
            elif resolved_title is None:
                # Old status without resolved_title, just trust completed status
                found = True

        # Priority 2: Check pattern-based filename (if pattern provided)
        if not found and title_pattern:
            total_entries = len(playlist_entries)
            for ext in ["mkv", "mp4", "webm", "avi", "mov"]:
                expected_filename = render_title(
                    title_pattern,
                    i=playlist_index,
                    title=video_title,
                    video_id=video_id,
                    ext=ext,
                    total=total_entries,
                )
                if expected_filename in existing_files_set:
                    found = True
                    break

        # Priority 3: Check normalized title in filesystem
        if not found and video_title:
            normalized_title = _normalize_for_comparison(video_title)
            if normalized_title in existing_names:
                found = True

        # Priority 4: Check video ID in existing filenames
        if not found and video_id and video_id in existing_video_ids:
            found = True

        if found:
            already_downloaded.append(entry)
        else:
            to_download.append(entry)

    total = len(playlist_entries)
    return already_downloaded, to_download, total


def _normalize_for_comparison(name: str) -> str:
    """
    Normalize a string for comparison.

    Removes special characters, extra spaces, and converts to lowercase.

    Args:
        name: String to normalize

    Returns:
        Normalized string
    """
    if not name:
        return ""

    # Remove special characters, keep only alphanumeric and spaces
    normalized = re.sub(r"[^\w\s]", "", name.lower())
    # Remove extra spaces
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def get_download_ratio(
    already_downloaded: List[Dict],
    to_download: List[Dict],
) -> str:
    """
    Format the download ratio as a readable string.

    Args:
        already_downloaded: List of already downloaded entries
        to_download: List of entries to download

    Returns:
        str: Formatted ratio like "5/20" or "0/20"
    """
    total = len(already_downloaded) + len(to_download)
    downloaded = len(already_downloaded)
    return f"{downloaded}/{total}"


def get_download_progress_percent(
    already_downloaded: List[Dict],
    to_download: List[Dict],
) -> float:
    """
    Calculate download progress as percentage.

    Args:
        already_downloaded: List of already downloaded entries
        to_download: List of entries to download

    Returns:
        float: Progress percentage (0.0 to 100.0)
    """
    total = len(already_downloaded) + len(to_download)
    if total == 0:
        return 0.0

    downloaded = len(already_downloaded)
    return (downloaded / total) * 100.0


# === PLAYLIST FOLDER STRUCTURE ===


def create_playlist_workspace(
    tmp_base_dir: Path,
    playlist_id: str,
) -> Path:
    """
    Create temporary workspace folder for a playlist.

    Args:
        tmp_base_dir: Base temporary directory
        playlist_id: Playlist ID

    Returns:
        Path: Path to playlist workspace folder
    """
    playlist_folder = tmp_base_dir / f"youtube-playlist-{playlist_id}"
    ensure_dir(playlist_folder)
    return playlist_folder


def create_video_workspace_in_playlist(
    playlist_workspace: Path,
    video_id: str,
    platform: str = "youtube",
) -> Path:
    """
    Create a video workspace folder within a playlist workspace.

    Args:
        playlist_workspace: Path to playlist workspace
        video_id: Video ID
        platform: Platform name (default: "youtube")

    Returns:
        Path: Path to video workspace folder within playlist
    """
    video_folder = playlist_workspace / f"{platform}-{video_id}"
    ensure_dir(video_folder)
    return video_folder


def get_video_workspace_path(
    playlist_workspace: Path,
    video_id: str,
    platform: str = "youtube",
) -> Path:
    """
    Get path to a video workspace within a playlist (without creating).

    Args:
        playlist_workspace: Path to playlist workspace
        video_id: Video ID
        platform: Platform name (default: "youtube")

    Returns:
        Path: Path to video workspace folder
    """
    return playlist_workspace / f"{platform}-{video_id}"


# === PLAYLIST STATUS MANAGEMENT ===


def create_playlist_status(
    playlist_workspace: Path,
    url: str,
    playlist_id: str,
    playlist_title: str,
    entries: List[Dict],
) -> Dict:
    """
    Create initial status.json for a playlist.

    Args:
        playlist_workspace: Path to playlist workspace
        url: Playlist URL
        playlist_id: Playlist ID
        playlist_title: Playlist title
        entries: List of video entries

    Returns:
        Dict with playlist status data
    """
    # Build video entries status
    videos_status = {}
    for entry in entries:
        video_id = entry.get("id", "unknown")
        videos_status[video_id] = {
            "title": entry.get("title", "Unknown"),
            "url": entry.get("url", ""),
            "status": "pending",  # pending, downloading, completed, failed, skipped
            "downloaded_at": None,
            "error": None,
        }

    status_data = {
        "url": url,
        "id": playlist_id,
        "title": playlist_title,
        "type": "playlist",
        "total_videos": len(entries),
        "videos": videos_status,
        # User preferences (updated on each download)
        "custom_title": None,  # User-provided folder name
        "playlist_location": None,  # Destination subfolder
        "title_pattern": None,  # Pattern for video filenames
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    # Save to file
    status_path = playlist_workspace / "status.json"
    try:
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        safe_push_log(f"📊 Playlist status file created: {status_path.name}")
    except Exception as e:
        safe_push_log(f"⚠️ Could not create playlist status file: {e}")

    return status_data


def load_playlist_status(playlist_workspace: Path) -> Optional[Dict]:
    """
    Load playlist status from status.json.

    Args:
        playlist_workspace: Path to playlist workspace

    Returns:
        Dict with playlist status or None if not found
    """
    status_path = playlist_workspace / "status.json"
    if not status_path.exists():
        return None

    try:
        with open(status_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        safe_push_log(f"⚠️ Could not load playlist status: {e}")
        return None


def save_playlist_status(playlist_workspace: Path, status_data: Dict) -> bool:
    """
    Save playlist status to status.json.

    Args:
        playlist_workspace: Path to playlist workspace
        status_data: Status data to save

    Returns:
        bool: True if saved successfully
    """
    status_path = playlist_workspace / "status.json"
    status_data["last_updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        safe_push_log(f"⚠️ Could not save playlist status: {e}")
        return False


def update_video_status_in_playlist(
    playlist_workspace: Path,
    video_id: str,
    status: str,
    error: Optional[str] = None,
    extra_data: Optional[Dict] = None,
) -> bool:
    """
    Update the status of a specific video in playlist status.

    Args:
        playlist_workspace: Path to playlist workspace
        video_id: Video ID to update
        status: New status ("pending", "downloading", "completed", "failed", "skipped")
        error: Optional error message (for failed status)
        extra_data: Optional dict with additional fields to store (e.g., title_pattern, resolved_title)

    Returns:
        bool: True if updated successfully
    """
    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        safe_push_log(f"⚠️ Playlist status not found, cannot update video {video_id}")
        return False

    videos = status_data.get("videos", {})
    if video_id not in videos:
        safe_push_log(f"⚠️ Video {video_id} not found in playlist status")
        return False

    videos[video_id]["status"] = status
    if status == "completed":
        videos[video_id]["downloaded_at"] = datetime.now(timezone.utc).isoformat()
    if error:
        videos[video_id]["error"] = error

    # Add extra data if provided (for pattern info, resolved title, etc.)
    if extra_data:
        for key, value in extra_data.items():
            videos[video_id][key] = value

    return save_playlist_status(playlist_workspace, status_data)


def get_playlist_progress(playlist_workspace: Path) -> Tuple[int, int, int, int]:
    """
    Get playlist download progress from status.json.

    Args:
        playlist_workspace: Path to playlist workspace

    Returns:
        Tuple of (completed, pending, failed, total)
    """
    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        return 0, 0, 0, 0

    videos = status_data.get("videos", {})
    completed = sum(1 for v in videos.values() if v.get("status") == "completed")
    pending = sum(
        1 for v in videos.values() if v.get("status") in ("pending", "downloading")
    )
    failed = sum(1 for v in videos.values() if v.get("status") == "failed")
    skipped = sum(1 for v in videos.values() if v.get("status") == "skipped")

    total = len(videos)
    return completed, pending + skipped, failed, total


def get_videos_to_download(playlist_workspace: Path) -> List[str]:
    """
    Get list of video IDs that still need to be downloaded.

    Args:
        playlist_workspace: Path to playlist workspace

    Returns:
        List of video IDs with pending status
    """
    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        return []

    videos = status_data.get("videos", {})
    return [
        video_id
        for video_id, video_data in videos.items()
        if video_data.get("status") in ("pending", "failed")
    ]


def mark_video_as_skipped(
    playlist_workspace: Path,
    video_id: str,
    reason: str = "Already exists in destination",
) -> bool:
    """
    Mark a video as skipped (already exists in destination).

    Args:
        playlist_workspace: Path to playlist workspace
        video_id: Video ID to mark as skipped
        reason: Reason for skipping

    Returns:
        bool: True if updated successfully
    """
    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        return False

    videos = status_data.get("videos", {})
    if video_id not in videos:
        return False

    videos[video_id]["status"] = "skipped"
    videos[video_id]["skip_reason"] = reason

    return save_playlist_status(playlist_workspace, status_data)


def add_playlist_download_attempt(
    playlist_workspace: Path,
    custom_title: str,
    playlist_location: str,
    title_pattern: Optional[str] = None,
) -> bool:
    """
    Update playlist preferences in status.json.

    Updates the root-level fields with the user's current choices:
    - custom_title: The playlist folder name entered by the user
    - playlist_location: The subfolder/category selected
    - title_pattern: The pattern used for naming videos

    These values are overwritten each time (only the latest matters).

    Args:
        playlist_workspace: Path to playlist workspace
        custom_title: User-provided playlist folder name
        playlist_location: Destination subfolder path
        title_pattern: Pattern used for naming videos (optional)

    Returns:
        bool: True if recorded successfully, False otherwise
    """
    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        safe_push_log(
            "⚠️ Playlist status file not found, cannot record download attempt"
        )
        return False

    # Update root-level preferences (overwrite previous values)
    status_data["custom_title"] = custom_title
    status_data["playlist_location"] = playlist_location
    if title_pattern:
        status_data["title_pattern"] = title_pattern

    safe_push_log(
        f"📊 Updated playlist preferences: folder='{custom_title}', "
        f"location='{playlist_location}'"
    )

    return save_playlist_status(playlist_workspace, status_data)


def get_last_playlist_download_attempt(playlist_workspace: Path) -> Optional[Dict]:
    """
    Get the current playlist preferences from status.json.

    Returns the root-level custom_title, playlist_location, and title_pattern.

    Args:
        playlist_workspace: Path to playlist workspace

    Returns:
        Dict with keys 'custom_title', 'playlist_location', 'title_pattern' or None if not set
    """
    if not playlist_workspace or not playlist_workspace.exists():
        return None

    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        return None

    # Check if preferences have been set (custom_title is the key indicator)
    custom_title = status_data.get("custom_title")
    if not custom_title:
        return None

    # Return preferences from root level
    return {
        "custom_title": custom_title,
        "playlist_location": status_data.get("playlist_location", "/"),
        "title_pattern": status_data.get("title_pattern"),
    }


# === FINAL COPY TO DESTINATION ===


def copy_playlist_to_destination(
    playlist_workspace: Path,
    dest_dir: Path,
    playlist_name: str,
    video_extensions: List[str] = None,
) -> Tuple[int, int]:
    """
    Copy all completed videos from playlist workspace to destination folder.

    Creates a folder with playlist_name in dest_dir and copies all completed videos.

    Args:
        playlist_workspace: Path to playlist workspace
        dest_dir: Base destination directory
        playlist_name: Name for the playlist folder
        video_extensions: List of video extensions to copy

    Returns:
        Tuple of (copied_count, failed_count)
    """
    if video_extensions is None:
        video_extensions = [".mkv", ".mp4", ".webm"]

    # Create playlist destination folder
    sanitized_name = sanitize_filename(playlist_name)
    playlist_dest = dest_dir / sanitized_name
    ensure_dir(playlist_dest)

    safe_push_log(f"📁 Creating playlist folder: {playlist_dest}")

    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        safe_push_log("⚠️ No playlist status found")
        return 0, 0

    videos = status_data.get("videos", {})
    copied = 0
    failed = 0

    for video_id, video_data in videos.items():
        if video_data.get("status") != "completed":
            continue

        # Find the video folder
        video_folder = get_video_workspace_path(playlist_workspace, video_id)
        if not video_folder.exists():
            safe_push_log(f"⚠️ Video folder not found: {video_folder}")
            failed += 1
            continue

        # Find the final video file
        final_file = None
        for ext in video_extensions:
            # Look for final.ext first
            potential = video_folder / f"final{ext}"
            if potential.exists():
                final_file = potential
                break

            # Look for video-*.ext files
            video_files = list(video_folder.glob(f"video-*{ext}"))
            if video_files:
                final_file = video_files[0]
                break

        if not final_file:
            safe_push_log(f"⚠️ No video file found for {video_id}")
            failed += 1
            continue

        # Determine destination filename
        # Use video title if available, otherwise video ID
        video_title = video_data.get("title", video_id)
        dest_filename = f"{sanitize_filename(video_title)}{final_file.suffix}"
        dest_path = playlist_dest / dest_filename

        try:
            move_final_to_destination(final_file, dest_path, safe_push_log)
            copied += 1
        except Exception as e:
            safe_push_log(f"❌ Failed to move {video_id}: {e}")
            failed += 1

    safe_push_log(f"📊 Playlist move complete: {copied} moved, {failed} failed")
    return copied, failed

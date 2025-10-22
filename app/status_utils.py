"""
Status tracking utilities for video downloads.

This module manages status.json files that track download progress
and completion status for each video.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.logs_utils import safe_push_log


def create_initial_status(
    url: str,
    video_id: str,
    title: str,
    content_type: str,
    tmp_video_dir: Path,
) -> Dict:
    """
    Create initial status.json file for a video.

    Args:
        url: Video URL
        video_id: Unique video identifier
        title: Video title
        content_type: "video" or "playlist"
        tmp_video_dir: Path to the unique video temporary directory

    Returns:
        Dict with initial status data
    """
    status_data = {
        "url": url,
        "id": video_id,
        "title": title,
        "type": content_type,
        "selected_formats": [],  # Will be populated during download
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    # Save to file
    status_path = tmp_video_dir / "status.json"
    try:
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        safe_push_log(f"📊 Status file created: {status_path.name}")
    except Exception as e:
        safe_push_log(f"⚠️ Could not create status file: {e}")

    return status_data


def load_status(tmp_video_dir: Path) -> Optional[Dict]:
    """
    Load status.json from the video directory.

    Args:
        tmp_video_dir: Path to the unique video temporary directory

    Returns:
        Dict with status data or None if not found
    """
    status_path = tmp_video_dir / "status.json"
    if not status_path.exists():
        return None

    try:
        with open(status_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        safe_push_log(f"⚠️ Could not load status file: {e}")
        return None


def save_status(tmp_video_dir: Path, status_data: Dict) -> bool:
    """
    Save status data to status.json.

    Args:
        tmp_video_dir: Path to the unique video temporary directory
        status_data: Status data to save

    Returns:
        bool: True if saved successfully, False otherwise
    """
    status_path = tmp_video_dir / "status.json"

    # Update last_updated timestamp
    status_data["last_updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        safe_push_log(f"⚠️ Could not save status file: {e}")
        return False


def add_selected_format(
    tmp_video_dir: Path,
    video_format: str,
    subtitles: List[str],
    filesize_approx: int,
) -> bool:
    """
    Add a selected format to status.json when starting download.

    Args:
        tmp_video_dir: Path to the unique video temporary directory
        video_format: Format ID (e.g., "399+251")
        subtitles: List of subtitle files (e.g., ["subtitles.en.srt"])
        filesize_approx: Approximate file size in bytes

    Returns:
        bool: True if added successfully, False otherwise
    """
    status_data = load_status(tmp_video_dir)
    if not status_data:
        safe_push_log("⚠️ Status file not found, cannot add format")
        return False

    # Create format entry
    format_entry = {
        "video_format": video_format,
        "subtitles": subtitles,
        "filesize_approx": filesize_approx,
        "status": "downloading",
    }

    # Check if format already exists (update instead of duplicate)
    existing_index = None
    for i, fmt in enumerate(status_data.get("selected_formats", [])):
        if fmt.get("video_format") == video_format:
            existing_index = i
            break

    if existing_index is not None:
        # Update existing entry
        status_data["selected_formats"][existing_index] = format_entry
        safe_push_log(f"📊 Updated format {video_format} status to 'downloading'")
    else:
        # Add new entry
        status_data["selected_formats"].append(format_entry)
        safe_push_log(f"📊 Added format {video_format} with status 'downloading'")

    return save_status(tmp_video_dir, status_data)


def update_format_status(
    tmp_video_dir: Path,
    video_format: str,
    final_file: Path,
) -> bool:
    """
    Update format status to 'completed' or 'incomplete' based on file verification.

    Compares actual file size with expected size using tolerance:
    - tolerance = max(100KB, expected_size * 1%)

    Args:
        tmp_video_dir: Path to the unique video temporary directory
        video_format: Format ID to update
        final_file: Path to the final downloaded file

    Returns:
        bool: True if updated successfully, False otherwise
    """
    status_data = load_status(tmp_video_dir)
    if not status_data:
        safe_push_log("⚠️ Status file not found, cannot update format status")
        return False

    # Find the format entry
    format_entry = None
    for fmt in status_data.get("selected_formats", []):
        if fmt.get("video_format") == video_format:
            format_entry = fmt
            break

    if not format_entry:
        safe_push_log(f"⚠️ Format {video_format} not found in status")
        return False

    # Get actual file size
    if not final_file.exists():
        format_entry["status"] = "incomplete"
        format_entry["error"] = "File not found"
        safe_push_log(
            f"❌ Format {video_format} marked as 'incomplete' - file not found"
        )
        return save_status(tmp_video_dir, status_data)

    actual_size = final_file.stat().st_size
    expected_size = format_entry.get("filesize_approx", 0)

    # Calculate tolerance: max(100KB, 1% of expected size)
    tolerance = max(100000, expected_size * 0.01)

    # Check if size is within tolerance
    size_diff = abs(actual_size - expected_size)

    if size_diff <= tolerance:
        format_entry["status"] = "completed"
        format_entry["actual_filesize"] = actual_size
        safe_push_log(
            f"✅ Format {video_format} marked as 'completed' "
            f"(size: {actual_size / (1024*1024):.2f}MiB, "
            f"expected: {expected_size / (1024*1024):.2f}MiB, "
            f"diff: {size_diff / 1024:.1f}KB)"
        )
    else:
        format_entry["status"] = "incomplete"
        format_entry["actual_filesize"] = actual_size
        format_entry["size_difference"] = size_diff
        safe_push_log(
            f"⚠️ Format {video_format} marked as 'incomplete' "
            f"(size: {actual_size / (1024*1024):.2f}MiB, "
            f"expected: {expected_size / (1024*1024):.2f}MiB, "
            f"diff: {size_diff / (1024*1024):.2f}MiB exceeds tolerance)"
        )

    return save_status(tmp_video_dir, status_data)


def get_format_status(tmp_video_dir: Path, video_format: str) -> Optional[str]:
    """
    Get the status of a specific format.

    Args:
        tmp_video_dir: Path to the unique video temporary directory
        video_format: Format ID to check

    Returns:
        str: "downloading", "completed", "incomplete", or None if not found
    """
    status_data = load_status(tmp_video_dir)
    if not status_data:
        return None

    for fmt in status_data.get("selected_formats", []):
        if fmt.get("video_format") == video_format:
            return fmt.get("status")

    return None


def is_format_completed(tmp_video_dir: Path, video_format: str) -> bool:
    """
    Check if a format download is completed.

    Args:
        tmp_video_dir: Path to the unique video temporary directory
        video_format: Format ID to check

    Returns:
        bool: True if completed, False otherwise
    """
    status = get_format_status(tmp_video_dir, video_format)
    return status == "completed"


def mark_format_error(
    tmp_video_dir: Path,
    video_format: str,
    error_message: str = "Download failed",
) -> bool:
    """
    Mark a format as failed/error in status.json.

    Args:
        tmp_video_dir: Path to the unique video temporary directory
        video_format: Format ID to mark as error
        error_message: Error description

    Returns:
        bool: True if updated successfully, False otherwise
    """
    status_data = load_status(tmp_video_dir)
    if not status_data:
        return False

    # Find the format entry
    format_entry = None
    for fmt in status_data.get("selected_formats", []):
        if fmt.get("video_format") == video_format:
            format_entry = fmt
            break

    if not format_entry:
        return False

    # Update to error status
    format_entry["status"] = "error"
    format_entry["error"] = error_message
    safe_push_log(f"❌ Format {video_format} marked as 'error': {error_message}")

    return save_status(tmp_video_dir, status_data)


def get_first_completed_format(tmp_video_dir: Path) -> Optional[str]:
    """
    Get the format ID of the first completed download.

    Args:
        tmp_video_dir: Path to the unique video temporary directory

    Returns:
        str: Format ID of first completed download, or None if no completed downloads
    """
    status_data = load_status(tmp_video_dir)
    if not status_data:
        return None

    for fmt in status_data.get("selected_formats", []):
        if fmt.get("status") == "completed":
            format_id = fmt.get("video_format")
            safe_push_log(
                f"✅ Found completed format in status: {format_id} "
                f"(size: {fmt.get('actual_filesize', 0) / (1024*1024):.2f}MiB)"
            )
            return format_id

    return None

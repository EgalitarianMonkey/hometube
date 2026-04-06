"""
Status tracking utilities for video downloads.

This module manages status.json files that track download progress
and completion status for each video.
"""

from datetime import datetime, timezone
from pathlib import Path

from app.json_utils import safe_load_json, safe_save_json
from app.logs_utils import safe_push_log


def create_initial_status(
    url: str,
    video_id: str,
    title: str,
    content_type: str,
    tmp_url_workspace: Path,
) -> dict:
    """
    Create initial status.json file for a video.

    Args:
        url: Video URL
        video_id: Unique video identifier
        title: Video title
        content_type: "video" or "playlist"
        tmp_url_workspace: Path to the URL's temporary workspace directory

    Returns:
        Dict with initial status data
    """
    status_data = {
        "url": url,
        "id": video_id,
        "title": title,
        "type": content_type,
        "downloaded_formats": {},  # Dict with format_id as keys
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    # Save to file
    status_path = tmp_url_workspace / "status.json"
    if safe_save_json(status_path, status_data):
        safe_push_log(f"📊 Status file created: {status_path.name}")

    return status_data


def load_status(tmp_url_workspace: Path) -> dict | None:
    """
    Load status.json from the URL workspace directory.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory

    Returns:
        Dict with status data or None if not found
    """
    return safe_load_json(tmp_url_workspace / "status.json")


def save_status(tmp_url_workspace: Path, status_data: dict) -> bool:
    """
    Save status data to status.json.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        status_data: Status data to save

    Returns:
        bool: True if saved successfully, False otherwise
    """
    # Update last_updated timestamp
    status_data["last_updated"] = datetime.now(timezone.utc).isoformat()

    return safe_save_json(tmp_url_workspace / "status.json", status_data)


def add_selected_format(
    tmp_url_workspace: Path,
    video_format: str,
    subtitles: list[str],
    filesize_approx: int,
) -> bool:
    """
    Add a selected format to status.json when starting download.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        video_format: Format ID (e.g., "399+251")
        subtitles: List of subtitle files (e.g., ["subtitles.en.srt"])
        filesize_approx: Approximate file size in bytes

    Returns:
        bool: True if added successfully, False otherwise
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        safe_push_log("⚠️ Status file not found, cannot add format")
        return False

    # Ensure downloaded_formats is a dict (migration from old list format)
    if isinstance(status_data.get("downloaded_formats"), list):
        status_data["downloaded_formats"] = {}
        safe_push_log("📊 Migrated downloaded_formats from list to dict")

    # Create format entry (without redundant video_format key)
    format_entry = {
        "subtitles": subtitles,
        "filesize_approx": filesize_approx,
        "status": "downloading",
    }

    # Check if format already exists BEFORE adding it
    action = "Updated" if video_format in status_data["downloaded_formats"] else "Added"

    # Add or update format entry using format_id as key
    status_data["downloaded_formats"][video_format] = format_entry

    safe_push_log(f"📊 {action} format {video_format} with status 'downloading'")

    return save_status(tmp_url_workspace, status_data)


def update_format_status(
    tmp_url_workspace: Path,
    video_format: str,
    final_file: Path,
) -> bool:
    """
    Update format status to 'completed' or 'incomplete' based on file verification.

    Compares actual file size with expected size using tolerance:
    - tolerance = max(100KB, expected_size * 1%)

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        video_format: Format ID to update
        final_file: Path to the final downloaded file

    Returns:
        bool: True if updated successfully, False otherwise
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        safe_push_log("⚠️ Status file not found, cannot update format status")
        return False

    # Ensure downloaded_formats is a dict
    if isinstance(status_data.get("downloaded_formats"), list):
        status_data["downloaded_formats"] = {}

    # Get format entry directly by key
    downloaded_formats = status_data.get("downloaded_formats", {})
    format_entry = downloaded_formats.get(video_format)

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
        return save_status(tmp_url_workspace, status_data)

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

    return save_status(tmp_url_workspace, status_data)


def get_format_status(tmp_url_workspace: Path, video_format: str) -> str | None:
    """
    Get the status of a specific format.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        video_format: Format ID to check

    Returns:
        str: "downloading", "completed", "incomplete", or None if not found
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        return None

    # Handle both old list format and new dict format
    downloaded_formats = status_data.get("downloaded_formats", {})

    if isinstance(downloaded_formats, dict):
        # New dict format - direct key access
        format_entry = downloaded_formats.get(video_format)
        return format_entry.get("status") if format_entry else None
    else:
        # Old list format - backward compatibility
        for fmt in downloaded_formats:
            if fmt.get("video_format") == video_format:
                return fmt.get("status")
        return None


def is_format_completed(tmp_url_workspace: Path, video_format: str) -> bool:
    """
    Check if a format download is completed.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        video_format: Format ID to check

    Returns:
        bool: True if completed, False otherwise
    """
    status = get_format_status(tmp_url_workspace, video_format)
    return status == "completed"


def mark_format_error(
    tmp_url_workspace: Path,
    video_format: str,
    error_message: str = "Download failed",
) -> bool:
    """
    Mark a format as failed/error in status.json.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        video_format: Format ID to mark as error
        error_message: Error description

    Returns:
        bool: True if updated successfully, False otherwise
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        return False

    # Ensure downloaded_formats is a dict
    if isinstance(status_data.get("downloaded_formats"), list):
        status_data["downloaded_formats"] = {}

    # Get format entry directly by key
    downloaded_formats = status_data.get("downloaded_formats", {})
    format_entry = downloaded_formats.get(video_format)

    if not format_entry:
        return False

    # Update to error status
    format_entry["status"] = "error"
    format_entry["error"] = error_message
    safe_push_log(f"❌ Format {video_format} marked as 'error': {error_message}")

    return save_status(tmp_url_workspace, status_data)


def get_first_completed_format(tmp_url_workspace: Path) -> str | None:
    """
    Get the format ID of the first completed download.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory

    Returns:
        str: Format ID of first completed download, or None if no completed downloads
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        return None

    downloaded_formats = status_data.get("downloaded_formats", {})

    # Handle both dict and list formats
    if isinstance(downloaded_formats, dict):
        # New dict format - iterate over items
        for format_id, format_entry in downloaded_formats.items():
            if format_entry.get("status") == "completed":
                safe_push_log(
                    f"✅ Found completed format in status: {format_id} "
                    f"(size: {format_entry.get('actual_filesize', 0) / (1024*1024):.2f}MiB)"
                )
                return format_id
    else:
        # Old list format - backward compatibility
        for fmt in downloaded_formats:
            if fmt.get("status") == "completed":
                format_id = fmt.get("video_format")
                safe_push_log(
                    f"✅ Found completed format in status: {format_id} "
                    f"(size: {fmt.get('actual_filesize', 0) / (1024*1024):.2f}MiB)"
                )
                return format_id

    return None


def add_download_attempt(
    tmp_url_workspace: Path,
    custom_title: str,
    video_location: str,
    requested_format_id: str | None = None,
    media_type: str = "video",
) -> bool:
    """
    Record a download attempt in status.json.

    Each time the user clicks the Download button, this function records:
    - custom_title: The filename/title entered by the user
    - video_location: The subfolder/category selected
    - requested_format_id: The format ID that the user wants to download (if specified)
    - media_type: "video" or "audio"
    - date: ISO timestamp of the download attempt

    New attempts are added at the beginning of the list (index 0) for easy access.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        custom_title: User-provided filename/title
        video_location: Destination subfolder path
        requested_format_id: Optional format ID requested by user (e.g., from Choose Quality Available)
        media_type: "video" or "audio" (default: "video")

    Returns:
        bool: True if recorded successfully, False otherwise
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        safe_push_log("⚠️ Status file not found, cannot record download attempt")
        return False

    # Create attempt entry
    attempt_entry = {
        "custom_title": custom_title,
        "video_location": video_location,
        "media_type": media_type,
        "date": datetime.now(timezone.utc).isoformat(),
    }

    # Add requested format if specified
    if requested_format_id:
        attempt_entry["requested_format_id"] = requested_format_id

    # Initialize download_attempts list if it doesn't exist
    if "download_attempts" not in status_data:
        status_data["download_attempts"] = []

    # Insert at the beginning (position 0) so most recent is first
    status_data["download_attempts"].insert(0, attempt_entry)

    safe_push_log(
        f"📊 Recorded download attempt: title='{custom_title}', "
        f"location='{video_location}', type='{media_type}'"
    )

    return save_status(tmp_url_workspace, status_data)


def get_last_download_attempt(tmp_url_workspace: Path) -> dict | None:
    """
    Get the most recent download attempt from status.json.

    Returns the first entry in download_attempts list (newest first).

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory

    Returns:
        Dict with keys 'custom_title', 'video_location', 'date' or None if no attempts
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        return None

    attempts = status_data.get("download_attempts", [])
    if not attempts:
        return None

    # Return the first entry (most recent)
    return attempts[0]


def get_profiles_cached(
    tmp_url_workspace: Path,
    optimal_format_profiles: list[dict],
) -> list[dict]:
    """
    Get the list of optimal profiles that are cached (status = "completed").

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        optimal_format_profiles: List of optimal profile dictionaries with format_id

    Returns:
        List of cached profiles (subset of optimal_format_profiles)
    """
    if not tmp_url_workspace or not optimal_format_profiles:
        return []

    status_data = load_status(tmp_url_workspace)
    if not status_data:
        return []

    downloaded_formats = status_data.get("downloaded_formats", {})

    # Ensure it's a dict (migration from old format)
    if not isinstance(downloaded_formats, dict):
        return []

    # Filter profiles that have status "completed" in downloaded_formats
    cached_profiles = []
    for profile in optimal_format_profiles:
        format_id = profile.get("format_id", "")
        if not format_id:
            continue

        format_entry = downloaded_formats.get(format_id)
        if format_entry and format_entry.get("status") == "completed":
            cached_profiles.append(profile)

    return cached_profiles


# ─── Audio status tracking ─────────────────────────────────────────────────


def _ensure_downloaded_audio(status_data: dict) -> dict:
    """Ensure downloaded_audio dict exists in status_data."""
    if "downloaded_audio" not in status_data:
        status_data["downloaded_audio"] = {}
    return status_data["downloaded_audio"]


def add_audio_download(
    tmp_url_workspace: Path,
    audio_format: str,
    filesize_approx: int = 0,
) -> bool:
    """
    Mark an audio format as 'downloading' in status.json.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        audio_format: Audio format (e.g., "opus", "mp3", "m4a")
        filesize_approx: Approximate file size in bytes (0 if unknown)

    Returns:
        bool: True if saved successfully
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        safe_push_log("⚠️ Status file not found, cannot add audio download")
        return False

    downloaded_audio = _ensure_downloaded_audio(status_data)

    action = "Updated" if audio_format in downloaded_audio else "Added"

    downloaded_audio[audio_format] = {
        "status": "downloading",
        "filesize_approx": filesize_approx,
    }

    safe_push_log(f"🎵 {action} audio format {audio_format} with status 'downloading'")
    return save_status(tmp_url_workspace, status_data)


def update_audio_status(
    tmp_url_workspace: Path,
    audio_format: str,
    final_file: Path,
) -> bool:
    """
    Update audio status to 'completed' or 'incomplete' based on file verification.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        audio_format: Audio format key (e.g., "opus")
        final_file: Path to the downloaded audio file

    Returns:
        bool: True if updated successfully
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        safe_push_log("⚠️ Status file not found, cannot update audio status")
        return False

    downloaded_audio = _ensure_downloaded_audio(status_data)
    entry = downloaded_audio.get(audio_format)

    if not entry:
        # Auto-create entry if file exists (handles legacy / untracked downloads)
        entry = {"status": "downloading", "filesize_approx": 0}
        downloaded_audio[audio_format] = entry

    if not final_file.exists():
        entry["status"] = "incomplete"
        entry["error"] = "File not found"
        safe_push_log(
            f"❌ Audio {audio_format} marked as 'incomplete' - file not found"
        )
        return save_status(tmp_url_workspace, status_data)

    actual_size = final_file.stat().st_size
    entry["status"] = "completed"
    entry["actual_filesize"] = actual_size
    safe_push_log(
        f"✅ Audio {audio_format} marked as 'completed' "
        f"({actual_size / (1024*1024):.2f}MiB)"
    )
    return save_status(tmp_url_workspace, status_data)


def get_completed_audio(tmp_url_workspace: Path) -> str | None:
    """
    Get the format key of the first completed audio download.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory

    Returns:
        str: Audio format key (e.g., "opus") or None
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        return None

    downloaded_audio = status_data.get("downloaded_audio", {})
    if not isinstance(downloaded_audio, dict):
        return None

    for fmt, entry in downloaded_audio.items():
        if entry.get("status") == "completed":
            safe_push_log(
                f"✅ Found completed audio in status: {fmt} "
                f"({entry.get('actual_filesize', 0) / (1024*1024):.2f}MiB)"
            )
            return fmt

    return None


def is_audio_completed(tmp_url_workspace: Path, audio_format: str) -> bool:
    """
    Check if a specific audio format download is completed.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        audio_format: Audio format to check (e.g., "opus")

    Returns:
        bool: True if completed
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        return False

    downloaded_audio = status_data.get("downloaded_audio", {})
    if not isinstance(downloaded_audio, dict):
        return False

    entry = downloaded_audio.get(audio_format)
    return entry is not None and entry.get("status") == "completed"


def mark_audio_error(
    tmp_url_workspace: Path,
    audio_format: str,
    error_message: str = "Audio download failed",
) -> bool:
    """
    Mark an audio format as failed/error in status.json.

    Args:
        tmp_url_workspace: Path to the URL's temporary workspace directory
        audio_format: Audio format to mark
        error_message: Error description

    Returns:
        bool: True if updated successfully
    """
    status_data = load_status(tmp_url_workspace)
    if not status_data:
        return False

    downloaded_audio = _ensure_downloaded_audio(status_data)
    entry = downloaded_audio.get(audio_format)

    if not entry:
        return False

    entry["status"] = "error"
    entry["error"] = error_message
    safe_push_log(f"❌ Audio {audio_format} marked as 'error': {error_message}")
    return save_status(tmp_url_workspace, status_data)

"""
Playlist Synchronization Utilities for HomeTube.

This module provides resilient playlist synchronization capabilities:
- Detecting changes between local and remote playlist states
- Handling renamed videos via metadata inspection
- Archiving removed videos or deleting them based on settings
- Generating sync plans with dry-run support
"""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import get_settings
from app.file_system_utils import sanitize_filename, ensure_dir
from app.logs_utils import safe_push_log
from app.text_utils import render_title


# === SYNC ACTION TYPES ===


@dataclass
class SyncAction:
    """Represents a single synchronization action."""

    action_type: str  # "rename", "archive", "delete", "add", "keep", "relocate"
    video_id: str
    title: str
    details: str = ""
    old_path: Optional[Path] = None
    new_path: Optional[Path] = None
    old_index: Optional[int] = None
    new_index: Optional[int] = None


@dataclass
class PlaylistSyncPlan:
    """Complete synchronization plan for a playlist."""

    playlist_id: str
    playlist_title: str

    # Actions to perform
    videos_to_rename: List[SyncAction] = field(default_factory=list)
    videos_to_archive: List[SyncAction] = field(default_factory=list)
    videos_to_delete: List[SyncAction] = field(default_factory=list)
    videos_to_download: List[SyncAction] = field(default_factory=list)
    videos_already_synced: List[SyncAction] = field(default_factory=list)
    videos_to_relocate: List[SyncAction] = field(default_factory=list)

    # Location/pattern changes
    location_changed: bool = False
    old_location: str = ""
    new_location: str = ""
    pattern_changed: bool = False
    old_pattern: str = ""
    new_pattern: str = ""

    # Summary counts
    @property
    def total_actions(self) -> int:
        return (
            len(self.videos_to_rename)
            + len(self.videos_to_archive)
            + len(self.videos_to_delete)
            + len(self.videos_to_download)
            + len(self.videos_to_relocate)
        )

    @property
    def has_changes(self) -> bool:
        return self.total_actions > 0 or self.location_changed or self.pattern_changed


# === METADATA EXTRACTION ===


def get_video_metadata_from_file(video_path: Path) -> Optional[Dict]:
    """
    Extract metadata from a video file using ffprobe.

    Returns dict with: video_id (from comment), duration, title, source, etc.
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        format_data = data.get("format", {})
        tags = format_data.get("tags", {})

        # Try to get video_id - it might be stored as just the ID or as a full URL
        # Check both lowercase and uppercase tag names (MKV uses uppercase)
        comment = tags.get("comment", "") or tags.get("COMMENT", "")

        # Extract video_id from URL if necessary
        video_id = ""
        if comment:
            # Check if it's a YouTube URL and extract video_id
            if "youtube.com/watch?v=" in comment:
                # Extract video_id from URL like https://www.youtube.com/watch?v=IJT23BvjWMM
                match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", comment)
                if match:
                    video_id = match.group(1)
            elif "youtu.be/" in comment:
                # Extract from short URL like https://youtu.be/IJT23BvjWMM
                match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", comment)
                if match:
                    video_id = match.group(1)
            elif (
                len(comment) == 11
                and comment.replace("-", "").replace("_", "").isalnum()
            ):
                # It's already a video_id (11 chars, alphanumeric with - and _)
                video_id = comment
            else:
                # Use as-is (might be a different platform)
                video_id = comment

        return {
            "video_id": video_id,
            "title": tags.get("title", "") or tags.get("TITLE", ""),
            "album": tags.get("album", "") or tags.get("ALBUM", ""),
            "source": tags.get("source", "") or tags.get("SOURCE", ""),
            "playlist_id": tags.get("playlist_id", "") or tags.get("PLAYLIST_ID", ""),
            "purl": tags.get("purl", "") or tags.get("PURL", ""),
            "duration": float(format_data.get("duration", 0)),
            "filename": video_path.name,
            "path": video_path,
        }
    except Exception as e:
        safe_push_log(f"⚠️ Could not read metadata from {video_path.name}: {e}")
        return None


def scan_destination_videos(dest_dir: Path) -> Dict[str, Dict]:
    """
    Scan destination directory and extract metadata from all video files.

    Returns dict mapping video_id -> metadata dict
    """
    video_extensions = [".mkv", ".mp4", ".webm", ".avi", ".mov"]
    videos_by_id = {}
    videos_by_filename = {}

    if not dest_dir.exists():
        return videos_by_id

    for ext in video_extensions:
        for video_file in dest_dir.glob(f"*{ext}"):
            metadata = get_video_metadata_from_file(video_file)
            if metadata:
                video_id = metadata.get("video_id")
                if video_id:
                    videos_by_id[video_id] = metadata
                # Also index by filename for fallback matching
                videos_by_filename[video_file.name] = metadata

    return videos_by_id


def extract_title_from_pattern(
    filename: str,
    pattern: str,
    index: int,
    total: int,
) -> Optional[str]:
    """
    Try to extract the original title from a filename based on a known pattern.

    This is useful when a user has renamed a file but kept the pattern structure.
    """
    # This is a simplified approach - in practice, extracting from patterns is complex
    # For now, we'll return the filename stem as the "extracted" title
    return Path(filename).stem


# === ARCHIVE URL_INFO ===


def archive_url_info(playlist_workspace: Path) -> Optional[Path]:
    """
    Archive the current url_info.json before fetching a new one.

    Creates url_info-YYYYMMDD-HHMMSS.json as backup.

    Returns the path to the archived file, or None if no file to archive.
    """
    url_info_path = playlist_workspace / "url_info.json"

    if not url_info_path.exists():
        return None

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = playlist_workspace / f"url_info-{timestamp}.json"

    try:
        shutil.copy2(url_info_path, archive_path)
        safe_push_log(f"📦 Archived url_info.json → {archive_path.name}")
        return archive_path
    except Exception as e:
        safe_push_log(f"⚠️ Could not archive url_info.json: {e}")
        return None


def refresh_playlist_url_info(
    playlist_workspace: Path,
    playlist_url: str,
) -> Optional[Dict]:
    """
    Refresh url_info.json by fetching the latest playlist data from YouTube.

    This function:
    1. Archives the current url_info.json (if exists) as url_info-<timestamp>.json
    2. Fetches fresh playlist data from YouTube using yt-dlp
    3. Saves the new url_info.json
    4. Returns the new playlist data

    Args:
        playlist_workspace: Path to the playlist workspace folder
        playlist_url: URL of the playlist to fetch

    Returns:
        Dict with fresh playlist data or None if fetch failed
    """
    from app.core import build_cookies_params as core_build_cookies_params
    from app.config import get_settings, YOUTUBE_CLIENT_FALLBACKS
    from app.file_system_utils import is_valid_cookie_file, is_valid_browser
    from app.url_utils import build_url_info

    safe_push_log("🔄 Refreshing playlist data from YouTube...")

    # Step 1: Archive the old url_info.json
    archive_url_info(playlist_workspace)

    # Step 2: Fetch fresh data from YouTube using the same logic as init_url_workspace
    url_info_path = playlist_workspace / "url_info.json"

    # Build cookies params from config (same logic as build_cookies_params_from_config)
    settings = get_settings()
    cookies_params = []

    # Try cookies file first (most common for Docker/server setup)
    if settings.YOUTUBE_COOKIES_FILE_PATH and is_valid_cookie_file(
        settings.YOUTUBE_COOKIES_FILE_PATH
    ):
        cookies_params = core_build_cookies_params(
            cookies_method="file", cookies_file_path=settings.YOUTUBE_COOKIES_FILE_PATH
        )
    # Try browser cookies if configured
    elif settings.COOKIES_FROM_BROWSER and is_valid_browser(
        settings.COOKIES_FROM_BROWSER
    ):
        cookies_params = core_build_cookies_params(
            cookies_method="browser",
            browser_select=settings.COOKIES_FROM_BROWSER,
            browser_profile="",
        )
    # No cookies available - cookies_params stays empty list

    safe_push_log(f"📡 Fetching playlist info from: {playlist_url}")

    try:
        # Use build_url_info which handles all the complexity (retries, integrity checks, etc.)
        new_url_info = build_url_info(
            clean_url=playlist_url,
            json_output_path=url_info_path,
            cookies_params=cookies_params,
            youtube_cookies_file_path=settings.YOUTUBE_COOKIES_FILE_PATH or "",
            cookies_from_browser=settings.COOKIES_FROM_BROWSER or "",
            youtube_clients=YOUTUBE_CLIENT_FALLBACKS,
        )

        # Check if there was an error
        if isinstance(new_url_info, dict) and "error" in new_url_info:
            safe_push_log(f"❌ Failed to fetch playlist: {new_url_info.get('error')}")
            return None

        # Extract entry count for logging
        from app.playlist_utils import get_playlist_entries

        entries = get_playlist_entries(new_url_info)
        safe_push_log(f"✅ Refreshed playlist data: {len(entries)} videos found")

        return new_url_info

    except Exception as e:
        safe_push_log(f"❌ Error refreshing playlist: {e}")
        return None


# === SYNC PLAN GENERATION ===


def sync_playlist(
    playlist_workspace: Path,
    dest_dir: Path,
    new_url_info: Dict,
    new_location: str,
    new_pattern: str,
    dry_run: bool = True,
    keep_old_videos: Optional[bool] = None,
) -> PlaylistSyncPlan:
    """
    Generate a synchronization plan for a playlist.

    This function compares the current state (status.json + filesystem) with
    the new playlist state (new_url_info) and generates a plan of actions.

    Args:
        playlist_workspace: Path to the playlist workspace (tmp folder)
        dest_dir: Current destination directory for the playlist
        new_url_info: Fresh url_info.json from yt-dlp
        new_location: New location/subfolder for the playlist
        new_pattern: New title pattern for video filenames
        dry_run: If True, only compute the plan without making changes
        keep_old_videos: If True, archive removed videos; if False, delete them.
                        If None, uses PLAYLIST_KEEP_OLD_VIDEOS from settings.

    Returns:
        PlaylistSyncPlan with all actions needed to synchronize
    """
    from app.playlist_utils import load_playlist_status, get_playlist_entries

    settings = get_settings()
    if keep_old_videos is None:
        keep_old_videos = settings.PLAYLIST_KEEP_OLD_VIDEOS

    # Load existing status
    status_data = load_playlist_status(playlist_workspace)

    playlist_id = new_url_info.get("id", "unknown")
    playlist_title = new_url_info.get("title", "Unknown Playlist")
    playlist_channel = new_url_info.get("uploader", new_url_info.get("channel", ""))

    # IMPORTANT: Determine the EXISTING destination directory from status.json
    # This is where videos were previously downloaded, not the new destination
    existing_dest_dir = None
    if status_data:
        # Read preferences from root level (simplified structure)
        old_location = status_data.get("playlist_location", "/")
        old_folder_name = status_data.get("custom_title") or status_data.get(
            "title", playlist_title
        )

        if old_folder_name:
            videos_folder = settings.VIDEOS_FOLDER
            if old_location == "/" or old_location == "" or old_location is None:
                existing_dest_dir = videos_folder / sanitize_filename(old_folder_name)
            else:
                existing_dest_dir = (
                    videos_folder / old_location / sanitize_filename(old_folder_name)
                )

    # Use existing destination for scanning, fall back to new dest_dir
    scan_dest_dir = (
        existing_dest_dir
        if existing_dest_dir and existing_dest_dir.exists()
        else dest_dir
    )
    safe_push_log(f"🔍 Scanning for existing videos in: {scan_dest_dir}")

    plan = PlaylistSyncPlan(
        playlist_id=playlist_id,
        playlist_title=playlist_title,
    )

    # Get preferences for location/pattern comparison
    if status_data:
        old_location = status_data.get("playlist_location", "")
        old_pattern = status_data.get("title_pattern", "")

        # Check for location change
        if old_location and old_location != new_location:
            plan.location_changed = True
            plan.old_location = old_location
            plan.new_location = new_location

        # Check for pattern change
        if old_pattern and old_pattern != new_pattern:
            plan.pattern_changed = True
            plan.old_pattern = old_pattern
            plan.new_pattern = new_pattern

    # Get entries from new playlist
    new_entries = get_playlist_entries(new_url_info)
    new_video_ids = {entry.get("id") for entry in new_entries if entry.get("id")}

    # Build index mapping: video_id -> new_index
    new_index_map = {}
    for entry in new_entries:
        video_id = entry.get("id")
        if video_id:
            new_index_map[video_id] = entry.get("playlist_index", 0)

    # Get existing videos from status.json
    existing_videos = status_data.get("videos", {}) if status_data else {}
    existing_video_ids = set(existing_videos.keys())

    safe_push_log(f"📋 Status.json has {len(existing_videos)} videos tracked")
    safe_push_log(f"📥 New playlist has {len(new_video_ids)} videos")

    # Scan destination folder for actual files (use existing location)
    dest_videos_by_id = scan_destination_videos(scan_dest_dir)

    safe_push_log(f"📊 Found {len(dest_videos_by_id)} videos in {scan_dest_dir}")
    if dest_videos_by_id:
        safe_push_log(
            f"   Video IDs: {list(dest_videos_by_id.keys())[:5]}..."
        )  # Show first 5

    # === PHASE 1: Handle videos no longer in playlist ===
    removed_video_ids = existing_video_ids - new_video_ids

    for video_id in removed_video_ids:
        video_data = existing_videos.get(video_id, {})
        title = video_data.get("title", video_id)

        # Find the actual file if it exists
        file_metadata = dest_videos_by_id.get(video_id)
        old_path = file_metadata.get("path") if file_metadata else None

        if old_path and old_path.exists():
            if keep_old_videos:
                # Archive to Archives/ folder
                archive_dir = dest_dir / "Archives"
                # Generate clean filename without index
                clean_title = sanitize_filename(title)
                new_filename = f"{clean_title}{old_path.suffix}"
                new_path = archive_dir / new_filename

                action = SyncAction(
                    action_type="archive",
                    video_id=video_id,
                    title=title,
                    details=f"Move to Archives/ (removed from playlist)",
                    old_path=old_path,
                    new_path=new_path,
                )
                plan.videos_to_archive.append(action)
            else:
                # Delete the file
                action = SyncAction(
                    action_type="delete",
                    video_id=video_id,
                    title=title,
                    details="Delete (removed from playlist)",
                    old_path=old_path,
                )
                plan.videos_to_delete.append(action)

    # === PHASE 2: Handle existing videos that are still in playlist ===
    common_video_ids = existing_video_ids & new_video_ids
    total_videos = len(new_entries)

    # Statuses that indicate a video is already downloaded/synced
    completed_statuses = {"completed", "skipped"}

    for video_id in common_video_ids:
        video_data = existing_videos.get(video_id, {})
        old_status = video_data.get("status", "pending")
        title = video_data.get("title", video_id)

        safe_push_log(f"🔍 Processing {video_id[:11]}... | Status: {old_status}")

        # Get new index from playlist
        new_index = new_index_map.get(video_id, 0)
        old_index = video_data.get("playlist_index")

        # Check if file actually exists (ALWAYS check, regardless of status)
        file_metadata = dest_videos_by_id.get(video_id)

        safe_push_log(f"   File metadata found: {'Yes' if file_metadata else 'No'}")

        # Also check by resolved_title if metadata scan didn't find the video
        if not file_metadata:
            resolved_title = video_data.get("resolved_title")
            if resolved_title and scan_dest_dir.exists():
                resolved_path = scan_dest_dir / resolved_title
                if resolved_path.exists():
                    # File exists at resolved path, create synthetic metadata
                    file_metadata = {
                        "video_id": video_id,
                        "path": resolved_path,
                        "filename": resolved_title,
                    }
                    safe_push_log(f"✅ Found video by resolved_title: {resolved_title}")

        # If file exists, handle it (regardless of status in status.json)
        if file_metadata:
            old_path = file_metadata.get("path")

            # Calculate expected filename with new pattern and index
            for entry in new_entries:
                if entry.get("id") == video_id:
                    entry_title = entry.get("title", title)
                    break
            else:
                entry_title = title

            expected_filename = render_title(
                new_pattern,
                i=new_index,
                title=entry_title,
                video_id=video_id,
                ext=old_path.suffix.lstrip("."),
                total=total_videos,
                channel=playlist_channel,
            )
            expected_path = dest_dir / expected_filename

            # Check if rename is needed
            if old_path.name != expected_filename:
                action = SyncAction(
                    action_type="rename",
                    video_id=video_id,
                    title=title,
                    details=f"Rename: {old_path.name} → {expected_filename}",
                    old_path=old_path,
                    new_path=expected_path,
                    old_index=old_index,
                    new_index=new_index,
                )
                plan.videos_to_rename.append(action)
            else:
                # Already correctly named
                action = SyncAction(
                    action_type="keep",
                    video_id=video_id,
                    title=title,
                    details="Already synced",
                    old_path=old_path,
                    old_index=old_index,
                    new_index=new_index,
                )
                plan.videos_already_synced.append(action)

        # File doesn't exist - check if we should try to find it or download it
        else:
            # If status says completed, try harder to find the file
            if old_status in completed_statuses:
                # Status says completed but file not found - try to find by scanning
                # This handles user renames
                found_video = _find_renamed_video(
                    scan_dest_dir,
                    video_id,
                    video_data,
                    new_pattern,
                    new_index,
                    total_videos,
                )

                if found_video:
                    old_path = found_video.get("path")
                    expected_filename = render_title(
                        new_pattern,
                        i=new_index,
                        title=title,
                        video_id=video_id,
                        ext=old_path.suffix.lstrip("."),
                        total=total_videos,
                        channel=playlist_channel,
                    )
                    expected_path = dest_dir / expected_filename

                    if old_path.name != expected_filename:
                        action = SyncAction(
                            action_type="rename",
                            video_id=video_id,
                            title=title,
                            details=f"Found renamed file, rename: {old_path.name} → {expected_filename}",
                            old_path=old_path,
                            new_path=expected_path,
                            old_index=old_index,
                            new_index=new_index,
                        )
                        plan.videos_to_rename.append(action)
                    else:
                        action = SyncAction(
                            action_type="keep",
                            video_id=video_id,
                            title=title,
                            details="Found renamed file, already synced",
                            old_path=old_path,
                        )
                        plan.videos_already_synced.append(action)
                else:
                    # File truly not found - needs re-download
                    action = SyncAction(
                        action_type="add",
                        video_id=video_id,
                        title=title,
                        details="File not found (marked complete but missing)",
                        new_index=new_index,
                    )
                    plan.videos_to_download.append(action)
            else:
                # Status is not completed AND file not found - needs download
                action = SyncAction(
                    action_type="add",
                    video_id=video_id,
                    title=title,
                    details=f"Status: {old_status}, file not found",
                    new_index=new_index,
                )
                plan.videos_to_download.append(action)

    # === PHASE 3: Handle new videos (not in existing status) ===
    new_video_ids_to_add = new_video_ids - existing_video_ids

    for entry in new_entries:
        video_id = entry.get("id")
        if video_id in new_video_ids_to_add:
            title = entry.get("title", video_id)
            new_index = entry.get("playlist_index", 0)

            action = SyncAction(
                action_type="add",
                video_id=video_id,
                title=title,
                details="New video in playlist",
                new_index=new_index,
            )
            plan.videos_to_download.append(action)

    # === PHASE 4: Handle location change (move all files) ===
    if plan.location_changed:
        # All videos with existing files need to be relocated
        # This includes both already_synced and to_rename videos
        videos_to_relocate_set = set()

        # Collect all videos that have physical files and need relocation
        all_actions_with_files = plan.videos_already_synced + plan.videos_to_rename

        for action in all_actions_with_files:
            if action.old_path and action.video_id not in videos_to_relocate_set:
                relocate_action = SyncAction(
                    action_type="relocate",
                    video_id=action.video_id,
                    title=action.title,
                    details=f"Move to new location: {new_location}",
                    old_path=action.old_path,
                    # new_path will be computed during apply based on new_location
                    old_index=action.old_index,
                    new_index=action.new_index,
                )
                plan.videos_to_relocate.append(relocate_action)
                videos_to_relocate_set.add(action.video_id)

        # Remove relocated videos from to_download list
        # (They should not be re-downloaded, just moved)
        plan.videos_to_download = [
            action
            for action in plan.videos_to_download
            if action.video_id not in videos_to_relocate_set
        ]

    return plan


def _find_renamed_video(
    dest_dir: Path,
    video_id: str,
    video_data: Dict,
    pattern: str,
    expected_index: int,
    total: int,
) -> Optional[Dict]:
    """
    Try to find a video that was renamed by the user.

    Scans all videos in dest_dir and checks their metadata for matching video_id.
    Also performs approximate duration check.
    """
    video_extensions = [".mkv", ".mp4", ".webm", ".avi", ".mov"]

    # Get expected duration from video_data if available
    expected_duration = video_data.get("duration")

    for ext in video_extensions:
        for video_file in dest_dir.glob(f"*{ext}"):
            metadata = get_video_metadata_from_file(video_file)
            if not metadata:
                continue

            # Check video_id match
            if metadata.get("video_id") == video_id:
                # Extra validation: check duration if available (within 5% tolerance)
                if expected_duration and metadata.get("duration"):
                    duration_diff = abs(metadata["duration"] - expected_duration)
                    tolerance = expected_duration * 0.05  # 5% tolerance
                    if duration_diff > tolerance:
                        continue  # Duration mismatch, probably wrong video

                safe_push_log(
                    f"🔍 Found renamed video: {video_file.name} (ID: {video_id})"
                )
                return metadata

    return None


# === APPLY SYNC PLAN ===


def apply_sync_plan(
    plan: PlaylistSyncPlan,
    playlist_workspace: Path,
    dest_dir: Path,
    new_location: str,
    new_pattern: str,
    new_url_info: Dict,
) -> bool:
    """
    Apply a synchronization plan to the filesystem and status.json.

    Args:
        plan: The sync plan to apply
        playlist_workspace: Path to playlist workspace
        dest_dir: Current destination directory
        new_location: New location (may be same as current)
        new_pattern: New title pattern
        new_url_info: New url_info.json data

    Returns:
        True if all actions completed successfully
    """
    from app.playlist_utils import (
        load_playlist_status,
        save_playlist_status,
        get_playlist_entries,
    )

    settings = get_settings()
    success = True

    safe_push_log("🔄 Applying playlist synchronization plan...")

    # === Archive old url_info.json first ===
    archive_url_info(playlist_workspace)

    # === Save new url_info.json ===
    url_info_path = playlist_workspace / "url_info.json"
    try:
        with open(url_info_path, "w", encoding="utf-8") as f:
            json.dump(new_url_info, f, indent=2, ensure_ascii=False)
        safe_push_log("✅ Updated url_info.json with latest playlist data")
    except Exception as e:
        safe_push_log(f"❌ Failed to save url_info.json: {e}")
        return False

    # === Apply archive actions ===
    if plan.videos_to_archive:
        archive_dir = dest_dir / "Archives"
        ensure_dir(archive_dir)

        for action in plan.videos_to_archive:
            if action.old_path and action.old_path.exists():
                try:
                    # Ensure unique filename in archive
                    new_path = action.new_path
                    if new_path.exists():
                        stem = new_path.stem
                        suffix = new_path.suffix
                        counter = 1
                        while new_path.exists():
                            new_path = archive_dir / f"{stem}_{counter}{suffix}"
                            counter += 1

                    shutil.move(str(action.old_path), str(new_path))
                    safe_push_log(f"📦 Archived: {action.old_path.name} → Archives/")
                except Exception as e:
                    safe_push_log(f"❌ Failed to archive {action.old_path.name}: {e}")
                    success = False

    # === Apply delete actions ===
    for action in plan.videos_to_delete:
        if action.old_path and action.old_path.exists():
            try:
                action.old_path.unlink()
                safe_push_log(f"🗑️ Deleted: {action.old_path.name}")
            except Exception as e:
                safe_push_log(f"❌ Failed to delete {action.old_path.name}: {e}")
                success = False

    # === Apply rename actions ===
    # Skip rename actions for videos that will be relocated (relocation handles renaming)
    videos_being_relocated = (
        {action.video_id for action in plan.videos_to_relocate}
        if plan.location_changed
        else set()
    )

    for action in plan.videos_to_rename:
        # Skip if this video will be relocated (relocation handles both move and rename)
        if action.video_id in videos_being_relocated:
            continue

        if action.old_path and action.old_path.exists() and action.new_path:
            try:
                # Handle case where target exists
                if action.new_path.exists() and action.new_path != action.old_path:
                    safe_push_log(f"⚠️ Target exists, backup: {action.new_path.name}")
                    backup_path = action.new_path.with_suffix(
                        f".backup{action.new_path.suffix}"
                    )
                    action.new_path.rename(backup_path)

                action.old_path.rename(action.new_path)
                safe_push_log(
                    f"✏️ Renamed: {action.old_path.name} → {action.new_path.name}"
                )
            except Exception as e:
                safe_push_log(f"❌ Failed to rename {action.old_path.name}: {e}")
                success = False

    # === Apply relocate actions (if location changed) ===
    if plan.location_changed and plan.videos_to_relocate:
        # dest_dir already includes the user-provided custom_title
        # Ensure both the parent location and playlist folder exist
        if dest_dir.parent:
            ensure_dir(dest_dir.parent)
        ensure_dir(dest_dir)

        playlist_dest = dest_dir

        # Get total videos count and build entries map for title rendering
        entries = get_playlist_entries(new_url_info)
        total_videos = len(entries)
        entries_by_id = {e.get("id"): e for e in entries if e.get("id")}

        for action in plan.videos_to_relocate:
            if action.old_path and action.old_path.exists():
                try:
                    # Calculate the new filename based on pattern and index
                    entry = entries_by_id.get(action.video_id)
                    if entry and action.new_index is not None:
                        # Render the filename with the new pattern
                        new_filename = render_title(
                            new_pattern,
                            i=action.new_index,
                            title=entry.get("title", action.title),
                            video_id=action.video_id,
                            ext=action.old_path.suffix.lstrip("."),
                            total=total_videos,
                            channel=playlist_channel,
                        )
                    else:
                        # Fallback to old name if we can't compute new name
                        new_filename = action.old_path.name

                    new_path = playlist_dest / new_filename

                    # Handle case where target exists
                    if new_path.exists() and new_path != action.old_path:
                        safe_push_log(
                            f"⚠️ Target exists during relocation, backup: {new_path.name}"
                        )
                        backup_path = new_path.with_suffix(f".backup{new_path.suffix}")
                        new_path.rename(backup_path)

                    shutil.move(str(action.old_path), str(new_path))
                    safe_push_log(
                        f"📁 Relocated: {action.old_path.name} → {new_location}/{new_filename}"
                    )
                except Exception as e:
                    safe_push_log(f"❌ Failed to relocate {action.old_path.name}: {e}")
                    success = False

        # Clean up old directory if it's now empty
        # Get the old directory from the first relocated video
        if plan.videos_to_relocate:
            old_dir = plan.videos_to_relocate[0].old_path.parent
            try:
                # Check if directory is empty (no files or subdirectories except possibly .DS_Store)
                remaining_files = [
                    f
                    for f in old_dir.iterdir()
                    if f.name not in [".DS_Store", "Thumbs.db"]
                ]
                if not remaining_files:
                    old_dir.rmdir()
                    safe_push_log(f"🧹 Removed empty old directory: {old_dir.name}")
            except Exception as e:
                # Not critical if cleanup fails
                safe_push_log(f"⚠️ Could not clean up old directory: {e}")

    # === Update status.json ===
    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        # Create new status
        from app.playlist_utils import create_playlist_status

        entries = get_playlist_entries(new_url_info)
        status_data = create_playlist_status(
            playlist_workspace,
            new_url_info.get("webpage_url", ""),
            plan.playlist_id,
            plan.playlist_title,
            entries,
        )
    else:
        # Update existing status
        new_entries = get_playlist_entries(new_url_info)
        new_video_ids = {e.get("id") for e in new_entries if e.get("id")}

        # Remove videos no longer in playlist from status
        videos = status_data.get("videos", {})
        videos_to_remove = [vid for vid in videos if vid not in new_video_ids]
        for vid in videos_to_remove:
            del videos[vid]

        # Add new videos to status
        for entry in new_entries:
            video_id = entry.get("id")
            if video_id and video_id not in videos:
                videos[video_id] = {
                    "title": entry.get("title", "Unknown"),
                    "url": entry.get("url", ""),
                    "status": "to_download",
                    "playlist_index": entry.get("playlist_index"),
                    "downloaded_at": None,
                    "error": None,
                }

        # Update existing video indices
        for entry in new_entries:
            video_id = entry.get("id")
            if video_id and video_id in videos:
                videos[video_id]["playlist_index"] = entry.get("playlist_index")
                # Update title if changed
                videos[video_id]["title"] = entry.get(
                    "title", videos[video_id].get("title", "")
                )

        # Mark renamed videos as completed
        for action in plan.videos_to_rename:
            if action.video_id in videos:
                videos[action.video_id]["status"] = "completed"
                videos[action.video_id]["resolved_title"] = (
                    action.new_path.name if action.new_path else None
                )

        # Mark synced videos
        for action in plan.videos_already_synced:
            if action.video_id in videos:
                videos[action.video_id]["status"] = "completed"

        # Mark relocated videos as completed with updated resolved_title
        for action in plan.videos_to_relocate:
            if action.video_id in videos:
                videos[action.video_id]["status"] = "completed"
                # Calculate the new filename (same logic as in apply)
                entry = next(
                    (e for e in new_entries if e.get("id") == action.video_id), None
                )
                if entry and action.new_index is not None and action.old_path:
                    new_filename = render_title(
                        new_pattern,
                        i=action.new_index,
                        title=entry.get("title", action.title),
                        video_id=action.video_id,
                        ext=action.old_path.suffix.lstrip("."),
                        total=len(new_entries),
                        channel=playlist_channel,
                    )
                    videos[action.video_id]["resolved_title"] = new_filename

        status_data["videos"] = videos
        status_data["total_videos"] = len(new_entries)
        status_data["title"] = plan.playlist_title

    # Record synchronization timestamp
    status_data["playlist_synchronisation"] = datetime.now(timezone.utc).isoformat()
    status_data["last_sync_location"] = new_location
    status_data["last_sync_pattern"] = new_pattern

    # Save updated status
    if not save_playlist_status(playlist_workspace, status_data):
        safe_push_log("❌ Failed to save updated status.json")
        success = False
    else:
        safe_push_log("✅ Updated status.json with sync results")

    return success


def is_sync_recent(playlist_workspace: Path, max_hours: float = 2.0) -> bool:
    """
    Check if playlist synchronization was performed recently.

    Args:
        playlist_workspace: Path to playlist workspace
        max_hours: Maximum age in hours for sync to be considered recent

    Returns:
        True if sync was performed within max_hours
    """
    from app.playlist_utils import load_playlist_status

    status_data = load_playlist_status(playlist_workspace)
    if not status_data:
        return False

    sync_timestamp = status_data.get("playlist_synchronisation")
    if not sync_timestamp:
        return False

    try:
        sync_time = datetime.fromisoformat(sync_timestamp.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_hours = (now - sync_time).total_seconds() / 3600
        return age_hours <= max_hours
    except Exception:
        return False


def format_sync_plan_summary(plan: PlaylistSyncPlan) -> str:
    """
    Format a human-readable summary of the sync plan.
    """
    lines = []
    lines.append(f"📋 Playlist: {plan.playlist_title}")
    lines.append("")

    if plan.location_changed:
        lines.append(f"📁 Location change: {plan.old_location} → {plan.new_location}")

    if plan.pattern_changed:
        lines.append(f"📝 Pattern change: {plan.old_pattern} → {plan.new_pattern}")

    if plan.location_changed or plan.pattern_changed:
        lines.append("")

    # Summary counts
    lines.append("📊 Summary:")
    lines.append(f"   ✅ Already synced: {len(plan.videos_already_synced)}")
    lines.append(f"   ✏️ To rename: {len(plan.videos_to_rename)}")
    lines.append(f"   📥 To download: {len(plan.videos_to_download)}")

    if plan.videos_to_archive:
        lines.append(f"   📦 To archive: {len(plan.videos_to_archive)}")

    if plan.videos_to_delete:
        lines.append(f"   🗑️ To delete: {len(plan.videos_to_delete)}")

    if plan.videos_to_relocate:
        lines.append(f"   📁 To relocate: {len(plan.videos_to_relocate)}")

    return "\n".join(lines)


def format_sync_plan_details(plan: PlaylistSyncPlan) -> str:
    """
    Format detailed list of all sync actions.
    """
    lines = []

    if plan.videos_to_rename:
        lines.append("#### ✏️ Videos to rename:")
        for action in plan.videos_to_rename:
            lines.append(f"- **{action.title}**")
            if action.details:
                lines.append(f"  - {action.details}")
        lines.append("")

    if plan.videos_to_download:
        lines.append("#### 📥 Videos to download:")
        for action in plan.videos_to_download:
            lines.append(f"- `[{action.new_index}]` {action.title}")
        lines.append("")

    if plan.videos_to_relocate:
        lines.append("#### 📁 Videos to relocate:")
        for action in plan.videos_to_relocate:
            lines.append(f"- {action.title}")
            if action.details:
                lines.append(f"  - {action.details}")
        lines.append("")

    if plan.videos_to_archive:
        lines.append("#### 📦 Videos to archive:")
        for action in plan.videos_to_archive:
            lines.append(f"- {action.title}")
        lines.append("")

    if plan.videos_to_delete:
        lines.append("#### 🗑️ Videos to delete:")
        for action in plan.videos_to_delete:
            lines.append(f"- {action.title}")
        lines.append("")

    if plan.videos_already_synced:
        lines.append("#### ✅ Already synced:")
        for action in plan.videos_already_synced[:5]:  # Show first 5 only
            lines.append(f"- {action.title}")
        if len(plan.videos_already_synced) > 5:
            lines.append(f"- *... and {len(plan.videos_already_synced) - 5} more*")
        lines.append("")

    return "\n".join(lines)

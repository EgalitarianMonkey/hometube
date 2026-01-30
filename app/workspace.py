"""
Centralized workspace management for HomeTube.

This module provides a unified API for managing temporary workspaces.
All videos are stored in a single location, regardless of whether they
are downloaded individually or as part of a playlist.

Directory structure:
    TMP_DOWNLOAD_FOLDER/
    ├── videos/
    │   └── {platform}/
    │       └── {video_id}/
    │           ├── url_info.json
    │           ├── status.json
    │           ├── video-{FORMAT_ID}.{ext}
    │           ├── subtitles.{lang}.srt
    │           └── final.{ext}
    └── playlists/
        └── {platform}/
            └── {playlist_id}/
                ├── url_info.json
                ├── status.json
                └── (no video files - references videos/ folder)

Benefits:
- A video is never downloaded twice (even if in playlist AND downloaded individually)
- Clear separation between video data and playlist metadata
- Consistent paths for all videos regardless of download context
- Easy cleanup and cache management
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class UrlInfo:
    """Parsed URL information."""

    platform: str
    id: str
    type: str  # "video" or "playlist"

    def __str__(self) -> str:
        """Return a readable string representation."""
        return f"{self.platform}/{self.type}/{self.id}"


def parse_url(url: str) -> UrlInfo:
    """
    Parse a URL to extract platform, ID, and type.

    Args:
        url: Video or playlist URL

    Returns:
        UrlInfo with platform, id, and type

    Examples:
        >>> parse_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        UrlInfo(platform='youtube', id='dQw4w9WgXcQ', type='video')
        >>> parse_url("https://www.youtube.com/playlist?list=PLxxx")
        UrlInfo(platform='youtube', id='PLxxx', type='playlist')
    """
    if not url:
        return UrlInfo(platform="unknown", id="unknown", type="video")

    url = url.strip()

    # YouTube Playlist
    youtube_playlist_match = re.search(
        r"youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)", url
    )
    if youtube_playlist_match:
        return UrlInfo(
            platform="youtube",
            id=youtube_playlist_match.group(1),
            type="playlist",
        )

    # YouTube standard format
    youtube_watch_match = re.search(
        r"(?:youtube\.com/watch\?v=|youtube\.com/.*[?&]v=)([a-zA-Z0-9_-]{11})", url
    )
    if youtube_watch_match:
        return UrlInfo(
            platform="youtube",
            id=youtube_watch_match.group(1),
            type="video",
        )

    # YouTube short URL
    youtube_short_match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
    if youtube_short_match:
        return UrlInfo(
            platform="youtube",
            id=youtube_short_match.group(1),
            type="video",
        )

    # YouTube Shorts
    youtube_shorts_match = re.search(r"youtube\.com/shorts/([a-zA-Z0-9_-]+)", url)
    if youtube_shorts_match:
        return UrlInfo(
            platform="youtube",
            id=youtube_shorts_match.group(1),
            type="video",
        )

    # Instagram
    instagram_match = re.search(r"instagram\.com/(?:p|reel|tv)/([a-zA-Z0-9_-]+)", url)
    if instagram_match:
        return UrlInfo(
            platform="instagram",
            id=instagram_match.group(1),
            type="video",
        )

    # TikTok
    tiktok_match = re.search(r"tiktok\.com/.*?/video/(\d+)", url)
    if tiktok_match:
        return UrlInfo(
            platform="tiktok",
            id=tiktok_match.group(1),
            type="video",
        )

    # TikTok short URL
    tiktok_short_match = re.search(r"v[mt]\.tiktok\.com/([a-zA-Z0-9]+)", url)
    if tiktok_short_match:
        return UrlInfo(
            platform="tiktok",
            id=tiktok_short_match.group(1),
            type="video",
        )

    # Vimeo
    vimeo_match = re.search(r"vimeo\.com/(\d+)", url)
    if vimeo_match:
        return UrlInfo(
            platform="vimeo",
            id=vimeo_match.group(1),
            type="video",
        )

    # Dailymotion
    dailymotion_match = re.search(r"dailymotion\.com/video/([a-zA-Z0-9]+)", url)
    if dailymotion_match:
        return UrlInfo(
            platform="dailymotion",
            id=dailymotion_match.group(1),
            type="video",
        )

    # Generic fallback
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    return UrlInfo(platform="generic", id=url_hash, type="video")


def get_video_workspace(tmp_base: Path, platform: str, video_id: str) -> Path:
    """
    Get the workspace path for a video.

    This is the canonical location for ALL video files, regardless of
    whether the video is downloaded individually or as part of a playlist.

    Args:
        tmp_base: Base temporary directory (e.g., TMP_DOWNLOAD_FOLDER)
        platform: Platform name (e.g., "youtube")
        video_id: Video ID

    Returns:
        Path to video workspace (e.g., tmp/videos/youtube/dQw4w9WgXcQ/)
    """
    return tmp_base / "videos" / platform / video_id


def get_playlist_workspace(tmp_base: Path, platform: str, playlist_id: str) -> Path:
    """
    Get the workspace path for a playlist.

    Playlist workspaces only contain metadata (status.json, url_info.json).
    Video files are stored in get_video_workspace() locations.

    Args:
        tmp_base: Base temporary directory
        platform: Platform name (e.g., "youtube")
        playlist_id: Playlist ID

    Returns:
        Path to playlist workspace (e.g., tmp/playlists/youtube/PLxxxxx/)
    """
    return tmp_base / "playlists" / platform / playlist_id


def get_workspace_from_url(tmp_base: Path, url: str) -> Path:
    """
    Get the appropriate workspace path for a URL.

    Automatically determines if URL is video or playlist and returns
    the correct workspace path.

    Args:
        tmp_base: Base temporary directory
        url: Video or playlist URL

    Returns:
        Path to workspace
    """
    info = parse_url(url)
    if info.type == "playlist":
        return get_playlist_workspace(tmp_base, info.platform, info.id)
    return get_video_workspace(tmp_base, info.platform, info.id)


def ensure_video_workspace(tmp_base: Path, platform: str, video_id: str) -> Path:
    """
    Get and create the workspace path for a video.

    Args:
        tmp_base: Base temporary directory
        platform: Platform name
        video_id: Video ID

    Returns:
        Path to created video workspace
    """
    workspace = get_video_workspace(tmp_base, platform, video_id)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def ensure_playlist_workspace(tmp_base: Path, platform: str, playlist_id: str) -> Path:
    """
    Get and create the workspace path for a playlist.

    Args:
        tmp_base: Base temporary directory
        platform: Platform name
        playlist_id: Playlist ID

    Returns:
        Path to created playlist workspace
    """
    workspace = get_playlist_workspace(tmp_base, platform, playlist_id)
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def ensure_workspace_from_url(tmp_base: Path, url: str) -> Tuple[Path, UrlInfo]:
    """
    Create and return workspace for a URL.

    Args:
        tmp_base: Base temporary directory
        url: Video or playlist URL

    Returns:
        Tuple of (workspace_path, url_info)
    """
    info = parse_url(url)
    if info.type == "playlist":
        workspace = ensure_playlist_workspace(tmp_base, info.platform, info.id)
    else:
        workspace = ensure_video_workspace(tmp_base, info.platform, info.id)
    return workspace, info


def get_video_workspace_for_playlist_entry(
    tmp_base: Path, video_id: str, platform: str = "youtube"
) -> Path:
    """
    Get video workspace for a playlist entry.

    This ensures all videos are stored in the same location, whether
    downloaded individually or as part of a playlist.

    Args:
        tmp_base: Base temporary directory
        video_id: Video ID
        platform: Platform name (default: "youtube")

    Returns:
        Path to video workspace
    """
    return get_video_workspace(tmp_base, platform, video_id)


def ensure_video_workspace_for_playlist_entry(
    tmp_base: Path, video_id: str, platform: str = "youtube"
) -> Path:
    """
    Create and return video workspace for a playlist entry.

    Args:
        tmp_base: Base temporary directory
        video_id: Video ID
        platform: Platform name (default: "youtube")

    Returns:
        Path to created video workspace
    """
    return ensure_video_workspace(tmp_base, platform, video_id)


# === LEGACY COMPATIBILITY ===
# These functions provide backward compatibility with the old naming scheme


def get_legacy_folder_name(url: str) -> str:
    """
    Get the legacy folder name for backward compatibility.

    This returns the old-style folder name (e.g., "youtube-dQw4w9WgXcQ")
    for compatibility with existing code that hasn't been migrated yet.

    Args:
        url: Video or playlist URL

    Returns:
        Legacy folder name string

    Note:
        This is deprecated. Use parse_url() and get_*_workspace() instead.
    """
    if not url:
        return "unknown"

    info = parse_url(url)

    # Handle unknown platform edge case
    if info.platform == "unknown" and info.id == "unknown":
        return "unknown"

    if info.type == "playlist":
        return f"{info.platform}-playlist-{info.id}"
    if info.platform == "youtube" and "shorts" in url.lower():
        return f"youtube-shorts-{info.id}"
    return f"{info.platform}-{info.id}"


def extract_platform_and_id(folder_name: str) -> Optional[Tuple[str, str, str]]:
    """
    Extract platform, ID and type from a legacy folder name.

    Args:
        folder_name: Legacy folder name (e.g., "youtube-dQw4w9WgXcQ")

    Returns:
        Tuple of (platform, id, type) or None if not parseable
    """
    # Playlist pattern: platform-playlist-id
    playlist_match = re.match(r"([a-z]+)-playlist-(.+)", folder_name)
    if playlist_match:
        return (playlist_match.group(1), playlist_match.group(2), "playlist")

    # Video pattern: platform-id (including youtube-shorts-id)
    video_match = re.match(r"([a-z]+(?:-shorts)?)-(.+)", folder_name)
    if video_match:
        platform = video_match.group(1)
        # Normalize youtube-shorts to youtube
        if platform == "youtube-shorts":
            platform = "youtube"
        return (platform, video_match.group(2), "video")

    return None

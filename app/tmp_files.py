"""
Temporary file naming utilities for HomeTube.

This module provides functions to generate standardized, generic filenames
for temporary files in the video processing pipeline. This approach improves
robustness by making the system independent of video titles and allows easy
verification of what files exist.

Directory structure (NEW):
    TMP_DOWNLOAD_FOLDER/
    ├── videos/
    │   └── {platform}/           # e.g., youtube, instagram, tiktok
    │       └── {video_id}/
    │           ├── url_info.json         # Video metadata from yt-dlp
    │           ├── status.json           # Download status and progress
    │           ├── video-{FORMAT_ID}.{ext}   # Downloaded video track
    │           ├── audio-{FORMAT_ID}.{ext}   # Downloaded audio track(s)
    │           ├── subtitles.{lang}.srt  # Original subtitles
    │           ├── subtitles-cut.{lang}.srt  # Cut subtitles
    │           ├── session.log           # Processing logs
    │           └── final.{ext}           # Final muxed file (moved to destination)
    └── playlists/
        └── {platform}/
            └── {playlist_id}/
                ├── url_info.json         # Playlist metadata
                └── status.json           # Playlist download status

Benefits:
- Videos are NEVER downloaded twice (shared between playlists and individual downloads)
- Generic names independent of video titles
- Easy to verify what exists
- Resilient to title changes or special characters
- Clear file purpose from name
- Supports interrupted downloads/resume
"""

from pathlib import Path
from typing import Optional

# Shared constant for video extensions used throughout the codebase
VIDEO_EXTENSIONS = ["mkv", "mp4", "webm", "avi", "mov"]
AUDIO_EXTENSIONS = ["opus", "m4a", "webm", "mp3", "aac"]


def get_video_track_path(tmp_dir: Path, format_id: str, extension: str) -> Path:
    """
    Get path for a video track file.

    Args:
        tmp_dir: Temporary directory for the video
        format_id: Format ID from yt-dlp (e.g., "399")
        extension: File extension (e.g., "webm", "mp4")

    Returns:
        Path to video track file (e.g., video-399.webm)
    """
    # Remove leading dot if present
    ext = extension.lstrip(".")
    return tmp_dir / f"video-{format_id}.{ext}"


def get_audio_track_path(tmp_dir: Path, format_id: str, extension: str) -> Path:
    """
    Get path for an audio track file.

    Args:
        tmp_dir: Temporary directory for the video
        format_id: Format ID from yt-dlp (e.g., "251")
        extension: File extension (e.g., "opus", "m4a")

    Returns:
        Path to audio track file (e.g., audio-251.opus)
    """
    ext = extension.lstrip(".")
    return tmp_dir / f"audio-{format_id}.{ext}"


def get_subtitle_path(tmp_dir: Path, language: str, is_cut: bool = False) -> Path:
    """
    Get path for a subtitle file.

    Args:
        tmp_dir: Temporary directory for the video
        language: Language code (e.g., "en", "fr")
        is_cut: Whether this is a cut subtitle file

    Returns:
        Path to subtitle file (e.g., subtitles.en.srt or subtitles-cut.en.srt)
    """
    if is_cut:
        return tmp_dir / f"subtitles-cut.{language}.srt"
    return tmp_dir / f"subtitles.{language}.srt"


def get_final_path(tmp_dir: Path, extension: str) -> Path:
    """
    Get path for the final processed file ready for copying to destination.
    Uses completely generic name independent of video title.

    Args:
        tmp_dir: Temporary directory for the video
        extension: File extension (e.g., "mkv", "mp4")

    Returns:
        Path object for final file

    Example:
        >>> get_final_path(Path("/tmp/vid"), "mkv")
        Path("/tmp/vid/final.mkv")
    """
    return tmp_dir / f"final.{extension}"


def get_session_log_path(tmp_dir: Path) -> Path:
    """
    Get path for session log file.

    Args:
        tmp_dir: Temporary directory for the video

    Returns:
        Path to session log file (session.log)
    """
    return tmp_dir / "session.log"


def find_video_tracks(tmp_dir: Path) -> list[Path]:
    """
    Find all video track files in the temporary directory.

    Args:
        tmp_dir: Temporary directory for the video

    Returns:
        List of paths to video track files
    """
    if not tmp_dir.exists():
        return []

    tracks = []
    for ext in VIDEO_EXTENSIONS:
        tracks.extend(tmp_dir.glob(f"video-*.{ext}"))

    return sorted(tracks)


def find_audio_tracks(tmp_dir: Path) -> list[Path]:
    """
    Find all audio track files in the temporary directory.

    Args:
        tmp_dir: Temporary directory for the video

    Returns:
        List of paths to audio track files
    """
    if not tmp_dir.exists():
        return []

    tracks = []
    for ext in AUDIO_EXTENSIONS:
        tracks.extend(tmp_dir.glob(f"audio-*.{ext}"))

    return sorted(tracks)


def find_subtitles(tmp_dir: Path, is_cut: bool = False) -> list[Path]:
    """
    Find all subtitle files in the temporary directory.

    Args:
        tmp_dir: Temporary directory for the video
        is_cut: Whether to search for cut subtitles

    Returns:
        List of paths to subtitle files
    """
    if not tmp_dir.exists():
        return []

    pattern = "subtitles-cut.*.srt" if is_cut else "subtitles.*.srt"
    return sorted(tmp_dir.glob(pattern))


def find_final_file(tmp_dir: Path) -> Optional[Path]:
    """
    Find the final processed file in the temporary directory.
    Prioritizes MKV over other formats.

    Args:
        tmp_dir: Temporary directory for the video

    Returns:
        Path to final file or None if not found
    """
    if not tmp_dir.exists():
        return None

    # Prioritize MKV format (best for modern codecs), then MP4, then others
    for ext in VIDEO_EXTENSIONS:
        candidate = tmp_dir / f"final.{ext}"
        if candidate.exists():
            return candidate

    return None


def find_downloaded_video(tmp_dir: Path) -> Optional[Path]:
    """
    Find ANY downloaded video file in the temporary directory.

    This is the RESILIENT function that checks for any video file,
    not just 'final.{ext}'. This handles cases where:
    - The video was downloaded with a different naming convention
    - The video download was interrupted before rename to 'final'
    - Legacy naming conventions like 'video-{format_id}.{ext}'

    Priority order:
    1. final.{ext} (preferred, fully processed)
    2. video-*.{ext} (downloaded but maybe not fully processed)
    3. Any .mkv/.mp4/.webm file (fallback for any video)

    Args:
        tmp_dir: Temporary directory for the video

    Returns:
        Path to any video file found, or None if no video exists
    """
    if not tmp_dir.exists():
        return None

    # Priority 1: Look for final.{ext} (fully processed)
    for ext in VIDEO_EXTENSIONS:
        candidate = tmp_dir / f"final.{ext}"
        if candidate.exists():
            return candidate

    # Priority 2: Look for video-*.{ext} (downloaded video tracks)
    for ext in VIDEO_EXTENSIONS:
        matches = list(tmp_dir.glob(f"video-*.{ext}"))
        if matches:
            # Return the first one (or the largest one for safety)
            return max(matches, key=lambda p: p.stat().st_size)

    # Priority 3: Any video file in the directory (excluding subtitles, logs, etc.)
    for ext in VIDEO_EXTENSIONS:
        matches = list(tmp_dir.glob(f"*.{ext}"))
        # Exclude known non-video patterns
        matches = [
            m
            for m in matches
            if not m.name.startswith("audio-") and not m.name.startswith("subtitles")
        ]
        if matches:
            return max(matches, key=lambda p: p.stat().st_size)

    return None


def extract_format_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract format ID from a video or audio track filename.

    Args:
        filename: Filename (e.g., "video-399.webm" or "audio-251.opus")

    Returns:
        Format ID or None if not matching pattern

    Examples:
        >>> extract_format_id_from_filename("video-399.webm")
        "399"
        >>> extract_format_id_from_filename("audio-251.opus")
        "251"
    """
    import re

    # Match pattern: (video|audio)-{format_id}.{ext}
    match = re.match(r"(?:video|audio)-([^.]+)\.", filename)
    if match:
        return match.group(1)

    return None


def extract_language_from_subtitle(filename: str) -> Optional[str]:
    """
    Extract language code from a subtitle filename.

    Args:
        filename: Filename (e.g., "subtitles.en.srt" or "subtitles-cut.fr.srt")

    Returns:
        Language code or None if not matching pattern

    Examples:
        >>> extract_language_from_subtitle("subtitles.en.srt")
        "en"
        >>> extract_language_from_subtitle("subtitles-cut.fr.srt")
        "fr"
    """
    import re

    # Match pattern: subtitles(-cut)?.{lang}.srt
    match = re.match(r"subtitles(?:-cut)?\.([^.]+)\.srt", filename)
    if match:
        return match.group(1)

    return None

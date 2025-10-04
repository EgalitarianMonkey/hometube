"""
Subtitle embedding utilities.

This module provides utilities for checking and embedding subtitles into video files,
independent of the Streamlit UI framework.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


# Import safe_push_log from main module
try:
    from main import safe_push_log
except ImportError:
    # Fallback for testing environments
    def safe_push_log(message: str) -> None:
        print(f"LOG: {message}")


def has_embedded_subtitles(video_path: Path) -> bool:
    """
    Check if a video file has embedded subtitles using ffprobe.

    Args:
        video_path: Path to the video file to check

    Returns:
        bool: True if embedded subtitles are found, False otherwise
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "s",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Check if there are any subtitle streams
        subtitle_streams = data.get("streams", [])
        has_subs = len(subtitle_streams) > 0

        if has_subs:
            safe_push_log(
                f"📝 Found {len(subtitle_streams)} embedded subtitle stream(s)"
            )
        else:
            safe_push_log("🔍 No embedded subtitles detected")

        return has_subs

    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        safe_push_log(
            "⚠️ Could not check embedded subtitles (ffprobe not available or failed)"
        )
        return False


def embed_subtitles_manually(video_path: Path, subtitle_files: List[Path]) -> bool:
    """
    Manually embed subtitle files into video using ffmpeg.

    Args:
        video_path: Path to the video file
        subtitle_files: List of subtitle file paths to embed

    Returns:
        bool: True if embedding was successful, False otherwise
    """
    if not subtitle_files:
        return False

    backup_path = None
    temp_output = None

    try:
        # Create backup of original
        backup_path = video_path.with_suffix(video_path.suffix + ".backup")
        shutil.copy2(str(video_path), str(backup_path))

        # Determine container format
        ext = video_path.suffix.lower()
        codec = "mov_text" if ext == ".mp4" else "srt"

        # Create temporary output with proper extension
        temp_output = video_path.parent / (video_path.stem + "_tmp" + video_path.suffix)

        # Build ffmpeg command
        cmd = ["ffmpeg", "-y", "-i", str(video_path)]

        # Add subtitle inputs
        for sub_file in subtitle_files:
            cmd.extend(["-i", str(sub_file)])

        # Map video and audio streams
        cmd.extend(["-map", "0:v", "-map", "0:a"])

        # Map subtitle streams with language metadata
        for i, sub_file in enumerate(subtitle_files):
            cmd.extend(["-map", f"{i+1}:s"])

            # Extract language from filename (e.g., filename.en.srt -> en)
            basename = sub_file.name
            parts = basename.split(".")
            if len(parts) >= 3 and len(parts[-2]) == 2:  # language code
                lang = parts[-2]
                cmd.extend([f"-metadata:s:s:{i}", f"language={lang}"])

        # Set codec and other options
        cmd.extend(
            [
                "-c:v",
                "copy",  # Copy video without re-encoding
                "-c:a",
                "copy",  # Copy audio without re-encoding
                "-c:s",
                codec,  # Subtitle codec
                str(temp_output),  # Output file with proper extension
            ]
        )

        safe_push_log("🔧 Manually embedding subtitles using ffmpeg...")
        safe_push_log(f"   Command: {' '.join(cmd[:10])}...")

        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            # Replace original with new file
            video_path.unlink()
            temp_output.rename(video_path)
            backup_path.unlink()
            safe_push_log("✅ Successfully embedded subtitles manually")
            return True
        else:
            # Restore backup on failure
            if temp_output and temp_output.exists():
                temp_output.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(video_path)
            safe_push_log(f"❌ Failed to embed subtitles manually: {result.stderr}")
            return False

    except Exception as e:
        # Restore backup on any error
        if backup_path and backup_path.exists():
            backup_path.rename(video_path)
        if temp_output and temp_output.exists():
            temp_output.unlink()
        safe_push_log(f"❌ Error during manual subtitle embedding: {str(e)}")
        return False


def find_subtitle_files(
    video_path: Path, search_patterns: Optional[List[str]] = None
) -> List[Path]:
    """
    Find subtitle files matching the video file.

    Args:
        video_path: Path to the video file
        search_patterns: Optional list of subtitle filename patterns to search for.
                        If None, will search for common patterns based on video filename.

    Returns:
        List[Path]: List of found subtitle files, sorted by name
    """
    video_dir = video_path.parent
    video_stem = video_path.stem

    # Default search patterns if none provided
    if search_patterns is None:
        search_patterns = [
            f"{video_stem}.*.srt",  # e.g., video.en.srt, video.fr.srt
            f"{video_stem}.srt",  # e.g., video.srt
        ]

    # Search for subtitle files
    subtitle_files = []
    for pattern in search_patterns:
        for sub_file in video_dir.glob(pattern):
            if sub_file.is_file() and sub_file not in subtitle_files:
                subtitle_files.append(sub_file)
                safe_push_log(f"📝 Found subtitle file: {sub_file.name}")

    # Sort subtitle files by name for consistent order
    subtitle_files.sort(key=lambda x: x.name)
    return subtitle_files


def ensure_subtitles_embedded(
    video_path: Path, search_patterns: Optional[List[str]] = None
) -> bool:
    """
    Ensure subtitles are embedded in video file. If not, find and embed available subtitle files.

    Args:
        video_path: Path to the video file
        search_patterns: Optional list of subtitle filename patterns to search for.
                        If None, will search for common patterns based on video filename.

    Returns:
        bool: True if subtitles are already embedded or successfully embedded, False otherwise
    """
    if not video_path.exists():
        safe_push_log(f"❌ Video file not found: {video_path}")
        return False

    # Check if subtitles are already embedded
    if has_embedded_subtitles(video_path):
        safe_push_log("✅ Subtitles already embedded")
        return True

    # Find available subtitle files
    subtitle_files = find_subtitle_files(video_path, search_patterns)

    if not subtitle_files:
        safe_push_log("⚠️ No subtitle files found for embedding")
        return False

    # Attempt manual embedding
    safe_push_log(f"🔧 Attempting to embed {len(subtitle_files)} subtitle file(s)...")
    success = embed_subtitles_manually(video_path, subtitle_files)

    if success:
        safe_push_log("✅ Subtitles successfully embedded")
        return True
    else:
        safe_push_log("❌ Failed to embed subtitles")
        return False

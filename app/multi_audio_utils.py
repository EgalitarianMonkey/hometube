"""
Utilities for handling multi-audio downloads.
yt-dlp has issues with multi-language audio format strings, so we handle it manually.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional


def download_video_and_audios_separately(
    url: str,
    video_format_id: str,
    audio_formats: List[Dict],
    output_base: Path,
    temp_dir: Path,
    cookies_args: List[str] = None,
) -> Tuple[bool, Optional[Path]]:
    """
    Download video and multiple audio tracks separately, then merge with ffmpeg.

    This is needed because yt-dlp's format string like "313+251-8+251-0+251-1"
    doesn't correctly handle multiple language-specific audio streams.

    Args:
        url: Video URL
        video_format_id: Video format ID (e.g., "313")
        audio_formats: List of audio format dicts with 'format_id' and 'language'
        output_base: Base path for output file (without extension)
        temp_dir: Temporary directory for intermediate files
        cookies_args: Optional cookies arguments for yt-dlp

    Returns:
        Tuple of (success: bool, output_path: Optional[Path])
    """
    if cookies_args is None:
        cookies_args = []

    # Step 1: Download video only
    video_file = temp_dir / f"video_{video_format_id}.webm"
    print(f"📥 Downloading video stream: {video_format_id}")

    cmd_video = (
        [
            "yt-dlp",
            "-f",
            video_format_id,
            "-o",
            str(video_file),
            "--no-part",  # Don't use .part files
        ]
        + cookies_args
        + [url]
    )

    result = subprocess.run(cmd_video, capture_output=True, text=True)
    if result.returncode != 0 or not video_file.exists():
        print(f"❌ Failed to download video: {result.stderr}")
        return False, None

    # Step 2: Download each audio track separately
    audio_files = []
    for i, audio_fmt in enumerate(audio_formats):
        format_id = audio_fmt.get("format_id", "")
        language = audio_fmt.get("language", f"unknown_{i}")

        audio_file = temp_dir / f"audio_{format_id}_{language}.webm"
        print(f"📥 Downloading audio stream: {format_id} ({language})")

        cmd_audio = (
            [
                "yt-dlp",
                "-f",
                format_id,
                "-o",
                str(audio_file),
                "--no-part",
            ]
            + cookies_args
            + [url]
        )

        result = subprocess.run(cmd_audio, capture_output=True, text=True)
        if result.returncode != 0 or not audio_file.exists():
            print(f"⚠️ Failed to download audio {format_id}: {result.stderr}")
            continue

        audio_files.append((audio_file, language))

    if not audio_files:
        print("❌ No audio tracks downloaded")
        return False, None

    # Step 3: Merge video + all audios with ffmpeg
    output_file = Path(str(output_base) + ".mkv")
    print(
        f"🔀 Merging video + {len(audio_files)} audio track(s) into {output_file.name}"
    )

    # Build ffmpeg command
    cmd_ffmpeg = ["ffmpeg", "-y", "-i", str(video_file)]

    # Add all audio inputs
    for audio_file, _ in audio_files:
        cmd_ffmpeg.extend(["-i", str(audio_file)])

    # Map video
    cmd_ffmpeg.extend(["-map", "0:v:0"])

    # Map all audios
    for i in range(len(audio_files)):
        cmd_ffmpeg.extend(["-map", f"{i+1}:a:0"])

    # Copy codecs (no re-encoding)
    cmd_ffmpeg.extend(["-c:v", "copy", "-c:a", "copy"])

    # Set audio metadata (language tags)
    for i, (_, language) in enumerate(audio_files):
        # Normalize language code (e.g., "en-US" -> "eng", "fr-FR" -> "fra")
        lang_code = language.split("-")[0].lower()
        iso_lang = {
            "en": "eng",
            "fr": "fra",
            "es": "spa",
            "de": "deu",
            "it": "ita",
            "pt": "por",
            "ja": "jpn",
            "id": "ind",
            "hi": "hin",
            "zh": "chi",
            "ar": "ara",
            "ru": "rus",
        }.get(lang_code, lang_code)

        cmd_ffmpeg.extend(["-metadata:s:a:" + str(i), f"language={iso_lang}"])

    # Set first audio as default
    if audio_files:
        cmd_ffmpeg.extend(["-disposition:a:0", "default"])

    cmd_ffmpeg.append(str(output_file))

    # Run ffmpeg
    result = subprocess.run(cmd_ffmpeg, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ FFmpeg merge failed: {result.stderr}")
        return False, None

    # Cleanup temporary files
    video_file.unlink(missing_ok=True)
    for audio_file, _ in audio_files:
        audio_file.unlink(missing_ok=True)

    print(f"✅ Successfully created multi-audio file: {output_file.name}")
    return True, output_file

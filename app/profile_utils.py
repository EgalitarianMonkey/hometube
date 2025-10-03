"""
Utility functions for quality profile matching.
Separated from main.py to avoid Streamlit imports in tests.
"""

from typing import List, Dict, Optional, Tuple
import subprocess
import re
from pathlib import Path


def parse_format_line(line: str) -> Optional[Dict]:
    """
    Parse a line from yt-dlp --list-formats output.

    Args:
        line: Line from the formats list

    Returns:
        Dict in EXAMPLE_FORMATS format or None if not a valid format
    """
    line = line.strip()

    # Ignore headers and empty lines
    if (
        not line
        or line.startswith("ID")
        or line.startswith("─")
        or "Available formats" in line
        or "storyboard" in line
        or "mhtml" in line
    ):
        return None

    parts = line.split()
    if len(parts) < 3:
        return None

    try:
        format_id = parts[0]
        ext = parts[1]

        # Detect resolution and type
        resolution_str = "unknown"
        height = 0
        fps = None
        vcodec = "none"
        acodec = "none"

        # Look for resolution
        for i, part in enumerate(parts):
            if "x" in part and part.replace("x", "").replace(".", "").isdigit():
                resolution_str = part
                try:
                    height = int(part.split("x")[1])
                except:
                    height = 0
                # FPS often after resolution
                if i + 1 < len(parts) and parts[i + 1].isdigit():
                    fps = int(parts[i + 1])
                break
            elif part == "audio" and i + 1 < len(parts) and parts[i + 1] == "only":
                resolution_str = "audio only"
                height = 0
                break

        # Detect codecs in line content
        line_lower = line.lower()

        # Video codecs
        if "avc1" in line_lower or "h264" in line_lower:
            vcodec = "avc1"
        elif "vp9" in line_lower:
            vcodec = "vp9"
        elif "av01" in line_lower:
            vcodec = "av01"

        # Audio codecs
        if "mp4a" in line_lower or "aac" in line_lower:
            acodec = "aac"
        elif "opus" in line_lower:
            acodec = "opus"

        # Look for bitrates (numbers followed by 'k')
        tbr = None
        abr = None
        vbr = None

        for part in parts:
            if part.endswith("k") and part[:-1].replace(".", "").isdigit():
                rate = int(float(part[:-1]))
                if resolution_str == "audio only":
                    abr = rate
                    tbr = rate
                elif vcodec != "none" and acodec == "none":
                    vbr = rate
                    tbr = rate
                elif tbr is None:
                    tbr = rate

        return {
            "format_id": format_id,
            "ext": ext,
            "resolution": resolution_str,
            "height": height,
            "fps": fps,
            "vcodec": vcodec,
            "acodec": acodec,
            "abr": abr,
            "vbr": vbr,
            "tbr": tbr,
            "protocol": "https",
            "format_note": (
                f"{height}p"
                if height > 0
                else ("audio" if resolution_str == "audio only" else "unknown")
            ),
        }

    except (ValueError, IndexError):
        return None


def get_max_allowed_resolution(
    video_quality_max: str, available_formats: List[Dict]
) -> int:
    """
    Détermine la résolution maximale autorisée basée sur VIDEO_QUALITY_MAX.

    Args:
        video_quality_max: Valeur de VIDEO_QUALITY_MAX ("max", "2160", "1440", "1080", etc.)
        available_formats: Liste des formats vidéo disponibles

    Returns:
        int: Résolution maximale autorisée en pixels (hauteur)
    """
    if not available_formats:
        return 1080  # Default fallback

    # Find max available resolution
    max_available = max(
        f.get("height", 0) for f in available_formats if f.get("height", 0) > 0
    )

    # If VIDEO_QUALITY_MAX = "max", return the max available
    if video_quality_max == "max":
        return max_available

    # Otherwise, try to parse as integer
    try:
        max_requested = int(video_quality_max)
        # Return minimum between requested and available
        return min(max_requested, max_available)
    except (ValueError, TypeError):
        # If parsing fails, use max available
        return max_available


def match_profiles_to_formats(
    formats: List[Dict], quality_profiles: List[Dict], video_quality_max: str = "max"
) -> List[Dict]:
    """
    Nouvelle logique simplifiée de matching des profils.

    1. Détermine la résolution max autorisée selon VIDEO_QUALITY_MAX
    2. Filtre les formats à cette résolution exacte
    3. Pour chaque profil dans l'ordre QUALITY_PROFILES, propose max 2 configurations

    Args:
        formats: Liste des formats récupérés par get_video_formats()
        quality_profiles: Liste des profils de qualité définis
        video_quality_max: Résolution max autorisée ("max", "2160", "1080", etc.)

    Returns:
        Liste des combinaisons dans l'ordre strict de QUALITY_PROFILES
    """
    if not formats or not quality_profiles:
        return []

    # Separate video and audio formats
    video_formats = [f for f in formats if f["vcodec"] != "none"]
    audio_formats = [f for f in formats if f["acodec"] != "none"]

    if not video_formats or not audio_formats:
        return []

    # 1. Determine max allowed resolution
    max_resolution = get_max_allowed_resolution(video_quality_max, video_formats)

    # 2. Filter formats to this exact resolution
    target_video_formats = [
        f for f in video_formats if f.get("height", 0) == max_resolution
    ]

    if not target_video_formats:
        return []

    # 3. Group by codec and sort by quality
    video_by_codec = {}
    audio_by_codec = {}

    for fmt in target_video_formats:
        codec = fmt["vcodec"]
        if codec not in video_by_codec:
            video_by_codec[codec] = []
        video_by_codec[codec].append(fmt)

    for fmt in audio_formats:
        codec = fmt["acodec"]
        if codec not in audio_by_codec:
            audio_by_codec[codec] = []
        audio_by_codec[codec].append(fmt)

    # Sort by quality within each group
    for codec_formats in video_by_codec.values():
        codec_formats.sort(
            key=lambda x: (x.get("fps", 0) or 0, x.get("vbr", 0) or 0), reverse=True
        )

    for codec_formats in audio_by_codec.values():
        codec_formats.sort(key=lambda x: x.get("abr", 0) or 0, reverse=True)

    # 4. New simple logic: max 2×2 combinations per profile in QUALITY_PROFILES order
    all_combinations = []

    for profile in quality_profiles:
        profile_name = profile["name"]
        profile_combinations = []

        # Match video codecs for this profile
        for video_spec in profile.get("video_codec_ext", []):
            required_codecs = video_spec.get("vcodec", [])
            allowed_exts = video_spec.get("ext", [None])

            for required_codec in required_codecs:
                # Chercher les codecs qui matchent (exact ou préfixe)
                matching_codecs = []
                for available_codec in video_by_codec.keys():
                    if (
                        available_codec == required_codec
                        or available_codec.startswith(required_codec + ".")
                        or (required_codec == "h264" and available_codec == "avc1")
                    ):
                        matching_codecs.append(available_codec)

        # Collect all compatible video and audio formats for this profile
        matching_video_formats = []
        matching_audio_formats = []

        # Collect compatible video formats
        for video_spec in profile.get("video_codec_ext", []):
            required_codecs = video_spec.get("vcodec", [])
            allowed_exts = video_spec.get("ext", [None])

            for required_codec in required_codecs:
                # Look for matching codecs (exact or prefix)
                matching_codecs = []
                for available_codec in video_by_codec.keys():
                    if (
                        available_codec == required_codec
                        or available_codec.startswith(required_codec + ".")
                        or (required_codec == "h264" and available_codec == "avc1")
                    ):
                        matching_codecs.append(available_codec)

                for video_codec in matching_codecs:
                    video_formats = video_by_codec[video_codec]

                    # Filter by extension if specified
                    if allowed_exts and None not in allowed_exts:
                        video_formats = [
                            f for f in video_formats if f["ext"] in allowed_exts
                        ]

                    if video_formats:
                        matching_video_formats.extend(
                            video_formats[:2]
                        )  # Top 2 per codec

        # Collect compatible audio formats
        for audio_spec in profile.get("audio_codec_ext", []):
            audio_required_codecs = audio_spec.get("acodec", [])
            audio_allowed_exts = audio_spec.get("ext", [None])

            for audio_required_codec in audio_required_codecs:
                matching_audio_codecs = []
                for available_codec in audio_by_codec.keys():
                    if available_codec == audio_required_codec or (
                        audio_required_codec == "mp4a" and available_codec == "aac"
                    ):
                        matching_audio_codecs.append(available_codec)

                for audio_codec in matching_audio_codecs:
                    audio_formats = audio_by_codec[audio_codec]

                    # Filter by extension if specified
                    if audio_allowed_exts and None not in audio_allowed_exts:
                        audio_formats = [
                            f for f in audio_formats if f["ext"] in audio_allowed_exts
                        ]

                    if audio_formats:
                        matching_audio_formats.extend(
                            audio_formats[:2]
                        )  # Top 2 per codec

        # Deduplicate and take the 2 best of each type
        video_matches = list(
            {f["format_id"]: f for f in matching_video_formats}.values()
        )[:2]
        audio_matches = list(
            {f["format_id"]: f for f in matching_audio_formats}.values()
        )[:2]

        # Create ALL combinations between the best videos and audios
        if video_matches and audio_matches:
            for video_format in video_matches:  # Each video format
                for audio_format in audio_matches:  # × Each audio format
                    combination = {
                        "profile_name": profile_name,
                        "profile_label": profile["label"],
                        "video_format": video_format,
                        "audio_format": audio_format,
                        "format_spec": f"{video_format['format_id']}+{audio_format['format_id']}",
                        "container": profile["container"],
                        "extra_args": profile.get("extra_args", []),
                        "priority": profile["priority"],
                        "target_resolution": max_resolution,
                    }
                    profile_combinations.append(combination)

        # Add all combinations from this profile (up to 4 max with 2×2)
        all_combinations.extend(profile_combinations)

    # Return in strict QUALITY_PROFILES order (no sorting by score)
    return all_combinations

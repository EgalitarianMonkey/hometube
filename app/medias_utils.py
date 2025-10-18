"""
Media analysis utilities for HomeTube.

This module provides functions to analyze audio and video formats
from yt-dlp JSON output to optimize download strategies.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json


def analyze_audio_formats(
    url_info: Dict,
    language_primary: str = "",
    languages_secondaries: str = "",
    vo_first: bool = True,
) -> Tuple[Optional[str], List[Dict], bool]:
    """
    Analyze audio formats from yt-dlp JSON output to find the best quality audio tracks.

    Strategy:
    1. Filter for audio-only formats (vcodec='none')
    2. Prefer Opus codec (best quality/compression ratio)
    3. Find the highest bitrate audio track
    4. Return ALL formats with the same base format ID (e.g., all 251-* variants)
    5. Detect original voice (VO) language
    6. Filter and order by language preferences: VO first, then primary, then secondaries

    Args:
        url_info: Dictionary from yt-dlp JSON output (from url_analysis())
        language_primary: Primary language code (e.g., "fr", "en")
        languages_secondaries: Comma-separated secondary languages (e.g., "en,es,de")
        vo_first: If True, prioritize original voice first

    Returns:
        Tuple[Optional[str], List[Dict], bool]:
        - Original voice language code (or None if not detected)
        - List of filtered and ordered audio formats
        - Boolean indicating if multiple languages are available

    Examples:
        >>> url_info = get_url_info()
        >>> vo_lang, best_audios, multi_lang = analyze_audio_formats(
        ...     url_info, language_primary="fr", languages_secondaries="en,es"
        ... )
        >>> if vo_lang:
        ...     print(f"Original voice: {vo_lang}")
        >>> if multi_lang:
        ...     print(f"Found {len(best_audios)} language tracks")
    """
    if not url_info or "error" in url_info:
        return None, [], False

    # Get formats list
    formats = url_info.get("formats", [])
    if not formats:
        return None, [], False

    # STEP 1: Filter audio-only formats (vcodec='none')
    audio_only_formats = [
        fmt
        for fmt in formats
        if fmt.get("vcodec") == "none" and fmt.get("acodec") not in [None, "none"]
    ]

    if not audio_only_formats:
        return None, [], False

    # STEP 2: Prefer Opus codec
    opus_formats = [
        fmt
        for fmt in audio_only_formats
        if fmt.get("acodec", "").lower().startswith("opus")
    ]

    # Use Opus if available, otherwise use all audio formats
    candidate_formats = opus_formats if opus_formats else audio_only_formats

    # STEP 3: Find the format with the highest bitrate
    best_format = max(candidate_formats, key=lambda x: x.get("abr", 0))

    # Extract base format ID (e.g., "251" from "251-8")
    best_format_id = best_format.get("format_id", "")
    base_format_id = (
        best_format_id.split("-")[0] if "-" in best_format_id else best_format_id
    )

    # STEP 4: Get ALL formats with the same base format ID
    # This retrieves the entire group (e.g., all 251-0, 251-1, 251-2, ..., 251-9)
    best_group = [
        fmt
        for fmt in candidate_formats
        if fmt.get("format_id", "").split("-")[0] == base_format_id
    ]

    if not best_group:
        return None, [], False

    # STEP 5: Detect original voice (VO) language
    # Look for formats with "original" or "default" in format_note
    vo_lang = None
    for fmt in best_group:
        format_note = fmt.get("format_note", "").lower()
        if "original" in format_note or "default" in format_note:
            vo_lang = fmt.get("language")
            break

    # STEP 6: Filter and order by language preferences
    multiple_langs = len(best_group) > 1

    if not multiple_langs:
        # Single audio track, return as-is
        return vo_lang, best_group, False

    # Parse secondary languages
    secondary_langs = []
    if languages_secondaries:
        secondary_langs = [
            lang.strip().lower()
            for lang in languages_secondaries.split(",")
            if lang.strip()
        ]

    # Build ordered list based on preferences
    ordered_audios = []
    seen_languages = set()

    def normalize_lang(lang: str) -> str:
        """Normalize language code for comparison (e.g., en-US -> en)"""
        if not lang:
            return ""
        return lang.lower().split("-")[0]

    def matches_language(fmt_lang: str, target_lang: str) -> bool:
        """Check if format language matches target language"""
        if not fmt_lang or not target_lang:
            return False
        fmt_normalized = normalize_lang(fmt_lang)
        target_normalized = target_lang.lower()
        return fmt_normalized == target_normalized or fmt_lang.lower().startswith(
            target_normalized
        )

    # 1. Add VO first (if vo_first is True and VO detected)
    if vo_first and vo_lang:
        for fmt in best_group:
            if fmt.get("language") == vo_lang:
                ordered_audios.append(fmt)
                seen_languages.add(normalize_lang(vo_lang))
                break

    # 2. Add primary language (if not already added as VO)
    if language_primary:
        primary_normalized = normalize_lang(language_primary)
        if primary_normalized not in seen_languages:
            for fmt in best_group:
                fmt_lang = fmt.get("language", "")
                if matches_language(fmt_lang, language_primary):
                    ordered_audios.append(fmt)
                    seen_languages.add(normalize_lang(fmt_lang))
                    break

    # 3. Add secondary languages (in order, without duplicates)
    for secondary in secondary_langs:
        secondary_normalized = normalize_lang(secondary)
        if secondary_normalized not in seen_languages:
            for fmt in best_group:
                fmt_lang = fmt.get("language", "")
                if matches_language(fmt_lang, secondary):
                    ordered_audios.append(fmt)
                    seen_languages.add(normalize_lang(fmt_lang))
                    break

    # 4. Add remaining languages not yet included
    for fmt in best_group:
        fmt_lang = fmt.get("language", "")
        fmt_normalized = normalize_lang(fmt_lang)
        if fmt_normalized and fmt_normalized not in seen_languages:
            ordered_audios.append(fmt)
            seen_languages.add(fmt_normalized)

    # If no preferences matched, return all in original order
    if not ordered_audios:
        ordered_audios = sorted(best_group, key=lambda x: x.get("format_id", ""))

    return vo_lang, ordered_audios, multiple_langs


def get_audio_format_summary(audio_format: Dict) -> str:
    """
    Get a human-readable summary of an audio format.

    Args:
        audio_format: Audio format dictionary from yt-dlp

    Returns:
        Formatted string with audio format details
    """
    format_id = audio_format.get("format_id", "unknown")
    acodec = audio_format.get("acodec", "unknown")
    abr = audio_format.get("abr", 0)
    asr = audio_format.get("asr", 0)
    language = audio_format.get("language", "")
    format_note = audio_format.get("format_note", "")

    # Build summary
    parts = [f"ID: {format_id}"]
    parts.append(f"Codec: {acodec}")
    parts.append(f"{int(abr)}kbps")

    if asr:
        parts.append(f"{int(asr/1000)}kHz")

    if language:
        parts.append(f"Lang: {language}")

    if format_note:
        parts.append(f"({format_note})")

    return " | ".join(parts)


def analyze_video_formats(
    url_info: Dict, max_resolution: Optional[int] = None
) -> List[Dict]:
    """
    Analyze video formats from yt-dlp JSON output to find the best quality video tracks.

    Strategy:
    1. Filter for video formats (acodec='none' or has vcodec)
    2. Apply resolution limit if specified
    3. Prefer modern codecs (AV1 > VP9 > H.264)
    4. Sort by resolution and fps

    Args:
        url_info: Dictionary from yt-dlp JSON output
        max_resolution: Optional maximum resolution (e.g., 1080, 2160)

    Returns:
        List of best video formats sorted by quality (best first)
    """
    if not url_info or "error" in url_info:
        return []

    formats = url_info.get("formats", [])
    if not formats:
        return []

    # Filter for video formats
    video_formats = [fmt for fmt in formats if fmt.get("vcodec") not in [None, "none"]]

    if not video_formats:
        return []

    # Apply resolution limit if specified
    if max_resolution:
        video_formats = [
            fmt for fmt in video_formats if fmt.get("height", 0) <= max_resolution
        ]

    # Score codecs (higher is better)
    codec_scores = {
        "av01": 3,  # AV1
        "vp9": 2,  # VP9
        "vp09": 2,  # VP9
        "avc1": 1,  # H.264
        "h264": 1,  # H.264
    }

    def get_codec_score(fmt: Dict) -> int:
        vcodec = fmt.get("vcodec", "").lower()
        for codec_prefix, score in codec_scores.items():
            if vcodec.startswith(codec_prefix):
                return score
        return 0

    # Sort by: resolution, fps, codec quality, bitrate
    sorted_videos = sorted(
        video_formats,
        key=lambda x: (
            x.get("height", 0),
            x.get("fps", 0),
            get_codec_score(x),
            x.get("vbr", 0) + x.get("tbr", 0),
        ),
        reverse=True,
    )

    return sorted_videos


def load_url_info_from_file(file_path: Path) -> Optional[Dict]:
    """
    Load URL info from a JSON file.

    Args:
        file_path: Path to the JSON file (e.g., tmp/url_info.json)

    Returns:
        Dictionary with URL info or None if error
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {file_path}: {e}")
        return None
    except Exception as e:
        print(f"Error loading URL info from {file_path}: {e}")
        return None


def get_format_details(url_info: Dict, format_id: str) -> Optional[Dict]:
    """
    Get detailed information about a specific format.

    Args:
        url_info: Dictionary from yt-dlp JSON output
        format_id: Format ID to search for (e.g., "251-0", "616")

    Returns:
        Format dictionary or None if not found
    """
    if not url_info or "error" in url_info:
        return None

    formats = url_info.get("formats", [])
    for fmt in formats:
        if fmt.get("format_id") == format_id:
            return fmt

    return None


def group_audio_by_language(audio_formats: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group audio formats by language code.

    Args:
        audio_formats: List of audio format dictionaries

    Returns:
        Dictionary mapping language code to list of formats
    """
    grouped = {}

    for fmt in audio_formats:
        lang = fmt.get("language", "unknown")
        if lang not in grouped:
            grouped[lang] = []
        grouped[lang].append(fmt)

    return grouped


def get_best_audio_for_language(url_info: Dict, language: str = "en") -> Optional[Dict]:
    """
    Get the best audio format for a specific language.

    Args:
        url_info: Dictionary from yt-dlp JSON output
        language: Language code (e.g., "en", "fr", "en-US")

    Returns:
        Best audio format for the language or None if not found
    """
    # Get all best audios without filtering
    vo_lang, best_audios, _ = analyze_audio_formats(url_info)

    # Filter by language (support both exact match and prefix match)
    language_lower = language.lower()
    matching_audios = [
        fmt
        for fmt in best_audios
        if fmt.get("language", "").lower().startswith(language_lower)
    ]

    if not matching_audios:
        return None

    # Return the one with highest bitrate
    return max(matching_audios, key=lambda x: x.get("abr", 0))

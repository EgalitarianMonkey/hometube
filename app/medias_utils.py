"""
Media analysis utilities for HomeTube.

This module provides functions to analyze audio and video formats
from yt-dlp JSON output to optimize download strategies.
"""

from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import subprocess
import shlex

from app.config import get_settings

s = get_settings()


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


ytdlp_formats_only_video_arg = str()

if (
    s.VIDEO_QUALITY_MAX == "max"
    or s.VIDEO_QUALITY_MAX == ""
    or s.VIDEO_QUALITY_MAX is None
):
    ytdlp_formats_only_video_arg = '-f "bv*"'
else:
    ytdlp_formats_only_video_arg = f'-f "bv*[height<={s.VIDEO_QUALITY_MAX}]"'

ytdlp_formats_video_audio_arg = f"{ytdlp_formats_only_video_arg}+ba/b"
YTDLP_FORMATS_SORT_AV1_FIRST_ARG = (
    '-S "res,fps,codec:av1,codec:vp9,codec:h264,br,ext:webm:moved,ext:mp4"'
)
YTDLP_FORMATS_SORT_VP9_FIRST_ARG = (
    '-S "res,fps,codec:vp9,codec:h264,br,ext:webm:moved,ext:mp4"'
)


def get_formats_id_to_download(
    url_info_path: Path, multiple_langs: bool, audio_formats: List[Dict] = None
) -> List[Dict]:
    """
    Determine optimal download profiles (max 2 profiles: AV1 and VP9).

    Strategy:
    - If multiple_langs=False: fetch video+audio pairs (bv*+ba/b)
    - If multiple_langs=True: fetch video only (bv*), audio tracks will be added after

    For each case, we search for 2 profiles:
    1. Best with AV1 first
    2. Best with VP9 first

    Args:
        url_info_path: Path to yt-dlp JSON file
        multiple_langs: True if multiple audio tracks in different languages
        audio_formats: List of audio formats to combine (if multiple_langs=True)

    Returns:
        List of profile dictionaries (max 2):
        [
            {"format_id": "399+251", "ext": "webm", "height": 1080, "vcodec": "vp9", "protocol": "https"},
            {"format_id": "616+251", "ext": "webm", "height": 1080, "vcodec": "av1", "protocol": "https"}
        ]
    """

    profiles = []

    # Determine format arg based on multiple_langs
    if multiple_langs:
        format_arg = ytdlp_formats_only_video_arg
    else:
        format_arg = ytdlp_formats_video_audio_arg

    # Prepare the two sorting variants (AV1 first, VP9 first)
    sort_variants = [
        ("av1", YTDLP_FORMATS_SORT_AV1_FIRST_ARG),
        ("vp9", YTDLP_FORMATS_SORT_VP9_FIRST_ARG),
    ]

    for codec_pref, sort_arg in sort_variants:
        try:
            # Build yt-dlp command
            cmd = [
                "yt-dlp",
                "--load-info-json",
                str(url_info_path),
                "--simulate",
            ]

            # Add format arguments (using shlex to handle quotes)
            cmd.extend(shlex.split(format_arg))

            # Add sorting arguments
            cmd.extend(shlex.split(sort_arg))

            # Add print argument
            cmd.extend(
                [
                    "--print",
                    '{"format_id":"%(format_id)s","ext":"%(ext)s","height":%(height)s,"vcodec":"%(vcodec)s","protocol":"%(protocol)s"}',
                ]
            )

            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                print(f"⚠️ yt-dlp error for {codec_pref}: {result.stderr}")
                continue

            # Parse output (first line = best format)
            output_lines = result.stdout.strip().split("\n")
            if not output_lines or not output_lines[0]:
                continue

            # Take only the first line (best format)
            best_format_line = output_lines[0]

            try:
                format_info = json.loads(best_format_line)

                # If multiple_langs, add audio tracks to videos
                if multiple_langs and audio_formats:
                    # Get video ID only
                    video_id = format_info["format_id"]

                    # Create a profile for each video + audios combination
                    audio_ids = "+".join(
                        [a.get("format_id", "") for a in audio_formats]
                    )
                    format_info["format_id"] = f"{video_id}+{audio_ids}"

                # Add to profiles list
                profiles.append(format_info)

            except json.JSONDecodeError as e:
                print(f"⚠️ Failed to parse yt-dlp output for {codec_pref}: {e}")
                continue

        except subprocess.TimeoutExpired:
            print(f"⚠️ yt-dlp timeout for {codec_pref}")
            continue
        except Exception as e:
            print(f"⚠️ Error getting format for {codec_pref}: {e}")
            continue

    # Deduplicate profiles (if AV1 and VP9 give the same result)
    unique_profiles = []
    seen_format_ids = set()

    for profile in profiles:
        format_id = profile.get("format_id", "")
        if format_id and format_id not in seen_format_ids:
            unique_profiles.append(profile)
            seen_format_ids.add(format_id)

    return unique_profiles[:2]  # Maximum 2 profiles


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


def get_video_title_from_json(json_path: Optional[Path] = None) -> str:
    """
    Get video title from local url_info.json file.

    This is the modern approach that uses the JSON file already downloaded
    by url_analysis(), avoiding additional yt-dlp calls.

    Args:
        json_path: Path to url_info.json file. If None, uses default TMP location.

    Returns:
        str: Sanitized video title suitable for filename, or "video" if unavailable
    """
    try:
        # Import here to avoid circular imports
        from app.config import ensure_folders_exist

        try:
            from .utils import sanitize_filename
            from .logs_utils import safe_push_log
        except ImportError:
            from utils import sanitize_filename
            from logs_utils import safe_push_log

        # Get default path if not provided
        if json_path is None:
            _, tmp_folder = ensure_folders_exist()
            json_path = tmp_folder / "url_info.json"

        # Check if file exists
        if not json_path.exists():
            safe_push_log("⚠️ url_info.json not found, using default title")
            return "video"

        safe_push_log("📋 Retrieving video title from url_info.json...")

        # Load and parse JSON
        with open(json_path, "r", encoding="utf-8") as f:
            url_info = json.load(f)

        # Extract title
        title = url_info.get("title", "")

        if not title:
            safe_push_log("⚠️ No title found in url_info.json")
            return "video"

        # Sanitize title for filename usage
        sanitized = sanitize_filename(title)
        safe_push_log(f"✅ Title retrieved from JSON: {title}")

        return sanitized

    except json.JSONDecodeError as e:
        safe_push_log(f"❌ Invalid JSON in url_info.json: {e}")
        return "video"
    except Exception as e:
        safe_push_log(f"⚠️ Error reading video title from JSON: {e}")
        return "video"


def get_video_title(url: str, cookies_part: List[str] = None) -> str:
    """
    Get video title with fallback strategy.

    Modern approach:
    1. First try to get title from url_info.json (fast, no network call)
    2. Fallback to direct yt-dlp call if JSON not available

    Args:
        url: Video URL (used for fallback only)
        cookies_part: Cookie parameters for fallback (optional)

    Returns:
        str: Sanitized video title suitable for filename
    """
    try:
        # Import here to avoid circular imports
        try:
            from .logs_utils import (
                safe_push_log,
                is_authentication_error,
                log_authentication_error_hint,
            )
            from .utils import sanitize_filename
        except ImportError:
            from logs_utils import (
                safe_push_log,
                is_authentication_error,
                log_authentication_error_hint,
            )
            from utils import sanitize_filename
        import subprocess

        # Strategy 1: Try to get title from existing JSON (fastest)
        title = get_video_title_from_json()
        if title != "video":  # Successfully got title from JSON
            return title

        # Strategy 2: Fallback to direct yt-dlp call
        safe_push_log("🔄 Fallback: Calling yt-dlp directly for title...")

        # Build command strategies
        strategies = []

        # Try with cookies first if available
        if cookies_part:
            strategies.append(
                {
                    "name": "with cookies",
                    "cmd": ["yt-dlp", "--print", "title", "--no-download"]
                    + cookies_part
                    + [url],
                }
            )

        # Try without cookies
        strategies.append(
            {
                "name": "without cookies",
                "cmd": ["yt-dlp", "--print", "title", "--no-download", url],
            }
        )

        # Try each strategy
        for strategy in strategies:
            try:
                result = subprocess.run(
                    strategy["cmd"], capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0 and result.stdout.strip():
                    title = result.stdout.strip()
                    sanitized = sanitize_filename(title)
                    safe_push_log(f"✅ Title retrieved via {strategy['name']}: {title}")
                    return sanitized
                else:
                    safe_push_log(
                        f"⚠️ Title extraction {strategy['name']} failed: {result.stderr.strip()[:50]}..."
                    )
                    # Only show auth hint for first failure with cookies
                    if strategy["name"] == "with cookies" and is_authentication_error(
                        result.stderr
                    ):
                        log_authentication_error_hint(result.stderr)

            except subprocess.TimeoutExpired:
                safe_push_log(f"⚠️ Title extraction {strategy['name']} timed out")
                continue
            except Exception as e:
                safe_push_log(f"⚠️ Title extraction {strategy['name']} error: {e}")
                continue

        # All strategies failed
        safe_push_log("⚠️ Could not retrieve video title, using default")
        return "video"

    except Exception as e:
        safe_push_log(f"❌ Error in get_video_title: {e}")
        return "video"

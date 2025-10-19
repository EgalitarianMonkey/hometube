"""
Quality profiles configuration for HomeTube - LEGACY/ARCHIVED

This module contains the OLD quality profiles system that has been replaced
by the new dynamic strategy (get_formats_id_to_download in medias_utils.py).

All functions here are kept for:
1. Historical reference
2. UI compatibility during migration
3. Archive of previous profile-matching logic

NEW CODE SHOULD USE: medias_utils.get_formats_id_to_download() instead!
"""

# Standard library
import time
import streamlit as st
from typing import Dict, List, Optional, Tuple, Union

# Import centralized utilities
try:
    from .process_utils import run_subprocess_safe
    from .logs_utils import safe_push_log, log_title
except ImportError:
    from process_utils import run_subprocess_safe
    from logs_utils import safe_push_log, log_title


# Lazy imports to avoid circular dependencies
def _get_main_functions():
    """Lazy import to avoid circular dependencies"""
    try:
        from . import main

        return main
    except ImportError:
        import main as main_module

        return main_module


# Logging functions are now imported from logs_utils


def sanitize_url(url: str) -> str:
    """Stub for utils.sanitize_url"""
    try:
        from .utils import sanitize_url as su

        return su(url)
    except ImportError:
        try:
            from utils import sanitize_url as su

            return su(url)
        except ImportError:
            return url


def get_cached_video_analysis(url: str):
    """Stub - returns empty cache"""
    return {}, []


# run_subprocess_safe is now imported from logs_utils


def parse_format_line(line: str) -> Optional[Dict]:
    """Stub for profile_utils.parse_format_line"""
    try:
        from .profile_utils import parse_format_line as pfl

        return pfl(line)
    except ImportError:
        try:
            from profile_utils import parse_format_line as pfl

            return pfl(line)
        except ImportError:
            return None


def match_profiles_to_formats(formats, profiles, video_quality_max):
    """Stub for profile_utils.match_profiles_to_formats"""
    try:
        from .profile_utils import match_profiles_to_formats as mptf

        return mptf(formats, profiles, video_quality_max)
    except ImportError:
        try:
            from profile_utils import match_profiles_to_formats as mptf

            return mptf(formats, profiles, video_quality_max)
        except ImportError:
            return []


# Settings stub
class SettingsStub:
    VIDEO_QUALITY_MAX = 2160
    QUALITY_PROFILE = "auto"


settings = None
try:
    from .config import get_settings

    settings = get_settings()
except ImportError:
    try:
        from config import get_settings

        settings = get_settings()
    except ImportError:
        settings = SettingsStub()

# Constants
CACHE_EXPIRY_MINUTES = 30


# Placeholder for removed functions (were in main.py but removed in refactor)
def _resolve_auto_profiles(available_formats, available_codecs):
    """Placeholder - this function was removed from main.py"""
    safe_push_log("⚠️ _resolve_auto_profiles is deprecated and no longer used")
    return (
        "auto",
        [],
        "Function deprecated - use _get_optimal_profiles_from_json instead",
    )


def _match_single_profile(profile, available_formats, profile_type):
    """Placeholder - this function was removed from main.py"""
    safe_push_log("⚠️ _match_single_profile is deprecated and no longer used")
    return (
        "forced",
        [],
        "Function deprecated - use _get_optimal_profiles_from_json instead",
    )


QUALITY_PROFILES = [
    {
        "name": "mkv_av1_opus",
        "label": "🏆 MKV – AV1 + Opus (Ultimate Quality)",
        "video_codec_ext": [
            {"vcodec": ["av01"], "ext": ["webm", "mp4", None]},
        ],
        "audio_codec_ext": [
            {"acodec": ["opus"], "ext": ["webm", "ogg", None]},
        ],
        "container": "mkv",
        "extra_args": ["--prefer-free-formats", "--remux-video", "mkv"],
        "description": "Best quality with next-gen codecs, fast remux, excellent subtitle support",
        "priority": 1,
    },
    {
        "name": "mkv_vp9_opus",
        "label": "🥇 MKV – VP9 + Opus (Premium Fallback)",
        "video_codec_ext": [
            {"vcodec": ["vp9.2", "vp9"], "ext": ["webm", None]},
        ],
        "audio_codec_ext": [
            {"acodec": ["opus"], "ext": ["webm", "ogg", None]},
        ],
        "container": "mkv",
        "extra_args": ["--prefer-free-formats", "--remux-video", "mkv"],
        "description": "Premium fallback when AV1 unavailable, excellent quality and subtitle support",
        "priority": 2,
    },
    {
        "name": "mp4_av1_aac",
        "label": "🥈 MP4 – AV1 + AAC (Mobile/TV Compatible)",
        "video_codec_ext": [
            {"vcodec": ["av01"], "ext": ["mp4", None]},
        ],
        "audio_codec_ext": [
            {"acodec": ["mp4a", "aac"], "ext": ["m4a", "mp4", None]},
        ],
        "container": "mp4",
        "extra_args": ["--remux-video", "mp4"],
        "description": "Next-gen video with universal audio, great mobile/TV compatibility",
        "priority": 3,
        "audio_transcode": True,  # May need to transcode Opus → AAC
    },
    {
        "name": "mp4_h264_aac",
        "label": "🥉 MP4 – H.264 + AAC (Maximum Compatibility)",
        "video_codec_ext": [
            {"vcodec": ["avc1", "h264"], "ext": ["mp4", None]},
        ],
        "audio_codec_ext": [
            {"acodec": ["mp4a", "aac"], "ext": ["m4a", "mp4", None]},
        ],
        "container": "mp4",
        "extra_args": ["--remux-video", "mp4"],
        "description": "Universal compatibility, works on all devices and platforms",
        "priority": 4,
        "audio_transcode": True,
    },
]


def get_video_formats(
    url: str, cookies_part: List[str] = None
) -> Tuple[bool, List[Dict], str]:
    """
    Retrieve video format list from yt-dlp.

    Args:
        url: Video URL to analyze
        cookies_part: Optional cookie parameters

    Returns:
        Tuple[bool, List[Dict], str]:
        - success: True if retrieval successful
        - formats: List of format dictionaries with format_id, ext, vcodec, acodec, height, etc.
        - error_msg: Error message if failed
    """
    if cookies_part is None:
        cookies_part = []

    safe_push_log("🔍 Retrieving video formats...")

    # Fallback strategies with different clients
    strategies = [
        {"name": "Default", "args": [], "timeout": 20},
        {
            "name": "Android",
            "args": ["--extractor-args", "youtube:player_client=android"],
            "timeout": 25,
        },
        {
            "name": "iOS",
            "args": ["--extractor-args", "youtube:player_client=ios"],
            "timeout": 25,
        },
        {
            "name": "Web",
            "args": ["--extractor-args", "youtube:player_client=web"],
            "timeout": 30,
        },
    ]

    last_error = ""

    for i, strategy in enumerate(strategies, 1):
        try:
            safe_push_log(f"🔄 Trying {strategy['name']} client...")

            # Build command
            cmd = ["yt-dlp", "--list-formats", "--no-download"] + strategy["args"]
            if cookies_part:
                cmd.extend(cookies_part)
                safe_push_log("   🍪 With authentication...")
            else:
                safe_push_log("   🌐 Without authentication...")
            cmd.append(url)

            result = run_subprocess_safe(
                cmd,
                timeout=strategy["timeout"],
                error_context=f"Extraction formats ({strategy['name']})",
            )

            if result.returncode == 0 and result.stdout.strip():
                output_lines = result.stdout.strip().split("\n")

                # Parse format lines
                formats = []
                for line in output_lines:
                    format_info = parse_format_line(line)
                    if format_info:
                        formats.append(format_info)

                if formats:
                    video_formats = [f for f in formats if f["vcodec"] != "none"]
                    audio_formats = [f for f in formats if f["acodec"] != "none"]

                    safe_push_log(
                        f"   ✅ {len(video_formats)} video formats, {len(audio_formats)} audio formats"
                    )
                    return True, formats, ""
                else:
                    safe_push_log("   ⚠️ No valid format parsed")
                    # Debug: show some output lines
                    safe_push_log(
                        f"   🔍 Debug: {len(output_lines)} yt-dlp output lines"
                    )
                    for i, line in enumerate(output_lines[:5]):  # First 5 lines
                        safe_push_log(
                            f"   Line {i+1}: {line[:80]}..."
                        )  # Truncate to 80 chars
            else:
                error_msg = result.stderr.strip() if result.stderr else "No output"
                safe_push_log(f"   ❌ Failed: {error_msg[:50]}...")
                last_error = error_msg

        except Exception as e:
            safe_push_log(f"   💥 Exception: {str(e)[:50]}...")
            last_error = str(e)
            continue

    safe_push_log("❌ All extraction strategies failed")
    return False, [], last_error


# === PROFILE MATCHING SYSTEM ===


def extract_format_codecs(formats: List[Dict]) -> Dict:
    """
    Extract available codecs and their formats from yt-dlp format list.

    Args:
        formats: List of format dictionaries from yt-dlp

    Returns:
        Dict with video_codecs and audio_codecs analysis
    """
    video_codecs = {}
    audio_codecs = {}

    for fmt in formats:
        # Extract video codec info
        vcodec = fmt.get("vcodec", "none")
        if vcodec and vcodec != "none":
            ext = fmt.get("ext", "unknown")
            resolution = fmt.get("height", 0)
            fps = fmt.get("fps", 0)

            if vcodec not in video_codecs:
                video_codecs[vcodec] = []

            video_codecs[vcodec].append(
                {
                    "format_id": fmt.get("format_id"),
                    "ext": ext,
                    "resolution": resolution,
                    "fps": fps,
                    "filesize": fmt.get("filesize"),
                    "tbr": fmt.get("tbr"),
                }
            )

        # Extract audio codec info
        acodec = fmt.get("acodec", "none")
        if acodec and acodec != "none":
            ext = fmt.get("ext", "unknown")
            abr = fmt.get("abr", 0)

            if acodec not in audio_codecs:
                audio_codecs[acodec] = []

            audio_codecs[acodec].append(
                {
                    "format_id": fmt.get("format_id"),
                    "ext": ext,
                    "abr": abr,
                    "filesize": fmt.get("filesize"),
                }
            )

    return {"video_codecs": video_codecs, "audio_codecs": audio_codecs}


def match_codec_requirements(
    available_codecs: Dict, codec_ext_requirements: List[Dict]
) -> List[Dict]:
    """
    Match available codecs against profile requirements.

    Args:
        available_codecs: Available codecs from extract_format_codecs()
        codec_ext_requirements: List of codec/ext requirements from profile

    Returns:
        List of matching codec combinations with their formats
    """
    matches = []

    for requirement in codec_ext_requirements:
        required_codecs = requirement.get("vcodec", requirement.get("acodec", []))
        allowed_exts = requirement.get("ext", [])

        for codec in required_codecs:
            # Check for exact match or prefix match (e.g., 'av01' matches 'av01.0.08M.08')
            matching_codecs = [
                available_codec
                for available_codec in available_codecs.keys()
                if available_codec == codec or available_codec.startswith(codec)
            ]

            for matching_codec in matching_codecs:
                codec_formats = available_codecs[matching_codec]

                # Filter by extension if specified
                if allowed_exts and None not in allowed_exts:
                    codec_formats = [
                        fmt for fmt in codec_formats if fmt["ext"] in allowed_exts
                    ]

                if codec_formats:
                    # Sort by quality (resolution for video, bitrate for audio)
                    if "resolution" in codec_formats[0]:  # Video codec
                        codec_formats.sort(
                            key=lambda x: (x["resolution"], x["fps"], x["tbr"] or 0),
                            reverse=True,
                        )
                    else:  # Audio codec
                        codec_formats.sort(key=lambda x: x["abr"] or 0, reverse=True)

                    matches.append(
                        {
                            "codec": matching_codec,
                            "original_requirement": requirement,
                            "formats": codec_formats[:3],  # Top 3 best formats
                        }
                    )

    return matches


def match_profiles_to_formats_auto(formats: List[Dict]) -> List[Dict]:
    """
    Compatibility wrapper - match all QUALITY_PROFILES with available formats.

    Args:
        formats: List of formats retrieved by get_video_formats()

    Returns:
        List of optimal combinations sorted by priority/quality
    """
    if not formats:
        safe_push_log("❌ No format available for matching")
        return []

    # Progress logging
    video_formats = [f for f in formats if f["vcodec"] != "none"]
    audio_formats = [f for f in formats if f["acodec"] != "none"]
    safe_push_log(
        f"📊 Analysis: {len(video_formats)} video formats, {len(audio_formats)} audio formats"
    )

    # Use utility function with VIDEO_QUALITY_MAX and all QUALITY_PROFILES
    video_quality_max = settings.VIDEO_QUALITY_MAX
    combinations = match_profiles_to_formats(
        formats, QUALITY_PROFILES, video_quality_max
    )

    # Log results
    if combinations:
        safe_push_log(f"🎯 {len(combinations)} combinations generated:")
        for i, combo in enumerate(combinations, 1):
            video_info = combo["video_format"]
            audio_info = combo["audio_format"]
            safe_push_log(f"   {i}. {combo['profile_label']}")
            safe_push_log(
                f"      Format: {combo['format_spec']} ({video_info['height']}p + {audio_info['abr']}kbps)"
            )
    else:
        safe_push_log("❌ No viable combination found")

    return combinations


def get_optimal_profiles(formats: List[Dict], max_profiles: int = 10) -> List[Dict]:
    """
    Compatibility function - calls the new match_profiles_to_formats.

    Args:
        formats: List of yt-dlp formats
        max_profiles: Maximum number of profiles to return

    Returns:
        List of optimal combinations sorted by priority and quality
    """
    combinations = match_profiles_to_formats_auto(formats)
    return combinations[:max_profiles]


def get_profile_availability_summary(formats: List[Dict]) -> Dict:
    """
    Get a summary of profile availability for UI display.

    Args:
        formats: List of format dictionaries from yt-dlp

    Returns:
        Dictionary with profile availability information
    """
    if not formats:
        return {}

    available_formats = extract_format_codecs(formats)
    summary = {}

    for profile in QUALITY_PROFILES:
        video_matches = match_codec_requirements(
            available_formats["video_codecs"], profile["video_codec_ext"]
        )
        audio_matches = match_codec_requirements(
            available_formats["audio_codecs"], profile["audio_codec_ext"]
        )

        available = len(video_matches) > 0 and len(audio_matches) > 0

        summary[profile["name"]] = {
            "available": available,
            "label": profile["label"],
            "video_codecs_found": len(video_matches),
            "audio_codecs_found": len(audio_matches),
            "video_matches": [m["codec"] for m in video_matches],
            "audio_matches": [m["codec"] for m in audio_matches],
        }

    return summary


def format_profile_for_display(combination: Dict) -> str:
    """
    Format a profile combination for user-friendly display.

    Args:
        combination: Profile combination from get_optimal_profiles()

    Returns:
        Formatted string for display
    """
    video_info = combination["video_format"]
    audio_info = combination["audio_format"]

    return (
        f"{combination['profile_label']} | "
        f"{video_info['resolution']}@{video_info.get('fps', '?')}fps "
        f"({video_info.get('vcodec', '?')}) + "
        f"{audio_info.get('abr', '?')}kbps "
        f"({audio_info.get('acodec', '?')})"
    )


# === END DYNAMIC PROFILE MATCHING SYSTEM ===


def analyze_video_formats_unified(
    url: str, cookies_part: List[str]
) -> Tuple[Dict[str, bool], List[Dict]]:
    """
    Unified function that analyzes video formats and detects available codecs.

    Compatibility wrapper around the new get_video_formats functions.

    Args:
        url: Video URL to analyze
        cookies_part: Cookie parameters for authentication

    Returns:
        Tuple[Dict[str, bool], List[Dict]]:
        - Codec availability dict: {"av01": True, "vp9": True, ...}
        - List of all available formats with details (sorted by quality)
    """
    safe_push_log("")
    log_title("🔍 Analyzing video formats and codecs...")

    # Use the new simplified function
    success, formats, error_msg = get_video_formats(url, cookies_part)

    if success and formats:
        # Extract available codecs
        video_codecs = set()
        audio_codecs = set()

        for fmt in formats:
            if fmt["vcodec"] != "none":
                video_codecs.add(fmt["vcodec"])
            if fmt["acodec"] != "none":
                audio_codecs.add(fmt["acodec"])

        # Create availability dict for compatibility
        codecs_available = {
            "av01": any(codec.startswith("av01") for codec in video_codecs),
            "vp9": "vp9" in video_codecs,
            "h264": any(
                codec in ["h264", "avc1"] or codec.startswith("avc1")
                for codec in video_codecs
            ),
            "opus": "opus" in audio_codecs,
            "aac": "aac" in audio_codecs
            or any(codec.startswith("mp4a") for codec in audio_codecs),
        }

        # Sort formats by quality (descending height)
        sorted_formats = sorted(formats, key=lambda x: x.get("height", 0), reverse=True)

        safe_push_log(f"✅ Codecs detected: {sum(codecs_available.values())}/5")
        safe_push_log(f"📊 Formats analyzed: {len(sorted_formats)}")

        return codecs_available, sorted_formats

    # In case of failure, optimistic default return
    safe_push_log("⚠️ Analysis failed, using default values")
    default_codecs = {
        "av01": True,
        "vp9": True,
        "h264": True,
        "opus": True,
        "aac": True,
    }
    return default_codecs, []


def filter_viable_profiles(
    available_codecs: Dict[str, bool], mode: str = "auto"
) -> List[Dict]:
    """
    Filter quality profiles based on available codecs.

    Args:
        available_codecs: Dict of codec availability from probe_available_formats
        mode: "auto" for fallback mode, "forced" for single profile mode

    Returns:
        List of viable profiles, sorted by priority
    """
    viable_profiles = []

    # Analyze each profile for compatibility
    for profile in QUALITY_PROFILES:
        # Check if required codecs are available
        required_codecs = profile.get("requires_probe", [])
        profile_viable = all(
            available_codecs.get(codec, True) for codec in required_codecs
        )

        if profile_viable:
            viable_profiles.append(profile)
        else:
            missing_codecs = [
                codec
                for codec in required_codecs
                if not available_codecs.get(codec, True)
            ]

            # Provide detailed explanation for why profile was skipped
            reason_details = []
            if "av01" in missing_codecs:
                reason_details.append("AV1 codec not detected")
            if "vp9" in missing_codecs:
                reason_details.append("VP9 codec not detected")
            if "opus" in missing_codecs:
                reason_details.append("Opus audio not detected")

            reason_str = (
                " & ".join(reason_details)
                if reason_details
                else f"missing: {', '.join(missing_codecs)}"
            )
            safe_push_log(f"⏭️ Skipping {profile['label']} - {reason_str}")

    if not viable_profiles:
        # Fallback to most compatible profile if nothing else works
        safe_push_log("")
        safe_push_log("⚠️ Compatibility fallback activated")
        safe_push_log("💡 No profiles matched the detected codecs")
        safe_push_log("🔄 Forcing H.264 + AAC profile (maximum compatibility)")

        viable_profiles = [
            profile for profile in QUALITY_PROFILES if profile["name"] == "mp4_h264_aac"
        ]

        if not viable_profiles:
            safe_push_log("❌ Critical error: Even basic H.264 profile not found!")

    if viable_profiles:
        safe_push_log(f"✅ Final selection: {len(viable_profiles)} viable profile(s)")
        for i, p in enumerate(viable_profiles, 1):
            safe_push_log(f"   {i}. {p['label']}")
    return sorted(viable_profiles, key=lambda x: x["priority"])


def generate_format_string_from_profile(profile: Dict) -> str:
    """
    Generate a yt-dlp format string from a modern profile structure.

    Args:
        profile: Profile dict with video_codec_ext and audio_codec_ext

    Returns:
        yt-dlp format string compatible with the old format system
    """
    video_parts = []
    audio_parts = []

    # Generate video format selectors
    for video_spec in profile.get("video_codec_ext", []):
        codecs = video_spec.get("vcodec", [])
        exts = video_spec.get("ext", [])

        for codec in codecs:
            codec_selector = f"[vcodec^={codec}]"

            if exts and None not in exts:
                # Has specific extension requirements
                for ext in exts:
                    if ext:
                        video_parts.append(f"bv*{codec_selector}[ext={ext}]")
            else:
                # No specific extension requirements
                video_parts.append(f"bv*{codec_selector}")

    # Generate audio format selectors
    for audio_spec in profile.get("audio_codec_ext", []):
        codecs = audio_spec.get("acodec", [])
        exts = audio_spec.get("ext", [])

        for codec in codecs:
            codec_selector = f"[acodec^={codec}]"

            if exts and None not in exts:
                # Has specific extension requirements
                for ext in exts:
                    if ext:
                        audio_parts.append(f"ba*{codec_selector}[ext={ext}]")
            else:
                # No specific extension requirements
                audio_parts.append(f"ba*{codec_selector}")

    # Combine video and audio parts
    if not video_parts:
        video_parts = ["bv*"]
    if not audio_parts:
        audio_parts = ["ba*"]

    # Create combinations - each video with each audio
    combinations = []
    for video in video_parts[:2]:  # Limit to avoid too long strings
        for audio in audio_parts[:2]:
            combinations.append(f"{video}+{audio}")

    # Join combinations with fallback separator
    return "/".join(combinations) + "/b*"  # Final fallback to any format


def get_profile_by_name(profile_name: str) -> Optional[Dict]:
    """
    Get a quality profile by name (case-insensitive).

    Args:
        profile_name: Name of the profile to find

    Returns:
        Profile dict if found, None otherwise
    """
    if not profile_name or not isinstance(profile_name, str):
        return None

    profile_name = profile_name.strip().lower()

    # Skip auto mode
    if profile_name == "auto":
        return None

    for profile in QUALITY_PROFILES:
        if profile["name"].lower() == profile_name:
            return profile

    return None


def format_profile_codec_info(profile: Dict) -> str:
    """Format profile codec information for display."""
    # Extract video codecs
    video_codecs = []
    for video_spec in profile.get("video_codec_ext", []):
        video_codecs.extend(video_spec.get("vcodec", []))
    video_display = " / ".join(video_codecs) if video_codecs else "Any"

    # Extract audio codecs
    audio_codecs = []
    for audio_spec in profile.get("audio_codec_ext", []):
        audio_codecs.extend(audio_spec.get("acodec", []))
    audio_display = " / ".join(audio_codecs) if audio_codecs else "Any"

    container = profile.get("container", "Unknown")

    return f"🎬 Video: **{video_display}** | 🎵 Audio: **{audio_display}** | 📦 Container: **{container.upper()}**"


def get_default_profile_index() -> int:
    """
    Get the default profile index based on QUALITY_PROFILE configuration.

    For UI display purposes only. The actual profile selection logic
    is handled in smart_download_with_profiles().

    Returns:
        Index of the configured profile in QUALITY_PROFILES, or 0 if auto/not found
    """
    default_profile_name = settings.QUALITY_PROFILE

    # Auto mode or empty - return first profile for UI display
    if default_profile_name in ["", "auto"]:
        return 0

    # Find the index of the configured profile
    for i, profile in enumerate(QUALITY_PROFILES):
        if profile["name"].lower() == default_profile_name:
            return i

    # If configured profile not found, return 0 and log a warning
    print(
        f"⚠️ Configured QUALITY_PROFILE '{default_profile_name}' not found, using first profile for display"
    )
    return 0


def get_download_configuration() -> Dict:
    """
    Centralized configuration retrieval from session state.

    Returns:
        Dict with all download configuration parameters
    """
    # Check if we have a dynamic profile selected (new system)
    dynamic_profile = st.session_state.get("dynamic_profile_selected", None)
    selected_profile_name = None

    if dynamic_profile:
        # Use dynamic_profile object directly
        selected_profile_name = dynamic_profile
    else:
        # Fallback to traditional profile name lookup
        profile_name = st.session_state.get("quality_profile", None)
        if profile_name:
            selected_profile_name = profile_name

    return {
        "download_mode": st.session_state.get("download_mode", "auto"),
        "selected_profile_name": selected_profile_name,
        "selected_format": st.session_state.get("selected_format", "auto"),
        "refuse_quality_downgrade": st.session_state.get(
            "refuse_quality_downgrade", False
        ),
        "embed_chapters": st.session_state.get("embed_chapters", True),
        "embed_subs": st.session_state.get("embed_subs", True),
        "ytdlp_custom_args": st.session_state.get("ytdlp_custom_args", ""),
    }


def show_download_failure_help(cookies_available: bool, profiles_count: int):
    """
    Display helpful error messages when all download attempts fail.

    Args:
        cookies_available: Whether cookies are configured and available
        profiles_count: Number of profiles that were attempted
    """
    safe_push_log("")
    safe_push_log("❌ All profiles failed")
    safe_push_log("=" * 30)

    if not cookies_available:
        safe_push_log("🔑 No authentication configured")
        safe_push_log("💡 Try: Enable browser cookies or export cookie file")
    else:
        safe_push_log("🔑 Authentication issue")
        safe_push_log(
            "� Try: Refresh browser authentication or check video accessibility"
        )

    safe_push_log("📺 Modern video platforms require fresh auth for premium codecs")
    safe_push_log("=" * 30)


def _get_video_analysis_cached(
    url: str, cookies_part: List[str]
) -> Tuple[Dict[str, bool], List[Dict]]:
    """Get video format analysis with intelligent caching."""
    cached_url = st.session_state.get("codecs_detected_for_url", "")
    cache_timestamp = st.session_state.get("formats_detection_timestamp", 0)
    cache_age_minutes = (time.time() - cache_timestamp) / 60

    if cached_url == sanitize_url(url) and cache_age_minutes < CACHE_EXPIRY_MINUTES:
        # Use recent cache
        available_codecs, available_formats = get_cached_video_analysis(url)
        safe_push_log(f"💾 Using cached analysis ({cache_age_minutes:.1f}min old)")
    else:
        # Force fresh analysis for accurate profile matching
        safe_push_log("🆕 Fresh format analysis required for accurate profile matching")
        available_codecs, available_formats = analyze_video_formats_unified(
            sanitize_url(url), cookies_part
        )

        # Cache the results
        st.session_state["available_codecs"] = available_codecs
        st.session_state["available_formats"] = available_formats
        st.session_state["codecs_detected_for_url"] = sanitize_url(url)
        st.session_state["formats_detection_timestamp"] = time.time()

    # Show analysis summary
    codec_count = sum(available_codecs.values())
    format_count = len(available_formats)
    safe_push_log(
        f"📊 Analysis complete: {codec_count} codecs detected, {format_count} formats available"
    )

    if format_count == 0:
        safe_push_log("⚠️ No formats detected - this may indicate an access issue")
        safe_push_log("💡 Profile matching will use static fallback method")
    else:
        safe_push_log("✅ Format analysis successful - using dynamic profile matching")

    return available_codecs, available_formats


def resolve_download_profiles(
    download_mode: str,
    target_profile: Optional[Union[str, Dict]],
    available_formats: List[Dict],
    available_codecs: Dict[str, bool],
) -> Tuple[str, List[Dict], Optional[str]]:
    """
    Resolve which profiles to try for download based on mode and target.

    Args:
        download_mode: "auto" or "forced"
        target_profile: Profile name (str) or pre-resolved profile (dict) or None
        available_formats: List of available video formats
        available_codecs: Dict of detected codecs

    Returns:
        Tuple[actual_mode, profiles_to_try, error_message]
        - actual_mode: Final mode determined ("auto" or "forced")
        - profiles_to_try: List of profile dicts ready for download
        - error_message: Error string if resolution failed, None if success
    """
    # Handle QUALITY_PROFILE environment configuration
    configured_profile_name = settings.QUALITY_PROFILE

    if not target_profile:  # Only apply config if no explicit target
        if configured_profile_name in ["", "auto"]:
            safe_push_log("🤖 QUALITY_PROFILE=auto: Dynamic profile selection enabled")
            download_mode = "auto"
        else:
            configured_profile = get_profile_by_name(configured_profile_name)
            if configured_profile:
                safe_push_log(
                    f"⚙️ QUALITY_PROFILE={configured_profile_name}: Using specific profile"
                )
                safe_push_log(f"🎯 Profile: {configured_profile['label']}")
                download_mode = "forced"
                target_profile = configured_profile_name
            else:
                safe_push_log(
                    f"❌ ERROR: Configured QUALITY_PROFILE '{configured_profile_name}' not found!"
                )
                safe_push_log(
                    "📋 Available profiles: "
                    + ", ".join([p["name"] for p in QUALITY_PROFILES])
                )
                safe_push_log("🔄 Falling back to automatic profile selection")
                download_mode = "auto"

    # Resolve profiles based on final mode
    if download_mode == "forced" and target_profile:
        return _resolve_forced_profile(target_profile, available_formats)
    else:
        return _resolve_auto_profiles(available_formats, available_codecs)


def _resolve_forced_profile(
    target_profile: Union[str, Dict], available_formats: List[Dict]
) -> Tuple[str, List[Dict], Optional[str]]:
    """Resolve a single forced profile."""
    if isinstance(target_profile, dict):
        # Dynamic profile from UI
        safe_push_log(f"🔒 FORCED MODE (dynamic): {target_profile['label']}")

        if "_dynamic_combination" in target_profile:
            # Pre-resolved profile from UI - use directly
            safe_push_log("✅ Using pre-resolved profile combination from UI selection")
            return "forced", [target_profile], None
        else:
            # Raw dynamic profile - needs format matching
            safe_push_log("🔍 Matching dynamic profile with available formats...")
            return _match_single_profile(target_profile, available_formats, "dynamic")
    else:
        # Static profile name
        forced_profile = get_profile_by_name(target_profile)
        if not forced_profile:
            return "forced", [], f"Unknown profile: {target_profile}"

        safe_push_log(f"🔒 FORCED MODE (static): {forced_profile['label']}")
        safe_push_log("🔍 Matching static profile with available formats...")
        return _match_single_profile(forced_profile, available_formats, "static")

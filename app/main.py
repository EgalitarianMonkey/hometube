# Standard library imports
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Third-party imports
import requests
import streamlit as st

try:
    # Try relative imports first (when running as module or with Streamlit)
    from .translations import t, configure_language
    from .core import (
        build_base_ytdlp_command,
        build_cookies_params as core_build_cookies_params,
        build_sponsorblock_params as core_build_sponsorblock_params,
        get_sponsorblock_config as core_get_sponsorblock_config,
    )
    from .utils import (
        is_valid_cookie_file,
        sanitize_filename,
        sanitize_url,
        video_id_from_url,
        parse_time_like,
        fmt_hhmmss,
    )
    from .subtitles_utils import (
        embed_subtitles_manually,
        process_subtitles_for_cutting,
        check_required_subtitles_embedded,
        find_subtitle_files_optimized,
    )
    from .medias_utils import (
        analyze_audio_formats,
        get_formats_id_to_download,
        get_video_title,
        customize_video_metadata,
    )
    from .ytdlp_version_check import check_and_show_updates
    from .logs_utils import (
        is_cookies_expired_warning,
        should_suppress_message,
        is_authentication_error,
        is_format_unavailable_error,
        safe_push_log,
        log_title,
        log_authentication_error_hint,
        log_format_unavailable_error_hint,
        register_main_push_log,
    )

    from .file_system_utils import (
        list_subdirs_recursive,
        cleanup_tmp_files,
        should_remove_tmp_files,
        ensure_dir,
        move_file,
    )
    from .cut_utils import (
        get_keyframes,
        find_nearest_keyframes,
        build_cut_command,
    )
except ImportError:
    # Fallback for direct execution from app directory
    from translations import t, configure_language
    from core import (
        build_base_ytdlp_command,
        build_cookies_params as core_build_cookies_params,
        build_sponsorblock_params as core_build_sponsorblock_params,
        get_sponsorblock_config as core_get_sponsorblock_config,
    )
    from utils import (
        is_valid_cookie_file,
        sanitize_filename,
        sanitize_url,
        video_id_from_url,
        parse_time_like,
        fmt_hhmmss,
    )
    from subtitles_utils import (
        embed_subtitles_manually,
        process_subtitles_for_cutting,
        check_required_subtitles_embedded,
        find_subtitle_files_optimized,
    )
    from medias_utils import (
        analyze_audio_formats,
        get_formats_id_to_download,
        get_video_title,
        customize_video_metadata,
    )
    from ytdlp_version_check import check_and_show_updates
    from logs_utils import (
        is_cookies_expired_warning,
        should_suppress_message,
        is_authentication_error,
        is_format_unavailable_error,
        safe_push_log,
        log_title,
        log_authentication_error_hint,
        log_format_unavailable_error_hint,
        register_main_push_log,
    )

    from file_system_utils import (
        list_subdirs_recursive,
        cleanup_tmp_files,
        should_remove_tmp_files,
        ensure_dir,
        move_file,
    )
    from cut_utils import (
        get_keyframes,
        find_nearest_keyframes,
        build_cut_command,
    )

# Configuration import (must be after translations for configure_language)
from app.config import get_settings, ensure_folders_exist, print_config_summary

# === CONSTANTS ===

# Load settings once
settings = get_settings()

# Configure translations with the loaded UI language
configure_language(settings.UI_LANGUAGE)

# Ensure folders exist and get paths
VIDEOS_FOLDER, TMP_DOWNLOAD_FOLDER = ensure_folders_exist()

# Extract commonly used settings for backward compatibility
YOUTUBE_COOKIES_FILE_PATH = settings.YOUTUBE_COOKIES_FILE_PATH
COOKIES_FROM_BROWSER = settings.COOKIES_FROM_BROWSER
SUBTITLES_CHOICES = settings.SUBTITLES_CHOICES
IN_CONTAINER = settings.IN_CONTAINER

# Print configuration summary in development mode
if __name__ == "__main__" or settings.DEBUG:
    print_config_summary()

# CSS Styles
LOGS_CONTAINER_STYLE = """
    height: 400px;
    overflow-y: auto;
    background-color: #0e1117;
    color: #fafafa;
    padding: 1rem;
    border-radius: 0.5rem;
    font-family: 'Source Code Pro', monospace;
    font-size: 14px;
    line-height: 1.4;
    white-space: pre-wrap;
    border: 1px solid #262730;
"""

# API and system constants
SPONSORBLOCK_API = "https://sponsor.ajay.app"
MIN_COOKIE_FILE_SIZE = 100  # bytes
ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Browser support for cookie extraction
SUPPORTED_BROWSERS = [
    "brave",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "safari",
    "vivaldi",
    "whale",
]

# YouTube client fallback chain (ordered by reliability)
YOUTUBE_CLIENT_FALLBACKS = [
    {"name": "default", "args": []},
    {"name": "android", "args": ["--extractor-args", "youtube:player_client=android"]},
    {"name": "ios", "args": ["--extractor-args", "youtube:player_client=ios"]},
    {"name": "web", "args": ["--extractor-args", "youtube:player_client=web"]},
]

# Profile resolution constants
CACHE_EXPIRY_MINUTES = 5
MAX_OPTIMAL_PROFILES = 10

# Authentication error patterns
AUTH_ERROR_PATTERNS = [
    "sign in to confirm",
    "please log in",
    "login required",
    "video is private",
    "video is unavailable",
    "age restricted",
    "requires authentication",
    "authentication required",
    "requested format is not available",
    "format is not available",
    "403",
    "forbidden",
]


# === LEGACY STUBS FOR UI COMPATIBILITY ===
# These functions are stubs to allow the UI to compile
# The actual download logic uses ONLY the new strategy (_get_optimal_profiles_from_json)

# Empty profile list - old static profiles not used anymore
QUALITY_PROFILES = []


def get_profile_by_name(name: str) -> Optional[Dict]:
    """Stub - not used in new strategy"""
    return None


def get_default_profile_index() -> int:
    """Stub - not used in new strategy"""
    return 0


def format_profile_codec_info(profile: Dict) -> str:
    """Stub - not used in new strategy"""
    return "Using new dynamic strategy"


def get_optimal_profiles(formats: List[Dict], max_profiles: int = 10) -> List[Dict]:
    """Stub - not used in new strategy"""
    return []


def get_profile_availability_summary(formats: List[Dict]) -> Dict:
    """Stub - not used in new strategy"""
    return {}


def analyze_video_formats_unified(
    url: str, cookies_part: List[str]
) -> Tuple[Dict[str, bool], List[Dict]]:
    """Stub - not used in new strategy"""
    return {}, []


def get_download_configuration() -> Dict:
    """Stub - returns default config for new strategy"""
    return {
        "download_mode": "auto",
        "selected_profile_name": None,
        "selected_format": None,
        "refuse_quality_downgrade": False,
    }


def generate_format_string_from_profile(profile: Dict) -> str:
    """Stub - not used in new strategy"""
    return ""


# === VIDEO FORMAT EXTRACTION AND ANALYSIS ===


# parse_format_line is now imported at the top of the file from profile_utils


def _get_optimal_profiles_from_json() -> List[Dict]:
    """
    Get optimal download profiles using new strategy with get_formats_id_to_download().

    This function uses the intelligent format selection strategy that:
    - Prioritizes AV1 and VP9 codecs over H.264
    - Returns max 2 profiles (AV1-first and VP9-first)
    - Handles multi-language audio tracks correctly
    - Uses yt-dlp's format sorting directly

    Returns:
        List of profile dicts ready for download, or empty list if error
    """
    try:
        # Check if url_info.json exists
        json_path = TMP_DOWNLOAD_FOLDER / "url_info.json"
        if not json_path.exists():
            safe_push_log("⚠️ url_info.json not found, cannot use new profile strategy")
            return []

        # Load url_info to analyze audio tracks
        with open(json_path, "r", encoding="utf-8") as f:
            url_info = json.load(f)

        # Get language preferences from settings
        language_primary = settings.LANGUAGE_PRIMARY or "en"
        languages_secondaries = settings.LANGUAGES_SECONDARIES or ""
        vo_first = settings.VO_FIRST

        # Analyze audio formats
        safe_push_log("🎵 Analyzing audio tracks...")
        vo_lang, audio_formats, multiple_langs = analyze_audio_formats(
            url_info,
            language_primary=language_primary,
            languages_secondaries=languages_secondaries,
            vo_first=vo_first,
        )

        safe_push_log(f"   VO language: {vo_lang or 'unknown'}")
        safe_push_log(f"   Audio tracks: {len(audio_formats)}")
        safe_push_log(f"   Multi-language: {'Yes' if multiple_langs else 'No'}")

        # Get optimal profiles using new strategy
        safe_push_log("🎯 Selecting optimal video formats (AV1/VP9 priority)...")
        optimal_format_profiles = get_formats_id_to_download(
            str(json_path), multiple_langs, audio_formats
        )

        if not optimal_format_profiles:
            safe_push_log("❌ No optimal profiles returned by new strategy")
            return []

        log_title(f"✅ Found {len(optimal_format_profiles)} optimal profile(s)")

        # Convert to HomeTube profile format
        profiles_to_try = []
        for idx, format_profile in enumerate(optimal_format_profiles, 1):
            format_id = format_profile.get("format_id", "")
            vcodec = format_profile.get("vcodec", "unknown")
            height = format_profile.get("height", 0)
            ext = format_profile.get("ext", "unknown")
            protocol = format_profile.get("protocol", "https")

            # Determine codec label for display
            codec_label = "Unknown"
            if "av01" in vcodec.lower() or "av1" in vcodec.lower():
                codec_label = "AV1"
            elif "vp9" in vcodec.lower() or "vp09" in vcodec.lower():
                codec_label = "VP9"
            elif "avc" in vcodec.lower() or "h264" in vcodec.lower():
                codec_label = "H.264"

            # Determine container: Always MKV for modern codecs (AV1/VP9/Opus)
            # Modern format combination works best with MKV container
            container = "mkv"

            # Build profile name and label
            profile_name = f"optimal_{codec_label.lower()}_{height}p"
            profile_label = f"🎯 Optimal {codec_label} {height}p"

            safe_push_log("")
            safe_push_log(f"📦 Profile {idx}: {profile_label}")
            safe_push_log(f"   🆔 Format ID: {format_id}")
            safe_push_log(f"   🎬 Video Codec: {vcodec} ({codec_label})")
            safe_push_log(f"   📐 Resolution: {height}p")
            safe_push_log(f"   📦 Extension: {ext}")
            safe_push_log(f"   📁 Output Container: {container.upper()}")
            safe_push_log(f"   🌐 Protocol: {protocol}")

            # Create profile dict compatible with download system
            profile_compat = {
                "name": profile_name,
                "label": profile_label,
                "format": format_id,  # Direct format ID from yt-dlp
                "format_sort": "",  # Not needed, format already selected
                "extra_args": [],
                "container": container,
                "priority": idx,  # First profile has highest priority
                "_format_profile": format_profile,  # Keep original data for display
            }

            profiles_to_try.append(profile_compat)

        log_title(
            f"🎯 Will try {len(profiles_to_try)} profile(s) in order (best codec first)"
        )
        return profiles_to_try

    except FileNotFoundError:
        safe_push_log("⚠️ url_info.json not found for new profile strategy")
        return []
    except Exception as e:
        safe_push_log(f"⚠️ Error in new profile strategy: {e}")
        import traceback

        safe_push_log(f"   Traceback: {traceback.format_exc()}")
        return []


def smart_download_with_profiles(
    base_output: str,
    tmp_subfolder_dir: Path,
    embed_chapters: bool,
    embed_subs: bool,
    force_mp4: bool,
    ytdlp_custom_args: str,
    url: str,
    download_mode: str,
    target_profile: Optional[Union[str, Dict]] = None,
    refuse_quality_downgrade: bool = False,
    do_cut: bool = False,
    subs_selected: List[str] = None,
    sb_choice: str = "disabled",
    progress_placeholder=None,
    status_placeholder=None,
    info_placeholder=None,
) -> Tuple[int, str]:
    """
    Intelligent profile-based download with smart fallback strategy.

    This function implements the core quality profile system:
    1. Probes available codecs for compatibility
    2. Filters viable profiles based on codec availability
    3. Tries profiles in quality order (best to most compatible)
    4. For each profile, attempts all YouTube client fallbacks
    5. Supports both authentication methods (cookies + fallback)

    Args:
        download_mode: "auto" (try all viable profiles) or "forced" (single profile only)
        target_profile: specific profile name for forced mode
        refuse_quality_downgrade: stop at first failure instead of trying lower quality

    Returns:
        Tuple[int, str]: (return_code, error_message)
    """
    safe_push_log("")
    log_title("🎯 Starting profile-based download...")

    # Setup cookies (compact)
    cookies_available = False
    cookies_part = []
    cookies_method = st.session_state.get("cookies_method", "none")
    if cookies_method != "none":
        cookies_part = build_cookies_params()
        cookies_available = len(cookies_part) > 0

    # Reset session-based message suppression for new download
    session_keys_to_reset = ["auth_hint_shown_this_download", "po_token_warning_shown"]
    for key in session_keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]

    # Use NEW STRATEGY ONLY: get_formats_id_to_download() for optimal AV1/VP9 selection
    log_title("🎯 Selecting optimal profiles...")
    profiles_to_try = (
        _get_optimal_profiles_from_json()
    )  # Formats loaded from url_info.json

    if not profiles_to_try:
        error_msg = "No optimal profiles found. Make sure url_info.json exists and contains valid format data."
        safe_push_log(f"❌ {error_msg}")
        return 1, error_msg

    safe_push_log("")

    # Execute download attempts
    return _execute_profile_downloads(
        profiles_to_try,
        base_output,
        tmp_subfolder_dir,
        embed_chapters,
        embed_subs,
        ytdlp_custom_args,
        url,
        cookies_part,
        cookies_available,
        refuse_quality_downgrade,
        do_cut,
        subs_selected,
        sb_choice,
        progress_placeholder,
        status_placeholder,
        info_placeholder,
        download_mode,
    )


def _handle_profile_failure(
    profile: Dict,
    profile_idx: int,
    profiles_to_try: List[Dict],
    download_mode: str,
    refuse_quality_downgrade: bool,
) -> bool:
    """Handle profile failure and determine if we should continue trying."""
    safe_push_log("")
    safe_push_log(f"❌ FAILED: {profile['label']}")

    # Diagnose the main issue
    last_error = st.session_state.get("last_error", "").lower()
    if "requested format is not available" in last_error:
        safe_push_log("⚠️ Format rejected (authentication limitation)")
    elif any(auth_pattern in last_error for auth_pattern in AUTH_ERROR_PATTERNS):
        safe_push_log("🔐 Authentication/permission issue")
    else:
        safe_push_log("⚠️ Technical compatibility issue")

    # Determine fallback strategy
    remaining_profiles = len(profiles_to_try) - profile_idx

    if download_mode == "forced":
        safe_push_log("🔒 FORCED MODE: No fallback allowed")
        return False
    elif refuse_quality_downgrade:
        safe_push_log("🚫 STOPPING: Quality downgrade refused")
        return False
    elif remaining_profiles > 0:
        safe_push_log(
            f"🔄 FALLBACK: Trying next profile ({remaining_profiles} remaining)"
        )
        return True
    else:
        safe_push_log("❌ No more profiles available")
        return False


def _try_profile_with_clients(
    cmd_base: List[str],
    url: str,
    cookies_part: List[str],
    cookies_available: bool,
    status_placeholder,
    progress_placeholder,
    info_placeholder,
) -> bool:
    """Try downloading with all YouTube client fallbacks for a profile."""
    for client_idx, client in enumerate(YOUTUBE_CLIENT_FALLBACKS, 1):
        client_name = client["name"]
        client_args = client["args"]

        # Try with cookies first if available
        if cookies_available:
            if status_placeholder:
                status_placeholder.info(f"🍪 {client_name.title()} + cookies")

            cmd = cmd_base + client_args + cookies_part + [url]
            ret = run_cmd(
                cmd, progress_placeholder, status_placeholder, info_placeholder
            )

            if ret == 0:
                safe_push_log(f"✅ SUCCESS: {client_name.title()} client + cookies")
                return True

        # Try without cookies
        if status_placeholder:
            status_placeholder.info(f"🚀 {client_name.title()} client")

        cmd = cmd_base + client_args + [url]
        ret = run_cmd(cmd, progress_placeholder, status_placeholder, info_placeholder)

        if ret == 0:
            safe_push_log(f"✅ SUCCESS: {client_name.title()} client")
            return True

    return False


def _build_profile_command(
    profile: Dict,
    base_output: str,
    tmp_subfolder_dir: Path,
    embed_chapters: bool,
    embed_subs: bool,
    ytdlp_custom_args: str,
    subs_selected: List[str],
    do_cut: bool,
    sb_choice: str,
) -> List[str]:
    """Build ytdlp command for a specific profile."""
    # Get format string (always present in new strategy profiles)
    format_string = profile.get("format", "")

    # Create quality strategy
    quality_strategy = {
        "format": format_string,
        "format_sort": profile.get("format_sort", "res,fps,+size,br"),
        "extra_args": profile.get("extra_args", []),
    }

    # Use profile's container preference
    profile_container = profile.get("container", "mkv").lower()
    profile_force_mp4 = profile_container == "mp4"

    # Build base command
    cmd_base = build_base_ytdlp_command(
        base_output,
        tmp_subfolder_dir,
        format_string,
        embed_chapters,
        embed_subs,
        profile_force_mp4,
        ytdlp_custom_args,
        quality_strategy,
    )

    # Add subtitle options
    if subs_selected:
        langs_csv = ",".join(subs_selected)
        cmd_base.extend(
            [
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs",
                langs_csv,
                "--convert-subs",
                "srt",
            ]
        )

        # Embed preference
        embed_flag = (
            "--no-embed-subs"
            if do_cut
            else ("--embed-subs" if embed_subs else "--no-embed-subs")
        )
        cmd_base.append(embed_flag)

    # Add SponsorBlock parameters
    sb_params = build_sponsorblock_params(sb_choice)
    if sb_params:
        cmd_base.extend(sb_params)

    return cmd_base


def _get_profile_codec_info(profile: Dict) -> List[str]:
    """Extract codec information from profile for display."""
    codec_info = []

    # Extract format profile data (all profiles use new strategy format)
    format_profile = profile.get("_format_profile", {})
    video_codec = format_profile.get("vcodec", "").lower()
    format_id = profile.get("format", "")
    height = format_profile.get("height", 0)

    # Video codec info (detailed)
    if "av01" in video_codec or "av1" in video_codec:
        codec_info.append("🎬 AV1 codec")
    elif "vp9" in video_codec or "vp09" in video_codec:
        codec_info.append("🎥 VP9 codec")
    elif "avc" in video_codec or "h264" in video_codec:
        codec_info.append("📺 H.264 codec")
    else:
        codec_info.append(f"🎞️ {video_codec}")

    # Resolution info
    codec_info.append(f"📐 {height}p")

    # Format ID info
    codec_info.append(f"🆔 {format_id}")

    return codec_info


def _execute_profile_downloads(
    profiles_to_try: List[Dict],
    base_output: str,
    tmp_subfolder_dir: Path,
    embed_chapters: bool,
    embed_subs: bool,
    ytdlp_custom_args: str,
    url: str,
    cookies_part: List[str],
    cookies_available: bool,
    refuse_quality_downgrade: bool,
    do_cut: bool,
    subs_selected: List[str],
    sb_choice: str,
    progress_placeholder,
    status_placeholder,
    info_placeholder,
    download_mode: str,
) -> Tuple[int, str]:
    """Execute download attempts for each profile."""
    log_title("🚀 Starting download attempts...")

    for profile_idx, profile in enumerate(profiles_to_try, 1):
        safe_push_log("")
        safe_push_log(
            f"🏆 Profile {profile_idx}/{len(profiles_to_try)}: {profile['label']}"
        )

        # Show codec information concisely
        codec_info = _get_profile_codec_info(profile)
        safe_push_log(" | ".join(codec_info))

        if status_placeholder:
            status_placeholder.info(f"🏆 Profile {profile_idx}: {profile['label']}")

        # Build base command for this profile
        cmd_base = _build_profile_command(
            profile,
            base_output,
            tmp_subfolder_dir,
            embed_chapters,
            embed_subs,
            ytdlp_custom_args,
            subs_selected,
            do_cut,
            sb_choice,
        )

        # Store current profile for error diagnostics
        st.session_state["current_attempting_profile"] = profile["label"]

        # Try all YouTube clients with this profile
        success = _try_profile_with_clients(
            cmd_base,
            url,
            cookies_part,
            cookies_available,
            status_placeholder,
            progress_placeholder,
            info_placeholder,
        )

        if success:
            # Log successful download with detailed format info
            log_title("✅ Download successful!")
            safe_push_log(f"📦 Profile used: {profile['label']}")
            safe_push_log(f"🎯 Format ID: {profile.get('format', 'unknown')}")

            # Show codec details
            format_profile = profile.get("_format_profile", {})
            vcodec = format_profile.get("vcodec", "unknown")
            height = format_profile.get("height", 0)
            ext = format_profile.get("ext", "unknown")
            safe_push_log(f"🎬 Video codec: {vcodec}")
            safe_push_log(f"📐 Resolution: {height}p")
            safe_push_log(f"📦 Container: {ext}")

            log_title(
                f"📁 Container format: {profile.get('container', 'unknown').upper()}"
            )

            return 0, ""

        # Handle profile failure
        should_continue = _handle_profile_failure(
            profile,
            profile_idx,
            profiles_to_try,
            download_mode,
            refuse_quality_downgrade,
        )

        if not should_continue:
            break

    # All profiles failed - show simple error message
    profiles_count = len(profiles_to_try)
    if status_placeholder:
        status_placeholder.error("❌ All quality profiles failed")

    safe_push_log("")
    safe_push_log("❌ All profiles failed")
    safe_push_log("=" * 50)
    if not cookies_available:
        safe_push_log("🔑 No authentication configured")
        safe_push_log("💡 Try: Enable browser cookies or export cookie file")
    else:
        safe_push_log("🔑 Authentication issue")
        safe_push_log(
            "💡 Try: Refresh browser authentication or check video accessibility"
        )
    safe_push_log("=" * 50)

    return 1, f"All {profiles_count} profiles failed after full client fallback"


# === UTILITY FUNCTIONS ===


def is_valid_browser(browser_name: str) -> bool:
    """Check if browser name is supported"""
    if not browser_name:
        return False
    return browser_name.lower().strip() in SUPPORTED_BROWSERS


# === STREAMLIT UI CONFIGURATION ===

# Must be the first Streamlit command
st.set_page_config(
    page_title=t("page_title"),
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# === SIDEBAR ===
with st.sidebar.expander("⚙️ System"):
    if st.button("🔄 Check for updates", use_container_width=True):
        check_and_show_updates()


st.markdown(
    f"<h1 style='text-align: center;'>{t('page_header')}</h1>",
    unsafe_allow_html=True,
)


# === VERSION INFORMATION REMOVED ===
# Version info is now only shown in update notifications when needed


# === SESSION ===
if "run_seq" not in st.session_state:
    st.session_state.run_seq = 0  # incremented at each execution

# Initialize cancel and download state variables
if "download_finished" not in st.session_state:
    st.session_state.download_finished = (
        True  # True by default (no download in progress)
    )
if "download_cancelled" not in st.session_state:
    st.session_state.download_cancelled = False


# File system utilities moved to file_system_utils.py


# def smart_download_with_fallback(
#     base_cmd: List[str],
#     url: str,
#     progress_placeholder=None,
#     status_placeholder=None,
#     info_placeholder=None,
# ) -> Tuple[int, str]:
#     """
#     Intelligent download with progressive fallback strategies

#     Returns:
#         Tuple[int, str]: (return_code, error_message)
#     """
#     cookies_available = False
#     cookies_part = []

#     # Check if cookies are configured
#     cookies_method = st.session_state.get("cookies_method", "none")
#     if cookies_method != "none":
#         cookies_part = build_cookies_params()
#         cookies_available = len(cookies_part) > 0

#     # Strategy 1: Try without cookies first (fastest)
#     if status_placeholder:
#         status_placeholder.info(t("status_trying_no_auth"))
#     safe_push_log("🚀 Strategy 1: Trying without cookies (fastest)")

#     cmd = base_cmd + [url]
#     ret = run_cmd(cmd, progress_placeholder, status_placeholder, info_placeholder)

#     if ret == 0:
#         safe_push_log("✅ Success without authentication!")
#         return ret, ""

#     # Check if we got an authentication-related error
#     last_error = st.session_state.get("last_error", "").lower()
#     if not any(
#         error in last_error
#         for error in ["403", "forbidden", "signature", "unavailable"]
#     ):
#         return ret, "Non-authentication error"

#     safe_push_log("⚠️ Authentication error detected, trying fallback strategies...")

#     # Strategy 2: Try different YouTube clients
#     for i, client in enumerate(
#         YOUTUBE_CLIENT_FALLBACKS[1:], 2
#     ):  # Skip default (already tried)
#         client_name = client["name"]
#         if status_placeholder:
#             if client_name == "android":
#                 status_placeholder.info(t("status_retry_android"))
#             elif client_name == "ios":
#                 status_placeholder.info(t("status_retry_ios"))
#             elif client_name == "web":
#                 status_placeholder.info(t("status_retry_web"))
#             else:
#                 status_placeholder.info(f"🔄 Retry {i}: Using {client_name} client...")

#         safe_push_log(f"🔄 Strategy {i}: Trying with {client_name} client")

#         cmd = base_cmd + client["args"] + [url]
#         ret = run_cmd(cmd, progress_placeholder, status_placeholder, info_placeholder)

#         if ret == 0:
#             safe_push_log(f"✅ Success with {client_name} client!")
#             return ret, ""

#     # Strategy 3: Try with cookies if available
#     if cookies_available:
#         if status_placeholder:
#             status_placeholder.info(t("status_retry_cookies"))
#         safe_push_log("🍪 Strategy: Trying with authentication cookies")

#         # Try each client with cookies
#         for client in YOUTUBE_CLIENT_FALLBACKS:
#             client_name = client["name"]
#             safe_push_log(f"🔄 Trying {client_name} client + cookies")

#             cmd = base_cmd + client["args"] + cookies_part + [url]
#             ret = run_cmd(
#                 cmd, progress_placeholder, status_placeholder, info_placeholder
#             )

#             if ret == 0:
#                 safe_push_log(f"✅ Success with {client_name} client + cookies!")
#                 return ret, ""

#     # All strategies failed - show comprehensive error message
#     if status_placeholder:
#         status_placeholder.error("❌ Download failed after all retry attempts")

#     safe_push_log("❌ All fallback strategies failed")
#     safe_push_log("")
#     log_title("🚫 Download failed - Comprehensive troubleshooting:")

#     # Show specific error based on what was tried
#     if not cookies_available:
#         safe_push_log("🔑 PRIMARY ISSUE: No authentication configured")
#         safe_push_log("💡 IMMEDIATE SOLUTION:")
#         safe_push_log("   1. ⚠️  CONFIGURE COOKIES below")
#         safe_push_log("   2. 🌐 Use 'Browser Cookies' (easiest)")
#         safe_push_log("   3. 📁 Or export cookies from browser to file")
#         safe_push_log("")
#         safe_push_log(
#             "🎯 KEY INSIGHT: Even public videos need cookies for signature verification!"
#         )
#     else:
#         safe_push_log("🔑 AUTHENTICATION ISSUE: Cookies configured but not working")
#         safe_push_log("💡 SOLUTIONS TO TRY:")
#         safe_push_log("   1. 🔄 Update your cookies (they may be expired)")
#         safe_push_log("   2. 🌐 Sign out and back into YouTube in your browser")
#         safe_push_log("   3. 🔁 Try different browser or re-export cookies")
#         safe_push_log(f"   4. 📋 Current method: {cookies_method}")

#     safe_push_log("")
#     safe_push_log(
#         "📺 Technical context: YouTube uses encrypted signatures that require"
#     )
#     safe_push_log("    fresh authentication tokens to decrypt video URLs.")
#     safe_push_log("─" * 50)  # Static separator for end of troubleshooting section

#     return ret, "Authentication failed after all strategies"


# File system functions moved to file_system_utils.py
# customize_video_metadata function moved to medias_utils.py


# Subprocess and logging functions moved to logs_utils.py and process_utils.py
# log_title function moved to logs_utils.py


def extract_resolution_value(resolution_str: str) -> int:
    """Extract numeric value from resolution string for sorting"""
    if not resolution_str:
        return 0
    try:
        # Handle common resolution formats: "1920x1080", "1080p", "720p60", etc.
        if "x" in resolution_str:
            # Extract height from "1920x1080" format
            height = int(resolution_str.split("x")[1].split("p")[0])
            return height
        elif "p" in resolution_str:
            # Extract from "1080p", "720p60" format
            height = int(resolution_str.split("p")[0])
            return height
        else:
            # Unknown format, return 0 for lowest priority
            return 0
    except (ValueError, IndexError):
        return 0


@st.cache_data(ttl=3600, show_spinner=False)
def url_analysis(url: str) -> Optional[Dict]:
    """
    Analyze URL and fetch comprehensive video/playlist information using yt-dlp.
    Cached for 1 hour to avoid repeated API calls.
    Saves JSON to tmp/url_info.json for use with yt-dlp's --load-info-json.

    Args:
        url: Video or playlist URL to analyze

    Returns:
        Dict with video/playlist information or None if error
    """
    if not url or not url.strip():
        return None

    try:
        # Prepare output path for JSON file
        json_output_path = TMP_DOWNLOAD_FOLDER / "url_info.json"

        # Run yt-dlp with JSON output, skip download, flat playlist mode
        cmd = [
            "yt-dlp",
            "-J",  # JSON output
            "--skip-download",  # Don't download
            "--flat-playlist",  # For playlists, get basic info without extracting all videos
            "--playlist-end",
            "1",  # Only first video for quick playlist detection
            sanitize_url(url),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return {"error": f"yt-dlp failed: {result.stderr[:200]}"}

        # Parse JSON output
        try:
            info = json.loads(result.stdout)

            # Save JSON to file for later use with yt-dlp --load-info-json
            try:
                with open(json_output_path, "w", encoding="utf-8") as f:
                    json.dump(info, f, indent=2, ensure_ascii=False)
                safe_push_log(f"💾 URL info saved to {json_output_path}")
            except Exception as e:
                # Non-critical error - continue even if file write fails
                safe_push_log(f"⚠️ Could not save URL info to file: {e}")

            # Store in session state for global access
            st.session_state["url_info"] = info
            st.session_state["url_info_path"] = str(json_output_path)

            return info
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON: {str(e)}"}

    except subprocess.TimeoutExpired:
        return {"error": "Request timed out after 30 seconds"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def display_url_info(url_info: Dict) -> None:
    """
    Display URL analysis information in a user-friendly, visually appealing format.

    Args:
        url_info: Dict from url_analysis() containing video/playlist info
    """
    if not url_info:
        return

    # Check for errors first
    if "error" in url_info:
        st.error(f"❌ &nbsp; {t('error_analyzing_url')}: {url_info['error']}")
        return

    # Get extractor info for platform-specific display
    extractor = url_info.get("extractor", "").lower()
    extractor_key = url_info.get("extractor_key", "").lower()
    media_id = url_info.get("id")

    # Determine platform icon/emoji
    platform_emoji = "🎬"
    platform_name = "Video"
    if "youtube" in extractor or "youtube" in extractor_key:
        platform_emoji = "▶️"  # YouTube play button
        platform_name = "YouTube"
    elif "vimeo" in extractor:
        platform_emoji = "🎬"
        platform_name = "Vimeo"
    elif "dailymotion" in extractor:
        platform_emoji = "🎥"
        platform_name = "Dailymotion"

    # Determine if it's a playlist or single video
    is_playlist = url_info.get("_type") == "playlist" or "entries" in url_info

    if is_playlist:
        # ===== PLAYLIST INFORMATION =====
        title = url_info.get("title", "Unknown Playlist")
        entries_count = len(url_info.get("entries", []))

        # For flat-playlist mode, use playlist_count if available
        if "playlist_count" in url_info:
            entries_count = url_info["playlist_count"]

        # Display with platform branding
        st.success(f"📋 &nbsp; **{platform_name} {t('playlist_type')} _{media_id}_**")

        # Title in a nice container
        # st.markdown(f"&nbsp; &nbsp; 🎬 &nbsp; &nbsp; **{title}**")

        # title = info.get("title", "Titre inconnu")
        st.markdown(
            f"""
            <h2 style="font-weight:600; font-size:1.6em; margin-top:0;">
                &nbsp; &nbsp; 🎬 &nbsp; {title}
            </h2>
            """,
            unsafe_allow_html=True,
        )

        # Video count with icon
        st.markdown(
            f"&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; **{t('playlist_type')}:** {entries_count} videos"
        )

        # Show first video info if available
        if url_info.get("entries") and len(url_info["entries"]) > 0:
            first_video = url_info["entries"][0]
            if isinstance(first_video, dict) and "title" in first_video:
                st.caption(
                    f"&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; 📹 {t('url_first_video')}: _{first_video['title']}_"
                )

    elif url_info.get("_type") == "video" or "duration" in url_info:
        # ===== SINGLE VIDEO INFORMATION =====
        title = url_info.get("title", "Unknown Video")
        duration = url_info.get("duration", 0)
        view_count = url_info.get("view_count")
        like_count = url_info.get("like_count")
        uploader = url_info.get("uploader", url_info.get("channel", ""))

        # Display with platform branding
        st.success(
            f"{platform_emoji} &nbsp; **{platform_name} {t('video_type')} _{media_id}_**"
        )

        # Title in a nice container
        # st.markdown(f"#### {title}")
        # st.markdown(f"**{title}**")

        # title = info.get("title", "Titre inconnu")
        st.markdown(
            f"""
            <h2 style="font-weight:600; font-size:1.6em; margin-top:0;">
                &nbsp; &nbsp; 🎬 &nbsp; {title}
            </h2>
            """,
            unsafe_allow_html=True,
        )

        # Author/Channel
        if uploader:
            st.markdown(
                f"&nbsp; &nbsp; &nbsp; &nbsp; **{t('url_author')}:** {uploader}"
            )

        # Stats on one line (duration, views, likes)
        stats_parts = []

        # Duration
        if duration and duration > 0:
            duration_str = fmt_hhmmss(int(duration))
            stats_parts.append(f"⏱️ &nbsp; {duration_str}")

        # Views
        if view_count is not None and view_count > 0:
            views_formatted = f"{view_count:,}".replace(",", " ")
            stats_parts.append(f"👁️ &nbsp; {views_formatted} {t('url_views')}")

        # Likes
        if like_count is not None and like_count > 0:
            likes_formatted = f"{like_count:,}".replace(",", " ")
            stats_parts.append(f"👍 &nbsp; {likes_formatted} {t('url_likes')}")

        # Display all stats on one line
        if stats_parts:
            st.markdown(
                "&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;"
                + "&nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp;".join(
                    stats_parts
                )
            )

    else:
        # Unknown format - not a video or playlist
        st.error(f"❌ {t('error_invalid_url_type')}")
        st.caption(t("url_invalid_content"))


def get_url_info() -> Optional[Dict]:
    """
    Get the stored URL info from session state.

    Returns:
        Dict with URL information or None if not available
    """
    return st.session_state.get("url_info", None)


def get_url_info_path() -> Optional[Path]:
    """
    Get the path to the saved URL info JSON file.

    Returns:
        Path to url_info.json or None if not available
    """
    path_str = st.session_state.get("url_info_path", None)
    if path_str and Path(path_str).exists():
        return Path(path_str)
    return None


def analyze_video_on_url_change(url: str) -> None:
    """
    SIMPLIFIED: Only store URL for later analysis.
    No automatic analysis - wait for user to click Download or Detect Quality.

    Args:
        url: Video URL to store
    """
    clean_url = sanitize_url(url) if url else ""

    # Just store the URL - don't analyze automatically
    if clean_url:
        st.session_state["current_video_url"] = clean_url
        # Clear any previous results for this URL
        if st.session_state.get("codecs_detected_for_url", "") != clean_url:
            st.session_state.pop("available_codecs", None)
            st.session_state.pop("available_formats", None)
            st.session_state.pop("codecs_detected_for_url", None)


def detect_video_quality_now(url: str) -> None:
    """
    Simple function to detect video quality when user clicks button or starts download.
    Shows all logs in real-time directly in the UI.

    Args:
        url: Video URL to analyze
    """
    if not url:
        safe_push_log("❌ No URL provided for quality detection")
        return

    clean_url = sanitize_url(url)

    # Check if we already have results for this URL
    cached_url = st.session_state.get("codecs_detected_for_url", "")
    if cached_url == clean_url and st.session_state.get("available_codecs"):
        safe_push_log("💾 Using cached quality analysis results")
        return

    safe_push_log("")
    safe_push_log(f"🚀 Starting quality detection for: {clean_url[:50]}...")

    # Prepare authentication
    cookies_method = st.session_state.get("cookies_method", "none")
    cookies_part = []

    if cookies_method != "none":
        try:
            cookies_part = build_cookies_params()
            if cookies_part:
                safe_push_log(f"🍪 Using cookies from {cookies_method}")
            else:
                safe_push_log(
                    f"⚠️ Cookies method '{cookies_method}' configured but no valid cookies found"
                )
                cookies_method = "none"
        except Exception as e:
            safe_push_log(f"❌ Cookie setup failed: {str(e)[:50]}...")
            cookies_method = "none"
            cookies_part = []

    # Perform analysis with spinner for user feedback
    try:
        available_codecs, available_formats = analyze_video_formats_unified(
            clean_url, cookies_part
        )

        # Store results in session state
        st.session_state["available_codecs"] = available_codecs
        st.session_state["available_formats"] = available_formats
        st.session_state["codecs_detected_for_url"] = clean_url
        st.session_state["formats_detection_timestamp"] = time.time()

        # Calculate optimal profiles based on detected formats
        try:
            profile_summary = get_profile_availability_summary(available_formats)

            # Extract available profile names from summary
            available_profile_names = [
                name for name, info in profile_summary.items() if info["available"]
            ]

            # Store optimal profiles in session state for UI display
            st.session_state["available_profiles"] = available_profile_names
            st.session_state["profile_summary"] = profile_summary

            safe_push_log(
                f"🎯 Profile analysis: {len(available_profile_names)} profiles available from {len(QUALITY_PROFILES)} total"
            )

        except Exception as e:
            safe_push_log(f"⚠️ Profile analysis failed: {str(e)[:50]}... Using fallback")
            # Set empty profiles to trigger fallback behavior
            st.session_state["available_profiles"] = []
            st.session_state["profile_summary"] = {}

        # Success message
        codec_count = sum(available_codecs.values())
        format_count = len(available_formats)

        has_premium = available_codecs.get("av01") and available_codecs.get("opus")
        has_modern = available_codecs.get("vp9") and available_codecs.get("opus")

        if has_premium:
            safe_push_log(
                "🎉 ✅ Quality detection complete: Premium quality formats available!"
            )
        elif has_modern:
            safe_push_log(
                "✅ Quality detection complete: Modern quality formats available"
            )
        else:
            safe_push_log(
                "✅ Quality detection complete: Standard quality formats available"
            )

        safe_push_log(f"📊 Final results: {codec_count} codecs, {format_count} formats")
        safe_push_log("")

    except Exception as e:
        safe_push_log(f"❌ Quality detection failed: {str(e)[:100]}...")
        # Set optimistic defaults
        st.session_state["available_codecs"] = {
            "av01": True,
            "vp9": True,
            "h264": True,
            "opus": True,
            "aac": True,
        }
        st.session_state["available_formats"] = []
        st.session_state["codecs_detected_for_url"] = clean_url


def get_cached_video_analysis(url: str) -> Tuple[Dict[str, bool], List[Dict]]:
    """
    Get cached video analysis results from session state.

    Args:
        url: Video URL to get analysis for

    Returns:
        Tuple[Dict[str, bool], List[Dict]]: (available_codecs, available_formats)
        Returns optimistic defaults if no cache or URL mismatch
    """
    if not url:
        # Return defaults for empty URL
        default_codecs = {
            "av01": True,
            "vp9": True,
            "h264": True,
            "opus": True,
            "aac": True,
        }
        return default_codecs, []

    url = url.strip()
    cached_url = st.session_state.get("codecs_detected_for_url", "")

    if (
        cached_url == url
        and "available_codecs" in st.session_state
        and "available_formats" in st.session_state
    ):
        # Return cached results
        return (
            st.session_state["available_codecs"],
            st.session_state["available_formats"],
        )

    # No cache or URL mismatch - return optimistic defaults
    default_codecs = {
        "av01": True,
        "vp9": True,
        "h264": True,
        "opus": True,
        "aac": True,
    }
    return default_codecs, []

    # DEPRECATED - No longer using async format analysis with threading
    # Now using simple synchronous detect_video_quality_now() function
    # Threading code and cookie preparation removed - handled in synchronous functions


# _background_format_analysis function removed - threading approach abandoned
# Using simple synchronous approach with detect_video_quality_now() instead


# get_analysis_status_display() function removed - no longer needed with synchronous approach


# DEPRECATED - No longer using thread-based logging
# def analysis_log(message: str):
#     """DEPRECATED: Was for thread-safe logging, now using direct safe_push_log"""
#     pass


# transfer_analysis_logs_to_main function removed - no longer needed with synchronous approach


# --- 2) Retrieve raw SponsorBlock data ---
def fetch_sponsorblock_segments(
    url_or_id: str,
    categories=("sponsor", "selfpromo", "interaction", "intro", "outro", "preview"),
    api=SPONSORBLOCK_API,
    timeout=15,
):
    """
    Fetch SponsorBlock segments for a video.

    Args:
        url_or_id: Video URL or YouTube video ID
        categories: Categories to fetch
        api: SponsorBlock API endpoint
        timeout: Request timeout

    Returns:
        List of segments or empty list if unavailable/error
    """
    try:
        # Extract video ID - this will return empty string for non-YouTube URLs
        vid = url_or_id if len(url_or_id) == 11 else video_id_from_url(url_or_id)

        # If no valid YouTube video ID found, return empty list (not an error)
        if not vid or len(vid) != 11:
            return []

        # Validate that the video ID contains only valid characters
        if not vid.replace("-", "").replace("_", "").isalnum():
            return []

        r = requests.get(
            f"{api}/api/skipSegments",
            params={"videoID": vid, "categories": json.dumps(list(categories))},
            timeout=timeout,
        )

        # Handle different status codes appropriately
        if r.status_code == 404:
            # No sponsor segments found for this video (normal case)
            return []
        elif r.status_code == 400:
            # Bad request - likely invalid video ID format
            return []
        elif r.status_code == 403:
            # Forbidden - video might be private or restricted
            return []
        elif r.status_code >= 500:
            # Server error - SponsorBlock API issue
            return []

        r.raise_for_status()

        # Parse response
        raw = r.json()
        if not isinstance(raw, list):
            return []

        segments = []
        for x in raw:
            try:
                if isinstance(x, dict) and "segment" in x and "category" in x:
                    segment_data = x["segment"]
                    if isinstance(segment_data, list) and len(segment_data) >= 2:
                        segments.append(
                            {
                                "start": float(segment_data[0]),
                                "end": float(segment_data[1]),
                                "category": x["category"],
                            }
                        )
            except (ValueError, TypeError, KeyError):
                # Skip malformed segment data
                continue

        return segments

    except requests.exceptions.Timeout:
        # Timeout - SponsorBlock API is slow
        return []
    except requests.exceptions.ConnectionError:
        # Network issues
        return []
    except requests.exceptions.RequestException:
        # Other request errors
        return []
    except Exception:
        # Any other unexpected error
        return []


# SponsorBlock segment manipulation functions moved to cut_utils.py


def get_sponsorblock_segments(
    url: str, cookies_part: List[str], categories: List[str] = None
) -> List[Dict]:
    """
    Retrieves SponsorBlock segments from a video via direct API.
    Returns a list of segments with 'start' and 'end' in seconds.

    Args:
        url: Video URL
        cookies_part: Cookie parameters (not used for direct API)
        categories: List of categories to retrieve (default: all)
    """
    try:
        push_log(t("log_fetching_sponsorblock"))

        # Check if this is a YouTube URL
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        is_youtube = parsed_url.netloc.endswith(
            "youtube.com"
        ) or parsed_url.netloc.endswith("youtu.be")

        # Use specified categories or default ones
        if categories is None:
            categories = [
                "sponsor",
                "selfpromo",
                "interaction",
                "intro",
                "outro",
                "preview",
            ]

        # Try to fetch segments regardless of platform
        segments = fetch_sponsorblock_segments(url, categories=categories)

        if segments:
            # Display summary of found segments by category
            category_counts = {}
            total_duration = 0
            for seg in segments:
                cat = seg["category"]
                duration = seg["end"] - seg["start"]
                category_counts[cat] = category_counts.get(cat, 0) + 1
                total_duration += duration

            push_log(t("log_found_segments", count=len(segments)))

            # Display concise summary
            summary_parts = []
            for category, count in sorted(category_counts.items()):
                summary_parts.append(f"{category}: {count}")

            push_log(f"📋 Categories found: {', '.join(summary_parts)}")
            push_log(f"⏱️ Total sponsor content: {fmt_hhmmss(int(total_duration))}")

            # Display detailed info for each segment
            for seg in segments:
                start_str = fmt_hhmmss(int(seg["start"]))
                end_str = fmt_hhmmss(int(seg["end"]))
                duration = int(seg["end"] - seg["start"])
                push_log(
                    t(
                        "log_segment_info",
                        type=seg["category"],
                        start=start_str,
                        end=end_str,
                        duration=duration,
                    )
                )
        else:
            # No segments found - provide context-appropriate message
            if is_youtube:
                video_id = video_id_from_url(url)
                if video_id:
                    push_log(t("log_sponsorblock_no_data"))
                    push_log(
                        "💡 This YouTube video has no community-submitted sponsor segments"
                    )
                else:
                    push_log("⚠️ Could not extract valid YouTube video ID from URL")
            else:
                push_log("ℹ️ SponsorBlock data not available for this platform")
                push_log(f"🔗 Platform: {parsed_url.netloc}")
                push_log("💡 SponsorBlock is a YouTube-specific community database")

        return segments

    except Exception as e:
        push_log(t("log_sponsorblock_error", error=e))
        return []


def calculate_sponsor_overlap(
    start_sec: int, end_sec: int, sponsor_segments: List[Dict]
) -> Tuple[int, int]:
    """
    Calculates total sponsor time in the requested section and adjusts the end.

    Args:
        start_sec: Desired section start (seconds)
        end_sec: Desired section end (seconds)
        sponsor_segments: List of sponsor segments

    Returns:
        tuple: (sponsor_time_removed, new_end_adjusted_for_shortened_video)
    """
    if not sponsor_segments:
        return 0, end_sec

    total_sponsor_time = 0
    overlapping_segments = []
    # Find all sponsor segments that overlap with our section
    for segment in sponsor_segments:
        seg_start = segment["start"]
        seg_end = segment["end"]

        # Calculate the overlap
        overlap_start = max(start_sec, seg_start)
        overlap_end = min(end_sec, seg_end)

        if overlap_start < overlap_end:
            overlap_duration = overlap_end - overlap_start
            total_sponsor_time += overlap_duration
            overlapping_segments.append(
                {
                    **segment,
                    "overlap_start": overlap_start,
                    "overlap_end": overlap_end,
                    "overlap_duration": overlap_duration,
                }
            )

    # CORRECTED LOGIC:
    # After sponsor removal by yt-dlp, the video is shortened
    # We want to cut in this shortened video from start_sec to (end_sec -
    # sponsor_time_removed)
    adjusted_end = end_sec - total_sponsor_time

    if overlapping_segments:
        push_log(
            t(
                "log_sponsorblock_analysis",
                start=fmt_hhmmss(start_sec),
                end=fmt_hhmmss(end_sec),
            )
        )
        for seg in overlapping_segments:
            push_log(
                t(
                    "log_sponsorblock_segment_removed",
                    type=seg.get("category", seg.get("type", "unknown")),
                    start=fmt_hhmmss(int(seg["overlap_start"])),
                    end=fmt_hhmmss(int(seg["overlap_end"])),
                    duration=int(seg["overlap_duration"]),
                )
            )
        push_log(t("log_total_sponsor_time", time=int(total_sponsor_time)))
        push_log(
            t(
                "log_cut_until",
                adjusted_end=fmt_hhmmss(int(adjusted_end)),
                original_end=fmt_hhmmss(end_sec),
            )
        )
        push_log(t("log_final_duration", duration=int(adjusted_end - start_sec)))

    return int(total_sponsor_time), int(adjusted_end)


def get_sponsorblock_config(sb_choice: str) -> Tuple[List[str], List[str]]:
    """
    Returns the SponsorBlock configuration based on user choice or dynamic detection.
    Wrapper around core function with UI-specific dynamic sponsor detection.

    Args:
        sb_choice: User choice for SponsorBlock

    Returns:
        tuple: (remove_categories, mark_categories) - lists of categories to
            remove/mark
    """
    # Check if we have dynamic sponsor detection results (UI-specific feature)
    if (
        "detected_sponsors" in st.session_state
        and st.session_state.detected_sponsors
        and (
            "sponsors_to_remove" in st.session_state
            or "sponsors_to_mark" in st.session_state
        )
    ):
        remove_cats = st.session_state.get("sponsors_to_remove", [])
        mark_cats = st.session_state.get("sponsors_to_mark", [])
        return remove_cats, mark_cats

    # Fallback to core preset configurations
    return core_get_sponsorblock_config(sb_choice)


def build_sponsorblock_params(sb_choice: str) -> List[str]:
    """
    Builds yt-dlp parameters for SponsorBlock based on user choice.

    Args:
        sb_choice: User choice for SponsorBlock

    Returns:
        list: yt-dlp parameters for SponsorBlock
    """
    # Use the core version for the actual logic
    result = core_build_sponsorblock_params(sb_choice)

    # Add UI logs for user feedback
    if "--sponsorblock-remove" in result:
        idx = result.index("--sponsorblock-remove")
        if idx + 1 < len(result):
            safe_push_log(f"SponsorBlock Remove: {result[idx + 1]}")

    if "--sponsorblock-mark" in result:
        idx = result.index("--sponsorblock-mark")
        if idx + 1 < len(result):
            safe_push_log(f"SponsorBlock Mark: {result[idx + 1]}")

    return result


def build_cookies_params() -> List[str]:
    """
    Builds cookie parameters based on user selection.

    Returns:
        list: yt-dlp parameters for cookies
    """
    cookies_method = st.session_state.get("cookies_method", "none")

    if cookies_method == "file":
        result = core_build_cookies_params(
            cookies_method="file", cookies_file_path=YOUTUBE_COOKIES_FILE_PATH
        )
        if "--cookies" in result:
            safe_push_log(f"🍪 Using cookies from file: {YOUTUBE_COOKIES_FILE_PATH}")
        else:
            safe_push_log(
                f"⚠️ Cookies file not found, falling back to no cookies: "
                f"{YOUTUBE_COOKIES_FILE_PATH}"
            )
        return result

    elif cookies_method == "browser":
        browser = st.session_state.get("browser_select", "chrome")
        profile = st.session_state.get("browser_profile", "").strip()

        result = core_build_cookies_params(
            cookies_method="browser", browser_select=browser, browser_profile=profile
        )
        browser_config = f"{browser}:{profile}" if profile else browser
        safe_push_log(f"🍪 Using cookies from browser: {browser_config}")
        return result

    else:  # none
        result = core_build_cookies_params(cookies_method="none")
        safe_push_log("🍪 No cookies authentication")
        return result


class DownloadMetrics:
    """Class to manage download progress metrics and display"""

    def __init__(self):
        self.speed = ""
        self.eta = ""
        self.file_size = ""
        self.fragments_info = ""
        self.last_progress = 0
        self.start_time = time.time()

    def update_speed(self, speed: str):
        self.speed = speed

    def update_eta(self, eta: str):
        self.eta = eta

    def update_size(self, size: str):
        self.file_size = size

    def update_fragments(self, fragments: str):
        self.fragments_info = fragments

    def mark_step_complete(self, step_name: str, size: str = ""):
        """Mark a processing step as complete and clear ETA"""
        self.speed = step_name
        self.eta = ""  # Clear ETA for completed steps
        if size:
            self.file_size = size

    def display(self, info_placeholder):
        """Display current metrics in the UI with intelligent fragment display"""
        # Show fragments only during active downloads (when we have meaningful fragment info)
        show_frags = bool(self.fragments_info and "/" in str(self.fragments_info))

        # Don't show ETA for completed processes
        display_eta = self.eta
        if any(
            complete in self.speed.lower()
            for complete in ["complete", "downloaded", "cut", "metadata"]
            if self.speed
        ):
            display_eta = ""

        # Calculate elapsed time
        elapsed_seconds = int(time.time() - self.start_time)
        elapsed_str = fmt_hhmmss(elapsed_seconds) if elapsed_seconds > 0 else ""

        update_download_metrics(
            info_placeholder,
            speed=self.speed,
            eta=display_eta,
            size=self.file_size,
            fragments=self.fragments_info,
            show_fragments=show_frags,
            elapsed=elapsed_str,
        )

    def reset(self):
        """Reset all metrics"""
        self.speed = ""
        self.eta = ""
        self.file_size = ""
        self.fragments_info = ""
        self.last_progress = 0
        self.start_time = time.time()


# Progress parsing patterns and utility functions
DOWNLOAD_PROGRESS_PATTERN = re.compile(
    r"\[download\]\s+(\d{1,3}\.\d+)%\s+of\s+([\d.]+\w+)\s+at\s+"
    r"([\d.]+\w+/s)\s+ETA\s+(\d{2}:\d{2})"
)
FRAGMENT_PROGRESS_PATTERN = re.compile(
    r"\[download\]\s+Got fragment\s+(\d+)\s+of\s+(\d+)"
)
GENERIC_PERCENTAGE_PATTERN = re.compile(r"(\d{1,3}(?:\.\d+)?)%")


def parse_download_progress(line: str) -> Optional[Tuple[float, str, str, str]]:
    """Parse download progress line and return (percentage, size, speed, eta)"""
    match = DOWNLOAD_PROGRESS_PATTERN.search(line)
    if match:
        return float(match.group(1)), match.group(2), match.group(3), match.group(4)
    return None


def parse_fragment_progress(line: str) -> Optional[Tuple[int, int]]:
    """Parse fragment progress and return (current, total)"""
    match = FRAGMENT_PROGRESS_PATTERN.search(line)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def parse_generic_percentage(line: str) -> Optional[float]:
    """Parse generic percentage from line"""
    if "download" in line:
        return None
    match = GENERIC_PERCENTAGE_PATTERN.search(line)
    if match:
        return min(100.0, max(0.0, float(match.group(1))))
    return None


# URL input for main form
# url = st.text_input(
#     t("video_url"),
#     value="",
#     help="Enter the YouTube video URL",
#     key="main_url",
# )

st.markdown("\n")

# === MAIN INPUTS (OUTSIDE FORM FOR DYNAMIC BEHAVIOR) ===
url = st.text_input(
    t("video_url"),
    value="",
    placeholder="https://www.youtube.com/watch?v=...",
    key="main_url",
)

# Store URL for manual analysis if needed
if url and url.strip():
    analyze_video_on_url_change(url)

    # Analyze URL and display information with spinner
    with st.spinner(t("url_analysis_spinner")):
        url_info = url_analysis(url.strip())
        if url_info:
            display_url_info(url_info)

filename = st.text_input(t("video_name"), help=t("video_name_help"))

# === FOLDER SELECTION ===
# Handle cancel action - reset to root folder
if "folder_selection_reset" in st.session_state:
    del st.session_state.folder_selection_reset
    # Force reset by incrementing the selectbox key
    if "folder_selectbox_key" not in st.session_state:
        st.session_state.folder_selectbox_key = 0
    st.session_state.folder_selectbox_key += 1

# Initialize selectbox key if not exists
if "folder_selectbox_key" not in st.session_state:
    st.session_state.folder_selectbox_key = 0

# Reload folder list if a new folder was just created to include it in the options
existing_subdirs = list_subdirs_recursive(
    VIDEOS_FOLDER, max_depth=2
)  # Allow 2 levels deep
folder_options = ["/"] + existing_subdirs + [t("create_new_folder")]

video_subfolder = st.selectbox(
    t("destination_folder"),
    options=folder_options,
    index=0,  # Always default to root folder when reset
    format_func=lambda x: (
        "📁 Root folder (/)"
        if x == "/"
        else t("create_new_folder") if x == t("create_new_folder") else f"📁 {x}"
    ),
    # Dynamic key for reset
    key=f"folder_selectbox_{st.session_state.folder_selectbox_key}",
)

# Handle new folder creation
if video_subfolder == t("create_new_folder"):
    st.markdown(f"**{t('create_new_folder_title')}**")

    # Parent folder selection
    parent_folder_options = ["/"] + existing_subdirs
    parent_folder = st.selectbox(
        t("create_inside_folder"),
        options=parent_folder_options,
        index=0,
        format_func=lambda x: t("root_folder") if x == "/" else f"📁 {x}",
        help=t("create_inside_folder_help"),
        key="parent_folder_select",
    )

    # Show current path preview
    if parent_folder == "/":
        st.caption(t("path_preview"))
    else:
        st.caption(t("path_preview_with_parent", parent=parent_folder))

    new_folder_name = st.text_input(
        t("folder_name_label"),
        placeholder=t("folder_name_placeholder"),
        help=t("folder_name_help"),
        key="new_folder_input",
    )

    # Real-time validation preview
    if new_folder_name and new_folder_name.strip():
        sanitized_name = sanitize_filename(new_folder_name)

        if sanitized_name:
            # Determine the full path based on parent selection
            if parent_folder == "/":
                potential_path = VIDEOS_FOLDER / sanitized_name
                full_path_display = sanitized_name
            else:
                potential_path = VIDEOS_FOLDER / parent_folder / sanitized_name
                full_path_display = f"{parent_folder}/{sanitized_name}"

            if sanitized_name != new_folder_name.strip():
                st.info(t("folder_will_be_created_as", path=full_path_display))
            else:
                # Check if folder already exists
                if potential_path.exists():
                    st.warning(t("folder_already_exists", path=full_path_display))
                else:
                    st.success(t("ready_to_create_folder", path=full_path_display))

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button(t("create_folder_btn"), key="create_folder_btn", type="primary"):
            if new_folder_name and new_folder_name.strip():
                # Sanitize folder name
                sanitized_name = sanitize_filename(new_folder_name)

                if sanitized_name:
                    # Determine the full path based on parent selection
                    if parent_folder == "/":
                        new_folder_path = VIDEOS_FOLDER / sanitized_name
                        relative_path = sanitized_name
                    else:
                        new_folder_path = VIDEOS_FOLDER / parent_folder / sanitized_name
                        relative_path = f"{parent_folder}/{sanitized_name}"

                    try:
                        if new_folder_path.exists():
                            st.warning(t("folder_exists_using", path=relative_path))
                            st.session_state.new_folder_created = relative_path
                        else:
                            ensure_dir(new_folder_path)
                            st.success(
                                t("folder_created_successfully", path=relative_path)
                            )
                            st.session_state.new_folder_created = relative_path
                        st.rerun()
                    except Exception as e:
                        st.error(t("error_creating_folder", error=e))
                else:
                    st.warning(t("enter_valid_folder_name"))
            else:
                st.warning(t("enter_folder_name"))

    with col2:
        if st.button(t("cancel_folder_btn"), key="cancel_folder_btn"):
            # Reset to root folder
            st.session_state.folder_selection_reset = True
            st.rerun()

# If a new folder was just created, select it automatically
if "new_folder_created" in st.session_state:
    video_subfolder = st.session_state.new_folder_created
    del st.session_state.new_folder_created
    st.rerun()

# subtitles multiselect from env
subs_selected = st.multiselect(
    t("subtitles_to_embed"),
    options=SUBTITLES_CHOICES,
    default=[],
    help=t("subtitles_help"),
)

# st.markdown(f"### {t('options')}")
st.markdown("\n")

# === DYNAMIC SECTIONS (OUTSIDE FORM) ===

# Optional cutting section with dynamic behavior
with st.expander(f"{t('ads_sponsors_title')}", expanded=False):
    # st.markdown(f"### {t('optional_cutting')}")

    st.info(t("ads_sponsors_presentation"))

    # Initialize session state for detected sponsors
    if "detected_sponsors" not in st.session_state:
        st.session_state.detected_sponsors = []
    if "sponsors_to_remove" not in st.session_state:
        st.session_state.sponsors_to_remove = []
    if "sponsors_to_mark" not in st.session_state:
        st.session_state.sponsors_to_mark = []

    # SponsorBlock presets first
    preset_help = "These are preset configurations."
    if st.session_state.detected_sponsors:
        preset_help += (
            " ⚡ Dynamic configuration is active and will override these presets."
        )
    else:
        preset_help += " Use 'Detect Sponsors' below for dynamic configuration."

    sb_choice = st.selectbox(
        f"### {t('ads_sponsors_label')} (Presets)",
        options=[
            t("sb_option_1"),  # Default
            t("sb_option_2"),  # Moderate
            t("sb_option_3"),  # Aggressive
            t("sb_option_4"),  # Conservative
            t("sb_option_5"),  # Minimal
            t("sb_option_6"),  # Disabled
        ],
        index=0,
        key="sb_choice",
        help=preset_help,
    )

    # Dynamic sponsor detection section
    st.markdown("---")
    col1, col2 = st.columns([2, 1])

    with col1:
        detect_btn = st.button(
            t("detect_sponsors_button"),
            help=t("detect_sponsors_help"),
            key="detect_sponsors_btn",
        )

    # Reset button if dynamic detection is active
    if st.session_state.detected_sponsors:
        with col2:
            if st.button("🔄 Reset Dynamic Detection", key="reset_detection"):
                st.session_state.detected_sponsors = []
                st.session_state.sponsors_to_remove = []
                st.session_state.sponsors_to_mark = []
                st.rerun()

    # Handle sponsor detection
    if detect_btn and url.strip():
        with st.spinner("🔍 Analyzing video for sponsor segments..."):
            try:
                # Get cookies for yt-dlp - use centralized function
                cookies_part = build_cookies_params()

                # Detect all sponsor segments
                clean_url = sanitize_url(url)
                segments = fetch_sponsorblock_segments(clean_url)

                if segments:
                    st.session_state.detected_sponsors = segments
                    st.success(f"✅ {len(segments)} sponsor segments detected!")
                else:
                    st.session_state.detected_sponsors = []
                    st.info("ℹ️ No sponsor segments found in this video")

            except Exception as e:
                st.error(f"❌ Error detecting sponsors: {e}")
                st.session_state.detected_sponsors = []

    # Display detected sponsors if any
    if st.session_state.detected_sponsors:
        st.markdown("---")
        st.markdown(f"### {t('sponsors_detected_title')}")

        # Summary
        total_duration = sum(
            seg["end"] - seg["start"] for seg in st.session_state.detected_sponsors
        )
        category_counts = {}
        for seg in st.session_state.detected_sponsors:
            cat = seg["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        summary_parts = [
            f"{cat}: {count}" for cat, count in sorted(category_counts.items())
        ]
        duration_str = fmt_hhmmss(int(total_duration))

        st.info(
            t(
                "sponsors_detected_summary",
                count=len(st.session_state.detected_sponsors),
                duration=duration_str,
            )
        )
        st.text(f"Categories: {', '.join(summary_parts)}")

        # Configuration section
        st.markdown(f"### {t('sponsors_config_title')}")

        # Group segments by category to avoid duplicates
        categories_with_segments = {}
        for seg in st.session_state.detected_sponsors:
            cat = seg["category"]
            if cat not in categories_with_segments:
                categories_with_segments[cat] = []
            categories_with_segments[cat].append(seg)

        col_remove, col_mark = st.columns(2)

        with col_remove:
            st.markdown(f"**{t('sponsors_remove_label')}**")
            remove_options = []
            for cat, segments in categories_with_segments.items():
                total_duration = sum(seg["end"] - seg["start"] for seg in segments)
                count = len(segments)
                duration_str = fmt_hhmmss(int(total_duration))
                label = f"{cat} ({count} segments, {duration_str})"
                if st.checkbox(
                    label,
                    key=f"remove_{cat}",
                    value=(cat in ["sponsor", "selfpromo", "interaction"]),
                ):
                    remove_options.append(cat)

            st.session_state.sponsors_to_remove = remove_options

        with col_mark:
            st.markdown(f"**{t('sponsors_mark_label')}**")
            mark_options = []
            for cat, segments in categories_with_segments.items():
                # Don't mark if it's being removed
                if cat not in st.session_state.sponsors_to_remove:
                    total_duration = sum(seg["end"] - seg["start"] for seg in segments)
                    count = len(segments)
                    duration_str = fmt_hhmmss(int(total_duration))
                    label = f"{cat} ({count} segments, {duration_str})"
                    if st.checkbox(
                        label,
                        key=f"mark_{cat}",
                        value=(cat in ["intro", "preview", "outro"]),
                    ):
                        mark_options.append(cat)
                else:
                    # Show disabled checkbox for removed categories
                    total_duration = sum(seg["end"] - seg["start"] for seg in segments)
                    count = len(segments)
                    duration_str = fmt_hhmmss(int(total_duration))
                    st.text(
                        f"🚫 {cat} ({count} segments, {duration_str}) - Will be removed"
                    )

            st.session_state.sponsors_to_mark = mark_options

# Optional cutting section with dynamic behavior
with st.expander(f"{t('cutting_title')}", expanded=False):
    # st.markdown(f"### {t('optional_cutting')}")

    st.info(t("cutting_modes_presentation"))

    # Cutting mode selection
    # st.markdown(f"**{t('cutting_mode_title')}**")
    default_cutting_mode = settings.CUTTING_MODE
    cutting_mode_options = ["keyframes", "precise"]
    default_index = (
        cutting_mode_options.index(default_cutting_mode)
        if default_cutting_mode in cutting_mode_options
        else 0
    )

    cutting_mode = st.radio(
        t("cutting_mode_prompt"),
        options=cutting_mode_options,
        format_func=lambda x: {
            "keyframes": t("cutting_mode_keyframes"),
            "precise": t("cutting_mode_precise"),
        }[x],
        index=default_index,
        help=t("cutting_mode_help"),
        key="cutting_mode",
    )

    if cutting_mode == "keyframes":
        st.info(t("cutting_mode_keyframes_info"))
    else:
        st.warning(t("cutting_mode_precise_info"))

        # Re-encoding options for precise mode (DYNAMIC!)
        st.markdown(f"**{t('advanced_encoding_options')}**")

        # Codec selection
        codec_choice = st.radio(
            t("codec_video"),
            options=["h264", "h265"],
            format_func=lambda x: {
                "h264": t("codec_h264"),
                "h265": t("codec_h265"),
            }[x],
            index=0,
            help=t("codec_help"),
            key="codec_choice",
        )

        # Quality preset
        quality_preset = st.radio(
            t("encoding_quality"),
            options=["balanced", "high_quality"],
            format_func=lambda x: {
                "balanced": t("quality_balanced"),
                "high_quality": t("quality_high"),
            }[x],
            index=0,
            help=t("quality_help"),
            key="quality_preset",
        )

        # Show current settings DYNAMICALLY
        if codec_choice == "h264":
            crf_value = "16" if quality_preset == "balanced" else "14"
            preset_value = "slow" if quality_preset == "balanced" else "slower"
            st.info(t("h264_settings", preset=preset_value, crf=crf_value))
        else:
            crf_value = "16" if quality_preset == "balanced" else "14"
            preset_value = "slow" if quality_preset == "balanced" else "slower"
            st.info(t("h265_settings", preset=preset_value, crf=crf_value))

    c1, c2 = st.columns([1, 1])
    with c1:
        start_text = st.text_input(
            t("start_time"),
            value="",
            help=t("time_format_help"),
            placeholder="0:11",
            key="start_text",
        )
    with c2:
        end_text = st.text_input(
            t("end_time"),
            value="",
            help=t("time_format_help"),
            placeholder="6:55",
            key="end_text",
        )

    st.info(t("sponsorblock_sections_info"))

# Video quality selection with dynamic behavior
with st.expander(f"{t('quality_title')}", expanded=False):
    # Initialize session state for formats
    if "available_formats" not in st.session_state:
        st.session_state.available_formats = []
    if "selected_format" not in st.session_state:
        st.session_state.selected_format = "auto"

    # === 1. QUALITY PROFILES SECTION (FIRST) ===
    st.subheader("🏆 Quality Profiles")
    st.info(
        "🎯 **Intelligent quality strategies** - HomeTube automatically selects the best codecs and formats for optimal quality and compatibility."
    )

    # Download mode selection
    download_mode = st.radio(
        "Quality Strategy:",
        options=["auto", "forced"],
        format_func=lambda x: {
            "auto": "🔄 Auto (Best Quality) - Recommended",
            "forced": "🎯 Force Profile (No Fallback)",
        }[x],
        index=0,
        help="Auto mode tries profiles in order until success. Forced mode only tries your selected profile.",
        key="download_mode",
        horizontal=True,
    )

    if download_mode == "auto":
        st.info(
            "🤖 **Auto Mode**: HomeTube will try all quality profiles in order (best to most compatible) and stop at the first success."
        )

        # Show dynamic profile generation based on available formats
        if url:
            clean_url = sanitize_url(url)

            # Check if analysis is complete
            analysis_complete = (
                st.session_state.get("codecs_detected_for_url", "") == clean_url
                and "available_codecs" in st.session_state
            )

            if analysis_complete:
                _, available_formats = get_cached_video_analysis(clean_url)

                if available_formats:
                    # Generate optimal profile combinations
                    optimal_combinations = get_optimal_profiles(
                        available_formats, max_profiles=10
                    )

                    if optimal_combinations:
                        st.success(
                            f"🎯 **{len(optimal_combinations)} optimal combinations generated** (from available formats)"
                        )

                        with st.expander(
                            "📋 Generated Profile Combinations (Auto Mode)",
                            expanded=True,
                        ):
                            for i, combination in enumerate(optimal_combinations, 1):
                                video_info = combination["video_format"]
                                audio_info = combination["audio_format"]

                                # Create detailed display
                                quality_info = (
                                    f"{video_info['resolution']}p"
                                    f"@{video_info.get('fps', '?')}fps "
                                    f"({video_info.get('vcodec', '?')}) + "
                                    f"{audio_info.get('abr', '?')}kbps "
                                    f"({audio_info.get('acodec', '?')})"
                                )

                                format_spec = combination["format_spec"]
                                container = combination["container"].upper()

                                st.write(f"✅ {i}. **{combination['profile_label']}**")
                                st.write(f"   📊 Quality: {quality_info}")
                                st.write(f"   🔧 Format: `{format_spec}` → {container}")
                    else:
                        # Use cached profile analysis from detect_video_quality_now
                        available_profiles = st.session_state.get(
                            "available_profiles", []
                        )
                        profile_summary = st.session_state.get("profile_summary", {})

                        # If no cached analysis, fallback to live calculation
                        if not available_profiles and not profile_summary:
                            profile_summary = get_profile_availability_summary(
                                available_formats
                            )
                            available_profiles = [
                                name
                                for name, info in profile_summary.items()
                                if info["available"]
                            ]

                        if available_profiles:
                            st.success(
                                f"🎯 **{len(available_profiles)} profiles available** (from {len(QUALITY_PROFILES)} total)"
                            )

                            with st.expander(
                                "📋 Available Profile Summary", expanded=True
                            ):
                                for profile_name in available_profiles:
                                    info = profile_summary[profile_name]
                                    st.write(f"✅ **{info['label']}**")
                                    st.write(
                                        f"   🎬 Video: {', '.join(info['video_matches'])}"
                                    )
                                    st.write(
                                        f"   🔊 Audio: {', '.join(info['audio_matches'])}"
                                    )
                        else:
                            st.warning(
                                "⚠️ No profiles match available formats - will try all profiles as fallback"
                            )
                else:
                    # No formats available - show static profile list
                    with st.expander(
                        "📋 All Profile Order (No Format Analysis)", expanded=False
                    ):
                        for i, profile in enumerate(QUALITY_PROFILES, 1):
                            st.write(
                                f"{i}. **{profile['label']}** - {profile['description']}"
                            )
            else:
                # No analysis yet - encourage user to detect profiles
                st.warning(
                    "⚠️ **No profile analysis done yet** - Click '🔍 Detect Available Profiles' below to see which profiles work best for this video."
                )

                # Show all profiles as fallback
                with st.expander(
                    "📋 All Quality Profiles (Default Order)", expanded=False
                ):
                    st.info(
                        "These profiles will be tried in order if no detection is performed:"
                    )
                    for i, profile in enumerate(QUALITY_PROFILES, 1):
                        st.write(
                            f"{i}. **{profile['label']}** - {profile['description']}"
                        )
        else:
            # No URL yet - show all profiles with hint
            st.info(
                "💡 Enter a video URL above, then use '🔍 Detect Available Profiles' to see optimal profiles for that video"
            )
            with st.expander("📋 Default Profile Order (Auto Mode)", expanded=False):
                st.info(
                    "These profiles will be tried in order when no specific detection is performed:"
                )
                for i, profile in enumerate(QUALITY_PROFILES, 1):
                    st.write(f"{i}. **{profile['label']}** - {profile['description']}")

        # Store auto mode
        selected_profile = None

    else:
        st.warning(
            "🔒 **Forced Mode**: Only your selected profile will be tried. Download will fail if this specific combination is unavailable."
        )

        # Check if we have dynamic profile analysis results
        if url:
            clean_url = sanitize_url(url)
            analysis_complete = (
                st.session_state.get("codecs_detected_for_url", "") == clean_url
                and "available_codecs" in st.session_state
            )

            if analysis_complete:
                _, available_formats = get_cached_video_analysis(clean_url)

                if available_formats:
                    # Generate optimal profile combinations (same as auto mode)
                    optimal_combinations = get_optimal_profiles(
                        available_formats, max_profiles=10
                    )

                    if optimal_combinations:
                        st.success(
                            f"🎯 **{len(optimal_combinations)} real detected profiles available** (same as Auto Mode)"
                        )

                        # Create selectbox with real detected combinations
                        def format_combination_option(combination_idx):
                            combination = optimal_combinations[combination_idx]
                            video_info = combination["video_format"]
                            audio_info = combination["audio_format"]

                            quality_info = (
                                f"{video_info['resolution']}p"
                                f"@{video_info.get('fps', '?')}fps "
                                f"({video_info.get('vcodec', '?')}) + "
                                f"{audio_info.get('abr', '?')}kbps "
                                f"({audio_info.get('acodec', '?')})"
                            )

                            return f"{combination['profile_label']} | {quality_info}"

                        selected_combination_idx = st.selectbox(
                            "Select detected profile combination:",
                            options=list(range(len(optimal_combinations))),
                            format_func=format_combination_option,
                            index=0,
                            help="These are the real detected and matched profiles for this specific video.",
                            key="quality_profile_combination",
                        )

                        # Get the selected combination
                        selected_combination = optimal_combinations[
                            selected_combination_idx
                        ]

                        # Store the combination for download use - convert to profile-like structure
                        dynamic_profile = {
                            "name": selected_combination["profile_name"],
                            "label": selected_combination["profile_label"],
                            "format": selected_combination["format_spec"],
                            "format_sort": f"res:{selected_combination['video_format']['resolution']},fps,+size,br",
                            "extra_args": selected_combination["extra_args"],
                            "container": selected_combination["container"],
                            "priority": selected_combination["priority"],
                            "_dynamic_combination": selected_combination,  # Store original for reference
                        }

                        # Store in session state for download logic
                        st.session_state["dynamic_profile_selected"] = dynamic_profile
                        selected_profile = dynamic_profile[
                            "name"
                        ]  # Store name for compatibility

                        # Show detailed info about selected combination
                        st.info(f"🎯 **{selected_combination['profile_label']}**")

                        video_info = selected_combination["video_format"]
                        audio_info = selected_combination["audio_format"]

                        st.write(
                            f"📊 **Quality**: {video_info['resolution']}p@{video_info.get('fps', '?')}fps ({video_info.get('vcodec', '?')}) + {audio_info.get('abr', '?')}kbps ({audio_info.get('acodec', '?')})"
                        )
                        st.write(
                            f"🔧 **Format**: `{selected_combination['format_spec']}` → {selected_combination['container'].upper()}"
                        )

                        # Show available combinations preview
                        with st.expander(
                            "📋 All Detected Profile Combinations", expanded=False
                        ):
                            for i, combination in enumerate(optimal_combinations, 1):
                                video_info = combination["video_format"]
                                audio_info = combination["audio_format"]

                                quality_info = (
                                    f"{video_info['resolution']}p"
                                    f"@{video_info.get('fps', '?')}fps "
                                    f"({video_info.get('vcodec', '?')}) + "
                                    f"{audio_info.get('abr', '?')}kbps "
                                    f"({audio_info.get('acodec', '?')})"
                                )

                                format_spec = combination["format_spec"]
                                container = combination["container"].upper()

                                status_icon = (
                                    "🎯" if i - 1 == selected_combination_idx else "📋"
                                )
                                st.write(
                                    f"{status_icon} {i}. **{combination['profile_label']}**"
                                )
                                st.write(f"   📊 Quality: {quality_info}")
                                st.write(f"   🔧 Format: `{format_spec}` → {container}")

                    else:
                        # Fallback to static profiles if no dynamic combinations found
                        st.warning(
                            "⚠️ No dynamic profiles generated - using static profiles as fallback"
                        )

                        selected_profile = st.selectbox(
                            "Select quality profile:",
                            options=[profile["name"] for profile in QUALITY_PROFILES],
                            format_func=lambda x: next(
                                p["label"] for p in QUALITY_PROFILES if p["name"] == x
                            ),
                            index=get_default_profile_index(),
                            help="Using static profiles as fallback. Try 'Detect Available Profiles' for better options.",
                            key="quality_profile",
                        )

                        # Show selected profile details
                        profile = get_profile_by_name(selected_profile)
                        if profile:
                            st.info(f"🎯 **{profile['label']}**")
                            st.write(f"📋 {profile['description']}")
                            st.write(format_profile_codec_info(profile))
                else:
                    # No formats available - fallback to static profiles
                    st.warning(
                        "⚠️ No formats detected - using static profiles as fallback"
                    )

                    selected_profile = st.selectbox(
                        "Select quality profile:",
                        options=[profile["name"] for profile in QUALITY_PROFILES],
                        format_func=lambda x: next(
                            p["label"] for p in QUALITY_PROFILES if p["name"] == x
                        ),
                        index=get_default_profile_index(),
                        help="No formats detected. Try 'Detect Available Profiles' for better options.",
                        key="quality_profile",
                    )

                    # Show selected profile details
                    profile = get_profile_by_name(selected_profile)
                    if profile:
                        st.info(f"🎯 **{profile['label']}**")
                        st.write(f"📋 {profile['description']}")
                        st.write(format_profile_codec_info(profile))
            else:
                # No analysis yet - encourage detection
                st.info(
                    "💡 Click '🔍 Detect Available Profiles' below to see real detected profiles for this video"
                )

                selected_profile = st.selectbox(
                    "Select quality profile:",
                    options=[profile["name"] for profile in QUALITY_PROFILES],
                    format_func=lambda x: next(
                        p["label"] for p in QUALITY_PROFILES if p["name"] == x
                    ),
                    index=get_default_profile_index(),
                    help="Use 'Detect Available Profiles' to see real matched profiles for this video.",
                    key="quality_profile",
                )

                # Show selected profile details
                profile = get_profile_by_name(selected_profile)
                if profile:
                    st.info(f"🎯 **{profile['label']}**")
                    st.write(f"📋 {profile['description']}")
                    st.write(format_profile_codec_info(profile))
        else:
            # No URL provided
            selected_profile = st.selectbox(
                "Select quality profile:",
                options=[profile["name"] for profile in QUALITY_PROFILES],
                format_func=lambda x: next(
                    p["label"] for p in QUALITY_PROFILES if p["name"] == x
                ),
                index=get_default_profile_index(),
                help="Enter a URL above and use 'Detect Available Profiles' to see real matched profiles.",
                key="quality_profile",
            )

            # Show selected profile details
            profile = get_profile_by_name(selected_profile)
            if profile:
                st.info(f"🎯 **{profile['label']}**")
                st.write(f"📋 {profile['description']}")
                st.write(format_profile_codec_info(profile))

    # === 2. ADVANCED PROFILE OPTIONS ===
    with st.expander("⚙️ Advanced Profile Options", expanded=False):
        st.info(
            "🔧 **Fine-tune profile behavior** - These options affect how the quality profiles above are applied."
        )

        prefer_free_formats = st.checkbox(
            "Prefer free formats (WebM/Opus)",
            value=True,
            help="Prioritize open/free codecs when available. Automatically disabled for MP4 profiles.",
            key="prefer_free_formats",
        )

        refuse_quality_downgrade = st.checkbox(
            "Refuse quality downgrade",
            value=False,
            help="Fail download if premium codecs (AV1/Opus) are unavailable, instead of falling back to lower quality.",
            key="refuse_quality_downgrade",
        )

    # === 3. FORMAT AND CODEC DETECTION ===
    st.subheader("🔍 Detect Available Quality Profiles")
    st.info(
        "🎯 **Discover optimal profiles** - Analyze the video to find the best matching quality profiles available."
    )

    # Manual quality detection button and status in a single section
    if url and url.strip():
        clean_url = sanitize_url(url)
        has_analysis = (
            st.session_state.get("codecs_detected_for_url", "") == clean_url
            and "available_codecs" in st.session_state
        )

        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button(
                "🔍 Detect Available Profiles",
                help="Analyze video formats and generate matching quality profiles",
                type="primary",
            ):
                detect_video_quality_now(url.strip())
                st.rerun()

        with col2:
            if has_analysis:
                # Analysis complete - show quality summary
                _, cached_formats = get_cached_video_analysis(clean_url)
                st.session_state.available_formats = cached_formats

                if cached_formats:
                    max_res = max(
                        extract_resolution_value(f["resolution"])
                        for f in cached_formats
                    )
                    if max_res >= 2160:
                        st.success("✅ 4K+ quality available - profiles updated above")
                    elif max_res >= 1080:
                        st.success("✅ HD quality available - profiles updated above")
                    else:
                        st.success(
                            "✅ Standard quality available - profiles updated above"
                        )
                else:
                    st.success(
                        "✅ Analysis complete - use manual format selection below"
                    )
            else:
                st.info("💡 Click to detect optimal profiles for this video")
    else:
        st.info("💡 Enter a video URL above to analyze available quality profiles")

    # === 4. DETECTED CODECS DISPLAY ===
    if url:
        clean_url = sanitize_url(url)

        # Only show codec details if analysis is complete
        cached_codecs, _ = get_cached_video_analysis(clean_url)

        # Check if we have real analysis results (not just defaults)
        has_real_analysis = (
            st.session_state.get("codecs_detected_for_url", "") == clean_url
            and "available_codecs" in st.session_state
        )

        if has_real_analysis and any(cached_codecs.values()):
            st.markdown("### 🧬 Detected Video Codecs")

            # Create columns for codec display
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**📹 Video Codecs:**")
                if cached_codecs.get("av01"):
                    st.success("🏆 AV1 (Premium)")
                else:
                    st.error("❌ AV1 (Premium)")

                if cached_codecs.get("vp9"):
                    st.success("🥈 VP9 (Modern)")
                else:
                    st.error("❌ VP9 (Modern)")

                if cached_codecs.get("h264"):
                    st.success("📺 H.264 (Compatible)")
                else:
                    st.error("❌ H.264 (Compatible)")

            with col2:
                st.markdown("**🎵 Audio Codecs:**")
                if cached_codecs.get("opus"):
                    st.success("🎧 Opus (High Quality)")
                else:
                    st.error("❌ Opus (High Quality)")

                if cached_codecs.get("aac"):
                    st.success("🔊 AAC (Compatible)")
                else:
                    st.error("❌ AAC (Compatible)")

            # Quality assessment
            has_premium = cached_codecs.get("av01") and cached_codecs.get("opus")
            has_modern = cached_codecs.get("vp9") and cached_codecs.get("opus")

            if has_premium:
                st.success(
                    "🏆 **Premium Quality Available** - AV1 + Opus codecs detected"
                )
            elif has_modern:
                st.info("🥈 **Modern Quality Available** - VP9 + Opus codecs detected")
            else:
                st.warning("📺 **Standard Quality Only** - Basic codecs available")

    # === 5. MANUAL FORMAT SELECTION ===
    with st.expander("🔧 Manual Format Selection", expanded=False):
        st.info(
            "🎯 **Override profiles** - Select a specific format from the detected list. This overrides the intelligent profile system above."
        )
        st.warning(
            "⚠️ Advanced users only: This bypasses quality profiles and may result in format compatibility issues."
        )

        if st.session_state.available_formats:
            format_options = [t("quality_auto_option")] + [
                f"{fmt['resolution']} - {fmt['ext']} ({fmt['format_id']})"
                for fmt in st.session_state.available_formats
            ]

            selected_format_display = st.selectbox(
                t("quality_select_prompt"),
                options=format_options,
                index=0,
                help="Legacy format selection - overrides profile system",
                key="format_selector",
            )

            # Store the actual format ID for yt-dlp
            if selected_format_display == t("quality_auto_option"):
                st.session_state.selected_format = "auto"
            else:
                # Extract format ID from the display string
                for fmt in st.session_state.available_formats:
                    if f"({fmt['id']})" in selected_format_display:
                        st.session_state.selected_format = fmt["id"]
                        break
        else:
            st.info("💡 Use 'Detect Quality' above to populate format options here")


# Optional embedding section for chapter and subs
with st.expander(f"{t('embedding_title')}", expanded=False):
    # === SUBTITLES SECTION ===
    st.markdown(f"### {t('subtitles_section_title')}")
    st.info(t("subtitles_info"))

    embed_subs = st.checkbox(
        t("embed_subs"),
        value=settings.EMBED_SUBTITLES,
        key="embed_subs",
        help=t("embed_subs_help"),
    )

    # === CHAPTERS SECTION ===
    st.markdown(f"### {t('chapters_section_title')}")
    st.info(t("chapters_info"))

    embed_chapters = st.checkbox(
        t("embed_chapters"),
        value=settings.EMBED_CHAPTERS,
        key="embed_chapters",
        help=t("embed_chapters_help"),
    )

# === COOKIES MANAGEMENT ===
with st.expander(t("cookies_title"), expanded=False):
    # Show cookies expiration warning if detected during recent downloads
    if st.session_state.get("cookies_expired", False):
        st.warning("🔄 " + t("cookies_expired_friendly_message"))

        # Add a button to clear the warning
        if st.button(t("cookies_warning_dismiss"), key="dismiss_cookies_warning"):
            st.session_state["cookies_expired"] = False
            st.rerun()

    st.info(t("cookies_presentation"))

    # Determine default cookie method based on available options
    def get_default_cookie_method():
        # Check if cookies file exists and is valid
        if is_valid_cookie_file(YOUTUBE_COOKIES_FILE_PATH):
            return "file"

        # Check if browser is configured
        if is_valid_browser(COOKIES_FROM_BROWSER):
            return "browser"

        # Default to no cookies
        return "none"

    # Initialize session state for cookies method
    if "cookies_method" not in st.session_state:
        st.session_state.cookies_method = get_default_cookie_method()

    cookies_method = st.radio(
        t("cookies_method_prompt"),
        options=["file", "browser", "none"],
        format_func=lambda x: {
            "file": t("cookies_method_file"),
            "browser": t("cookies_method_browser"),
            "none": t("cookies_method_none"),
        }[x],
        index=["file", "browser", "none"].index(st.session_state.cookies_method),
        help=t("cookies_method_help"),
        key="cookies_method_radio",
        horizontal=True,
    )

    # Update session state
    st.session_state.cookies_method = cookies_method

    # Show details based on selected method
    if cookies_method == "file":
        st.markdown("**📁 File-based cookies:**")
        if is_valid_cookie_file(YOUTUBE_COOKIES_FILE_PATH):
            try:
                file_stat = os.stat(YOUTUBE_COOKIES_FILE_PATH)
                file_size = file_stat.st_size
                mod_time = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(file_stat.st_mtime)
                )
                st.success(f"✅ Cookies file found: `{YOUTUBE_COOKIES_FILE_PATH}`")
                st.info(f"📊 Size: {file_size:,} bytes | 📅 Modified: {mod_time}")
            except Exception as e:
                st.error(f"❌ Error reading cookies file: {e}")
        else:
            if YOUTUBE_COOKIES_FILE_PATH:
                st.error(f"❌ Cookies file not found: `{YOUTUBE_COOKIES_FILE_PATH}`")
            else:
                st.error("❌ No cookies file path configured in environment variables")
            st.info(
                "💡 Set YOUTUBE_COOKIES_FILE_PATH environment variable or export "
                "cookies from your browser using an extension like 'Get cookies.txt'"
            )

    elif cookies_method == "browser":
        st.markdown("**🌐 Browser-based cookies:**")

        # Get default browser from env or default to chrome
        default_browser = (
            COOKIES_FROM_BROWSER.strip().lower()
            if COOKIES_FROM_BROWSER.strip()
            else "chrome"
        )
        if default_browser not in SUPPORTED_BROWSERS:
            default_browser = "chrome"

        selected_browser = st.selectbox(
            "Select browser:",
            options=SUPPORTED_BROWSERS,
            index=SUPPORTED_BROWSERS.index(default_browser),
            help="Choose the browser from which to extract cookies",
            key="browser_select",
        )

        # Profile selection (optional)
        browser_profile = st.text_input(
            "Browser profile (optional):",
            value="",
            help="Leave empty for default profile, or specify profile name/path",
            placeholder="Default, Profile 1, /path/to/profile",
            key="browser_profile",
        )

        # Show current configuration
        browser_config = selected_browser
        if browser_profile.strip():
            browser_config = f"{selected_browser}:{browser_profile.strip()}"

        st.info(f"🔧 Will use: `--cookies-from-browser {browser_config}`")
        st.warning(
            "⚠️ Make sure your browser is closed or restart it after using this option"
        )

    else:  # none
        st.markdown("**🚫 No authentication:**")
        st.warning("⚠️ Without cookies, you won't be able to download:")
        st.markdown(
            """
        - Age-restricted videos
        - Member-only content
        - Some region-restricted videos
        - Videos requiring sign-in
        """
        )
        st.info("✅ Public videos will work normally")


# === ADVANCED OPTIONS ===
with st.expander(t("advanced_options"), expanded=False):
    st.info(t("advanced_options_presentation"))

    # Custom yt-dlp arguments
    ytdlp_custom_args = st.text_input(
        t("ytdlp_custom_args"),
        value=settings.YTDLP_CUSTOM_ARGS,
        placeholder=t("ytdlp_custom_args_placeholder"),
        help=t("ytdlp_custom_args_help"),
        key="ytdlp_custom_args",
    )

    st.markdown("---")

    # Debug options
    st.markdown("**🔍 Debug Options**")

    # Store current REMOVE_TMP_FILES setting in session state
    if "remove_tmp_files" not in st.session_state:
        st.session_state.remove_tmp_files = should_remove_tmp_files()

    remove_tmp_files = st.checkbox(
        "Remove temporary files after processing",
        value=st.session_state.remove_tmp_files,
        help="When disabled, all temporary files (.srt, .vtt, .part, intermediate outputs) will be kept for debugging. Check the tmp/ folder after download.",
        key="remove_tmp_files_checkbox",
    )

    # Store in session state for UI state tracking
    # Note: settings object is immutable, so we only track UI state here
    st.session_state.remove_tmp_files = remove_tmp_files

    if not remove_tmp_files:
        st.info(
            "🔍 **Debug mode active**: Temporary files will be preserved in the tmp/ folder for inspection."
        )


# === DOWNLOAD BUTTON ===
st.markdown("\n")
st.markdown("\n")

# Create a centered, prominent download button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    submitted = st.button(
        f"🎬 &nbsp; {t('download_button')}",
        type="primary",
        use_container_width=True,
        help=t("download_button_help"),
    )

st.markdown("\n")

# === CANCEL BUTTON PLACEHOLDER ===
cancel_placeholder = st.empty()

st.markdown("---")

# === ENHANCED STATUS & PROGRESS ZONE ===
# Create a more detailed status section
status_container = st.container()
with status_container:
    # Main status
    status_placeholder = st.empty()

    # Progress with details
    progress_placeholder = st.progress(0, text=t("waiting"))

    # Additional info row (initially hidden)
    info_placeholder = st.empty()

# === Logs (PLACED AT BOTTOM OF PAGE) ===
# st.markdown("---")
st.markdown("\n")
st.markdown("\n")
st.markdown(f"### {t('logs')}")
logs_placeholder = st.empty()  # black scrollable window (bottom)
download_btn_placeholder = st.empty()  # "Download logs" button (bottom)

ALL_LOGS: list[str] = []  # global buffer (complete log content)
run_unique_key = (
    f"download_logs_btn_{st.session_state.run_seq}"  # unique key per execution
)


def render_download_button():
    # dynamic rendering with current logs
    if ALL_LOGS:  # Only render if there are logs
        download_btn_placeholder.download_button(
            t("download_logs_button"),
            data="\n".join(ALL_LOGS),
            file_name="logs.txt",
            mime="text/plain",
            # Unique key with log count
            key=f"download_logs_btn_{st.session_state.run_seq}_{len(ALL_LOGS)}",
        )


def push_log(line: str):
    # Clean the line of ANSI escape sequences and control characters
    clean_line = line.rstrip("\n")

    # Remove ANSI escape sequences (colors, cursor movements, etc.)
    clean_line = ANSI_ESCAPE_PATTERN.sub("", clean_line)

    # Remove other control characters except newlines and tabs
    clean_line = "".join(
        char for char in clean_line if ord(char) >= 32 or char in "\t\n"
    )

    ALL_LOGS.append(clean_line)

    # Update logs display
    with logs_placeholder.container():
        # Scrollable logs container - additional HTML escaping for safety
        logs_content = (
            "\n".join(ALL_LOGS[-400:])
            .replace("&", "&amp;")  # Escape & first
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )
        st.markdown(
            f'<div style="{LOGS_CONTAINER_STYLE}">{logs_content}</div>',
            unsafe_allow_html=True,
        )

    # Update the download button with current logs
    render_download_button()


# Register this push_log function for use by other modules
register_main_push_log(push_log)


# Pending analysis logs system removed - using direct synchronous logging instead


def update_download_metrics(
    info_placeholder,
    speed="",
    eta="",
    size="",
    fragments="",
    show_fragments=True,
    elapsed="",
):
    """Update the download metrics display with clean, predictable layout"""
    if info_placeholder is None:
        return

    # Determine if this is a completed process
    is_completed = speed and (
        any(icon in speed for icon in ["✅", "✂️", "📝"]) or "complete" in speed.lower()
    )

    metrics_parts = []

    if is_completed:
        # COMPLETED PROCESS: Clean 3-column layout
        # Status (clean up icons)
        if speed:
            clean_status = speed.replace("✅ ", "").replace("✂️ ", "").replace("📝 ", "")
            metrics_parts.append(f"{t('metrics_status')}: {clean_status}")

        # Size (always show for completed)
        if size:
            metrics_parts.append(f"{t('metrics_size')}: {size}")

        # Duration (total time taken - only if meaningful)
        if elapsed and elapsed != "Completed":
            metrics_parts.append(f"{t('metrics_duration')}: {elapsed}")

        # Display in clean 3-column layout for completed processes
        with info_placeholder.container():
            if len(metrics_parts) >= 2:
                # Always use 3 columns for consistent layout
                cols = st.columns(3)
                for i in range(3):
                    if i < len(metrics_parts):
                        cols[i].markdown(metrics_parts[i])
                    # Empty columns are left blank naturally

    else:
        # ACTIVE DOWNLOAD: Dynamic layout with ETA
        # Speed
        if speed:
            metrics_parts.append(f"{t('metrics_speed')}: {speed}")

        # Size
        if size:
            metrics_parts.append(f"{t('metrics_size')}: {size}")

        # ETA (estimated time remaining - only for active downloads)
        if eta and eta not in ["00:00", "00:01"]:
            metrics_parts.append(f"{t('metrics_eta')}: {eta}")

        # Duration (time elapsed so far - only if different from ETA)
        if elapsed and (not eta or eta in ["00:00", "00:01"]):
            metrics_parts.append(f"{t('metrics_duration')}: {elapsed}")

        # Progress/Fragments (only when actively downloading)
        if fragments and show_fragments and "/" in str(fragments):
            metrics_parts.append(f"{t('metrics_progress')}: {fragments}")

        # Display with dynamic columns (prioritize most important info)
        with info_placeholder.container():
            if metrics_parts:
                # Limit to 4 columns max for readability
                display_metrics = metrics_parts[:4]
                cols = st.columns(len(display_metrics))
                for i, metric in enumerate(display_metrics):
                    cols[i].markdown(metric)

    # Fallback if no metrics at all
    if not metrics_parts:
        info_placeholder.info("📊 Processing...")


def create_command_summary(cmd: List[str]) -> str:
    """Create a user-friendly summary of the yt-dlp command instead of showing the full verbose command"""
    if not cmd or len(cmd) < 2:
        return "Running command..."

    # Extract key information from the command
    summary_parts = []

    # Determine the client being used
    if "--extractor-args" in cmd:
        extractor_idx = cmd.index("--extractor-args")
        if extractor_idx + 1 < len(cmd):
            extractor_arg = cmd[extractor_idx + 1]
            if "android" in extractor_arg:
                summary_parts.append("📱 Android client")
            elif "ios" in extractor_arg:
                summary_parts.append("📱 iOS client")
            elif "web" in extractor_arg:
                summary_parts.append("🌐 Web client")
            else:
                summary_parts.append("🔧 Custom client")
    else:
        summary_parts.append("🎯 Default client")

    # Check for authentication
    if "--cookies" in cmd:
        summary_parts.append("🍪 with cookies")
    else:
        summary_parts.append("🔓 no auth")

    # Get the URL (usually the last argument)
    url = cmd[-1] if cmd else ""
    if "youtube.com" in url or "youtu.be" in url:
        video_id = (
            url.split("v=")[-1].split("&")[0] if "v=" in url else url.split("/")[-1]
        )
        summary_parts.append(f"📺 {video_id[:11]}")

    return " • ".join(summary_parts)


def run_cmd(cmd: List[str], progress=None, status=None, info=None) -> int:
    """Execute command with enhanced progress tracking and metrics display"""
    start_time = time.time()

    # Create a user-friendly command summary instead of the full verbose command
    cmd_summary = create_command_summary(cmd)
    push_log(f"🚀 {cmd_summary}")

    # Also show the actual complete command for transparency
    if cmd and "yt-dlp" in cmd[0]:
        # Show the full yt-dlp command exactly as executed
        cmd_str = " ".join(cmd)
        push_log(f"💻 Full yt-dlp command:\n{cmd_str}")
    elif cmd and "ffmpeg" in cmd[0]:
        # Show the full ffmpeg command exactly as executed
        cmd_str = " ".join(cmd)
        push_log(f"💻 Full ffmpeg command:\n{cmd_str}")

    # Initialize metrics tracking
    metrics = DownloadMetrics()

    try:
        with subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
        ) as proc:
            for line in proc.stdout:
                # Check for cancellation request
                if st.session_state.get("download_cancelled", False):
                    safe_push_log(t("download_cancelled"))
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return -1  # Cancelled return code

                line = line.rstrip("\n")

                # Clean ANSI escape sequences before logging (FFmpeg can output colors)
                clean_line = ANSI_ESCAPE_PATTERN.sub("", line)

                # Check if this message should be suppressed from user logs
                if not should_suppress_message(clean_line):
                    push_log(clean_line)

                # Track cookies expiration for user-friendly notification
                if is_cookies_expired_warning(clean_line):
                    if not hasattr(metrics, "_cookies_expired_detected"):
                        metrics._cookies_expired_detected = True
                        # Set session state for persistent notification
                        st.session_state["cookies_expired"] = True
                        push_log("🔄 " + t("cookies_expired_friendly_message"))

                # Capture error messages for fallback strategies - use cleaned line
                line_lower = clean_line.lower()
                if any(
                    keyword in line_lower for keyword in ["error", "failed", "unable"]
                ):
                    st.session_state["last_error"] = clean_line

                # Check for format unavailable errors (premium codec authentication issues)
                if is_format_unavailable_error(clean_line):
                    # Don't spam logs - only show hint once per profile attempt
                    current_profile = st.session_state.get(
                        "current_attempting_profile", ""
                    )
                    hint_key = f"_format_hint_shown_{current_profile}"

                    if not getattr(
                        metrics, hint_key, False
                    ) and not st.session_state.get(hint_key, False):
                        push_log("")  # Empty line for readability
                        log_format_unavailable_error_hint(clean_line, current_profile)
                        push_log("")  # Empty line for readability
                        setattr(metrics, hint_key, True)
                        st.session_state[hint_key] = (
                            True  # Persist across different run_cmd calls
                        )

                # Check for HTTP 403 and other authentication errors
                elif is_authentication_error(clean_line):
                    # Don't spam logs - only show hint once per download
                    if not getattr(metrics, "_auth_hint_shown", False):
                        push_log("")  # Empty line for readability
                        log_authentication_error_hint(clean_line)
                        push_log("")  # Empty line for readability
                        metrics._auth_hint_shown = True

                # Skip processing if no UI components provided
                if not (progress and status):
                    continue

                # Calculate elapsed time
                elapsed = time.time() - start_time
                elapsed_str = fmt_hhmmss(int(elapsed))

                # === DOWNLOAD PROGRESS WITH DETAILS ===
                download_progress = parse_download_progress(clean_line)
                if download_progress:
                    percent, size, speed, eta_time = download_progress
                    try:
                        pct_int = int(percent)
                        if (
                            abs(pct_int - metrics.last_progress) >= 1
                        ):  # Only update every 1%
                            # Simplified progress bar - details shown in metrics below
                            progress.progress(pct_int / 100.0, text=f"{percent}%")

                            # Update metrics
                            metrics.update_speed(speed)
                            metrics.update_eta(eta_time)
                            metrics.update_size(size)
                            if info:
                                metrics.display(info)
                                # Debug: also show in logs occasionally
                                if pct_int % 10 == 0:  # Every 10%
                                    push_log(
                                        f"📊 Progress: {percent}% | Speed: {speed} | ETA: {eta_time} | Size: {size}"
                                    )

                            metrics.last_progress = pct_int
                        continue
                    except ValueError:
                        pass

                # === FRAGMENT DOWNLOAD ===
                fragment_progress = parse_fragment_progress(clean_line)
                if fragment_progress:
                    current, total = fragment_progress
                    try:
                        percent = int((current / total) * 100)
                        fragments_str = f"{current}/{total}"

                        if (
                            abs(percent - metrics.last_progress) >= 5
                        ):  # Update every 5% for fragments
                            # Simplified fragment progress bar
                            progress.progress(
                                percent / 100.0,
                                text=f"{percent}% ({current}/{total} fragments)",
                            )

                            metrics.update_fragments(fragments_str)
                            if info:
                                metrics.display(info)
                                # Debug: show fragment progress in logs occasionally
                                if percent % 20 == 0:  # Every 20%
                                    push_log(
                                        f"🧩 Fragments: {fragments_str} ({percent}% complete)"
                                    )

                            metrics.last_progress = percent
                        continue
                    except (ValueError, ZeroDivisionError):
                        pass

                # === GENERIC PERCENTAGE PROGRESS ===
                generic_percent = parse_generic_percentage(clean_line)
                if generic_percent is not None:
                    try:
                        pct_int = int(generic_percent)
                        if abs(pct_int - metrics.last_progress) >= 5:  # Update every 5%
                            progress.progress(
                                pct_int / 100.0,
                                text=f"⚙️ Processing... {pct_int}% | ⏱️ {elapsed_str}",
                            )
                            metrics.last_progress = pct_int
                        continue
                    except ValueError:
                        pass

                # === STATUS DETECTION ===
                # line_lower already set above from clean_line

                # Detect specific statuses with more precise matching
                if any(
                    keyword in line_lower
                    for keyword in ["merging", "muxing", "combining"]
                ):
                    status.info(t("status_merging"))
                elif any(
                    phrase in line_lower
                    for phrase in [
                        "ffmpeg -i",
                        "cutting at",
                        "trimming video",
                        "extracting clip",
                    ]
                ):
                    status.info(t("status_cutting_video"))
                elif any(
                    keyword in line_lower
                    for keyword in ["converting", "encoding", "re-encoding"]
                ):
                    status.info(t("status_processing_ffmpeg"))
                elif any(
                    keyword in line_lower
                    for keyword in ["downloading", "fetching", "[download]"]
                ):
                    status.info(t("status_downloading"))

            ret = proc.wait()

            # Final status update
            total_time = time.time() - start_time
            total_time_str = fmt_hhmmss(int(total_time))

            if ret == 0:
                if status:
                    status.success(t("status_command_success", time=total_time_str))
                if progress:
                    progress.progress(1.0, text=t("status_completed"))
            else:
                if status:
                    status.error(
                        t("status_command_failed", code=ret, time=total_time_str)
                    )

            return ret

    except Exception as e:
        total_time = time.time() - start_time
        total_time_str = fmt_hhmmss(int(total_time))
        push_log(t("log_runner_exception", error=e))
        if status:
            status.error(t("status_command_exception", error=e, time=total_time_str))
        return 1


# === ACTION ===
if submitted:
    # new execution -> new button key (avoid Streamlit duplicates)
    st.session_state.run_seq += 1
    st.session_state.download_cancelled = False  # Initialize cancellation flag
    st.session_state.download_finished = False  # Track download state
    ALL_LOGS.clear()
    # The download button will be rendered dynamically by push_log()

# === CANCEL BUTTON ===
# Show cancel button during active downloads
if st.session_state.get("run_seq", 0) > 0 and not st.session_state.get(
    "download_finished", False
):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            t("cancel_button"),
            key=f"cancel_btn_{st.session_state.get('run_seq', 0)}",
            help=t("cancel_button_help"),
            type="secondary",
            use_container_width=True,
        ):
            st.session_state.download_cancelled = True
            st.session_state.download_finished = True
            st.info(t("download_cancelled"))
            st.rerun()

# Continue with download logic if submitted
if submitted:

    if not url:
        st.error(t("error_provide_url"))
        st.stop()

    # If filename is empty, we'll get it from the video title later
    if not filename.strip():
        push_log("📝 No filename provided, will use video title")
        filename = None  # Will be set later from video metadata

    # Parse cutting times
    start_sec = parse_time_like(start_text)
    end_sec = parse_time_like(end_text)

    # Determine if we need to cut sections
    do_cut = start_sec is not None and end_sec is not None and end_sec > start_sec

    # resolve dest dir using simple folder logic
    if video_subfolder == "/":
        dest_dir = VIDEOS_FOLDER
    else:
        dest_dir = VIDEOS_FOLDER / video_subfolder

    # create dirs
    ensure_dir(VIDEOS_FOLDER)
    ensure_dir(TMP_DOWNLOAD_FOLDER)
    ensure_dir(dest_dir)

    push_log(f"📁 Destination folder: {dest_dir}")

    # Create temporary subfolder structure with same hierarchy
    if video_subfolder == "/":
        tmp_subfolder_dir = TMP_DOWNLOAD_FOLDER
    else:
        tmp_subfolder_dir = TMP_DOWNLOAD_FOLDER / video_subfolder
        ensure_dir(tmp_subfolder_dir)

    push_log(t("log_temp_download_folder", folder=tmp_subfolder_dir))

    # build bases
    clean_url = sanitize_url(url)

    # Setup cookies for yt-dlp operations
    cookies_part = build_cookies_params()

    # If no filename provided, get video title
    if filename is None:
        filename = get_video_title(clean_url, cookies_part)

    base_output = filename  # without extension

    # Always check for SponsorBlock segments for this video (informational)
    push_log("🔍 Analyzing video for sponsor segments...")
    try:
        all_sponsor_segments = get_sponsorblock_segments(clean_url, cookies_part)
        if not all_sponsor_segments:
            push_log("✅ No sponsor segments detected in this video")
    except Exception as e:
        push_log(f"⚠️ Could not analyze sponsor segments: {e}")

    # === NEW STRATEGY: Simple configuration from settings ===
    # Get settings for quality preferences (used by new strategy internally)
    settings = get_settings()
    push_log("🤖 Using new dynamic strategy with optimal format selection")

    # === NEW STRATEGY: Always use dynamic format selection ===
    # The new strategy dynamically selects the best AV1/VP9 formats available
    push_log("🤖 Using new dynamic strategy with optimal format selection")
    quality_strategy_to_use = "auto_profiles"  # Always use the new strategy
    format_spec = "bv*+ba/b"  # Placeholder - actual formats determined by get_formats_id_to_download()

    # --- yt-dlp base command construction
    # New strategy: Always use MKV container (better for modern codecs)
    force_mp4 = False  # MKV supports all modern codecs better

    ytdlp_custom_args = st.session_state.get("ytdlp_custom_args", "")

    # Only build base command if NOT using profile system
    if quality_strategy_to_use == "auto_profiles" or isinstance(
        quality_strategy_to_use, dict
    ):
        # Profile system handles command building internally
        common_base = []
    else:
        # Legacy system - build base command normally
        common_base = build_base_ytdlp_command(
            base_output,
            tmp_subfolder_dir,
            format_spec,
            embed_chapters,
            embed_subs,
            force_mp4,
            ytdlp_custom_args,
            quality_strategy_to_use,
        )

    # subtitles - different handling based on whether we'll cut or not
    subs_part = []
    if subs_selected:
        langs_csv = ",".join(subs_selected)
        subs_part = [
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            langs_csv,
            "--convert-subs",
            "srt",
        ]

        # For cutting: always separate files for proper processing
        # For no cutting: respect user's embed_subs choice

        if do_cut:
            subs_part += ["--no-embed-subs"]  # Always separate for section cutting
        else:
            if embed_subs:
                subs_part += ["--embed-subs"]  # Embed if user wants it and no cutting
            else:
                subs_part += ["--no-embed-subs"]  # Separate if user prefers it

    # cookies - use new dynamic cookie management
    cookies_part = build_cookies_params()

    # SponsorBlock configuration
    sb_part = build_sponsorblock_params(sb_choice)

    # === Section Decision with intelligent SponsorBlock analysis ===
    # Variables for SponsorBlock adjustment
    original_end_sec = end_sec
    sponsor_time_removed = 0
    adjusted_end_sec = end_sec

    # If we have both sections AND SponsorBlock Remove, analyze segments
    remove_cats, _ = get_sponsorblock_config(sb_choice)
    if do_cut and remove_cats:  # If there are categories to remove
        push_log(t("log_sponsorblock_intelligent_analysis"))
        sponsor_segments = get_sponsorblock_segments(
            clean_url, cookies_part, remove_cats
        )
        sponsor_time_removed, adjusted_end_sec = calculate_sponsor_overlap(
            start_sec, end_sec, sponsor_segments
        )

        if sponsor_time_removed > 0:
            push_log(t("log_adjusted_section"))
            push_log(
                t(
                    "log_section_requested",
                    start=fmt_hhmmss(start_sec),
                    end=fmt_hhmmss(original_end_sec),
                    duration=original_end_sec - start_sec,
                )
            )
            push_log(
                t(
                    "log_section_final",
                    start=fmt_hhmmss(start_sec),
                    end=fmt_hhmmss(adjusted_end_sec),
                    duration=adjusted_end_sec - start_sec,
                )
            )
            push_log(t("log_content_obtained", duration=adjusted_end_sec - start_sec))
            end_sec = adjusted_end_sec  # Use adjusted end for the rest

    # New simplified logic with intelligent SponsorBlock adjustment:
    # - Always download the complete video (with SponsorBlock if requested)
    # - If sections requested, analyze SponsorBlock and adjust automatically
    # - Cut with ffmpeg afterwards with the right coordinates
    if do_cut:
        if sponsor_time_removed > 0:
            push_log(t("log_scenario_adjusted"))
            push_log(t("log_final_content_info", duration=adjusted_end_sec - start_sec))
        elif subs_selected:
            push_log(t("log_scenario_mp4_cutting"))
        else:
            push_log(t("log_scenario_ffmpeg_cutting"))
    else:
        push_log(t("log_scenario_standard"))

    # --- Final yt-dlp command with intelligent fallback
    push_log(t("log_download_with_sponsorblock"))

    # Build base command without cookies (fallback handles auth)
    cmd_base = [
        *common_base,
        *subs_part,
        *sb_part,
    ]

    progress_placeholder.progress(0, text=t("status_preparation"))
    status_placeholder.info(t("status_downloading_simple"))

    # Use intelligent fallback with retry strategies
    # NEW STRATEGY: Always use dynamic profile selection
    if quality_strategy_to_use == "auto_profiles":
        push_log("🤖 Auto mode: Will try all profiles in quality order")
        ret_dl, error_msg = smart_download_with_profiles(
            base_output,
            tmp_subfolder_dir,
            embed_chapters,
            embed_subs,
            force_mp4,
            ytdlp_custom_args,
            clean_url,
            "auto",  # Always use auto mode with new strategy
            None,  # No target profile - let new strategy decide
            False,  # refuse_quality_downgrade = False (allow fallback)
            do_cut,
            subs_selected,
            sb_choice,
            progress_placeholder,
            status_placeholder,
            info_placeholder,
        )

    # Handle cancellation
    if ret_dl == -1:
        status_placeholder.info(t("cleaning_temp_files"))
        cleanup_tmp_files(base_output, tmp_subfolder_dir, "download")
        status_placeholder.success(t("cleanup_complete"))

        # Mark download as finished
        st.session_state.download_finished = True
        st.stop()

    # Search for the final file in TMP subfolder (prioritize MKV format from new strategy)
    final_tmp = None

    # New strategy prefers MKV, but search all common formats
    search_extensions = [".mkv", ".mp4", ".webm"]

    for ext in search_extensions:
        p = tmp_subfolder_dir / f"{base_output}{ext}"
        if p.exists():
            final_tmp = p
            safe_push_log(f"📄 Found output file: {p.name}")
            break

    if not final_tmp:
        status_placeholder.error(t("error_download_failed"))
        st.stop()

    # === Measure downloaded file size ===
    downloaded_size = final_tmp.stat().st_size
    downloaded_size_mb = downloaded_size / (1024 * 1024)
    downloaded_size_str = f"{downloaded_size_mb:.2f}MiB"

    # Update metrics with accurate downloaded file size
    if info_placeholder:
        update_download_metrics(
            info_placeholder,
            speed="✅ Downloaded",
            eta="",  # Clear ETA for completed download
            size=downloaded_size_str,
            show_fragments=False,
        )

    push_log(f"📊 Downloaded file size: {downloaded_size_str} (actual measurement)")

    # === Post-processing according to scenario ===
    final_source = final_tmp

    # If sections requested → cut with ffmpeg using selected mode
    if do_cut:
        # Get cutting mode from UI
        cut_mode = st.session_state.get("cutting_mode", "keyframes")
        push_log(t("log_cutting_mode_selected", mode=cut_mode))

        status_placeholder.info(t("status_cutting_video"))

        # Determine cut output format based on source file and preferences
        source_ext = final_tmp.suffix  # .mkv, .mp4, or .webm

        # Smart format selection for cutting:
        # 1. If source is MP4 and we have subtitles, keep MP4 for compatibility
        # 2. If source is MKV, keep MKV to preserve all codec features
        # 3. For WebM, convert to MKV for better subtitle support
        if source_ext == ".mp4":
            cut_ext = ".mp4"  # Keep MP4 format
        elif source_ext == ".mkv":
            cut_ext = ".mkv"  # Keep MKV format
        else:  # .webm or other
            cut_ext = ".mkv"  # Convert to MKV for better compatibility

        if source_ext == cut_ext:
            push_log(f"🎬 Cutting format: {cut_ext} (preserved)")
        else:
            push_log(f"🎬 Cutting format: {source_ext} → {cut_ext} (converted)")

        cut_output = tmp_subfolder_dir / f"{base_output}_cut{cut_ext}"

        if cut_output.exists():
            try:
                if should_remove_tmp_files():
                    cut_output.unlink()
                    push_log("🗑️ Removed existing cut output file")
                else:
                    push_log(
                        f"🔍 Debug mode: Keeping existing cut output file {cut_output.name}"
                    )
            except Exception:
                pass

        # === DETERMINE CUTTING TIMESTAMPS ===
        if cut_mode == "keyframes":
            push_log(t("log_mode_keyframes"))
            # Extract keyframes and find nearest ones
            keyframes = get_keyframes(final_tmp)
            if keyframes:
                actual_start, actual_end = find_nearest_keyframes(
                    keyframes, start_sec, end_sec
                )
                push_log(
                    f"🎯 Keyframes timestamps: {actual_start:.3f}s → {actual_end:.3f}s"
                )
                push_log(f"📝 Original request: {start_sec}s → {end_sec}s")
                push_log(
                    f"⚖️ Offset: start={abs(actual_start - start_sec):.3f}s, end={abs(actual_end - end_sec):.3f}s"
                )
            else:
                # Fallback to exact timestamps if keyframe extraction fails
                actual_start, actual_end = float(start_sec), float(end_sec)
                push_log(t("log_keyframes_fallback"))
                push_log(
                    f"🎯 Using exact timestamps: {actual_start:.3f}s → {actual_end:.3f}s"
                )
        else:  # precise mode
            push_log(t("log_mode_precise"))
            actual_start, actual_end = float(start_sec), float(end_sec)
            push_log(f"🎯 Precise timestamps: {actual_start:.3f}s → {actual_end:.3f}s")

        duration = actual_end - actual_start

        # Process subtitles for cutting using dedicated utility function
        push_log("")
        processed_subtitle_files = []
        if subs_selected:
            processed_subtitle_files = process_subtitles_for_cutting(
                base_output=base_output,
                tmp_subfolder_dir=tmp_subfolder_dir,
                subtitle_languages=subs_selected,
                start_time=actual_start,
                duration=duration,
            )

        # STEP 3: MUX - Cut video and optionally add processed subtitles
        if processed_subtitle_files:
            push_log(
                f"📹 Step 3 - MUX: Cutting video and adding {len(processed_subtitle_files)} subtitle track(s)"
            )
        else:
            push_log("📹 Step 3 - MUX: Cutting video (no subtitles)")

        # Build video cutting command using dedicated utility function
        cmd_cut = build_cut_command(
            final_tmp=final_tmp,
            actual_start=actual_start,
            duration=duration,
            processed_subtitle_files=processed_subtitle_files,
            cut_output=cut_output,
            cut_ext=cut_ext,
        )

        # === EXECUTE FINAL CUTTING COMMAND ===
        # Execute ffmpeg cut command
        try:
            push_log(t("log_ffmpeg_execution", mode=cut_mode))
            ret_cut = run_cmd(
                cmd_cut,
                progress=progress_placeholder,
                status=status_placeholder,
                info=info_placeholder,
            )

            # Handle cancellation during cutting
            if ret_cut == -1:
                status_placeholder.info(t("cleaning_temp_files"))
                cleanup_tmp_files(base_output, tmp_subfolder_dir, "cutting")
                status_placeholder.success(t("cleanup_complete"))

                # Mark download as finished
                st.session_state.download_finished = True
                st.stop()

            if ret_cut != 0 or not cut_output.exists():
                status_placeholder.error(t("error_ffmpeg_cut_failed"))
                st.stop()
        except Exception as e:
            st.error(t("error_ffmpeg", error=e))
            st.stop()

        # Rename the cut file to the final name (without _cut suffix)
        # Keep the same extension as the cut output
        final_extension = cut_output.suffix  # .mkv, .mp4, etc.
        final_cut_name = tmp_subfolder_dir / f"{base_output}{final_extension}"

        push_log(f"📄 Final cut file: {final_cut_name.name}")

        if final_cut_name.exists():
            try:
                if should_remove_tmp_files():
                    final_cut_name.unlink()
                    push_log("🗑️ Removed existing final file")
                else:
                    push_log(
                        f"🔍 Debug mode: Keeping existing final file {final_cut_name.name}"
                    )
            except Exception:
                pass
        # In debug mode, copy instead of rename to preserve intermediate files
        if not should_remove_tmp_files():
            push_log(
                f"🔍 Debug mode: Copying cut file to preserve intermediate {cut_output.name}"
            )
            import shutil

            shutil.copy2(cut_output, final_cut_name)
            push_log("✅ Cut file copied to final name (intermediate preserved)")
        else:
            cut_output.rename(final_cut_name)
            push_log("✅ Cut file renamed to final name")

        # The renamed cut file becomes our final source
        final_source = final_cut_name

        # Measure cut file size
        if final_source.exists():
            cut_size = final_source.stat().st_size
            cut_size_mb = cut_size / (1024 * 1024)
            cut_size_str = f"{cut_size_mb:.2f}MiB"

            # Update metrics with cut file size
            if info_placeholder:
                update_download_metrics(
                    info_placeholder,
                    speed="✂️ Cut complete",
                    eta="",  # Clear ETA for completed cutting
                    size=cut_size_str,
                    show_fragments=False,
                )

            push_log(f"📊 Cut file size: {cut_size_str} (after cutting)")

        # Delete the original complete file to save space
        try:
            if final_tmp.exists() and final_tmp != final_source:
                if should_remove_tmp_files():
                    final_tmp.unlink()
                    push_log("🗑️ Removed original file after cutting")
                else:
                    push_log(f"🔍 Debug mode: Keeping original file {final_tmp.name}")
        except Exception as e:
            push_log(t("log_cleanup_warning", error=e))
    else:
        # No cutting, use the original downloaded file
        final_source = final_tmp  # === Cleanup + move

    # === METADATA CUSTOMIZATION ===
    # Customize metadata with user-provided title
    if filename and filename.strip():
        try:
            status_placeholder.info("📝 Customizing video metadata...")

            # Get original title for preservation in album field
            original_title = get_video_title(clean_url, cookies_part)

            # Apply custom metadata with user title
            if not customize_video_metadata(final_source, filename, original_title):
                push_log("⚠️ Metadata customization failed, using original metadata")
            else:
                # Measure file size after metadata customization
                if final_source.exists():
                    metadata_size = final_source.stat().st_size
                    metadata_size_mb = metadata_size / (1024 * 1024)
                    metadata_size_str = f"{metadata_size_mb:.2f}MiB"

                    # Update metrics with post-metadata size
                    if info_placeholder:
                        update_download_metrics(
                            info_placeholder,
                            speed="📝 Metadata added",
                            eta="",  # Clear ETA for completed metadata step
                            size=metadata_size_str,
                            show_fragments=False,
                        )

                    push_log(f"📊 File size after metadata: {metadata_size_str}")

        except Exception as e:
            push_log(f"⚠️ Error during metadata customization: {e}")

    # === SUBTITLE VERIFICATION & MANUAL EMBEDDING ===
    # Check if subtitles were requested and verify they are properly embedded
    if subs_selected:
        safe_push_log("🔍 Checking if all required subtitles are properly embedded...")

        if not check_required_subtitles_embedded(final_source, subs_selected):
            safe_push_log(
                "⚠️ Some or all required subtitles are missing, attempting manual embedding..."
            )

            # Find available subtitle files using optimized search
            subtitle_files_to_embed = find_subtitle_files_optimized(
                base_output=base_output,
                tmp_subfolder_dir=tmp_subfolder_dir,
                subtitle_languages=subs_selected,
                is_cut=do_cut,
            )

            # Attempt manual embedding
            if subtitle_files_to_embed:
                status_placeholder.info("🔧 Manually embedding subtitles...")

                if embed_subtitles_manually(final_source, subtitle_files_to_embed):
                    safe_push_log("✅ Subtitles successfully embedded manually")

                    # Clean up subtitle files after successful embedding
                    if should_remove_tmp_files():
                        for sub_file in subtitle_files_to_embed:
                            try:
                                sub_file.unlink()
                                safe_push_log(
                                    f"🗑️ Removed subtitle file: {sub_file.name}"
                                )
                            except Exception as e:
                                safe_push_log(
                                    f"⚠️ Could not remove subtitle file {sub_file.name}: {e}"
                                )
                    else:
                        safe_push_log(
                            "🔍 Debug mode: Keeping subtitle files for inspection"
                        )
                else:
                    safe_push_log("❌ Manual subtitle embedding failed")
            else:
                safe_push_log("⚠️ No subtitle files found for manual embedding")
        else:
            safe_push_log("✅ All required subtitles are already properly embedded")

    # === CLEANUP EXTRA FILES ===
    # Clean up temporary files now that cutting and metadata are complete
    cleanup_tmp_files(base_output, tmp_subfolder_dir, "subtitles")

    # Measure final processed file size before moving
    if final_source.exists():
        processed_size = final_source.stat().st_size
        processed_size_mb = processed_size / (1024 * 1024)
        push_log(f"📊 Processed file size: {processed_size_mb:.2f}MiB (before move)")

    try:
        final_moved = move_file(final_source, dest_dir)
        progress_placeholder.progress(100, text=t("status_completed"))

        # Get final file size for accurate display
        final_file_size = final_moved.stat().st_size
        final_size_mb = final_file_size / (1024 * 1024)
        final_size_str = f"{final_size_mb:.2f}MiB"

        # Update metrics with final accurate file size (no duration for now)
        if info_placeholder:
            update_download_metrics(
                info_placeholder,
                speed="✅ Complete",
                eta="",  # Explicitly clear ETA
                size=final_size_str,
                show_fragments=False,
                elapsed="",  # No duration for final display until we implement proper tracking
            )

        # Log the final file size for accuracy
        push_log(f"📊 Final file size: {final_size_str} (accurate measurement)")

        # Format full file path properly for display
        if video_subfolder == "/":
            display_path = f"Videos/{final_moved.name}"
        else:
            display_path = f"Videos/{video_subfolder}/{final_moved.name}"

        status_placeholder.success(t("status_file_ready", subfolder=display_path))
        st.toast(t("toast_download_completed"), icon="✅")
    except Exception:
        status_placeholder.warning(t("warning_file_not_found"))

    # Mark download as finished
    st.session_state.download_finished = True


# Application runs automatically when loaded by Streamlit

# Standard library imports
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Third-party imports
import streamlit as st

try:
    # Try relative imports first (when running as module or with Streamlit)
    from .translations import t, configure_language
    from .core import (
        build_base_ytdlp_command,
        build_cookies_params as core_build_cookies_params,
    )
    from .file_system_utils import (
        is_valid_cookie_file,
        is_valid_browser,
        sanitize_filename,
        list_subdirs_recursive,
        ensure_dir,
        should_remove_tmp_files,
        get_unique_video_folder_name_from_url,
    )
    from .display_utils import (
        fmt_hhmmss,
        parse_time_like,
        build_info_items,
        render_media_card,
    )
    from .medias_utils import (
        analyze_audio_formats,
        get_profiles_with_formats_id_to_download,
        get_available_formats,
        get_video_title,
        customize_video_metadata,
    )
    from .url_utils import (
        is_url_info_complet,
        sanitize_url,
        build_url_info,
    )
    from . import tmp_files
    from .subtitles_utils import (
        embed_subtitles_manually,
        process_subtitles_for_cutting,
        check_required_subtitles_embedded,
        find_subtitle_files_optimized,
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
    from .cut_utils import (
        get_keyframes,
        find_nearest_keyframes,
        build_cut_command,
    )
    from .sponsors_utils import (
        fetch_sponsorblock_segments,
        get_sponsorblock_segments,
        calculate_sponsor_overlap,
        get_sponsorblock_config,
        build_sponsorblock_params,
    )
    from .integrations_utils import post_download_actions
    from .status_utils import (
        create_initial_status,
        add_selected_format,
        update_format_status,
        mark_format_error,
        get_first_completed_format,
    )
except ImportError:
    # Fallback for direct execution from app directory
    from translations import t, configure_language
    from core import (
        build_base_ytdlp_command,
        build_cookies_params as core_build_cookies_params,
    )
    from file_system_utils import (
        is_valid_cookie_file,
        is_valid_browser,
        sanitize_filename,
        list_subdirs_recursive,
        ensure_dir,
        should_remove_tmp_files,
        get_unique_video_folder_name_from_url,
    )
    from display_utils import (
        fmt_hhmmss,
        parse_time_like,
        build_info_items,
        render_media_card,
    )
    from medias_utils import (
        analyze_audio_formats,
        get_profiles_with_formats_id_to_download,
        get_available_formats,
        get_video_title,
        customize_video_metadata,
    )
    from url_utils import (
        is_url_info_complet,
        sanitize_url,
        build_url_info,
    )
    import tmp_files
    from subtitles_utils import (
        embed_subtitles_manually,
        process_subtitles_for_cutting,
        check_required_subtitles_embedded,
        find_subtitle_files_optimized,
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
    from cut_utils import (
        get_keyframes,
        find_nearest_keyframes,
        build_cut_command,
    )
    from sponsors_utils import (
        fetch_sponsorblock_segments,
        get_sponsorblock_segments,
        calculate_sponsor_overlap,
        get_sponsorblock_config,
        build_sponsorblock_params,
    )
    from integrations_utils import post_download_actions
    from status_utils import (
        create_initial_status,
        add_selected_format,
        update_format_status,
        mark_format_error,
        get_first_completed_format,
    )

# Configuration import (must be after translations for configure_language)
from app.config import (
    get_settings,
    ensure_folders_exist,
    print_config_summary,
    get_default_subtitle_languages,
)

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
IN_CONTAINER = settings.IN_CONTAINER

# Get default subtitle languages based on audio preferences
SUBTITLES_CHOICES = get_default_subtitle_languages()

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


# === VIDEO FORMAT EXTRACTION AND ANALYSIS ===


def _process_quality_strategy(quality_strategy: str, url: str) -> None:
    """
    Process the selected quality strategy and update session state with optimal profiles.

    Args:
        quality_strategy: Selected strategy ("auto_best", "best_no_fallback", etc.)
        url: Video URL to analyze
    """
    if not url or not url.strip():
        return

    try:
        # Get tmp directory from session state (set during url_analysis)
        tmp_video_dir = st.session_state.get("tmp_video_dir")
        if not tmp_video_dir:
            # Reset profiles to empty to avoid showing stale data
            st.session_state.optimal_format_profiles = []
            st.session_state.chosen_format_profiles = []
            return

        # Check if we already have a cached download - skip format probing if so
        existing_video_tracks = tmp_files.find_video_tracks(tmp_video_dir)
        if existing_video_tracks:
            safe_push_log(f"✅ Found cached video: {existing_video_tracks[0].name}")
            safe_push_log("⚡ Skipping format probing - will reuse cached file")
            # Set minimal session state to allow download flow to continue
            st.session_state.optimal_format_profiles = []
            st.session_state.chosen_format_profiles = []
            return

        # Get url_info from session state (already loaded by url_analysis)
        url_info = st.session_state.get("url_info")
        if not url_info:
            # Reset profiles to empty to avoid showing stale data
            st.session_state.optimal_format_profiles = []
            st.session_state.chosen_format_profiles = []
            return

        # Get JSON path from session state
        json_path_str = st.session_state.get("url_info_path")
        if not json_path_str:
            # Reset profiles to empty to avoid showing stale data
            st.session_state.optimal_format_profiles = []
            st.session_state.chosen_format_profiles = []
            return

        json_path = Path(json_path_str)

        # Get optimal profiles using new strategy
        if quality_strategy in ["auto_best", "best_no_fallback", "choose_profile"]:
            # Load url_info to analyze audio tracks
            language_primary = settings.LANGUAGE_PRIMARY or "en"
            # Convert list to comma-separated string
            languages_secondaries = (
                ",".join(settings.LANGUAGES_SECONDARIES)
                if settings.LANGUAGES_SECONDARIES
                else ""
            )
            vo_first = settings.VO_FIRST

            # Analyze audio formats
            vo_lang, audio_formats, multiple_langs = analyze_audio_formats(
                url_info,
                language_primary=language_primary,
                languages_secondaries=languages_secondaries,
                vo_first=vo_first,
            )

            # Get optimal profiles
            optimal_format_profiles = get_profiles_with_formats_id_to_download(
                json_path, multiple_langs, audio_formats
            )

            st.session_state.optimal_format_profiles = optimal_format_profiles

            # profiles_to_try = [{'format_id': '399+251', 'ext': 'webm', 'height': 1080, 'vcodec': 'av01.0.08M.08', 'protocol': 'https+https'}, {'format_id': '248+251', 'ext': 'webm', 'height': 1080, 'vcodec': 'vp9', 'protocol': 'https+https'}]

            # Set chosen profiles based on strategy
            if quality_strategy == "auto_best":
                st.session_state.chosen_format_profiles = optimal_format_profiles
            elif quality_strategy == "best_no_fallback":
                # Only the first (best) profile
                st.session_state.chosen_format_profiles = (
                    optimal_format_profiles[:1] if optimal_format_profiles else []
                )
            # For choose_profile, chosen_format_profiles will be set by user selection

        elif quality_strategy == "choose_available":
            # Load all available formats for selection
            available_formats = get_available_formats(url_info)
            st.session_state.available_formats_list = available_formats

    except Exception as e:
        safe_push_log(f"❌ Error processing quality strategy: {str(e)[:100]}...")


def _display_strategy_content(quality_strategy: str, url: str) -> None:
    """
    Display content specific to the selected quality strategy.

    Args:
        quality_strategy: Selected strategy
        url: Video URL
    """
    st.markdown("---")

    if quality_strategy == "auto_best":
        st.info(t("quality_auto_best_desc"))

        optimal_profiles = st.session_state.get("optimal_format_profiles", [])
        if optimal_profiles:
            st.success(t("quality_profiles_generated", count=len(optimal_profiles)))

            with st.expander(t("quality_profiles_list_title"), expanded=True):
                for i, profile in enumerate(optimal_profiles, 1):
                    height = profile.get("height", "?")
                    vcodec = profile.get("vcodec", "unknown")
                    ext = profile.get("ext", "unknown")
                    format_id = profile.get("format_id", "unknown")

                    st.markdown(f"**{i}. {height}p ({vcodec}) - {ext.upper()}**")
                    st.code(f"Format ID: {format_id}", language="text")
        else:
            st.warning(t("quality_no_profiles_warning"))

    elif quality_strategy == "best_no_fallback":
        st.warning(t("quality_best_no_fallback_desc"))

        # Show quality downgrade setting
        st.checkbox(
            t("quality_refuse_downgrade"),
            value=not settings.QUALITY_DOWNGRADE,
            help=t("quality_refuse_downgrade_help"),
            key="refuse_quality_downgrade_best",
        )

        optimal_profiles = st.session_state.get("optimal_format_profiles", [])
        if optimal_profiles:
            best_profile = optimal_profiles[0]
            height = best_profile.get("height", "?")
            vcodec = best_profile.get("vcodec", "unknown")
            ext = best_profile.get("ext", "unknown")
            format_id = best_profile.get("format_id", "unknown")

            profile_str = f"{height}p ({vcodec}) - {ext.upper()}"
            st.success(t("quality_selected_profile", profile=profile_str))
            st.code(f"Format ID: {format_id}", language="text")
        else:
            st.warning(t("quality_best_profile_not_available"))

    elif quality_strategy == "choose_profile":
        st.info(t("quality_choose_profile_desc"))

        optimal_profiles = st.session_state.get("optimal_format_profiles", [])
        if optimal_profiles:
            profile_options = []
            for i, profile in enumerate(optimal_profiles):
                height = profile.get("height", "?")
                vcodec = profile.get("vcodec", "unknown")
                ext = profile.get("ext", "unknown")
                label = f"{height}p ({vcodec}) - {ext.upper()}"
                profile_options.append(label)

            selected_index = st.selectbox(
                t("quality_select_profile_prompt"),
                options=range(len(profile_options)),
                format_func=lambda x: profile_options[x],
                key="selected_profile_index",
            )

            # Update chosen profiles based on selection
            if selected_index is not None:
                st.session_state.chosen_format_profiles = [
                    optimal_profiles[selected_index]
                ]

                # Show selected profile details
                selected_profile = optimal_profiles[selected_index]
                format_id = selected_profile.get("format_id", "unknown")
                st.success(
                    t("quality_selected", profile=profile_options[selected_index])
                )
                st.code(f"Format ID: {format_id}", language="text")
        else:
            st.warning(t("quality_no_profiles_selection"))

    elif quality_strategy == "choose_available":
        st.info(t("quality_choose_available_desc"))
        st.warning(t("quality_choose_available_warning"))

        available_formats = st.session_state.get("available_formats_list", [])
        if available_formats:
            format_options = [t("quality_format_auto_option")]
            for fmt in available_formats:
                format_options.append(f"{fmt['description']} - {fmt['format_id']}")

            selected_format = st.selectbox(
                t("quality_select_format_prompt"),
                options=format_options,
                key="selected_available_format",
            )

            if selected_format != t("quality_format_auto_option"):
                # Extract format_id from selection
                format_id = selected_format.split(" - ")[-1]
                st.success(t("quality_selected_format", format=selected_format))

                # Create a profile-like dict for consistency
                for fmt in available_formats:
                    if fmt["format_id"] == format_id:
                        chosen_profile = {
                            "format_id": format_id,
                            "height": fmt["height"],
                            "vcodec": fmt["vcodec"],
                            "ext": fmt["ext"],
                            "label": f"Manual: {fmt['description']}",
                        }
                        st.session_state.chosen_format_profiles = [chosen_profile]
                        break
            else:
                # Fallback to auto mode
                st.session_state.chosen_format_profiles = st.session_state.get(
                    "optimal_format_profiles", []
                )
        else:
            st.warning(t("quality_no_formats_selection"))


def _get_optimal_profiles_from_json(url: str) -> List[Dict]:
    """
    Get optimal download profiles using get_profiles_with_formats_id_to_download().

    This is a simple wrapper that calls get_profiles_with_formats_id_to_download() which now
    returns complete profiles with all necessary fields (label, name, container, etc.).

    Args:
        url: Video URL to get profiles for

    Returns:
        List of complete profile dicts ready for download, or empty list if error
    """
    try:
        # Get tmp directory and url_info from session state (set during url_analysis)
        tmp_video_dir = st.session_state.get("tmp_video_dir")
        url_info = st.session_state.get("url_info")
        json_path_str = st.session_state.get("url_info_path")

        if not tmp_video_dir or not url_info or not json_path_str:
            safe_push_log("⚠️ Video info not initialized. Analyze URL first.")
            return []

        json_path = Path(json_path_str)
        if not json_path.exists():
            safe_push_log("⚠️ url_info.json not found, cannot use profile strategy")
            return []

        # Get language preferences from settings
        language_primary = settings.LANGUAGE_PRIMARY or "en"
        # Convert list to comma-separated string
        languages_secondaries = (
            ",".join(settings.LANGUAGES_SECONDARIES)
            if settings.LANGUAGES_SECONDARIES
            else ""
        )
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

        # Get optimal profiles - now returns complete profiles with all fields
        safe_push_log("🎯 Selecting optimal video formats (AV1/VP9 priority)...")
        optimal_profiles = get_profiles_with_formats_id_to_download(
            str(json_path), multiple_langs, audio_formats
        )

        if not optimal_profiles:
            safe_push_log("❌ No optimal profiles returned")
            return []

        log_title(f"✅ Found {len(optimal_profiles)} optimal profile(s)")

        # Log profile details
        for idx, profile in enumerate(optimal_profiles, 1):
            safe_push_log("")
            safe_push_log(f"📦 Profile {idx}: {profile.get('label', 'Unknown')}")
            safe_push_log(f"   🆔 Format ID: {profile.get('format_id', '')}")
            safe_push_log(f"   🎬 Video Codec: {profile.get('vcodec', 'unknown')}")
            safe_push_log(f"   📐 Resolution: {profile.get('height', 0)}p")
            safe_push_log(f"   📦 Extension: {profile.get('ext', 'unknown')}")
            safe_push_log(
                f"   📁 Output Container: {profile.get('container', 'mkv').upper()}"
            )
            safe_push_log(f"   🌐 Protocol: {profile.get('protocol', 'https')}")

        log_title(
            f"🎯 Will try {len(optimal_profiles)} profile(s) in order (best codec first)"
        )
        return optimal_profiles

    except FileNotFoundError:
        safe_push_log("⚠️ url_info.json not found for profile strategy")
        return []
    except Exception as e:
        safe_push_log(f"⚠️ Error in profile strategy: {e}")
        import traceback

        safe_push_log(f"   Traceback: {traceback.format_exc()}")
        return []


def smart_download_with_profiles(
    base_output: str,
    tmp_video_dir: Path,
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

    # Use NEW STRATEGY: get profiles from quality strategy session state
    log_title("🎯 Using quality strategy profiles...")

    # Get profiles from session state (set by quality strategy)
    chosen_profiles = st.session_state.get("chosen_format_profiles", [])
    quality_strategy = st.session_state.get("download_quality_strategy", "auto_best")

    if chosen_profiles:
        profiles_to_try = chosen_profiles
        safe_push_log(
            f"✅ Using {len(profiles_to_try)} profiles from {quality_strategy} strategy"
        )
    else:
        # Fallback to old method if no strategy profiles available
        safe_push_log("⚠️ No strategy profiles found, using fallback method")
        profiles_to_try = _get_optimal_profiles_from_json(url)

    if not profiles_to_try:
        error_msg = "No profiles available for download. Please select a quality strategy first."
        safe_push_log(f"❌ {error_msg}")
        return 1, error_msg

    # Update download mode and refuse_quality_downgrade based on strategy
    if quality_strategy == "auto_best":
        download_mode = "auto"
        refuse_quality_downgrade = False
    elif quality_strategy == "best_no_fallback":
        download_mode = "forced"
        refuse_quality_downgrade = st.session_state.get(
            "refuse_quality_downgrade_best", not settings.QUALITY_DOWNGRADE
        )
    elif quality_strategy in ["choose_profile", "choose_available"]:
        download_mode = "forced"
        refuse_quality_downgrade = False  # User made specific choice

    safe_push_log("")

    # Execute download attempts
    return _execute_profile_downloads(
        profiles_to_try,
        base_output,
        tmp_video_dir,
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
    tmp_video_dir: Path,
    embed_chapters: bool,
    embed_subs: bool,
    ytdlp_custom_args: str,
    subs_selected: List[str],
    do_cut: bool,
    sb_choice: str,
) -> List[str]:
    """Build ytdlp command for a specific profile."""
    # Get format string from format_id (single source of truth)
    format_string = profile.get("format_id", "")

    # Create quality strategy
    quality_strategy = {
        "format": format_string,
        "format_sort": "res,fps,+size,br",  # Standard sort
        "extra_args": [],
    }

    # Use profile's container preference (always MKV from get_profiles_with_formats_id_to_download)
    profile_container = profile.get("container", "mkv").lower()
    profile_force_mp4 = profile_container == "mp4"

    # Build base command
    cmd_base = build_base_ytdlp_command(
        base_output,
        tmp_video_dir,
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

    # Extract data directly from unified profile structure
    video_codec = profile.get("vcodec", "").lower()
    format_id = profile.get("format_id", "")
    height = profile.get("height", 0)

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
    tmp_video_dir: Path,
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
    safe_push_log(f"profiles_to_try: {profiles_to_try}")

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
            tmp_video_dir,
            embed_chapters,
            embed_subs,
            ytdlp_custom_args,
            subs_selected,
            do_cut,
            sb_choice,
        )

        # Store current profile for error diagnostics
        st.session_state["current_attempting_profile"] = profile["label"]

        # Update status.json - mark format as "downloading"
        format_id = profile.get("format_id", "unknown")
        filesize_approx = profile.get("filesize_approx", 0)
        add_selected_format(
            tmp_video_dir=tmp_video_dir,
            video_format=format_id,
            subtitles=[f"subtitles.{lang}.srt" for lang in subs_selected],
            filesize_approx=filesize_approx,
        )

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
            safe_push_log(f"🎯 Format ID: {profile.get('format_id', 'unknown')}")

            # Show codec details from unified profile structure
            vcodec = profile.get("vcodec", "unknown")
            height = profile.get("height", 0)
            ext = profile.get("ext", "unknown")
            safe_push_log(f"🎬 Video codec: {vcodec}")
            safe_push_log(f"📐 Resolution: {height}p")
            safe_push_log(f"📦 Container: {ext}")

            log_title(
                f"📁 Container format: {profile.get('container', 'unknown').upper()}"
            )

            # Store format_id in session state for file renaming
            st.session_state["downloaded_format_id"] = profile.get(
                "format_id", "unknown"
            )

            return 0, ""

        # Mark format as error in status.json
        format_id = profile.get("format_id", "unknown")
        mark_format_error(
            tmp_video_dir=tmp_video_dir,
            video_format=format_id,
            error_message="Download failed - all clients exhausted",
        )

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


def init_url_workspace(
    clean_url: str,
    json_output_path: Path,
    video_tmp_dir: Path,
) -> Optional[Dict]:
    """
    Initialize workspace for a new URL by fetching video info and creating status files.

    This function:
    1. Builds cookies parameters from config
    2. Fetches video/playlist info from yt-dlp
    3. Creates url_info.json with integrity checks
    4. Creates initial status.json for download tracking
    5. Updates session state with the new info

    Args:
        clean_url: Sanitized video URL
        json_output_path: Path where url_info.json will be saved
        video_tmp_dir: Temporary directory for this video

    Returns:
        Dict with video/playlist information or error dict
    """
    # Build cookies parameters from config (important to avoid bot detection)
    # Use config-based cookies since session_state may not be available yet
    cookies_params = build_cookies_params_from_config()

    # Download and build url_info with integrity checks
    info = build_url_info(
        clean_url=clean_url,
        json_output_path=json_output_path,
        cookies_params=cookies_params,
        youtube_cookies_file_path=YOUTUBE_COOKIES_FILE_PATH,
        cookies_from_browser=COOKIES_FROM_BROWSER,
    )

    # Store in session state for global access
    st.session_state["url_info"] = info
    st.session_state["url_info_path"] = str(json_output_path)

    # Create initial status.json file
    if info and "error" not in info:
        video_id = info.get("id", "unknown")
        title = info.get("title", "Unknown")
        content_type = "playlist" if info.get("_type") == "playlist" else "video"

        create_initial_status(
            url=clean_url,
            video_id=video_id,
            title=title,
            content_type=content_type,
            tmp_video_dir=video_tmp_dir,
        )

    return info


def url_analysis(url: str) -> Optional[Dict]:
    """
    Analyze URL and fetch comprehensive video/playlist information using yt-dlp.
    Always initializes session state variables and checks for existing url_info.json.

    This function:
    1. Sanitizes URL and creates unique tmp folder
    2. Sets all session state variables (tmp_video_dir, unique_folder_name, etc.)
    3. Checks if url_info.json exists with good integrity
    4. If exists: loads it and returns
    5. If not: fetches from yt-dlp via init_url_workspace()

    Args:
        url: Video or playlist URL to analyze

    Returns:
        Dict with video/playlist information or None if error
    """
    if not url or not url.strip():
        return None

    try:
        # Sanitize URL and create unique folder for this video
        clean_url = sanitize_url(url)
        unique_folder_name = get_unique_video_folder_name_from_url(clean_url)
        video_tmp_dir = TMP_DOWNLOAD_FOLDER / unique_folder_name

        # Check if NEW_DOWNLOAD_WITHOUT_TMP_FILES is enabled
        if settings.NEW_DOWNLOAD_WITHOUT_TMP_FILES and video_tmp_dir.exists():
            safe_push_log(f"🗑️ Removing tmp files for fresh download: {video_tmp_dir}")
            import shutil

            shutil.rmtree(video_tmp_dir)

        ensure_dir(video_tmp_dir)

        # ALWAYS store in session state for reuse across the application
        st.session_state["tmp_video_dir"] = video_tmp_dir
        st.session_state["unique_folder_name"] = unique_folder_name
        st.session_state["current_video_url"] = clean_url

        # Prepare output path for JSON file in the unique video folder
        json_output_path = video_tmp_dir / "url_info.json"

        # === CHECK IF URL_INFO.JSON ALREADY EXISTS WITH GOOD INTEGRITY ===
        url_info_is_complet, existing_info = is_url_info_complet(json_output_path)

        if url_info_is_complet and existing_info:
            # Store in session state and return immediately (no download needed)
            st.session_state["url_info"] = existing_info
            st.session_state["url_info_path"] = str(json_output_path)
            return existing_info
        else:
            # Initialize workspace and fetch video info
            return init_url_workspace(clean_url, json_output_path, video_tmp_dir)

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
    # media_id = url_info.get("id")

    # Determine platform icon/emoji
    platform_emoji = "🎬"
    platform_name = "Video"
    if "youtube" in extractor or "youtube" in extractor_key:
        platform_emoji = "▶️"  # YouTube play button (red)
        platform_name = "YouTube"
    elif "vimeo" in extractor:
        platform_emoji = "🎞️"  # Vimeo film
        platform_name = "Vimeo"
    elif "dailymotion" in extractor:
        platform_emoji = "🎥"  # Dailymotion camera
        platform_name = "Dailymotion"
    elif "instagram" in extractor:
        platform_emoji = "📸"  # Instagram camera
        platform_name = "Instagram"

    # Determine if it's a playlist or single video
    is_playlist = url_info.get("_type") == "playlist" or "entries" in url_info

    if is_playlist:
        # ===== PLAYLIST INFORMATION =====
        title = url_info.get("title", "Unknown Playlist")
        uploader = url_info.get("uploader", url_info.get("channel", ""))

        # Get playlist count
        entries_count = url_info.get("playlist_count") or len(
            url_info.get("entries", [])
        )

        # Get first video title if available
        first_video_title = None
        entries = url_info.get("entries", [])
        if entries and isinstance(entries[0], dict):
            first_video_title = entries[0].get("title")

        # Build info items using helper
        info_items = build_info_items(
            platform_emoji=platform_emoji,
            platform_name=platform_name,
            media_type="Playlist",
            uploader=uploader,
            entries_count=entries_count,
            first_video_title=first_video_title,
        )

        # Render card
        st.html(render_media_card(title, info_items))

    elif url_info.get("_type") == "video" or "duration" in url_info:
        # ===== SINGLE VIDEO INFORMATION =====
        title = url_info.get("title", "Unknown Video")
        uploader = url_info.get("uploader", url_info.get("channel", ""))
        duration = url_info.get("duration", 0)
        view_count = url_info.get("view_count")
        like_count = url_info.get("like_count")

        # Build info items using helper
        info_items = build_info_items(
            platform_emoji=platform_emoji,
            platform_name=platform_name,
            media_type="Video",
            uploader=uploader,
            duration=duration,
            view_count=view_count,
            like_count=like_count,
        )

        # Render card
        st.html(render_media_card(title, info_items))

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
    Get the path to the saved URL info JSON file from session state.

    Returns:
        Path to url_info.json or None if not available
    """
    path_str = st.session_state.get("url_info_path", None)
    if path_str and Path(path_str).exists():
        return Path(path_str)
    return None


def get_tmp_video_dir() -> Optional[Path]:
    """
    Get the unique temporary directory from session state.
    This directory is created during url_analysis() and stored in session.

    Returns:
        Path to the unique temporary directory or None if not initialized
    """
    return st.session_state.get("tmp_video_dir")


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


def build_cookies_params_from_config() -> List[str]:
    """
    Builds cookie parameters from configuration settings (for early URL analysis).
    Used before session_state is available.

    Returns:
        list: yt-dlp parameters for cookies
    """
    # Try cookies file first (most common for Docker/server setup)
    if YOUTUBE_COOKIES_FILE_PATH and Path(YOUTUBE_COOKIES_FILE_PATH).exists():
        return core_build_cookies_params(
            cookies_method="file", cookies_file_path=YOUTUBE_COOKIES_FILE_PATH
        )

    # Try browser cookies if configured
    if COOKIES_FROM_BROWSER and is_valid_browser(COOKIES_FROM_BROWSER):
        return core_build_cookies_params(
            cookies_method="browser",
            browser_select=COOKIES_FROM_BROWSER,
            browser_profile="",
        )

    # No cookies available
    return []


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

# Analyze URL and display information
if url and url.strip():
    with st.spinner(t("url_analysis_spinner")):
        url_info = url_analysis(url)
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
# Default subtitles are determined by audio language preferences (LANGUAGE_PRIMARY, LANGUAGES_SECONDARIES)
subs_selected = st.multiselect(
    t("subtitles_to_embed"),
    options=SUBTITLES_CHOICES,
    default=SUBTITLES_CHOICES,  # Pre-select subtitles based on audio preferences
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

# Video quality selection with new strategy
with st.expander(f"{t('quality_title')}", expanded=False):
    # Initialize session state for quality management
    if "optimal_format_profiles" not in st.session_state:
        st.session_state.optimal_format_profiles = []
    if "chosen_format_profiles" not in st.session_state:
        st.session_state.chosen_format_profiles = []
    if "available_formats_list" not in st.session_state:
        st.session_state.available_formats_list = []

    # st.info(
    #     "🏆 **Smart quality selection** - Choose your strategy for optimal video quality and compatibility."
    # )

    # Determine default strategy based on QUALITY_DOWNGRADE setting
    # If QUALITY_DOWNGRADE=false, default to "best_no_fallback" (no fallback on failure)
    # If QUALITY_DOWNGRADE=true, default to "auto_best" (try multiple profiles)
    default_strategy_index = 0 if settings.QUALITY_DOWNGRADE else 1

    # Quality strategy selection
    quality_strategy = st.radio(
        t("quality_strategy_prompt"),
        options=["auto_best", "best_no_fallback", "choose_profile", "choose_available"],
        format_func=lambda x: {
            "auto_best": t("quality_strategy_auto_best"),
            "best_no_fallback": t("quality_strategy_best_no_fallback"),
            "choose_profile": t("quality_strategy_choose_profile"),
            "choose_available": t("quality_strategy_choose_available"),
        }[x],
        index=default_strategy_index,
        help=t("quality_strategy_help"),
        key="quality_strategy",
        horizontal=False,
    )

    # Process strategy selection and update profiles
    if url and url.strip():
        clean_url = sanitize_url(url)
        _process_quality_strategy(quality_strategy, clean_url)

    # Display strategy-specific content
    _display_strategy_content(quality_strategy, url)

    # Store final configuration in session state for download
    st.session_state["download_quality_strategy"] = quality_strategy


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

    # Store current REMOVE_TMP_FILES_AFTER_DOWNLOAD setting in session state
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

    # If only end is specified, start from the beginning (0)
    if start_sec is None and end_sec is not None:
        start_sec = 0
        push_log("⏱️ Start time not specified, cutting from beginning (0s)")

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

    # Check if video already exists in destination (safety check)
    if filename:
        # Check all common video extensions
        existing_files = []
        for ext in [".mkv", ".mp4", ".webm", ".avi", ".mov"]:
            potential_file = dest_dir / f"{filename}{ext}"
            if potential_file.exists():
                existing_files.append(potential_file)

        if existing_files and not settings.ALLOW_OVERWRITE_EXISTING_VIDEO:
            # File exists and overwrite is not allowed
            log_title("⚠️ VIDEO ALREADY EXISTS - SKIPPING DOWNLOAD")
            push_log("")
            push_log(f"📁 Existing file: {existing_files[0].name}")
            push_log(
                f"📊 File size: {existing_files[0].stat().st_size / (1024 * 1024):.2f}MiB"
            )
            push_log("")
            push_log("🛡️ Protection active: ALLOW_OVERWRITE_EXISTING_VIDEO=false")
            push_log(
                "ℹ️  To allow overwrites, set ALLOW_OVERWRITE_EXISTING_VIDEO=true in .env"
            )
            push_log("")
            push_log("✅ Skipping download to protect existing file")

            status_placeholder.warning(
                f"⚠️ File already exists: {existing_files[0].name}\n\n"
                "Download skipped to protect existing file.\n"
                "To allow overwrites, set ALLOW_OVERWRITE_EXISTING_VIDEO=true"
            )

            # Mark download as finished
            st.session_state.download_finished = True
            st.stop()  # Stop execution here

    # build bases
    clean_url = sanitize_url(url)

    # Get unique temporary folder from session state (set during url_analysis)
    # This ensures each video has its own isolated workspace
    tmp_video_dir = st.session_state.get("tmp_video_dir")
    unique_folder_name = st.session_state.get("unique_folder_name", "unknown")

    if not tmp_video_dir:
        st.error("❌ Video workspace not initialized. Please re-enter the URL.")
        st.stop()

    # All temporary files are written to the root of the unique video folder
    # The video_subfolder is only used when copying the final file to destination
    push_log(f"🔧 Unique video workspace: {unique_folder_name}")
    push_log(t("log_temp_download_folder", folder=tmp_video_dir))

    # Setup cookies for yt-dlp operations
    cookies_part = build_cookies_params()

    # If no filename provided, get video title
    if filename is None:
        filename = get_video_title(clean_url, cookies_part)

    base_output = filename  # without extension

    # Log download strategy
    push_log("")
    log_title("� Download Strategy")
    push_log("  1️⃣  Download with readable name (yt-dlp compatibility)")
    push_log("  2️⃣  Rename to generic names (resilience & independence)")
    push_log("  3️⃣  Skip if generic files exist (resume support)")
    push_log("")
    push_log(f"📝 Target filename: {base_output}")

    # Check if a completed download already exists (status.json verification)
    # Priority: 1) Check status.json for completed format 2) Fallback to generic file search
    existing_generic_file = None
    completed_format_id = get_first_completed_format(tmp_video_dir)

    if completed_format_id:
        # We have a completed format in status.json - find the corresponding file
        log_title("✅ Found completed download in status")
        push_log(f"  🎯 Format ID: {completed_format_id}")

        # Try to find the video file with this format ID
        existing_video_tracks = tmp_files.find_video_tracks(tmp_video_dir)
        for track in existing_video_tracks:
            track_format_id = tmp_files.extract_format_id_from_filename(track.name)
            if track_format_id and track_format_id in completed_format_id:
                existing_generic_file = track
                push_log(f"  📦 Found file: {existing_generic_file.name}")
                push_log(
                    f"  📊 Size: {existing_generic_file.stat().st_size / (1024*1024):.2f}MiB"
                )
                push_log("  🔄 Skipping download, reusing completed file")
                push_log("")
                break

        if not existing_generic_file:
            push_log("  ⚠️ Status shows completed but file not found, will re-download")
    else:
        # Fallback: check for any generic video file (backward compatibility)
        existing_video_tracks = tmp_files.find_video_tracks(tmp_video_dir)
        existing_generic_file = (
            existing_video_tracks[0] if existing_video_tracks else None
        )

        if existing_generic_file:
            log_title("✅ Found cached download (legacy detection)")
            push_log(f"  📦 Existing file: {existing_generic_file.name}")
            push_log("  🔄 Skipping download, reusing cached file")
            push_log("  ℹ️  Note: No status.json entry for this file, consider updating")
            push_log("")

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
    # settings = get_settings()
    push_log("🤖 Using new dynamic strategy with optimal format selection")

    # === NEW STRATEGY: Always use dynamic format selection ===
    # The new strategy dynamically selects the best AV1/VP9 formats available
    push_log("🤖 Using new dynamic strategy with optimal format selection")
    quality_strategy_to_use = "auto_profiles"  # Always use the new strategy
    format_spec = "bv*+ba/b"  # Placeholder - actual formats determined by get_profiles_with_formats_id_to_download()

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
            tmp_video_dir,
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

    # Check if we can skip download by reusing existing generic file
    if existing_generic_file:
        status_placeholder.success(t("status_reusing_existing_file"))
        ret_dl = 0  # Success code
        push_log("⚡ Skipped download - using cached file")
    else:
        status_placeholder.info(t("status_downloading_simple"))

        # Use intelligent fallback with retry strategies
        # NEW STRATEGY: Always use dynamic profile selection
        if quality_strategy_to_use == "auto_profiles":
            push_log("🤖 Auto mode: Will try all profiles in quality order")
            ret_dl, error_msg = smart_download_with_profiles(
                base_output,
                tmp_video_dir,
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
            status_placeholder.info("Download cancelled")
            # Note: Temporary files are kept for resilience
            # Manual cleanup can be done via REMOVE_TMP_FILES setting

            # Mark download as finished
            st.session_state.download_finished = True
            st.stop()

    # Search for the final file in TMP subfolder
    # Priority: 1) Generic file (from cache/previous run) 2) Fresh download with original name
    final_tmp = None

    # First check if we already found a generic file earlier (cache hit)
    if existing_generic_file:
        final_tmp = existing_generic_file
        safe_push_log(f"✓ Using cached file: {final_tmp.name}")
    else:
        # New download - look for file with original name and rename to generic
        safe_push_log("")
        log_title("📦 Organizing downloaded files")

        search_extensions = [".mkv", ".mp4", ".webm"]
        downloaded_file = None

        for ext in search_extensions:
            p = tmp_video_dir / f"{base_output}{ext}"
            if p.exists():
                downloaded_file = p
                safe_push_log(f"  📄 Found: {p.name}")
                break

        if not downloaded_file:
            status_placeholder.error(t("error_download_failed"))
            st.stop()

        # Get format_id from session (stored during download)
        format_id = st.session_state.get("downloaded_format_id", "unknown")
        safe_push_log(f"  🔍 Format ID from session: {format_id}")

        # Rename to generic filename with format ID: video-{FORMAT_ID}.{ext}
        generic_name = tmp_files.get_video_track_path(
            tmp_video_dir, format_id, downloaded_file.suffix.lstrip(".")
        )
        safe_push_log(f"  🔍 Target generic name: {generic_name.name}")

        # Rename video file
        try:
            if generic_name.exists():
                if should_remove_tmp_files():
                    generic_name.unlink()
                    safe_push_log(f"  🗑️ Removed existing: {generic_name.name}")
                else:
                    safe_push_log(
                        f"  ⚠️ Generic file already exists: {generic_name.name}"
                    )

            safe_push_log(f"  🔄 Renaming: {downloaded_file} → {generic_name}")
            downloaded_file.rename(generic_name)
            safe_push_log(
                f"  ✅ Video renamed: {downloaded_file.name} → {generic_name.name}"
            )

            # Verify the file exists after rename
            if generic_name.exists():
                size_mb = generic_name.stat().st_size / (1024 * 1024)
                safe_push_log(
                    f"  ✅ Verified: {generic_name.name} exists ({size_mb:.1f} MiB)"
                )
            else:
                safe_push_log(
                    f"  ❌ ERROR: {generic_name.name} doesn't exist after rename!"
                )

            final_tmp = generic_name
        except Exception as e:
            safe_push_log(f"  ⚠️ Could not rename video: {str(e)}")
            final_tmp = downloaded_file

        # Rename subtitle files to generic names
        if subs_selected:
            safe_push_log("")
            safe_push_log("  📝 Organizing subtitle files...")
            for lang in subs_selected:
                original_sub = tmp_video_dir / f"{base_output}.{lang}.srt"
                if original_sub.exists():
                    generic_sub = tmp_files.get_subtitle_path(
                        tmp_video_dir, lang, is_cut=False
                    )
                    try:
                        original_sub.rename(generic_sub)
                        safe_push_log(
                            f"    ✅ {lang}: {original_sub.name} → {generic_sub.name}"
                        )
                    except Exception as e:
                        safe_push_log(f"    ⚠️ Could not rename {lang}: {str(e)}")
                else:
                    safe_push_log(f"    ℹ️  No {lang} subtitle downloaded")

        safe_push_log("")
        log_title("✅ File organization complete")
        safe_push_log(f"  📦 Video: {final_tmp.name}")
        if subs_selected:
            safe_push_log("  📝 Subtitles: subtitles.{lang}.srt format")
        safe_push_log("  💡 Files are now independent of video title")
        safe_push_log("")

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

        # Use generic name for cut output: final.{ext}
        cut_output = tmp_files.get_final_path(tmp_video_dir, cut_ext.lstrip("."))

        if cut_output.exists():
            try:
                if should_remove_tmp_files():
                    cut_output.unlink()
                    push_log("🗑️ Removed existing final file")
                else:
                    push_log(
                        f"🔍 Debug mode: Keeping existing final file {cut_output.name}"
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
                tmp_video_dir=tmp_video_dir,
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
                status_placeholder.info("Cutting cancelled")
                # Note: Temporary files are kept for resilience and cache reuse
                # Manual cleanup can be done via REMOVE_TMP_FILES setting

                # Mark download as finished
                st.session_state.download_finished = True
                st.stop()

            if ret_cut != 0 or not cut_output.exists():
                status_placeholder.error(t("error_ffmpeg_cut_failed"))
                st.stop()
        except Exception as e:
            st.error(t("error_ffmpeg", error=e))
            st.stop()

        # Cut output is already named correctly (final.{ext})
        # No need to rename - it's already the final file with generic name
        push_log(f"✅ Cut complete: {cut_output.name}")

        # The cut file is our final source (already correctly named)
        final_source = cut_output

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
        # No cutting - copy downloaded video to final.{ext} for consistency
        # Keep the original video-{FORMAT_ID}.{ext} for cache reuse
        push_log("📦 No cutting requested, preparing final file...")

        final_path = tmp_files.get_final_path(
            tmp_video_dir, final_tmp.suffix.lstrip(".")
        )

        if final_tmp != final_path:
            try:
                # Remove existing final file if it exists
                if final_path.exists():
                    if should_remove_tmp_files():
                        final_path.unlink()
                        push_log("🗑️ Removed existing final file")
                    else:
                        push_log("🔍 Debug mode: Overwriting existing final file")

                # Copy (not rename!) to final name, keeping original for cache
                shutil.copy2(str(final_tmp), str(final_path))
                push_log(f"� Copied: {final_tmp.name} → {final_path.name}")
                push_log(f"💾 Kept original {final_tmp.name} for cache reuse")
                final_source = final_path
            except Exception as e:
                push_log(f"⚠️ Could not copy to final, using original: {str(e)}")
                final_source = final_tmp
        else:
            # Already has final name
            final_source = final_tmp
            push_log(
                f"✓ File already has final name: {final_source.name}"
            )  # === Cleanup + move

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
                tmp_video_dir=tmp_video_dir,
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

    # === NO AUTOMATIC CLEANUP ===
    # Temporary files are KEPT for resilience and cache reuse
    # - video-{FORMAT_ID}.{ext} can be reused for future downloads
    # - subtitles.{lang}.srt can be reused
    # - final.{ext} can be reused for resume scenarios
    # Manual cleanup: set REMOVE_TMP_FILES=true in .env or delete tmp/ folder

    # Measure final processed file size before copying
    if final_source.exists():
        processed_size = final_source.stat().st_size
        processed_size_mb = processed_size / (1024 * 1024)
        push_log(f"📊 Processed file size: {processed_size_mb:.2f}MiB (before copy)")

    try:
        # Build final destination path with intended filename
        final_ext = final_source.suffix
        final_destination = dest_dir / f"{base_output}{final_ext}"

        # Copy file with intended name
        shutil.copy2(str(final_source), str(final_destination))
        push_log(f"✅ Copied to: {final_destination.name}")
        push_log(f"📋 Original kept in: {final_source.parent.name}/{final_source.name}")

        final_copied = final_destination
        progress_placeholder.progress(100, text=t("status_completed"))

        # Get final file size for accurate display
        final_file_size = final_copied.stat().st_size
        final_size_mb = final_file_size / (1024 * 1024)
        final_size_str = f"{final_size_mb:.2f}MiB"

        # Update status.json - verify file and mark as completed or incomplete
        format_id = st.session_state.get("downloaded_format_id", "unknown")
        update_format_status(
            tmp_video_dir=tmp_video_dir,
            video_format=format_id,
            final_file=final_source,  # Verify the file in tmp (before copy)
        )

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

        # Trigger media-server integrations (Jellyfin, etc.)
        post_download_actions(safe_push_log, log_title)

        # Format full file path properly for display
        if video_subfolder == "/":
            display_path = f"Videos/{final_copied.name}"
        else:
            display_path = f"Videos/{video_subfolder}/{final_copied.name}"

        status_placeholder.success(t("status_file_ready", subfolder=display_path))
        st.toast(t("toast_download_completed"), icon="✅")
    except Exception:
        status_placeholder.warning(t("warning_file_not_found"))

    # Mark download as finished
    st.session_state.download_finished = True


# Application runs automatically when loaded by Streamlit

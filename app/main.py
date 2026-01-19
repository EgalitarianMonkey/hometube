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
        clean_all_tmp_folders,
        cleanup_tmp_files,
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
        video_id_from_url,
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
        add_download_attempt,
        get_last_download_attempt,
    )
    from .playlist_utils import (
        save_playlist_status,
        is_playlist_info,
        get_playlist_entries,
        check_existing_videos_in_destination,
        get_download_progress_percent,
        create_playlist_workspace,
        create_video_workspace_in_playlist,
        create_playlist_status,
        load_playlist_status,
        update_video_status_in_playlist,
        mark_video_as_skipped,
        add_playlist_download_attempt,
        get_last_playlist_download_attempt,
    )
    from .playlist_sync import (
        sync_playlist,
        apply_sync_plan,
        format_sync_plan_details,
        refresh_playlist_url_info,
    )
    from .text_utils import render_title, DEFAULT_PLAYLIST_TITLE_PATTERN
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
        clean_all_tmp_folders,
        cleanup_tmp_files,
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
        video_id_from_url,
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
        add_download_attempt,
        get_last_download_attempt,
        is_format_completed,
        get_profiles_cached,
    )
    from playlist_utils import (
        save_playlist_status,
        is_playlist_info,
        get_playlist_entries,
        check_existing_videos_in_destination,
        get_download_progress_percent,
        create_playlist_workspace,
        create_video_workspace_in_playlist,
        create_playlist_status,
        load_playlist_status,
        update_video_status_in_playlist,
        mark_video_as_skipped,
        add_playlist_download_attempt,
        get_last_playlist_download_attempt,
    )
    from playlist_sync import (
        sync_playlist,
        apply_sync_plan,
        format_sync_plan_details,
        refresh_playlist_url_info,
    )
    from text_utils import render_title, DEFAULT_PLAYLIST_TITLE_PATTERN

# Configuration import (must be after translations for configure_language)
from app.config import (
    get_settings,
    ensure_folders_exist,
    print_config_summary,
    get_default_subtitle_languages,
    YOUTUBE_CLIENT_FALLBACKS,
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


def _display_strategy_content(quality_strategy: str) -> None:
    """
    Display content specific to the selected quality strategy and update chosen profiles.
    Uses pre-computed profiles from session state (set during url_analysis).

    Args:
        quality_strategy: Selected strategy
    """
    st.markdown("---")

    # Get pre-computed profiles from session state (computed in url_analysis)
    optimal_format_profiles = st.session_state.get("optimal_format_profiles", [])
    available_formats = st.session_state.get("available_formats_list", [])

    # Get tmp workspace for checking individual format status
    tmp_url_workspace = st.session_state.get("tmp_url_workspace")

    # Get cached profiles once for efficient lookups (O(1) instead of O(n) per check)
    cached_profiles = []
    cached_format_ids = set()
    if tmp_url_workspace:
        cached_profiles = get_profiles_cached(
            tmp_url_workspace, optimal_format_profiles
        )
        cached_format_ids = {p.get("format_id", "") for p in cached_profiles}

    # Helper function to check if a specific profile is cached and completed
    def is_profile_cached(profile: Dict) -> bool:
        """Check if a specific profile/format is downloaded and completed."""
        format_id = profile.get("format_id", "")
        return format_id in cached_format_ids

    # Check if ANY video is cached (for general message)
    has_any_cached_video = len(cached_profiles) > 0
    if has_any_cached_video:
        safe_push_log("📦 Found cached video file(s)")
        st.success(
            f"✅ {len(cached_profiles)} profile(s) already downloaded and available"
        )

    safe_push_log(f"🎨 Displaying UI for strategy: {quality_strategy}")

    if quality_strategy == "auto_best":
        st.info(t("quality_auto_best_desc"))

        # Filter profiles: only include non-cached profiles for download
        profiles_to_download = [
            p for p in optimal_format_profiles if not is_profile_cached(p)
        ]

        if profiles_to_download:
            st.session_state.chosen_format_profiles = profiles_to_download
        else:
            # All profiles are cached
            st.session_state.chosen_format_profiles = []

        if optimal_format_profiles:
            cached_count = len(optimal_format_profiles) - len(profiles_to_download)
            count_msg = t(
                "quality_profiles_generated", count=len(optimal_format_profiles)
            )
            if cached_count > 0:
                count_msg += f" ({cached_count} already cached)"
            st.success(count_msg)

            with st.expander(t("quality_profiles_list_title"), expanded=True):
                for i, profile in enumerate(optimal_format_profiles, 1):
                    height = profile.get("height", "?")
                    vcodec = profile.get("vcodec", "unknown")
                    ext = profile.get("ext", "unknown")
                    format_id = profile.get("format_id", "unknown")

                    # Check if THIS specific profile is cached
                    is_cached = is_profile_cached(profile)
                    cache_indicator = " 📦 (cached)" if is_cached else ""
                    st.markdown(
                        f"**{i}. {height}p ({vcodec}) - {ext.upper()}{cache_indicator}**"
                    )
                    st.code(f"Format ID: {format_id}", language="text")
        else:
            st.warning(t("quality_no_profiles_warning"))

    elif quality_strategy == "best_no_fallback":
        st.warning(t("quality_best_no_fallback_desc"))

        if optimal_format_profiles:
            best_profile = optimal_format_profiles[0]
            is_best_cached = is_profile_cached(best_profile)

            # Only download if not cached
            if is_best_cached:
                st.session_state.chosen_format_profiles = []
            else:
                st.session_state.chosen_format_profiles = [best_profile]

            # Show quality downgrade setting (only if not cached)
            if not is_best_cached:
                st.checkbox(
                    t("quality_refuse_downgrade"),
                    value=not settings.QUALITY_DOWNGRADE,
                    help=t("quality_refuse_downgrade_help"),
                    key="refuse_quality_downgrade_best",
                )

            height = best_profile.get("height", "?")
            vcodec = best_profile.get("vcodec", "unknown")
            ext = best_profile.get("ext", "unknown")
            format_id = best_profile.get("format_id", "unknown")

            cache_indicator = " 📦 (cached)" if is_best_cached else ""
            profile_str = f"{height}p ({vcodec}) - {ext.upper()}{cache_indicator}"
            st.success(t("quality_selected_profile", profile=profile_str))
            st.code(f"Format ID: {format_id}", language="text")
        else:
            st.warning(t("quality_best_profile_not_available"))

    elif quality_strategy == "choose_profile":
        st.info(t("quality_choose_profile_desc"))

        if optimal_format_profiles:
            # Build profile options with individual cache indicators
            profile_options = []
            for i, profile in enumerate(optimal_format_profiles):
                height = profile.get("height", "?")
                vcodec = profile.get("vcodec", "unknown")
                ext = profile.get("ext", "unknown")
                is_cached = is_profile_cached(profile)
                cache_indicator = " 📦 (cached)" if is_cached else ""
                label = f"{height}p ({vcodec}) - {ext.upper()}{cache_indicator}"
                profile_options.append(label)

            # Show selectbox even if profiles are cached (user may want to re-download)
            selected_index = st.selectbox(
                t("quality_select_profile_prompt"),
                options=range(len(profile_options)),
                format_func=lambda x: profile_options[x],
                key="selected_profile_index",
            )

            # Update chosen profiles based on selection
            if selected_index is not None:
                selected_profile = optimal_format_profiles[selected_index]
                is_selected_cached = is_profile_cached(selected_profile)

                if is_selected_cached:
                    st.session_state.chosen_format_profiles = []
                else:
                    st.session_state.chosen_format_profiles = [selected_profile]

                # Show selected profile details
                format_id = selected_profile.get("format_id", "unknown")
                if is_selected_cached:
                    st.info(
                        f"📦 Selected profile is already cached: {profile_options[selected_index]}"
                    )
                else:
                    st.success(
                        t("quality_selected", profile=profile_options[selected_index])
                    )
                st.code(f"Format ID: {format_id}", language="text")
        else:
            st.warning(t("quality_no_profiles_selection"))

    elif quality_strategy == "choose_available":
        st.info(t("quality_choose_available_desc"))
        st.warning(t("quality_choose_available_warning"))

        safe_push_log(f"📊 Available formats count: {len(available_formats)}")

        if available_formats:
            # Always show selectbox - user may want to download a different format
            format_options = [t("quality_format_auto_option")]
            for fmt in available_formats:
                format_options.append(f"{fmt['description']} - {fmt['format_id']}")

            # Add cache indicator to prompt if ANY video is cached
            prompt = t("quality_select_format_prompt")
            if has_any_cached_video:
                prompt += " (📦 some formats cached - will re-download if different format selected)"

            selected_format = st.selectbox(
                prompt,
                options=format_options,
                key="selected_available_format",
            )

            if selected_format != t("quality_format_auto_option"):
                # Extract format_id from selection
                format_id = selected_format.split(" - ")[-1]

                # Check if this specific format is cached
                is_format_cached = tmp_url_workspace and is_format_completed(
                    tmp_url_workspace, format_id
                )

                if is_format_cached:
                    st.info(f"📦 Selected format is already cached: {selected_format}")
                    st.session_state.chosen_format_profiles = []
                else:
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
                # Fallback to auto mode: use non-cached optimal profiles
                if has_any_cached_video:
                    profiles_to_download = [
                        p for p in optimal_format_profiles if not is_profile_cached(p)
                    ]
                    st.session_state.chosen_format_profiles = profiles_to_download
                else:
                    st.session_state.chosen_format_profiles = st.session_state.get(
                        "optimal_format_profiles", []
                    )
        else:
            st.warning(t("quality_no_formats_selection"))


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

    if not chosen_profiles:
        error_msg = "No profiles available for download. Please select a quality strategy first."
        safe_push_log(f"❌ {error_msg}")
        return 1, error_msg

    profiles_to_try = chosen_profiles
    safe_push_log(
        f"✅ Using {len(profiles_to_try)} profiles from {quality_strategy} strategy"
    )

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
    preferred_client: str = None,
) -> bool:
    """
    Try downloading with all YouTube client fallbacks for a profile.

    Args:
        cmd_base: Base yt-dlp command
        url: Video URL
        cookies_part: Cookie arguments
        cookies_available: Whether cookies are configured
        status_placeholder: Streamlit status placeholder
        progress_placeholder: Streamlit progress placeholder
        info_placeholder: Streamlit info placeholder
        preferred_client: Name of client that worked for url_info.json (tried first)

    Returns:
        True if download succeeded, False otherwise
    """
    # Build ordered list of clients, prioritizing the one that worked for url_info
    clients_to_try = []

    if preferred_client:
        # Find the preferred client configuration
        preferred_config = next(
            (c for c in YOUTUBE_CLIENT_FALLBACKS if c["name"] == preferred_client), None
        )

        if preferred_config:
            safe_push_log(
                f"🎯 Prioritizing {preferred_client} client (used for URL analysis)"
            )
            clients_to_try.append(preferred_config)

            # Add remaining clients (except the preferred one)
            clients_to_try.extend(
                [c for c in YOUTUBE_CLIENT_FALLBACKS if c["name"] != preferred_client]
            )
        else:
            # Preferred client not found, use default order
            clients_to_try = YOUTUBE_CLIENT_FALLBACKS
    else:
        # No preference, use default order
        clients_to_try = YOUTUBE_CLIENT_FALLBACKS

    # Try each client in order
    for client_idx, client in enumerate(clients_to_try, 1):
        client_name = client["name"]
        client_args = client["args"]

        # Show priority indicator for first attempt
        priority_indicator = "🎯 " if client_idx == 1 and preferred_client else ""

        # Try with cookies first if available
        if cookies_available:
            if status_placeholder:
                status_placeholder.info(
                    f"{priority_indicator}🍪 {client_name.title()} + cookies"
                )

            cmd = cmd_base + client_args + cookies_part + [url]
            ret = run_cmd(
                cmd, progress_placeholder, status_placeholder, info_placeholder
            )

            if ret == 0:
                safe_push_log(f"✅ SUCCESS: {client_name.title()} client + cookies")
                return True

        # Try without cookies
        if status_placeholder:
            status_placeholder.info(
                f"{priority_indicator}🚀 {client_name.title()} client"
            )

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

    # Try to read preferred YouTube client from url_info.json
    preferred_client = None
    try:
        url_info_path = tmp_video_dir / "url_info.json"
        if url_info_path.exists():
            from app.url_utils import load_url_info_from_file

            url_info = load_url_info_from_file(url_info_path)
            if url_info:
                preferred_client = url_info.get("_hometube_successful_client")
                if preferred_client:
                    safe_push_log(
                        f"🎯 Will prioritize {preferred_client} client (used for URL analysis)"
                    )
    except Exception as e:
        safe_push_log(f"⚠️ Could not read preferred client from url_info.json: {e}")

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
            tmp_url_workspace=tmp_video_dir,
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
            preferred_client,
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
            tmp_url_workspace=tmp_video_dir,
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
    tmp_url_workspace: Path,
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
        tmp_url_workspace: Temporary workspace directory for this URL (video or playlist)

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
        youtube_clients=YOUTUBE_CLIENT_FALLBACKS,
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
            tmp_url_workspace=tmp_url_workspace,
        )

    return info


def compute_optimal_profiles(url_info: Dict, json_path: Path) -> None:
    """
    Compute optimal format profiles for a VIDEO (not playlist).
    This function is called once after URL analysis to pre-calculate all profiles.

    For playlists, this function does nothing as profiles are computed per video.

    Args:
        url_info: Video information from yt-dlp
        json_path: Path to url_info.json file
    """
    # Only compute profiles for videos, not playlists
    is_playlist = url_info.get("_type") == "playlist"
    if is_playlist:
        safe_push_log(
            "ℹ️ Playlist detected - skipping profile computation (done per video)"
        )
        st.session_state.optimal_format_profiles = []
        st.session_state.available_formats_list = []
        return

    try:
        safe_push_log("🎯 Computing optimal format profiles...")

        # Get language preferences from settings
        language_primary = settings.LANGUAGE_PRIMARY or "en"
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

        # Get optimal profiles - returns complete profiles with all fields
        safe_push_log("🎯 Selecting optimal video formats (AV1/VP9 priority)...")
        optimal_profiles = get_profiles_with_formats_id_to_download(
            str(json_path), multiple_langs, audio_formats
        )

        if not optimal_profiles:
            safe_push_log("❌ No optimal profiles found")
            st.session_state.optimal_format_profiles = []
        else:
            safe_push_log(f"✅ Found {len(optimal_profiles)} optimal profile(s)")

            # Log profile details
            for idx, profile in enumerate(optimal_profiles, 1):
                safe_push_log(f"📦 Profile {idx}: {profile.get('label', 'Unknown')}")
                safe_push_log(f"   🆔 Format ID: {profile.get('format_id', '')}")
                safe_push_log(f"   🎬 Video Codec: {profile.get('vcodec', 'unknown')}")
                safe_push_log(f"   📐 Resolution: {profile.get('height', 0)}p")

            st.session_state.optimal_format_profiles = optimal_profiles

        # Also store available formats for "choose_available" strategy
        available_formats = get_available_formats(url_info)
        st.session_state.available_formats_list = available_formats

        safe_push_log("✅ Profile computation complete")

    except Exception as e:
        safe_push_log(f"⚠️ Error computing profiles: {str(e)}")
        st.session_state.optimal_format_profiles = []
        st.session_state.available_formats_list = []


# === REUSABLE VIDEO DOWNLOAD FUNCTIONS ===
# These functions encapsulate the video download workflow so it can be reused
# for both single videos and videos within playlists


def initialize_video_workspace(
    video_url: str,
    video_id: str,
    video_title: str,
    video_workspace: Path,
) -> Tuple[Optional[Dict], bool]:
    """
    Initialize a video workspace with url_info.json and status.json.

    This function:
    1. Checks if url_info.json exists, loads it if available
    2. Fetches url_info.json if it doesn't exist
    3. Creates status.json if it doesn't exist
    4. Computes optimal profiles for the video

    Args:
        video_url: Full URL of the video
        video_id: Video ID
        video_title: Video title
        video_workspace: Path to video workspace directory

    Returns:
        Tuple[Optional[Dict], bool]: (url_info dict or None, success bool)
    """
    video_url_info_path = video_workspace / "url_info.json"
    video_status_path = video_workspace / "status.json"

    # Check if url_info.json already exists
    video_url_info = None
    if video_url_info_path.exists():
        try:
            import json

            with open(video_url_info_path, "r", encoding="utf-8") as f:
                video_url_info = json.load(f)
            safe_push_log(f"📋 Using existing url_info.json for {video_title}")
        except Exception as e:
            safe_push_log(f"⚠️ Could not load existing url_info.json: {e}")

    # If url_info.json doesn't exist, fetch it
    if not video_url_info:
        safe_push_log(f"📋 Fetching url_info.json for {video_title}...")
        cookies_params = build_cookies_params_from_config()

        video_url_info = build_url_info(
            clean_url=video_url,
            json_output_path=video_url_info_path,
            cookies_params=cookies_params,
            youtube_cookies_file_path=YOUTUBE_COOKIES_FILE_PATH,
            cookies_from_browser=COOKIES_FROM_BROWSER,
            youtube_clients=YOUTUBE_CLIENT_FALLBACKS,
        )

    if video_url_info and "error" not in video_url_info:
        # Create status.json if it doesn't exist
        if not video_status_path.exists():
            create_initial_status(
                url=video_url,
                video_id=video_id,
                title=video_title,
                content_type="video",
                tmp_url_workspace=video_workspace,
            )
            safe_push_log(f"📊 Created status.json for {video_title}")

        # Compute optimal profiles for this video
        compute_optimal_profiles(video_url_info, video_url_info_path)

        # Copy to chosen_format_profiles for smart_download_with_profiles()
        optimal_profiles = st.session_state.get("optimal_format_profiles", [])
        if optimal_profiles:
            st.session_state["chosen_format_profiles"] = optimal_profiles
            st.session_state["download_quality_strategy"] = "auto_best"

        return video_url_info, True
    else:
        return None, False


def check_existing_video_file(
    video_workspace: Path,
    requested_format_id: Optional[str] = None,
) -> Tuple[Optional[Path], Optional[str]]:
    """
    Check if a video file already exists in the workspace.

    This function implements the same logic as single videos:
    1. Checks status.json for completed format
    2. Finds the corresponding file
    3. Falls back to any video file if no status.json entry

    Args:
        video_workspace: Path to video workspace directory
        requested_format_id: Optional format ID requested by user

    Returns:
        Tuple[Optional[Path], Optional[str]]: (existing_file_path or None, completed_format_id or None)
    """
    existing_generic_file = None
    completed_format_id = get_first_completed_format(video_workspace)

    if completed_format_id:
        # Check if user requested a different format than what's completed
        if requested_format_id and requested_format_id != completed_format_id:
            safe_push_log(f"🔄 User requested different format: {requested_format_id}")
            safe_push_log(f"   Current cached format: {completed_format_id}")
            safe_push_log("   Will re-download with new format")
            return None, None

        # We have a completed format in status.json - find the corresponding file
        log_title("✅ Found completed download in status")
        safe_push_log(f"  🎯 Format ID: {completed_format_id}")

        # Try to find the video file with this format ID
        existing_video_tracks = tmp_files.find_video_tracks(video_workspace)
        for track in existing_video_tracks:
            track_format_id = tmp_files.extract_format_id_from_filename(track.name)
            if track_format_id and track_format_id in completed_format_id:
                existing_generic_file = track
                safe_push_log(f"  📦 Found file: {existing_generic_file.name}")
                safe_push_log(
                    f"  📊 Size: {existing_generic_file.stat().st_size / (1024*1024):.2f}MiB"
                )
                safe_push_log("  🔄 Skipping download, reusing completed file")
                safe_push_log("")
                return existing_generic_file, completed_format_id

        if not existing_generic_file:
            safe_push_log(
                "  ⚠️ Status shows completed but file not found, will re-download"
            )
    else:
        # Fallback: check for any generic video file (backward compatibility)
        existing_video_tracks = tmp_files.find_video_tracks(video_workspace)
        existing_generic_file = (
            existing_video_tracks[0] if existing_video_tracks else None
        )

        if existing_generic_file:
            log_title("✅ Found cached download (legacy detection)")
            safe_push_log(f"  📦 Existing file: {existing_generic_file.name}")
            safe_push_log("  🔄 Skipping download, reusing cached file")
            safe_push_log(
                "  ℹ️  Note: No status.json entry for this file, consider updating"
            )
            safe_push_log("")

    return existing_generic_file, completed_format_id


def download_single_video(
    video_url: str,
    video_id: str,
    video_title: str,
    video_workspace: Path,
    base_output: str,
    embed_chapters: bool,
    embed_subs: bool,
    force_mp4: bool,
    ytdlp_custom_args: str,
    do_cut: bool,
    subs_selected: List[str],
    sb_choice: str,
    requested_format_id: Optional[str] = None,
    progress_placeholder=None,
    status_placeholder=None,
    info_placeholder=None,
) -> Tuple[int, Optional[Path], Optional[str]]:
    """
    Download a single video using the full workflow.

    This function:
    1. Initializes the video workspace
    2. Checks for existing files
    3. Downloads if needed or reuses existing file
    4. Returns the final file path

    Args:
        video_url: Full URL of the video
        video_id: Video ID
        video_title: Video title
        video_workspace: Path to video workspace directory
        base_output: Base output filename (without extension)
        embed_chapters: Whether to embed chapters
        embed_subs: Whether to embed subtitles
        force_mp4: Whether to force MP4 container
        ytdlp_custom_args: Custom yt-dlp arguments
        do_cut: Whether to cut sections
        subs_selected: List of subtitle languages
        sb_choice: SponsorBlock choice
        requested_format_id: Optional format ID requested by user
        progress_placeholder: Streamlit progress placeholder
        status_placeholder: Streamlit status placeholder
        info_placeholder: Streamlit info placeholder

    Returns:
        Tuple[int, Optional[Path], Optional[str]]: (return_code, final_file_path, error_message)
        return_code: 0 = success, -1 = cancelled, >0 = error
    """
    # Initialize workspace
    video_url_info, success = initialize_video_workspace(
        video_url, video_id, video_title, video_workspace
    )

    if not success:
        error_msg = (
            video_url_info.get("error", "Unknown error")
            if video_url_info
            else "Failed to fetch video info"
        )
        return 1, None, error_msg

    # Check for existing file
    existing_file, completed_format_id = check_existing_video_file(
        video_workspace, requested_format_id
    )

    if existing_file:
        safe_push_log("⚡ Skipping download - using cached file")

        # Update status to completed if not already
        if completed_format_id:
            update_format_status(
                tmp_url_workspace=video_workspace,
                video_format=completed_format_id,
                final_file=existing_file,
            )

        return 0, existing_file, None
    else:
        safe_push_log(f"📥 Downloading {video_title} with full workflow...")
        ret_dl, error_msg = smart_download_with_profiles(
            base_output=base_output,
            tmp_video_dir=video_workspace,
            embed_chapters=embed_chapters,
            embed_subs=embed_subs,
            force_mp4=force_mp4,
            ytdlp_custom_args=ytdlp_custom_args,
            url=video_url,
            download_mode="auto",
            target_profile=None,
            refuse_quality_downgrade=False,
            do_cut=do_cut,
            subs_selected=subs_selected,
            sb_choice=sb_choice,
            progress_placeholder=progress_placeholder,
            status_placeholder=status_placeholder,
            info_placeholder=info_placeholder,
        )

        if ret_dl == 0:
            # Find the final file
            final_file = find_final_video_file(video_workspace, base_output)

            # Organize files: rename to generic name and create final.{ext} (same as single videos)
            if final_file and final_file.exists():
                final_file = organize_downloaded_video_file(
                    video_workspace=video_workspace,
                    downloaded_file=final_file,
                    base_output=base_output,
                    subs_selected=subs_selected,
                )

            return ret_dl, final_file, None
        else:
            return ret_dl, None, error_msg


def find_final_video_file(
    video_workspace: Path,
    base_output: str,
) -> Optional[Path]:
    """
    Find the final video file after download.

    This function searches for the downloaded file in multiple ways:
    1. By base output name (what yt-dlp created)
    2. By generic name (final.{ext})
    3. Any video file in the workspace (fallback)

    Args:
        video_workspace: Path to video workspace directory
        base_output: Base output filename (without extension)

    Returns:
        Optional[Path]: Path to final file or None if not found
    """
    final_tmp = None

    # First, try to find the file by the base output name (what yt-dlp created)
    base_output_sanitized = sanitize_filename(base_output)
    for ext in [".mkv", ".mp4", ".webm"]:
        potential_file = video_workspace / f"{base_output_sanitized}{ext}"
        if potential_file.exists():
            final_tmp = potential_file
            safe_push_log(f"✅ Found downloaded file: {potential_file.name}")
            break

    # Check for final.{ext} (generic name)
    if not final_tmp:
        for ext in [".mkv", ".mp4", ".webm"]:
            final_path = tmp_files.get_final_path(video_workspace, ext.lstrip("."))
            if final_path.exists():
                final_tmp = final_path
                safe_push_log(f"✅ Found final file: {final_path.name}")
                break

    # Fallback: find any video file in the workspace
    if not final_tmp:
        existing_video_tracks = tmp_files.find_video_tracks(video_workspace)
        if existing_video_tracks:
            final_tmp = existing_video_tracks[0]
            safe_push_log(f"✅ Found video file: {final_tmp.name}")

    return final_tmp


def organize_downloaded_video_file(
    video_workspace: Path,
    downloaded_file: Path,
    base_output: str,
    subs_selected: List[str] = None,
) -> Path:
    """
    Organize downloaded video file: rename to generic name and create final.{ext}.

    This function implements the same logic as single videos:
    1. Renames downloaded file to video-{FORMAT_ID}.{ext}
    2. Renames subtitle files to generic names
    3. Copies video to final.{ext} for consistency

    Args:
        video_workspace: Path to video workspace directory
        downloaded_file: Path to the downloaded video file
        base_output: Base output filename (without extension)
        subs_selected: List of subtitle languages (optional)

    Returns:
        Path: Path to final.{ext} file
    """
    import shutil

    # Get format_id from session (stored during download)
    format_id = st.session_state.get("downloaded_format_id", "unknown")
    safe_push_log(f"  🔍 Format ID from session: {format_id}")

    # Rename to generic filename with format ID: video-{FORMAT_ID}.{ext}
    generic_name = tmp_files.get_video_track_path(
        video_workspace, format_id, downloaded_file.suffix.lstrip(".")
    )
    safe_push_log(f"  🔍 Target generic name: {generic_name.name}")

    # Rename video file if needed
    if downloaded_file != generic_name:
        try:
            if generic_name.exists():
                if should_remove_tmp_files():
                    generic_name.unlink()
                    safe_push_log(f"  🗑️ Removed existing: {generic_name.name}")
                else:
                    safe_push_log(
                        f"  ⚠️ Generic file already exists: {generic_name.name}"
                    )

            safe_push_log(
                f"  🔄 Renaming: {downloaded_file.name} → {generic_name.name}"
            )
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
                return downloaded_file  # Return original if rename failed

            final_tmp = generic_name
        except Exception as e:
            safe_push_log(f"  ⚠️ Could not rename video: {str(e)}")
            final_tmp = downloaded_file
    else:
        final_tmp = downloaded_file

    # Rename subtitle files to generic names
    if subs_selected:
        for lang in subs_selected:
            # Look for subtitle files with the original name
            for ext in [".srt", ".vtt"]:
                original_sub = video_workspace / f"{base_output}.{lang}{ext}"
                if original_sub.exists():
                    generic_sub = tmp_files.get_subtitle_path(
                        video_workspace, lang, is_cut=False
                    )
                    try:
                        if generic_sub.exists():
                            generic_sub.unlink()
                        original_sub.rename(generic_sub)
                        safe_push_log(
                            f"  ✅ Subtitle renamed: {original_sub.name} → {generic_sub.name}"
                        )
                    except Exception as e:
                        safe_push_log(f"  ⚠️ Could not rename subtitle: {str(e)}")

    # Copy to final.{ext} for consistency (keep original for cache reuse)
    final_path = tmp_files.get_final_path(video_workspace, final_tmp.suffix.lstrip("."))

    if final_tmp != final_path:
        try:
            # Remove existing final file if it exists
            if final_path.exists():
                if should_remove_tmp_files():
                    final_path.unlink()
                    safe_push_log("🗑️ Removed existing final file")
                else:
                    safe_push_log("🔍 Debug mode: Overwriting existing final file")

            # Copy (not rename!) to final name, keeping original for cache
            shutil.copy2(str(final_tmp), str(final_path))
            safe_push_log(f"📦 Copied: {final_tmp.name} → {final_path.name}")
            safe_push_log(f"💾 Kept original {final_tmp.name} for cache reuse")
            return final_path
        except Exception as e:
            safe_push_log(f"⚠️ Could not copy to final, using original: {str(e)}")
            return final_tmp
    else:
        # Already has final name
        safe_push_log(f"✓ File already has final name: {final_tmp.name}")
        return final_tmp


def url_analysis(url: str) -> Optional[Dict]:
    """
    Analyze URL and fetch comprehensive video/playlist information using yt-dlp.
    Always initializes session state variables and checks for existing url_info.json.

    This function:
    1. Sanitizes URL and creates unique tmp folder
    2. Sets all session state variables (tmp_url_workspace, unique_folder_name, etc.)
    3. Checks if url_info.json exists with good integrity
    4. If exists: loads it and returns
    5. If not: fetches from yt-dlp via init_url_workspace()
    6. For VIDEOS only: computes optimal format profiles

    Args:
        url: Video or playlist URL to analyze

    Returns:
        Dict with video/playlist information or None if error
    """
    if not url or not url.strip():
        return None

    try:
        # Sanitize URL and create unique folder for this URL (video or playlist)
        clean_url = sanitize_url(url)
        unique_folder_name = get_unique_video_folder_name_from_url(clean_url)
        tmp_url_workspace = TMP_DOWNLOAD_FOLDER / unique_folder_name

        # Check if NEW_DOWNLOAD_WITHOUT_TMP_FILES is enabled (UI override or config default)
        clean_tmp_before_download = st.session_state.get(
            "new_download_without_tmp_files", settings.NEW_DOWNLOAD_WITHOUT_TMP_FILES
        )
        if clean_tmp_before_download and tmp_url_workspace.exists():
            safe_push_log(
                f"🗑️ Removing tmp files for fresh download: {tmp_url_workspace}"
            )
            import shutil

            shutil.rmtree(tmp_url_workspace)

        ensure_dir(tmp_url_workspace)

        # ALWAYS store in session state for reuse across the application
        st.session_state["tmp_url_workspace"] = tmp_url_workspace
        st.session_state["unique_folder_name"] = unique_folder_name
        st.session_state["current_video_url"] = clean_url

        # Reset folder initialization flag for new URL
        st.session_state["default_folder_initialized"] = False
        # Reset selected destination folder when URL changes (allows re-initialization from status preferences)
        if "selected_destination_folder" in st.session_state:
            del st.session_state["selected_destination_folder"]
        # Reset sync plan when URL changes
        if "playlist_sync_plan" in st.session_state:
            st.session_state["playlist_sync_plan"] = None

        # Prepare output path for JSON file in the unique URL workspace folder
        json_output_path = tmp_url_workspace / "url_info.json"

        # === CHECK IF URL_INFO.JSON ALREADY EXISTS WITH GOOD INTEGRITY ===
        url_info_is_complet, existing_info = is_url_info_complet(json_output_path)

        if url_info_is_complet and existing_info:
            # Check if this is an existing playlist that needs fresh data
            # (playlist with previous downloads should always get fresh url_info)
            should_refresh_playlist = False

            if is_playlist_info(existing_info):
                playlist_id = existing_info.get("id", "")
                if playlist_id:
                    # Check if this playlist has been downloaded before (custom_title set)
                    playlist_workspace = create_playlist_workspace(
                        TMP_DOWNLOAD_FOLDER, playlist_id
                    )
                    existing_status = load_playlist_status(playlist_workspace)
                    if (
                        existing_status
                        and existing_status.get("custom_title") is not None
                    ):
                        # This is an existing playlist - always refresh to get latest state
                        should_refresh_playlist = True
                        safe_push_log(
                            "🔄 Existing playlist detected - refreshing url_info.json"
                        )

            if should_refresh_playlist:
                # Refresh playlist data from YouTube
                fresh_info = refresh_playlist_url_info(
                    playlist_workspace=tmp_url_workspace,
                    playlist_url=clean_url,
                )
                if fresh_info:
                    st.session_state["url_info"] = fresh_info
                    st.session_state["url_info_path"] = str(json_output_path)
                    # No need to compute optimal profiles for playlists
                    return fresh_info
                else:
                    # Fallback to cached data if refresh fails
                    safe_push_log(
                        "⚠️ Could not refresh playlist data, using cached version"
                    )
                    st.session_state["url_info"] = existing_info
                    st.session_state["url_info_path"] = str(json_output_path)
                    return existing_info
            else:
                # Store in session state and return immediately (no download needed)
                st.session_state["url_info"] = existing_info
                st.session_state["url_info_path"] = str(json_output_path)

                # Compute optimal profiles for videos (not playlists) - SINGLE SOURCE OF TRUTH
                compute_optimal_profiles(existing_info, json_output_path)

                return existing_info
        else:
            # Initialize workspace and fetch video info
            info = init_url_workspace(clean_url, json_output_path, tmp_url_workspace)

            # Compute optimal profiles for videos (not playlists) - SINGLE SOURCE OF TRUTH
            if info and "error" not in info:
                compute_optimal_profiles(info, json_output_path)

            return info

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
        playlist_id = url_info.get("id", "")

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

        # Store playlist info in session state
        st.session_state["is_playlist"] = True
        st.session_state["playlist_title"] = title
        st.session_state["playlist_id"] = playlist_id
        st.session_state["playlist_entries"] = get_playlist_entries(url_info)
        st.session_state["playlist_total_count"] = entries_count
        st.session_state["playlist_channel"] = (
            uploader  # Store channel for title pattern
        )

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

        # Mark as not a playlist
        st.session_state["is_playlist"] = False

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


def get_tmp_url_workspace() -> Optional[Path]:
    """
    Get the unique URL workspace directory from session state.
    This directory is created during url_analysis() and stored in session.
    It contains all temporary files for the analyzed URL (video or playlist).

    Returns:
        Path to the URL workspace directory or None if not initialized
    """
    return st.session_state.get("tmp_url_workspace")


def get_tmp_video_dir() -> Optional[Path]:
    """
    Get the temporary video directory from session state.

    For single videos: returns the URL workspace directory (same as get_tmp_url_workspace())
    For playlists: will return the specific video's subdirectory (future implementation)

    Returns:
        Path to the video temporary directory or None if not initialized
    """
    # For now, tmp_video_dir is the same as tmp_url_workspace (single video case)
    # In the future, for playlists, this will return a subdirectory
    return st.session_state.get("tmp_url_workspace")


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
#     t("video_or_playlist_url"),
#     value="",
#     help="Enter the YouTube video URL",
#     key="main_url",
# )

st.markdown("\n")

# === MAIN INPUTS (OUTSIDE FORM FOR DYNAMIC BEHAVIOR) ===
url = st.text_input(
    t("video_or_playlist_url"),
    value="",
    placeholder="https://www.youtube.com/watch?v=...",
    key="main_url",
)

# Analyze URL and display information
url_info = None
if url and url.strip():
    # Check if URL has changed or if it's the first analysis
    current_url_in_session = st.session_state.get("current_video_url")
    url_info_in_session = st.session_state.get("url_info")

    # Only run analysis if URL changed or no info in session
    if current_url_in_session != url or not url_info_in_session:
        with st.spinner(t("url_analysis_spinner")):
            url_info = url_analysis(url)
            if url_info:
                display_url_info(url_info)
                # IMPORTANT: If yt-dlp detected a playlist (even from a watch?v=...&list=... URL),
                # we need to update tmp_url_workspace to use the playlist workspace
                if is_playlist_info(url_info):
                    playlist_id = url_info.get("id", "")
                    if playlist_id:
                        playlist_workspace = create_playlist_workspace(
                            TMP_DOWNLOAD_FOLDER, playlist_id
                        )
                        st.session_state["tmp_url_workspace"] = playlist_workspace
                        st.session_state["unique_folder_name"] = (
                            f"youtube-playlist-{playlist_id}"
                        )
    else:
        # Reuse existing url_info from session state
        url_info = url_info_in_session
        display_url_info(url_info)

        # Ensure tmp_url_workspace is set correctly when reusing URL
        # For playlists, always use the playlist workspace path
        clean_url = sanitize_url(url)
        is_playlist = is_playlist_info(url_info)
        if is_playlist:
            playlist_id = url_info.get("id", "")
            if playlist_id:
                playlist_workspace = create_playlist_workspace(
                    TMP_DOWNLOAD_FOLDER, playlist_id
                )
                # Always update to ensure we use the correct playlist workspace
                st.session_state["tmp_url_workspace"] = playlist_workspace
                st.session_state["unique_folder_name"] = (
                    f"youtube-playlist-{playlist_id}"
                )
        elif "tmp_url_workspace" not in st.session_state or not st.session_state.get(
            "tmp_url_workspace"
        ):
            # Only reconstruct for videos if not already set
            unique_folder_name = get_unique_video_folder_name_from_url(clean_url)
            tmp_url_workspace = TMP_DOWNLOAD_FOLDER / unique_folder_name
            st.session_state["tmp_url_workspace"] = tmp_url_workspace
            st.session_state["unique_folder_name"] = unique_folder_name

        # Compute optimal profiles for videos (not playlists) when reusing URL
        # This ensures the quality selection UI displays correct profiles
        url_info_path = st.session_state.get("url_info_path")
        if url_info and "error" not in url_info and url_info_path:
            json_output_path = Path(url_info_path)
            if json_output_path.exists():
                compute_optimal_profiles(url_info, json_output_path)

# Try to get last download attempt to pre-fill fields
default_filename = None  # Use None to distinguish "not set" from "empty string"
default_folder = None
last_attempt = None  # Initialize to avoid NameError

tmp_url_workspace = st.session_state.get("tmp_url_workspace")
# Check if it's a playlist - prioritize url_info from current analysis
is_playlist_mode = False
url_info_check = url_info if url_info else st.session_state.get("url_info", {})
if url_info_check:
    is_playlist_mode = is_playlist_info(url_info_check)
    # Update session state for consistency
    if is_playlist_mode:
        st.session_state["is_playlist"] = True
elif st.session_state.get("is_playlist", False):
    # Fallback to session state if url_info not available
    is_playlist_mode = True

# For playlists, ensure we have the correct workspace even if tmp_url_workspace is not set
if is_playlist_mode and not tmp_url_workspace:
    # Try to construct workspace from playlist_id or URL
    playlist_id = st.session_state.get("playlist_id")
    if playlist_id:
        tmp_url_workspace = create_playlist_workspace(TMP_DOWNLOAD_FOLDER, playlist_id)
    elif url and url.strip():
        # Fallback: construct from URL
        clean_url = sanitize_url(url)
        unique_folder_name = get_unique_video_folder_name_from_url(clean_url)
        tmp_url_workspace = TMP_DOWNLOAD_FOLDER / unique_folder_name
    # Update session state with the workspace we found/created
    if tmp_url_workspace:
        st.session_state["tmp_url_workspace"] = tmp_url_workspace

if tmp_url_workspace:
    if is_playlist_mode:
        # For playlists, use playlist-specific function
        last_attempt = get_last_playlist_download_attempt(tmp_url_workspace)
        if last_attempt:
            # Use custom_title even if it's an empty string (user might have cleared it)
            default_filename = last_attempt.get("custom_title")
            playlist_location = last_attempt.get("playlist_location")
            # Only set default_folder if playlist_location is not None and not empty
            if playlist_location:
                default_folder = playlist_location
            # Pre-fill title_pattern if available
            if "title_pattern" in last_attempt:
                st.session_state["playlist_title_pattern"] = last_attempt[
                    "title_pattern"
                ]
    else:
        # For single videos, use regular function
        last_attempt = get_last_download_attempt(tmp_url_workspace)
        if last_attempt:
            default_filename = last_attempt.get("custom_title")
            video_location = last_attempt.get("video_location")
            # Only set default_folder if video_location is not None and not empty
            if video_location:
                default_folder = video_location

# === PLAYLIST PROGRESS DISPLAY ===
# Show download ratio for playlists
# Use the is_playlist_mode already determined above (don't re-check)
# is_playlist_mode is already set from lines 2081-2090
playlist_already_downloaded = []
playlist_to_download = []

if is_playlist_mode:
    playlist_entries = st.session_state.get("playlist_entries", [])
    playlist_total = st.session_state.get("playlist_total_count", 0)
    playlist_title = st.session_state.get("playlist_title", "Playlist")

    # Default filename to playlist title if not set from last attempt
    # Use None check to distinguish "not set" from "empty string"
    if default_filename is None:
        default_filename = playlist_title
    # If default_filename is empty string from last_attempt, keep it (user might have cleared it)
    # Ensure default_filename is a string for st.text_input
    if default_filename is None:
        default_filename = ""

    # Show playlist progress section
    # st.markdown(f"### {t('playlist_progress_title')}")

    # Check if destination folder is selected to compute progress
    # We'll compute the ratio based on the selected destination folder
    # For now, show the total count
    st.info(t("playlist_videos_found", count=playlist_total))

    # Display input for playlist name (instead of video name)
    filename = st.text_input(
        t("playlist_name"), value=default_filename or "", help=t("playlist_name_help")
    )

    # Display input for video titles pattern (playlist only)
    # Get default from session state (pre-filled from last attempt), config, or built-in default
    default_pattern = st.session_state.get(
        "playlist_title_pattern",
        settings.PLAYLIST_VIDEOS_TITLES_PATTERN or DEFAULT_PLAYLIST_TITLE_PATTERN,
    )
    playlist_title_pattern = st.text_input(
        t("playlist_title_pattern"),
        value=default_pattern,
        help=t("playlist_title_pattern_help"),
        key="playlist_title_pattern_input",
    )
    # Store in session state for use in download logic
    st.session_state["playlist_title_pattern"] = playlist_title_pattern
else:
    # Regular video mode
    # Ensure default_filename is a string for st.text_input
    if default_filename is None:
        default_filename = ""
    filename = st.text_input(
        t("video_name"), value=default_filename or "", help=t("video_name_help")
    )

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

# Initialize default folder from last attempt (only once per URL)
if "default_folder_initialized" not in st.session_state:
    st.session_state.default_folder_initialized = False

# Reset initialization flag if URL changed (checked by comparing current URL with stored one)
# This ensures we re-initialize when a new URL is entered
current_url_in_state = st.session_state.get("current_video_url")
if url and url.strip() and current_url_in_state != url:
    st.session_state.default_folder_initialized = False

# Set prefilled_folder if we have a valid default_folder and haven't initialized yet
if (
    tmp_url_workspace
    and default_folder is not None
    and default_folder != ""  # Also check for empty string
    and not st.session_state.default_folder_initialized
):
    st.session_state.prefilled_folder = default_folder
    st.session_state.default_folder_initialized = True

# Reload folder list if a new folder was just created to include it in the options
existing_subdirs = list_subdirs_recursive(
    VIDEOS_FOLDER, max_depth=2
)  # Allow 2 levels deep
folder_options = ["/"] + existing_subdirs + [t("create_new_folder")]

# Determine default folder index
# Priority: 1. Previously selected folder (persisted), 2. Prefilled from status preferences, 3. Root folder
folder_index = 0  # Default to root

# Check if we have a previously selected folder for this URL
selected_folder_key = "selected_destination_folder"
if selected_folder_key in st.session_state:
    # Use the previously selected folder
    selected_folder = st.session_state[selected_folder_key]
    if selected_folder in folder_options:
        folder_index = folder_options.index(selected_folder)
elif "prefilled_folder" in st.session_state:
    # Use the prefilled folder from status preferences (first time initialization)
    prefilled = st.session_state.prefilled_folder
    if prefilled in folder_options:
        folder_index = folder_options.index(prefilled)
        # Store as selected folder so it persists across reruns
        st.session_state[selected_folder_key] = prefilled
    # Clear the prefilled value after using it
    del st.session_state.prefilled_folder

video_subfolder = st.selectbox(
    t("destination_folder"),
    options=folder_options,
    index=folder_index,
    format_func=lambda x: (
        "📁 Root folder (/)"
        if x == "/"
        else t("create_new_folder") if x == t("create_new_folder") else f"📁 {x}"
    ),
    # Dynamic key for reset
    key=f"folder_selectbox_{st.session_state.folder_selectbox_key}",
)

# Persist the selected folder for future reruns
if video_subfolder != t("create_new_folder"):
    st.session_state[selected_folder_key] = video_subfolder

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

# === FILE/PLAYLIST EXISTENCE CHECK ===
# Check what already exists in destination
if (
    filename
    and filename.strip()
    and video_subfolder
    and video_subfolder != t("create_new_folder")
):
    # Determine destination directory
    if video_subfolder == "/":
        check_dest_dir = VIDEOS_FOLDER
    else:
        check_dest_dir = VIDEOS_FOLDER / video_subfolder

    if is_playlist_mode:
        # === PLAYLIST PROGRESS CALCULATION ===
        # Check which videos from the playlist already exist in destination
        playlist_entries = st.session_state.get("playlist_entries", [])

        if playlist_entries:
            # For playlists, destination is a subfolder with the playlist name
            playlist_dest_dir = check_dest_dir / sanitize_filename(filename)

            # Get the title pattern for existence checking
            check_title_pattern = st.session_state.get(
                "playlist_title_pattern", DEFAULT_PLAYLIST_TITLE_PATTERN
            )

            playlist_already_downloaded, playlist_to_download, total = (
                check_existing_videos_in_destination(
                    playlist_dest_dir,
                    playlist_entries,
                    playlist_workspace=tmp_url_workspace,
                    title_pattern=check_title_pattern,
                )
            )

            # Store in session state for download logic
            st.session_state["playlist_already_downloaded"] = (
                playlist_already_downloaded
            )
            st.session_state["playlist_to_download"] = playlist_to_download

            # Calculate progress metrics
            progress_percent = get_download_progress_percent(
                playlist_already_downloaded, playlist_to_download
            )

            # === PLAYLIST SYNCHRONIZATION (AUTOMATIC FOR EXISTING PLAYLISTS) ===
            # Check if this playlist has been downloaded before (status.json with custom_title set)
            playlist_id_for_sync = st.session_state.get("playlist_id", "")
            playlist_workspace_for_sync = None
            existing_status_for_sync = None
            has_previous_downloads = False
            sync_plan = None

            if playlist_id_for_sync:
                playlist_workspace_for_sync = create_playlist_workspace(
                    TMP_DOWNLOAD_FOLDER, playlist_id_for_sync
                )
                existing_status_for_sync = load_playlist_status(
                    playlist_workspace_for_sync
                )
                # Only consider it as "existing" if custom_title has been set
                if existing_status_for_sync:
                    has_previous_downloads = (
                        existing_status_for_sync.get("custom_title") is not None
                    )

            # For existing playlists, calculate sync plan automatically
            if existing_status_for_sync and has_previous_downloads:
                # Get saved preferences from status.json
                saved_location = existing_status_for_sync.get("playlist_location", "/")
                saved_pattern = existing_status_for_sync.get(
                    "title_pattern",
                    settings.PLAYLIST_VIDEOS_TITLES_PATTERN
                    or DEFAULT_PLAYLIST_TITLE_PATTERN,
                )

                # Get current UI values
                current_location = "/"
                if (
                    video_subfolder
                    and video_subfolder != "/"
                    and video_subfolder != t("create_new_folder")
                ):
                    current_location = video_subfolder

                current_pattern = st.session_state.get(
                    "playlist_title_pattern",
                    settings.PLAYLIST_VIDEOS_TITLES_PATTERN
                    or DEFAULT_PLAYLIST_TITLE_PATTERN,
                )

                # Compute sync plan automatically
                new_url_info = st.session_state.get("url_info", {})
                keep_old_videos_val = settings.PLAYLIST_KEEP_OLD_VIDEOS

                sync_plan = sync_playlist(
                    playlist_workspace=playlist_workspace_for_sync,
                    dest_dir=playlist_dest_dir,
                    new_url_info=new_url_info,
                    new_location=current_location,
                    new_pattern=current_pattern,
                    dry_run=True,
                    keep_old_videos=keep_old_videos_val,
                )

                # Store sync plan in session state
                st.session_state["playlist_sync_plan"] = sync_plan
                st.session_state["playlist_sync_dest"] = playlist_dest_dir
                st.session_state["playlist_sync_location"] = current_location
                st.session_state["playlist_sync_pattern"] = current_pattern
                st.session_state["playlist_workspace_for_sync"] = (
                    playlist_workspace_for_sync
                )

            # === DISPLAY STATUS AND CHANGES ===
            if sync_plan and sync_plan.has_non_download_changes:
                # Show what changes are pending (excluding download-only)
                changes_lines = []

                if sync_plan.videos_to_rename:
                    changes_lines.append(
                        t(
                            "playlist_changes_rename",
                            count=len(sync_plan.videos_to_rename),
                        )
                    )
                if sync_plan.videos_to_download:
                    changes_lines.append(
                        t(
                            "playlist_changes_download",
                            count=len(sync_plan.videos_to_download),
                        )
                    )
                if sync_plan.videos_to_relocate:
                    changes_lines.append(
                        t(
                            "playlist_changes_relocate",
                            count=len(sync_plan.videos_to_relocate),
                        )
                    )
                if sync_plan.videos_to_archive:
                    changes_lines.append(
                        t(
                            "playlist_changes_archive",
                            count=len(sync_plan.videos_to_archive),
                        )
                    )
                if sync_plan.videos_to_delete:
                    changes_lines.append(
                        t(
                            "playlist_changes_delete",
                            count=len(sync_plan.videos_to_delete),
                        )
                    )

                # Show progress bar
                st.progress(
                    progress_percent / 100.0,
                    text=t(
                        "playlist_ratio",
                        downloaded=len(playlist_already_downloaded),
                        total=total,
                    ),
                )

                # Show changes summary
                st.warning(
                    t("playlist_changes_summary") + "\n\n" + "\n\n".join(changes_lines)
                )

                # Show details in expander
                with st.expander(
                    t("playlist_sync_details", fallback="View detailed changes")
                ):
                    playlist_channel = st.session_state.get("playlist_channel", "")
                    st.markdown(
                        format_sync_plan_details(sync_plan, channel=playlist_channel)
                    )

                # Keep old videos option
                keep_old_videos_checkbox = st.checkbox(
                    t("playlist_keep_old_videos"),
                    value=settings.PLAYLIST_KEEP_OLD_VIDEOS,
                    help=t("playlist_keep_old_videos_help"),
                    key="playlist_keep_old_videos_checkbox",
                )
                st.session_state["playlist_keep_old_videos"] = keep_old_videos_checkbox

                # Apply button
                apply_changes_clicked = st.button(
                    t("playlist_apply_changes", fallback="✅ Apply Changes"),
                    help=t(
                        "playlist_apply_changes_help",
                        fallback="Apply all pending synchronization changes",
                    ),
                    type="primary",
                    key="apply_sync_btn",
                )

                if apply_changes_clicked:
                    with st.spinner(
                        t(
                            "playlist_applying_sync",
                            fallback="Applying synchronization...",
                        )
                    ):
                        # Get keep_old_videos preference from checkbox
                        keep_old_videos_pref = st.session_state.get(
                            "playlist_keep_old_videos",
                            settings.PLAYLIST_KEEP_OLD_VIDEOS,
                        )

                        success = apply_sync_plan(
                            plan=sync_plan,
                            playlist_workspace=playlist_workspace_for_sync,
                            dest_dir=playlist_dest_dir,
                            new_location=current_location,
                            new_pattern=current_pattern,
                            new_url_info=new_url_info,
                            keep_old_videos=keep_old_videos_pref,
                        )

                        if success:
                            st.success(
                                t(
                                    "playlist_sync_success",
                                    fallback="✅ Synchronization completed successfully!",
                                )
                            )
                            # Clear sync plan and reload
                            st.session_state["playlist_sync_plan"] = None
                            st.rerun()
                        else:
                            st.error(
                                t(
                                    "playlist_sync_failed",
                                    fallback="❌ Synchronization failed. Check logs for details.",
                                )
                            )
            elif len(playlist_to_download) == 0:
                # No changes and nothing to download - fully up to date
                st.success(
                    t(
                        "playlist_already_up_to_date",
                        fallback="✅ Playlist is already up to date!",
                    )
                )
            else:
                # Show progress bar and download count
                st.progress(
                    progress_percent / 100.0,
                    text=t(
                        "playlist_ratio",
                        downloaded=len(playlist_already_downloaded),
                        total=total,
                    ),
                )

                # Show count of videos to download
                st.info(t("playlist_to_download", count=len(playlist_to_download)))

    else:
        # === SINGLE VIDEO FILE EXISTENCE WARNING ===
        # Check for existing files with all common video extensions
        existing_files = []
        for ext in [".mkv", ".mp4", ".webm", ".avi", ".mov"]:
            potential_file = check_dest_dir / f"{filename}{ext}"
            if potential_file.exists():
                existing_files.append(potential_file)

        if existing_files:
            # File already exists - show warning
            existing_file = existing_files[0]
            file_size_mb = existing_file.stat().st_size / (1024 * 1024)

            if settings.ALLOW_OVERWRITE_EXISTING_VIDEO:
                st.warning(
                    f"⚠️ **File already exists:** `{existing_file.name}`\n\n"
                    f"📊 Size: {file_size_mb:.2f} MiB\n\n"
                    f"🔄 **Overwrite mode enabled** (ALLOW_OVERWRITE_EXISTING_VIDEO=true)\n\n"
                    f"The existing file will be replaced if you proceed with the download."
                )
            else:
                st.error(
                    f"❌ **File already exists:** `{existing_file.name}`\n\n"
                    f"📊 Size: {file_size_mb:.2f} MiB\n\n"
                    f"🛡️ **Protection active:** ALLOW_OVERWRITE_EXISTING_VIDEO=false\n\n"
                    f"Download will be skipped to protect the existing file.\n\n"
                    f"💡 To allow overwrites, set `ALLOW_OVERWRITE_EXISTING_VIDEO=true` in your `.env` file."
                )

# subtitles multiselect from env
# Default subtitles are determined by audio language preferences (LANGUAGE_PRIMARY, LANGUAGES_SECONDARIES)
default_subtitle_languages = get_default_subtitle_languages()
subs_selected = st.multiselect(
    t("subtitles_to_embed"),
    options=default_subtitle_languages,
    default=default_subtitle_languages,  # Pre-select subtitles based on audio preferences
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
if is_playlist_mode:
    # Cutting controls are irrelevant for playlists
    start_text = ""
    end_text = ""
else:
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

    # Display strategy-specific content (also sets chosen_format_profiles)
    _display_strategy_content(quality_strategy)

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
        st.markdown("""
        - Age-restricted videos
        - Member-only content
        - Some region-restricted videos
        - Videos requiring sign-in
        """)
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

    # Temporary Files Management
    st.markdown(f"**📀 {t('tmp_files_section_title')}**")
    st.caption(t("tmp_files_section_description"))

    # Initialize session state for temporary file options
    if "remove_tmp_files_after_download" not in st.session_state:
        st.session_state.remove_tmp_files_after_download = (
            settings.REMOVE_TMP_FILES_AFTER_DOWNLOAD
        )
    if "new_download_without_tmp_files" not in st.session_state:
        st.session_state.new_download_without_tmp_files = (
            settings.NEW_DOWNLOAD_WITHOUT_TMP_FILES
        )

    # Option 1: Remove files after successful download
    remove_tmp_files_after_download = st.checkbox(
        t("tmp_files_remove_after_download_label"),
        value=st.session_state.remove_tmp_files_after_download,
        help=t("tmp_files_remove_after_download_help"),
        key="remove_tmp_files_after_download_checkbox",
    )

    # Option 2: Clean tmp folder before download
    new_download_without_tmp_files = st.checkbox(
        t("tmp_files_clean_before_download_label"),
        value=st.session_state.new_download_without_tmp_files,
        help=t("tmp_files_clean_before_download_help"),
        key="new_download_without_tmp_files_checkbox",
    )

    # Update session state
    st.session_state.remove_tmp_files_after_download = remove_tmp_files_after_download
    st.session_state.new_download_without_tmp_files = new_download_without_tmp_files

    # Also update old key for backward compatibility
    st.session_state.remove_tmp_files = remove_tmp_files_after_download

    # Show info based on configuration
    if not remove_tmp_files_after_download and not new_download_without_tmp_files:
        st.success(t("tmp_files_mode_intelligent_caching"))
    elif new_download_without_tmp_files:
        st.warning(t("tmp_files_mode_fresh_start"))
    elif remove_tmp_files_after_download:
        st.info(t("tmp_files_mode_space_saving"))

    st.markdown("---")

    # Manual cleanup section
    st.markdown(f"**🗑️ {t('tmp_files_manual_cleanup_title')}**")
    st.caption(t("tmp_files_manual_cleanup_description"))

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button(
            t("tmp_files_clean_all_button"),
            type="secondary",
            use_container_width=True,
            key="clean_all_tmp_button",
        ):
            with st.spinner(t("tmp_files_cleaning_spinner")):
                folders_count, size_mb = clean_all_tmp_folders()

                if folders_count > 0:
                    st.success(
                        t(
                            "tmp_files_cleanup_success",
                            count=folders_count,
                            size=size_mb,
                        )
                    )
                else:
                    st.info(t("tmp_files_cleanup_nothing"))

    with col2:
        # Show tmp folder size if available
        try:
            if TMP_DOWNLOAD_FOLDER.exists():
                total_size = sum(
                    f.stat().st_size
                    for f in TMP_DOWNLOAD_FOLDER.rglob("*")
                    if f.is_file()
                )
                size_mb = total_size / (1024 * 1024)
                st.metric(
                    label=t("tmp_files_current_size"),
                    value=f"{size_mb:.0f} MB",
                )
        except Exception:
            pass

# === DOWNLOAD BUTTON ===
st.markdown("\n")
st.markdown("\n")

# Create a centered, prominent download button
# Use different label for playlists vs single videos
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if is_playlist_mode:
        # Check if playlist has pending sync changes or is up to date
        playlist_to_download_list = st.session_state.get("playlist_to_download", [])
        sync_plan_for_btn = st.session_state.get("playlist_sync_plan")

        # Determine button state based on sync plan
        # Only consider non-download changes as blocking
        has_pending_sync_changes = (
            sync_plan_for_btn is not None and sync_plan_for_btn.has_non_download_changes
        )
        playlist_is_up_to_date = (
            len(playlist_to_download_list) == 0 and not has_pending_sync_changes
        )

        if playlist_is_up_to_date:
            # Playlist is completely up to date - button disabled (message already shown above)
            submitted = st.button(
                f"{t('playlist_download_button')}",
                type="secondary",
                use_container_width=True,
                help=t(
                    "playlist_already_up_to_date",
                    fallback="All videos are already downloaded.",
                ),
                disabled=True,
            )
        elif has_pending_sync_changes:
            # Has changes to apply first - show warning
            st.warning(
                t(
                    "playlist_sync_required",
                    fallback="⚠️ Please apply pending changes first",
                )
            )
            submitted = st.button(
                f"{t('playlist_download_button')}",
                type="secondary",
                use_container_width=True,
                help=t("playlist_sync_required"),
                disabled=True,
            )
        else:
            # Ready to download
            submitted = st.button(
                f"{t('playlist_download_button')}",
                type="primary",
                use_container_width=True,
                help=t("playlist_download_help"),
            )
    else:
        submitted = st.button(
            f"{t('download_button')}",
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
            clean_status = (
                speed.replace("✅ ", "").replace("✂️ ", "").replace("📝 ", "")
            )
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

    # === PLAYLIST DOWNLOAD MODE ===
    if is_playlist_mode:
        playlist_name = filename or st.session_state.get("playlist_title", "Playlist")
        playlist_id = st.session_state.get("playlist_id", "unknown")
        playlist_to_download = st.session_state.get("playlist_to_download", [])
        playlist_entries = st.session_state.get("playlist_entries", [])

        if not playlist_to_download:
            st.success(t("playlist_all_downloaded"))
            st.session_state.download_finished = True
            st.stop()

        total_videos = len(playlist_entries)
        videos_to_dl = len(playlist_to_download)

        log_title(f"📋 PLAYLIST DOWNLOAD: {playlist_name}")
        push_log(f"📊 {videos_to_dl} videos to download out of {total_videos}")
        push_log("")

        # Create playlist workspace
        playlist_workspace = create_playlist_workspace(TMP_DOWNLOAD_FOLDER, playlist_id)
        push_log(f"🔧 Playlist workspace: {playlist_workspace}")

        # Create playlist destination folder
        playlist_dest = dest_dir / sanitize_filename(playlist_name)
        ensure_dir(playlist_dest)
        push_log(f"📁 Playlist destination: {playlist_dest}")

        # Ensure url_info.json exists in playlist workspace
        url_info = st.session_state.get("url_info", {})
        url_info_path = st.session_state.get("url_info_path")
        playlist_url_info_path = playlist_workspace / "url_info.json"

        if url_info_path and Path(url_info_path).exists():
            # Copy url_info.json to playlist workspace if it doesn't exist
            if not playlist_url_info_path.exists():
                import shutil

                shutil.copy2(url_info_path, playlist_url_info_path)
                push_log("📋 Copied url_info.json to playlist workspace")
        elif url_info and "error" not in url_info:
            # Save url_info.json if we have it but no file exists
            import json

            with open(playlist_url_info_path, "w", encoding="utf-8") as f:
                json.dump(url_info, f, indent=2, ensure_ascii=False)
            push_log("📋 Saved url_info.json to playlist workspace")

        # Create or load playlist status
        existing_status = load_playlist_status(playlist_workspace)
        if not existing_status:
            create_playlist_status(
                playlist_workspace=playlist_workspace,
                url=url,
                playlist_id=playlist_id,
                playlist_title=playlist_name,
                entries=playlist_entries,
            )
        else:
            # Update existing status with any new entries that might be missing
            videos_status = existing_status.get("videos", {})
            for entry in playlist_entries:
                video_id = entry.get("id", "")
                if video_id and video_id not in videos_status:
                    # Add missing video entry
                    videos_status[video_id] = {
                        "title": entry.get("title", "Unknown"),
                        "url": entry.get("url", ""),
                        "status": "pending",
                        "downloaded_at": None,
                        "error": None,
                    }
            # Save updated status
            save_playlist_status(playlist_workspace, existing_status)

        # Record download attempt
        # Get title_pattern from session state (set in UI)
        title_pattern = st.session_state.get(
            "playlist_title_pattern", DEFAULT_PLAYLIST_TITLE_PATTERN
        )
        add_playlist_download_attempt(
            playlist_workspace=playlist_workspace,
            custom_title=playlist_name,
            playlist_location=video_subfolder,
            title_pattern=title_pattern,
        )

        # Mark already downloaded videos as skipped
        playlist_already_downloaded = st.session_state.get(
            "playlist_already_downloaded", []
        )
        for entry in playlist_already_downloaded:
            video_id = entry.get("id", "")
            if video_id:
                mark_video_as_skipped(playlist_workspace, video_id)

        # Download each video in the playlist
        initial_completed_count = len(playlist_already_downloaded)
        completed_count = initial_completed_count
        failed_count = 0

        # Get the title pattern from session state
        title_pattern = st.session_state.get(
            "playlist_title_pattern", DEFAULT_PLAYLIST_TITLE_PATTERN
        )

        for idx, entry in enumerate(playlist_to_download, 1):
            video_id = entry.get("id", "")
            video_title = entry.get("title", f"Video {idx}")
            video_url = entry.get("url", "")
            # Get playlist index (1-based position in original playlist)
            playlist_index = entry.get("playlist_index", idx)

            if not video_url and video_id:
                video_url = f"https://www.youtube.com/watch?v={video_id}"

            downloads_total = max(videos_to_dl, 1)
            session_current = idx
            playlist_position = playlist_index or (initial_completed_count + idx)
            playlist_note = ""
            if total_videos:
                playlist_note = t(
                    "playlist_position_note",
                    current=playlist_position,
                    total=total_videos,
                )

            push_log("")
            download_message = t(
                "playlist_downloading_video",
                current=session_current,
                total=videos_to_dl,
                title=video_title,
            )
            log_title(download_message)
            if playlist_note:
                push_log(playlist_note)

            # Update status
            update_video_status_in_playlist(playlist_workspace, video_id, "downloading")
            status_message = download_message
            if playlist_note:
                status_message = f"{download_message}\n{playlist_note}"
            status_placeholder.info(status_message)

            # Update progress
            raw_progress = (session_current - 1) / downloads_total
            progress_percent = min(max(raw_progress, 0.0), 1.0)
            progress_placeholder.progress(progress_percent)

            # Create video workspace within playlist
            video_workspace = create_video_workspace_in_playlist(
                playlist_workspace, video_id
            )

            # Use the reusable video download function (same as single videos)
            base_output = sanitize_filename(video_title)
            do_cut_video = False  # No cutting for individual playlist videos
            subs_selected_video = subs_selected  # Use playlist subtitle settings
            force_mp4_video = False
            ytdlp_custom_args_video = st.session_state.get("ytdlp_custom_args", "")

            # Download the video using the reusable function
            ret_dl, final_tmp, error_msg = download_single_video(
                video_url=video_url,
                video_id=video_id,
                video_title=video_title,
                video_workspace=video_workspace,
                base_output=base_output,
                embed_chapters=embed_chapters,
                embed_subs=embed_subs,
                force_mp4=force_mp4_video,
                ytdlp_custom_args=ytdlp_custom_args_video,
                do_cut=do_cut_video,
                subs_selected=subs_selected_video,
                sb_choice=sb_choice,
                requested_format_id=None,  # Auto mode for playlists
                progress_placeholder=progress_placeholder,
                status_placeholder=status_placeholder,
                info_placeholder=info_placeholder,
            )

            # Handle cancellation
            if ret_dl == -1:
                push_log("⚠️ Download cancelled by user")
                st.session_state.download_finished = True
                st.stop()

            # Process result
            if ret_dl == 0 and final_tmp and final_tmp.exists():
                # Render the final filename using the pattern
                ext = final_tmp.suffix.lstrip(".")  # Remove leading dot
                playlist_channel = st.session_state.get("playlist_channel", "")
                resolved_title = render_title(
                    title_pattern,
                    i=playlist_index,
                    title=video_title,
                    video_id=video_id,
                    ext=ext,
                    total=total_videos,
                    channel=playlist_channel,
                )

                # Copy to playlist destination with rendered title
                dest_file = playlist_dest / resolved_title
                import shutil

                shutil.copy2(str(final_tmp), str(dest_file))
                push_log(f"✅ Copied to destination: {dest_file.name}")

                # Update playlist status to mark video as completed
                # Include pattern info for future reference
                update_video_status_in_playlist(
                    playlist_workspace,
                    video_id,
                    "completed",
                    extra_data={
                        "title_pattern": title_pattern,
                        "resolved_title": resolved_title,
                        "playlist_index": playlist_index,
                    },
                )
                push_log(
                    t(
                        "playlist_video_completed",
                        current=session_current,
                        total=videos_to_dl,
                        title=video_title,
                    )
                )
                completed_count += 1
            else:
                # Download failed or file not found
                error_msg_final = error_msg or "No file found after download"
                update_video_status_in_playlist(
                    playlist_workspace, video_id, "failed", error_msg_final
                )

                failure_message = t(
                    "playlist_video_failed",
                    current=session_current,
                    total=videos_to_dl,
                    title=video_title,
                )
                push_log(failure_message)

                status_details = failure_message
                if error_msg_final:
                    reason_text = t(
                        "playlist_video_failure_reason", reason=error_msg_final
                    )
                    push_log(reason_text)
                    status_details = f"{failure_message}\n{reason_text}"

                if status_placeholder:
                    status_placeholder.error(status_details)

                failed_count += 1

        # Final summary
        push_log("")
        log_title("📊 PLAYLIST DOWNLOAD COMPLETE")
        push_log(
            t(
                "playlist_download_complete",
                completed=completed_count,
                total=total_videos,
            )
        )
        if failed_count > 0:
            push_log(f"⚠️ {failed_count} video(s) failed")

        # Final progress
        progress_placeholder.progress(1.0, text=t("status_completed"))
        status_placeholder.success(
            t(
                "playlist_copy_complete",
                copied=completed_count - len(playlist_already_downloaded),
                folder=playlist_name,
            )
        )

        # Trigger media-server integrations
        post_download_actions(safe_push_log, log_title)

        st.toast(t("toast_download_completed"), icon="✅")
        st.session_state.download_finished = True
        st.stop()

    # === SINGLE VIDEO DOWNLOAD MODE (existing logic continues below) ===

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
    # This ensures each URL (video/playlist) has its own isolated workspace
    tmp_url_workspace = st.session_state.get("tmp_url_workspace")
    unique_folder_name = st.session_state.get("unique_folder_name", "unknown")

    if not tmp_url_workspace:
        st.error("❌ Video workspace not initialized. Please re-enter the URL.")
        st.stop()

    # For now, tmp_video_dir points to the same location as tmp_url_workspace
    # In the future, for playlists, each video will have its own subdirectory within tmp_url_workspace
    tmp_video_dir = tmp_url_workspace

    # All temporary files are written to the root of the unique URL workspace folder
    # The video_subfolder is only used when copying the final file to destination
    push_log(f"🔧 Unique URL workspace: {unique_folder_name}")
    push_log(t("log_temp_download_folder", folder=tmp_url_workspace))

    # Setup cookies for yt-dlp operations
    cookies_part = build_cookies_params()

    # If no filename provided, get video title
    if filename is None:
        filename = get_video_title(clean_url, cookies_part)

    base_output = filename  # without extension

    # Get requested format ID from chosen profiles (if user selected a specific format)
    requested_format_id = None
    chosen_format_profiles = st.session_state.get("chosen_format_profiles", [])
    if chosen_format_profiles:
        requested_format_id = chosen_format_profiles[0].get("format_id")

    # Record this download attempt in status.json
    add_download_attempt(
        tmp_url_workspace=tmp_url_workspace,
        custom_title=filename,
        video_location=video_subfolder,
        requested_format_id=requested_format_id,
    )

    # Log download strategy
    push_log("")
    log_title("📥 Download Strategy")
    push_log("  1️⃣  Download with readable name (yt-dlp compatibility)")
    push_log("  2️⃣  Rename to generic names (resilience & independence)")
    push_log("  3️⃣  Skip if generic files exist (resume support)")
    push_log("")
    push_log(f"📝 Target filename: {base_output}")
    if requested_format_id:
        push_log(f"🎯 Requested format: {requested_format_id}")

    # Check if a completed download already exists (status.json verification)
    # Priority: 1) Check status.json for completed format 2) Fallback to generic file search
    existing_generic_file = None
    completed_format_id = get_first_completed_format(tmp_video_dir)

    if completed_format_id:
        # Check if user requested a different format than what's completed
        if requested_format_id and requested_format_id != completed_format_id:
            push_log(f"🔄 User requested different format: {requested_format_id}")
            push_log(f"   Current cached format: {completed_format_id}")
            push_log("   Will re-download with new format")
            completed_format_id = None  # Force re-download
            existing_generic_file = None
        else:
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
                push_log(
                    "  ⚠️ Status shows completed but file not found, will re-download"
                )
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
            push_log(
                "  ℹ️  Note: No status.json entry for this file, consider updating"
            )
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

            # Extract video ID from URL
            video_id = video_id_from_url(clean_url)

            # Extract source platform from URL
            from app.medias_utils import get_source_from_url

            source = get_source_from_url(clean_url)

            # Get playlist ID if in playlist mode
            playlist_id = None
            if is_playlist_mode:
                playlist_id = st.session_state.get("playlist_id")

            # Get uploader/channel name from url_info.json
            uploader = None
            try:
                url_info_path = tmp_video_dir / "url_info.json"
                if url_info_path.exists():
                    from app.url_utils import load_url_info_from_file

                    url_info_data = load_url_info_from_file(url_info_path)
                    if url_info_data:
                        uploader = url_info_data.get(
                            "uploader", url_info_data.get("channel", "")
                        )
            except Exception as e:
                push_log(f"⚠️ Could not get uploader from url_info: {e}")

            # Log metadata information for debugging
            push_log(
                f"📝 Metadata to embed: video_id={video_id}, source={source}, playlist_id={playlist_id}, uploader={uploader}"
            )

            # Apply custom metadata with all available information
            if not customize_video_metadata(
                final_source,
                filename,
                original_title,
                video_id,
                source=source,
                playlist_id=playlist_id,
                webpage_url=clean_url,
                duration=None,  # Will be read from file
                uploader=uploader,
            ):
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
            tmp_url_workspace=tmp_video_dir,
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

        # Optional automatic cleanup of tmp workspace (env/UI controlled)
        if should_remove_tmp_files():
            try:
                cleanup_tmp_files(base_output, tmp_video_dir, "all")

                # Remove empty workspace folder to free disk space
                try:
                    if tmp_video_dir.exists() and not any(tmp_video_dir.iterdir()):
                        tmp_video_dir.rmdir()
                except Exception:
                    pass

                push_log("🧹 Temporary files removed (REMOVE_TMP_FILES_AFTER_DOWNLOAD)")
            except Exception as e:
                push_log(f"⚠️ Cleanup skipped: {e}")
    except Exception:
        status_placeholder.warning(t("warning_file_not_found"))

    # Mark download as finished
    st.session_state.download_finished = True


# Application runs automatically when loaded by Streamlit

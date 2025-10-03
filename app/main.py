import os
import re
import shutil
import subprocess
import json
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict

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
    from .quality_profiles import QUALITY_PROFILES
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
    from quality_profiles import QUALITY_PROFILES


# === CONSTANTS ===

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


def probe_available_formats(url: str, cookies_part: List[str]) -> Dict[str, bool]:
    """
    Probe video to check which codecs are actually available with comprehensive retry strategy.
    Returns a dict of codec availability to filter profiles intelligently.

    Args:
        url: Video URL to probe
        cookies_part: Cookie parameters for authentication

    Returns:
        Dict with codec availability: {"av01": True, "vp9": True, "opus": False, ...}
    """
    safe_push_log("")
    log_title("🔍 Analyzing video compatibility...")
    safe_push_log("💡 Strategy: Default client first (most reliable)")

    # Optimized strategies prioritizing the most successful client (Default)
    strategies = []

    # Strategy 1: Default client first (often most successful)
    if cookies_part:
        strategies.append(
            {
                "name": "🔄 Default Client (with cookies)",
                "description": "Most reliable - often finds all codecs",
                "cmd": ["yt-dlp", "--list-formats", "--no-download"]
                + cookies_part
                + [url],
                "timeout": 45,
                "priority": "highest",
            }
        )

    strategies.append(
        {
            "name": "🔄 Default Client (no cookies)",
            "description": "Most reliable fallback",
            "cmd": ["yt-dlp", "--list-formats", "--no-download", url],
            "timeout": 30,
            "priority": "highest",
        }
    )

    # Strategy 2: Specialized clients with cookies (if available)
    if cookies_part:
        strategies.append(
            {
                "name": "🌐 Web Browser (with cookies)",
                "description": "Premium formats with authentication",
                "cmd": [
                    "yt-dlp",
                    "--list-formats",
                    "--no-download",
                    "--extractor-args",
                    "youtube:player_client=web",
                ]
                + cookies_part
                + [url],
                "timeout": 45,
                "priority": "high",
            }
        )

        strategies.append(
            {
                "name": "🤖 Android App (with cookies)",
                "description": "Mobile client with authentication",
                "cmd": [
                    "yt-dlp",
                    "--list-formats",
                    "--no-download",
                    "--extractor-args",
                    "youtube:player_client=android",
                ]
                + cookies_part
                + [url],
                "timeout": 30,
                "priority": "medium",
            }
        )

    # Strategy 3: Specialized clients without cookies
    specialized_clients = [
        ("🌐 Web Browser (no cookies)", "web", 45),
        ("🤖 Android App (no cookies)", "android", 30),
        ("📱 iOS App (no cookies)", "ios", 30),
    ]

    for name, client, timeout in specialized_clients:
        strategies.append(
            {
                "name": name,
                "description": f"Specialized {client} client",
                "cmd": [
                    "yt-dlp",
                    "--list-formats",
                    "--no-download",
                    "--extractor-args",
                    f"youtube:player_client={client}",
                    url,
                ],
                "timeout": timeout,
                "priority": "low",
            }
        )

    # Strategy 4: Default client again as final fallback (double insurance)
    if cookies_part:
        strategies.append(
            {
                "name": "🔄 Default Client (final attempt with cookies)",
                "description": "Last resort with maximum timeout",
                "cmd": ["yt-dlp", "--list-formats", "--no-download", "--verbose"]
                + cookies_part
                + [url],
                "timeout": 60,
                "priority": "lowest",
            }
        )

    # Try each strategy and look for the most comprehensive result
    best_result = None
    best_codec_count = 0
    total_strategies = len(strategies)

    safe_push_log(f"🎯 Testing {total_strategies} detection strategies:")

    for i, strategy in enumerate(strategies, 1):
        try:
            safe_push_log("")
            safe_push_log(f"🔁 Strategy {i}/{total_strategies}: {strategy['name']}")

            result = run_subprocess_safe(
                strategy["cmd"],
                timeout=strategy.get("timeout", 30),
                error_context=f"Format probe ({strategy['name']})",
            )

            if result.returncode == 0 and result.stdout.strip():
                # Parse available codecs from output
                output = result.stdout.lower()

                # Enhanced codec detection patterns
                codecs_available = {
                    "av01": any(
                        pattern in output for pattern in ["av01", "av1", "aom"]
                    ),
                    "vp9": "vp9" in output,
                    "h264": any(
                        pattern in output for pattern in ["h264", "avc", "h.264"]
                    ),
                    "opus": "opus" in output,
                    "aac": "aac" in output,
                }

                # Count available codecs
                codec_count = sum(codecs_available.values())
                available_codecs = [
                    codec for codec, available in codecs_available.items() if available
                ]

                # Quality assessment
                has_premium = codecs_available.get("av01") and codecs_available.get(
                    "opus"
                )
                has_modern = codecs_available.get("vp9") and codecs_available.get(
                    "opus"
                )

                if has_premium:
                    quality_note = "🏆 Premium quality formats detected!"
                elif has_modern:
                    quality_note = "🥈 Modern quality formats detected"
                elif codec_count >= 3:
                    quality_note = "📺 Standard quality formats detected"
                else:
                    quality_note = "⚡ Basic compatibility formats only"

                safe_push_log(
                    f"✅ Success: {', '.join(available_codecs)} ({codec_count} total)"
                )
                safe_push_log(f"{quality_note}")

                # Keep the result with the most codecs (most comprehensive)
                if codec_count > best_codec_count:
                    best_result = codecs_available
                    best_codec_count = codec_count
                    safe_push_log("🏆 This is now our best result!")

                # Early exit conditions - stop if we found excellent results
                if has_premium and codec_count >= 4:
                    safe_push_log("")
                    safe_push_log(
                        "🎉 Excellent! Found all premium codecs - stopping search"
                    )
                    safe_push_log("")
                    return codecs_available

                # Also stop early if Default client found good results and we're past strategy 2
                if (
                    i >= 2
                    and "Default Client" in strategy["name"]
                    and codec_count >= 3
                    and has_modern
                ):
                    safe_push_log("")
                    safe_push_log(
                        "🎯 Default client found good codecs - stopping search"
                    )
                    safe_push_log("")
                    return codecs_available

            else:
                # Strategy failed - provide clear reason
                error_msg = (
                    result.stderr.strip() if result.stderr else "No output received"
                )

                if "sign in" in error_msg.lower() or "login" in error_msg.lower():
                    safe_push_log("🔐 Authentication required")
                elif "private" in error_msg.lower():
                    safe_push_log("🔒 Video private/restricted")
                elif "not available" in error_msg.lower():
                    safe_push_log("🌍 Region/client unavailable")
                else:
                    safe_push_log(f"❌ Failed: {error_msg[:50]}")

        except Exception as e:
            safe_push_log(f"💥 Error: {str(e)[:50]}")
            continue

    # Summarize results
    safe_push_log("")
    if best_result and best_codec_count > 0:
        available_codecs = [
            codec for codec, available in best_result.items() if available
        ]
        has_premium = best_result.get("av01") and best_result.get("opus")
        has_modern = best_result.get("vp9") and best_result.get("opus")

        if has_premium:
            safe_push_log("🎉 RESULT: Premium quality formats available!")
        elif has_modern:
            safe_push_log("✅ RESULT: Modern quality formats available")
        else:
            safe_push_log("📺 RESULT: Standard quality formats available")

        safe_push_log(f"📋 Final codec list: {', '.join(available_codecs)}")
        return best_result

    # All probes failed - provide helpful guidance
    safe_push_log("")
    safe_push_log("⚠️ Format detection failed")
    if cookies_part:
        safe_push_log(
            "💡 Possible causes: Expired cookies, special permissions, or geo-blocking"
        )
    else:
        safe_push_log(
            "💡 Possible causes: Authentication required, private video, or API issues"
        )

    safe_push_log(
        "🔄 Continuing with optimistic assumptions (all profiles will be tested)"
    )
    safe_push_log("")

    return {"av01": True, "vp9": True, "h264": True, "opus": True, "aac": True}


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


def get_profile_by_name(profile_name: str) -> Optional[Dict]:
    """Get a quality profile by name."""
    for profile in QUALITY_PROFILES:
        if profile["name"] == profile_name:
            return profile
    return None


def get_download_configuration() -> Dict:
    """
    Centralized configuration retrieval from session state.

    Returns:
        Dict with all download configuration parameters
    """
    return {
        "download_mode": st.session_state.get("download_mode", "auto"),
        "selected_profile_name": st.session_state.get("quality_profile", None),
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


def smart_download_with_profiles(
    base_output: str,
    tmp_subfolder_dir: Path,
    embed_chapters: bool,
    embed_subs: bool,
    force_mp4: bool,
    ytdlp_custom_args: str,
    url: str,
    download_mode: str,
    target_profile: str = None,
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

    # Probe available formats first
    available_codecs = probe_available_formats(url, cookies_part)

    # Determine profiles to try based on mode and compatibility
    log_title("🎯 Selecting quality profiles...")

    if download_mode == "forced" and target_profile:
        # Forced mode - single profile only
        profile = get_profile_by_name(target_profile)
        if not profile:
            return 1, f"Unknown profile: {target_profile}"

        profiles_to_try = [profile]
        safe_push_log(f"🔒 FORCED MODE: {profile['label']}")
        safe_push_log("⚠️ No fallback - will fail if this profile doesn't work")

    else:
        # Auto mode - try all viable profiles
        safe_push_log("🤖 Auto mode: Intelligent profile selection")

        # Show which codecs were detected
        detected_codecs = [
            codec for codec, available in available_codecs.items() if available
        ]
        safe_push_log(f"📋 Available codecs: {', '.join(detected_codecs)}")

        profiles_to_try = filter_viable_profiles(available_codecs, "auto")

        if profiles_to_try:
            safe_push_log(f"✅ Selected: {len(profiles_to_try)} compatible profile(s)")
            safe_push_log("")

            # Show selected profiles compactly
            for i, p in enumerate(profiles_to_try, 1):
                if i == 1:
                    priority_icon = "🏆"
                elif i == 2:
                    priority_icon = "🥈"
                elif i == 3:
                    priority_icon = "🥉"
                else:
                    priority_icon = "📋"
                safe_push_log(f"{priority_icon} Priority {i}: {p['label']}")
        else:
            safe_push_log("❌ No compatible profiles found!")

    if not profiles_to_try:
        safe_push_log("")
        safe_push_log("❌ Profile selection failed")
        safe_push_log(
            "💡 This means none of the quality profiles are compatible with the detected codecs"
        )
        safe_push_log("🔧 Try enabling different codec options or check your video URL")
        return 1, "No viable profiles found based on codec compatibility"

    # Try each profile with clear progress indication
    safe_push_log("")
    log_title("🚀 Starting download attempts...")

    for profile_idx, profile in enumerate(profiles_to_try, 1):
        safe_push_log("")
        safe_push_log(
            f"🏆 Profile {profile_idx}/{len(profiles_to_try)}: {profile['label']}"
        )

        # Show codec targeting in a concise way
        codec_info = []
        if "av01" in profile["format"].lower():
            codec_info.append("🎬 AV1 (best compression)")
        elif "vp9" in profile["format"].lower():
            codec_info.append("🎥 VP9 (modern)")
        else:
            codec_info.append("📺 H.264 (compatible)")

        if "opus" in profile["format"].lower():
            codec_info.append("🎵 Opus audio")
        else:
            codec_info.append("🔊 AAC audio")

        safe_push_log(" | ".join(codec_info))

        if status_placeholder:
            status_placeholder.info(f"🏆 Profile {profile_idx}: {profile['label']}")

        # Build base command for this profile
        cmd_base = build_base_ytdlp_command(
            base_output,
            tmp_subfolder_dir,
            profile["format"],
            embed_chapters,
            embed_subs,
            force_mp4,
            ytdlp_custom_args,
            profile,  # Pass profile for extra args
        )

        # Add subtitles if requested
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

        # Add SponsorBlock
        sb_params = build_sponsorblock_params(sb_choice)
        if sb_params:
            cmd_base.extend(sb_params)

        # Store current profile for error diagnostics
        st.session_state["current_attempting_profile"] = profile["label"]

        # Try all clients with this profile (compact logging)
        success = False
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
                    success = True
                    break

            # Try without cookies
            if status_placeholder:
                status_placeholder.info(f"🚀 {client_name.title()} client")

            cmd = cmd_base + client_args + [url]
            ret = run_cmd(
                cmd, progress_placeholder, status_placeholder, info_placeholder
            )

            if ret == 0:
                safe_push_log(f"✅ SUCCESS: {client_name.title()} client")
                success = True
                break

        if success:
            return 0, ""

        # Profile failed - provide compact summary
        safe_push_log("")
        safe_push_log(f"❌ FAILED: {profile['label']}")

        # Check what the main issue was (concise)
        last_error = st.session_state.get("last_error", "").lower()
        if "requested format is not available" in last_error:
            safe_push_log("⚠️ Format rejected (authentication limitation)")
        elif any(
            auth_word in last_error for auth_word in ["403", "forbidden", "sign in"]
        ):
            safe_push_log("🔐 Authentication/permission issue")
        else:
            safe_push_log("⚠️ Technical compatibility issue")

        # Check fallback options (compact)
        remaining_profiles = len(profiles_to_try) - profile_idx

        if download_mode == "forced":
            safe_push_log("🔒 FORCED MODE: No fallback allowed")
            break
        elif refuse_quality_downgrade:
            safe_push_log("🚫 STOPPING: Quality downgrade refused")
            break
        elif remaining_profiles > 0:
            safe_push_log(
                f"🔄 FALLBACK: Trying next profile ({remaining_profiles} remaining)"
            )
        else:
            safe_push_log("❌ No more profiles available")

    # All profiles failed - show comprehensive help
    profiles_count = len(profiles_to_try)
    if status_placeholder:
        status_placeholder.error("❌ All quality profiles failed")

    show_download_failure_help(cookies_available, profiles_count)
    return ret, f"All {profiles_count} profiles failed after full client fallback"


# Common authentication error keywords - more precise patterns
AUTH_ERROR_KEYWORDS = [
    "sign in to confirm",
    "please log in",
    "login required",
    "video is private",
    "video is unavailable",  # Full phrase, not just "unavailable"
    "age restricted",
    "requires authentication",
    "authentication required",
    "requested format is not available",  # Often indicates auth/cookie issues
    "format is not available",
    "http error 403",  # Forbidden - often signature/cookie related
    "403: forbidden",
    "unable to download video data",  # Common with signature issues
    "signature extraction failed",  # More specific than just "signature"
    "n parameter extraction failed",  # More specific than "n-sig"
    "cipher not found",  # More specific than just "cipher"
    "youtube said: unable to extract",
    "this video is not available",
    "members-only content",
]

# Constants
# LOG_SEPARATOR removed - now using log_title() function for dynamic sizing

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


# === ENVIRONMENT CONFIGURATION ===
def in_container() -> bool:
    """Detect if we are running inside a container (Docker/Podman)"""
    return Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


# Calculate once to avoid repeated filesystem checks
IN_CONTAINER = in_container()


# === DEFAULT CONFIGURATION ===
# Exhaustive dictionary defining all configurable variables with default values
DEFAULT_CONFIG = {
    # === Core Paths ===
    "VIDEOS_FOLDER": "/data/videos" if IN_CONTAINER else "./downloads",
    "TMP_DOWNLOAD_FOLDER": "/data/tmp" if IN_CONTAINER else "./tmp",
    # === Authentication ===
    "YOUTUBE_COOKIES_FILE_PATH": "",
    "COOKIES_FROM_BROWSER": "",
    # === Localization ===
    "UI_LANGUAGE": "en",
    "SUBTITLES_CHOICES": "en",
    # === Quality & Download Preferences ===
    "DEFAULT_DOWNLOAD_MODE": "auto",  # auto (try all profiles) or forced (single profile)
    "DEFAULT_QUALITY_PROFILE": "",  # mkv_av1_opus, mkv_vp9_opus, mp4_av1_aac, mp4_h264_aac
    "DEFAULT_REFUSE_QUALITY_DOWNGRADE": "false",  # Stop at first failure instead of trying lower quality
    "DEFAULT_EMBED_CHAPTERS": "true",  # Embed chapters by default
    "DEFAULT_EMBED_SUBS": "true",  # Embed subtitles by default
    # === Advanced Options ===
    "YTDLP_CUSTOM_ARGS": "",
    "DEFAULT_CUTTING_MODE": "keyframes",  # keyframes or precise
    "DEFAULT_BROWSER_SELECT": "chrome",  # Default browser for cookie extraction
    # === System ===
    "DEBUG": "false",
}


def load_environment_config() -> Dict[str, str]:
    """
    Load environment configuration with proper priority:
    1. Default values from DEFAULT_CONFIG
    2. Environment variables (os.getenv)
    3. .env file (only in local/non-container mode if python-dotenv available)

    Returns:
        Dictionary with all configuration values
    """
    config = DEFAULT_CONFIG.copy()

    # Get the directory where main.py is located for relative paths
    app_dir = Path(__file__).parent
    project_root = app_dir.parent

    # Step 1: Start with default values (already in config)

    # Step 2: Override with environment variables if they exist
    for key in config:
        env_value = os.getenv(key)
        if env_value is not None:
            config[key] = env_value

    # Step 3: Load from .env file only if not in container
    if not IN_CONTAINER:
        env_file = project_root / ".env"
        if env_file.exists():
            try:
                # Try to import and use python-dotenv if available
                from dotenv import load_dotenv

                # Load .env file values (don't override existing env vars)
                load_dotenv(env_file, override=False)

                # Update config with .env values that weren't already set by env vars
                for key in config:
                    new_env_value = os.getenv(key)
                    if new_env_value is not None:
                        config[key] = new_env_value

            except ImportError:
                # python-dotenv not available, skip .env file loading
                pass
            except Exception as e:
                print(f"⚠️ Error reading .env file: {e}")

    # Post-process configuration values

    # Handle relative paths
    if config["VIDEOS_FOLDER"] and not Path(config["VIDEOS_FOLDER"]).is_absolute():
        config["VIDEOS_FOLDER"] = str(project_root / config["VIDEOS_FOLDER"])

    if config["TMP_DOWNLOAD_FOLDER"]:
        if not Path(config["TMP_DOWNLOAD_FOLDER"]).is_absolute():
            config["TMP_DOWNLOAD_FOLDER"] = str(
                project_root / config["TMP_DOWNLOAD_FOLDER"]
            )
    else:
        # Default to VIDEOS_FOLDER/tmp if not specified
        config["TMP_DOWNLOAD_FOLDER"] = str(Path(config["VIDEOS_FOLDER"]) / "tmp")

    if (
        config["YOUTUBE_COOKIES_FILE_PATH"]
        and not Path(config["YOUTUBE_COOKIES_FILE_PATH"]).is_absolute()
    ):
        config["YOUTUBE_COOKIES_FILE_PATH"] = str(
            project_root / config["YOUTUBE_COOKIES_FILE_PATH"]
        )

    return config


# Load configuration
CONFIG = load_environment_config()

# Configure translations with the loaded UI language
configure_language(CONFIG["UI_LANGUAGE"])

# === ENV VARIABLES ===
# Determine the project root for robust default paths
app_dir = Path(__file__).parent
project_root = app_dir.parent

# Set up main configuration variables
VIDEOS_FOLDER = Path(CONFIG["VIDEOS_FOLDER"])
TMP_DOWNLOAD_FOLDER = Path(CONFIG["TMP_DOWNLOAD_FOLDER"])

# Ensure the folders exist with proper error handling
try:
    VIDEOS_FOLDER.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"⚠️ Could not create videos folder {VIDEOS_FOLDER}: {e}")
    # Fallback to a safe location
    fallback_folder = Path.home() / "HomeTube_Downloads"
    print(f"💡 Using fallback folder: {fallback_folder}")
    VIDEOS_FOLDER = fallback_folder
    try:
        VIDEOS_FOLDER.mkdir(parents=True, exist_ok=True)
    except Exception as e2:
        print(f"❌ Could not create fallback folder: {e2}")
        # Last resort: use current directory
        VIDEOS_FOLDER = Path.cwd() / "downloads"

# Ensure temp folder exists
try:
    TMP_DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"⚠️ Could not create temp folder {TMP_DOWNLOAD_FOLDER}: {e}")

# Cookies configuration
YOUTUBE_COOKIES_FILE_PATH = CONFIG["YOUTUBE_COOKIES_FILE_PATH"] or None
COOKIES_FROM_BROWSER = CONFIG["COOKIES_FROM_BROWSER"].strip().lower()

# Parse subtitle choices from configuration
SUBTITLES_CHOICES = [
    x.strip().lower() for x in CONFIG["SUBTITLES_CHOICES"].split(",") if x.strip()
]


# === CONFIGURATION SUMMARY ===
def print_config_summary():
    """Print a summary of the current configuration for debugging"""
    print("\n🔧 HomeTube Configuration Summary:")
    print(f"🏃 Running mode: {'Container' if IN_CONTAINER else 'Local'}")
    print(f"🌐 UI Language: {CONFIG['UI_LANGUAGE']}")
    print(f"📁 Videos folder: {VIDEOS_FOLDER}")
    print(f"📁 Temp folder: {TMP_DOWNLOAD_FOLDER}")

    # Check folder accessibility
    if not VIDEOS_FOLDER.exists():
        print(f"⚠️ Videos folder does not exist: {VIDEOS_FOLDER}")
    elif not os.access(VIDEOS_FOLDER, os.W_OK):
        print(f"⚠️ Videos folder is not writable: {VIDEOS_FOLDER}")
    else:
        print(f"✅ Videos folder is ready: {VIDEOS_FOLDER}")

    # Authentication status
    if YOUTUBE_COOKIES_FILE_PATH and Path(YOUTUBE_COOKIES_FILE_PATH).exists():
        print(f"🍪 Cookies file: {YOUTUBE_COOKIES_FILE_PATH}")
    elif COOKIES_FROM_BROWSER:
        print(f"🍪 Browser cookies: {COOKIES_FROM_BROWSER}")
    else:
        print("⚠️ No authentication configured (may limit video access)")

    print(f"🔤 Subtitle languages: {', '.join(SUBTITLES_CHOICES)}")

    # Environment file status (only relevant in local mode)
    if not IN_CONTAINER:
        # Check if python-dotenv is available
        import importlib.util

        if importlib.util.find_spec("dotenv") is not None:
            print("✅ python-dotenv available: .env files supported")
        else:
            print("⚠️ python-dotenv not available - .env files will be ignored")

        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            print(f"✅ Configuration file: {env_file}")
        else:
            print("⚠️ No .env file found - using defaults")
    else:
        print("📦 Container mode - using environment variables only")

    print()


# Print configuration summary in development mode
if __name__ == "__main__" or CONFIG["DEBUG"].lower() in ("true", "1", "yes"):
    print_config_summary()


# === UTILITY FUNCTIONS ===


def is_valid_browser(browser_name: str) -> bool:
    """Check if browser name is supported"""
    if not browser_name:
        return False
    return browser_name.lower().strip() in SUPPORTED_BROWSERS


# === UI CFG ===
st.set_page_config(page_title=t("page_title"), page_icon="🎬", layout="centered")
st.markdown(
    f"<h1 style='text-align: center;'>{t('page_header')}</h1>", unsafe_allow_html=True
)

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


# === Helpers FS ===
def list_subdirs(root: Path) -> List[str]:
    """List immediate subdirectories in root folder"""
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir()])


def list_subdirs_recursive(root: Path, max_depth: int = 2) -> List[str]:
    """
    List subdirectories recursively up to max_depth levels.
    Returns paths relative to root, formatted for display.
    """
    if not root.exists():
        return []

    subdirs = []

    def scan_directory(current_path: Path, current_depth: int, relative_path: str = ""):
        if current_depth > max_depth:
            return

        try:
            for item in sorted(current_path.iterdir()):
                if item.is_dir():
                    # Build the relative path for display
                    if relative_path:
                        full_relative = f"{relative_path}/{item.name}"
                    else:
                        full_relative = item.name

                    subdirs.append(full_relative)

                    # Recurse if we haven't reached max depth
                    if current_depth < max_depth:
                        scan_directory(item, current_depth + 1, full_relative)
        except PermissionError:
            # Skip directories we can't access
            pass

    scan_directory(root, 0)
    return subdirs


def is_sabr_warning(message: str) -> bool:
    """Check if message is a normal SABR/streaming warning that doesn't need auth hints"""
    message_lower = message.lower()
    sabr_patterns = [
        "sabr streaming",
        "sabr-only",
        "server-side ad placement",
        "formats have been skipped as they are missing a url",
        "youtube is forcing sabr",
        "youtube may have enabled",
    ]
    return any(pattern in message_lower for pattern in sabr_patterns)


def is_cookies_expired_warning(message: str) -> bool:
    """Check if message is a YouTube cookies expiration warning"""
    message_lower = message.lower()
    cookies_patterns = [
        "the provided youtube account cookies are no longer valid",
        "cookies are no longer valid",
        "they have likely been rotated in the browser as a security measure",
        "for tips on how to effectively export youtube cookies",
    ]
    return any(pattern in message_lower for pattern in cookies_patterns)


def should_suppress_message(message: str) -> bool:
    """Check if a message should be suppressed from user logs"""
    message_lower = message.lower()

    # Suppress empty lines
    if message.strip() == "":
        return True

    # Suppress cookies expiration warnings (we'll show a friendly message instead)
    if is_cookies_expired_warning(message):
        return True

    # Suppress SABR warnings (technical, not user-relevant)
    if is_sabr_warning(message):
        return True

    # Suppress repetitive PO Token warnings (shown once per session)
    if "po token" in message_lower and "gvs" in message_lower:
        session_key = "po_token_warning_shown"
        if st.session_state.get(session_key, False):
            return True  # Suppress repeated warnings
        st.session_state[session_key] = True
        # Allow first warning to show, but simplify it
        return False

    # Suppress other repetitive technical warnings
    repetitive_patterns = [
        "there are missing subtitles languages because a po token was not provided",
        "only images are available for download",
        "the extractor specified to use impersonation",
        "sleeping",  # "Sleeping 1.0 seconds" messages
    ]

    if any(pattern in message_lower for pattern in repetitive_patterns):
        return True

    # Suppress Python tracebacks and technical errors
    technical_patterns = [
        "traceback (most recent call last)",
        'file "<frozen runpy>"',
        'file "/usr/local/bin/yt-dlp',
        'file "/usr/lib/python',
        "contextlib.py",
        "cookies.py",
        "^file ",  # Generic file references in tracebacks
    ]

    return any(pattern in message_lower for pattern in technical_patterns)


def is_authentication_error(error_message: str) -> bool:
    """
    Check if an error message indicates an authentication/cookies issue.

    Excludes normal warnings like SABR streaming issues.

    Args:
        error_message: The error message to check

    Returns:
        True if it's likely an authentication issue
    """
    # Skip SABR warnings - these are normal technical warnings, not auth issues
    if is_sabr_warning(error_message):
        return False

    return any(keyword in error_message.lower() for keyword in AUTH_ERROR_KEYWORDS)


def is_http_403_error(error_message: str) -> bool:
    """Check if error is specifically HTTP 403 Forbidden"""
    error_lower = error_message.lower()
    return (
        "403" in error_lower and "forbidden" in error_lower
    ) or "unable to download video data" in error_lower


def log_http_403_error_hint(error_message: str = ""):
    """Log specific guidance for HTTP 403 errors - often signature/cookie related"""
    safe_push_log("🚫 HTTP 403 Forbidden Error Detected")
    safe_push_log("🔐 This is typically a signature verification or cookie issue")
    safe_push_log("")

    # Check for signature-specific issues
    if any(
        keyword in error_message.lower() for keyword in ["signature", "n-sig", "cipher"]
    ):
        safe_push_log("🔑 SIGNATURE ISSUE DETECTED:")
        safe_push_log("   • YouTube uses encrypted signatures to protect video streams")
        safe_push_log("   • These signatures expire quickly and require fresh cookies")
        safe_push_log("")

    cookies_method = _get_current_cookies_method()

    safe_push_log("💡 IMMEDIATE SOLUTIONS:")
    _log_authentication_solutions(cookies_method)
    if cookies_method == "browser":
        browser = st.session_state.get("browser_select", "chrome")
        safe_push_log(
            f"   4. 📋 Make sure you're actively logged into YouTube in {browser}"
        )

    safe_push_log("")
    safe_push_log(
        "🎯 KEY POINT: Even public videos need cookies for signature verification!"
    )


def log_authentication_error_hint(error_message: str = ""):
    """Log context-aware authentication error messages"""
    # Prevent spam - only show once per download session
    session_key = "auth_hint_shown_this_download"
    if st.session_state.get(session_key, False):
        return

    st.session_state[session_key] = True

    # Check if this is specifically an HTTP 403 error
    if is_http_403_error(error_message):
        log_http_403_error_hint(error_message)
        return

    safe_push_log("🍪 This appears to be a cookies/authentication issue")

    # Check current cookie configuration and provide specific guidance
    cookies_method = st.session_state.get("cookies_method", "none")

    if cookies_method == "none":
        safe_push_log("❌ No cookies configured - video likely requires authentication")
        safe_push_log(
            "💡 SOLUTION: Configure cookies in the 'Cookies & Authentication' section below"
        )
        safe_push_log("   • Use browser cookies (recommended) or")
        safe_push_log("   • Export cookies from browser to file")
    elif cookies_method == "file":
        if is_valid_cookie_file(YOUTUBE_COOKIES_FILE_PATH):
            safe_push_log("⏰ Cookies file configured but may be expired")
            safe_push_log("💡 SOLUTION: Update your cookies file")
            safe_push_log("   • Re-export cookies from your browser")
            safe_push_log("   • Make sure you're logged into YouTube in your browser")
        else:
            safe_push_log("❌ Cookies file configured but invalid/missing")
            safe_push_log("💡 SOLUTION: Fix your cookies file configuration")
    elif cookies_method == "browser":
        browser = st.session_state.get("browser_select", "chrome")
        safe_push_log(f"⏰ Browser cookies configured ({browser}) but may be expired")
        safe_push_log("💡 SOLUTION: Refresh your browser authentication")
        safe_push_log(f"   • Make sure you're logged into YouTube in {browser}")
        safe_push_log("   • Try signing out and back in to YouTube")

    safe_push_log(
        "📺 Note: Age-restricted and private videos always require authentication"
    )


def is_format_unavailable_error(error_message: str) -> bool:
    """Check if error is specifically about requested format not being available"""
    error_lower = error_message.lower()
    return (
        "requested format is not available" in error_lower
        or "format is not available" in error_lower
    )


def log_format_unavailable_error_hint(
    error_message: str = "", current_profile_name: str = ""
):
    """Log specific guidance for format unavailable errors - often auth issues with premium codecs"""

    # Prevent spam - only show detailed explanation once per profile
    session_key = f"format_hint_shown_{current_profile_name}"
    if st.session_state.get(session_key, False):
        # Just show brief message for subsequent failures
        safe_push_log("⚠️ Format rejected (authentication limitation)")
        return

    st.session_state[session_key] = True

    # Analyze the profile being attempted
    profile_info = ""
    if current_profile_name:
        if "av1" in current_profile_name.lower():
            profile_info = "AV1 codec"
        elif "vp9" in current_profile_name.lower():
            profile_info = "VP9 codec"
        elif "opus" in current_profile_name.lower():
            profile_info = "Opus audio"
        else:
            profile_info = current_profile_name

    safe_push_log("🚫 FORMAT AUTHENTICATION ISSUE")
    if profile_info:
        safe_push_log(f"🎯 YouTube refused to serve {profile_info} format")

    safe_push_log(
        "🔍 EXPLANATION: Format was detected as available, but YouTube's download"
    )
    safe_push_log(
        "   API uses stricter authentication for premium codecs than format detection."
    )
    safe_push_log("")

    cookies_method = _get_current_cookies_method()

    if cookies_method == "none":
        safe_push_log("🔧 SOLUTION: Enable authentication cookies for premium formats")
        safe_push_log("   • Use browser cookies (recommended)")
        safe_push_log(
            "   • Premium codecs (AV1, VP9, Opus) typically require authentication"
        )
    elif cookies_method in ["browser", "file"]:
        safe_push_log("💡 SOLUTION: Refresh your authentication")
        safe_push_log("   • Sign out and back into YouTube in your browser")
        safe_push_log("   • Clear browser cache and re-authenticate")
        if "av1" in profile_info.lower():
            safe_push_log("   • AV1 has the strictest authentication requirements")

    safe_push_log("✅ FALLBACK: Trying more compatible profiles next")


def smart_download_with_fallback(
    base_cmd: List[str],
    url: str,
    progress_placeholder=None,
    status_placeholder=None,
    info_placeholder=None,
) -> Tuple[int, str]:
    """
    Intelligent download with progressive fallback strategies

    Returns:
        Tuple[int, str]: (return_code, error_message)
    """
    cookies_available = False
    cookies_part = []

    # Check if cookies are configured
    cookies_method = st.session_state.get("cookies_method", "none")
    if cookies_method != "none":
        cookies_part = build_cookies_params()
        cookies_available = len(cookies_part) > 0

    # Strategy 1: Try without cookies first (fastest)
    if status_placeholder:
        status_placeholder.info(t("status_trying_no_auth"))
    safe_push_log("🚀 Strategy 1: Trying without cookies (fastest)")

    cmd = base_cmd + [url]
    ret = run_cmd(cmd, progress_placeholder, status_placeholder, info_placeholder)

    if ret == 0:
        safe_push_log("✅ Success without authentication!")
        return ret, ""

    # Check if we got an authentication-related error
    last_error = st.session_state.get("last_error", "").lower()
    if not any(
        error in last_error
        for error in ["403", "forbidden", "signature", "unavailable"]
    ):
        return ret, "Non-authentication error"

    safe_push_log("⚠️ Authentication error detected, trying fallback strategies...")

    # Strategy 2: Try different YouTube clients
    for i, client in enumerate(
        YOUTUBE_CLIENT_FALLBACKS[1:], 2
    ):  # Skip default (already tried)
        client_name = client["name"]
        if status_placeholder:
            if client_name == "android":
                status_placeholder.info(t("status_retry_android"))
            elif client_name == "ios":
                status_placeholder.info(t("status_retry_ios"))
            elif client_name == "web":
                status_placeholder.info(t("status_retry_web"))
            else:
                status_placeholder.info(f"🔄 Retry {i}: Using {client_name} client...")

        safe_push_log(f"🔄 Strategy {i}: Trying with {client_name} client")

        cmd = base_cmd + client["args"] + [url]
        ret = run_cmd(cmd, progress_placeholder, status_placeholder, info_placeholder)

        if ret == 0:
            safe_push_log(f"✅ Success with {client_name} client!")
            return ret, ""

    # Strategy 3: Try with cookies if available
    if cookies_available:
        if status_placeholder:
            status_placeholder.info(t("status_retry_cookies"))
        safe_push_log("🍪 Strategy: Trying with authentication cookies")

        # Try each client with cookies
        for client in YOUTUBE_CLIENT_FALLBACKS:
            client_name = client["name"]
            safe_push_log(f"🔄 Trying {client_name} client + cookies")

            cmd = base_cmd + client["args"] + cookies_part + [url]
            ret = run_cmd(
                cmd, progress_placeholder, status_placeholder, info_placeholder
            )

            if ret == 0:
                safe_push_log(f"✅ Success with {client_name} client + cookies!")
                return ret, ""

    # All strategies failed - show comprehensive error message
    if status_placeholder:
        status_placeholder.error("❌ Download failed after all retry attempts")

    safe_push_log("❌ All fallback strategies failed")
    safe_push_log("")
    log_title("🚫 Download failed - Comprehensive troubleshooting:")

    # Show specific error based on what was tried
    if not cookies_available:
        safe_push_log("🔑 PRIMARY ISSUE: No authentication configured")
        safe_push_log("💡 IMMEDIATE SOLUTION:")
        safe_push_log("   1. ⚠️  CONFIGURE COOKIES below")
        safe_push_log("   2. 🌐 Use 'Browser Cookies' (easiest)")
        safe_push_log("   3. 📁 Or export cookies from browser to file")
        safe_push_log("")
        safe_push_log(
            "🎯 KEY INSIGHT: Even public videos need cookies for signature verification!"
        )
    else:
        safe_push_log("🔑 AUTHENTICATION ISSUE: Cookies configured but not working")
        safe_push_log("💡 SOLUTIONS TO TRY:")
        safe_push_log("   1. 🔄 Update your cookies (they may be expired)")
        safe_push_log("   2. 🌐 Sign out and back into YouTube in your browser")
        safe_push_log("   3. 🔁 Try different browser or re-export cookies")
        safe_push_log(f"   4. 📋 Current method: {cookies_method}")

    safe_push_log("")
    safe_push_log(
        "📺 Technical context: YouTube uses encrypted signatures that require"
    )
    safe_push_log("    fresh authentication tokens to decrypt video URLs.")
    safe_push_log("─" * 50)  # Static separator for end of troubleshooting section

    return ret, "Authentication failed after all strategies"


def _build_strategy_command(
    base_cmd: List[str],
    client_args: List[str],
    cookies_part: List[str],
    url: str,
    use_cookies: bool = False,
) -> List[str]:
    """Build complete yt-dlp command with client args and optional cookies"""
    cmd = base_cmd + client_args
    if use_cookies and cookies_part:
        cmd.extend(cookies_part)
    cmd.append(url)
    return cmd


def _get_current_cookies_method() -> str:
    """Get current cookies method from session state"""
    return st.session_state.get("cookies_method", "none")


def _log_cookies_method_status(cookies_method: str) -> None:
    """Log current cookies method status"""
    safe_push_log(f"   4. 📋 Current method: {cookies_method}")


def _log_authentication_solutions(cookies_method: str) -> None:
    """Log common authentication error solutions based on current cookies method"""
    if cookies_method == "none":
        safe_push_log("   1. ⚠️  ENABLE COOKIES - This is likely the main issue")
        safe_push_log("   2. 🌐 Use Browser Cookies (easiest solution)")
        safe_push_log("   3. 📁 Or export cookies from your browser to a file")
    elif cookies_method == "browser":
        safe_push_log("   1. 🔄 UPDATE YOUR COOKIES - They may be expired")
        safe_push_log("   2. 🌐 Sign out and back into YouTube in your browser")
        safe_push_log("   3. 🔁 Try refreshing/re-extracting cookies")
    else:  # file method
        safe_push_log("   1. 🔄 UPDATE YOUR COOKIES - They may be expired")
        safe_push_log("   2. 🌐 Sign out and back into YouTube in your browser")
        safe_push_log("   3. 🔁 Try different browser or re-export cookies")


def _log_strategy_header(
    strategy_name: str, strategy_num: int, total_strategies: int
) -> None:
    """Log strategy attempt header with consistent formatting"""
    safe_push_log("")
    log_title(f"🎯 Strategy {strategy_num}/{total_strategies}: {strategy_name}")


def cleanup_temp_files(base_filename: str, tmp_dir: Path = None) -> None:
    """Clean up temporary files created during download"""
    if tmp_dir is None:
        tmp_dir = TMP_DOWNLOAD_FOLDER

    safe_push_log(t("cleaning_temp_files"))

    try:
        # Clean up various temporary files
        patterns = [f"{base_filename}.*", "*.part", "*.ytdl", "*.temp", "*.tmp"]

        files_cleaned = 0
        for pattern in patterns:
            for file_path in tmp_dir.glob(pattern):
                try:
                    if file_path.is_file():
                        file_path.unlink()
                        files_cleaned += 1
                except Exception as e:
                    safe_push_log(f"⚠️ Could not remove {file_path.name}: {e}")

        if files_cleaned > 0:
            safe_push_log(f"🧹 Cleaned {files_cleaned} temporary files")

        safe_push_log(t("cleanup_complete"))

    except Exception as e:
        safe_push_log(f"⚠️ Error during cleanup: {e}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def move_file(src: Path, dest_dir: Path) -> Path:
    target = dest_dir / src.name
    shutil.move(str(src), str(target))
    return target


def cleanup_extras(tmp_dir: Path, base_filename: str):
    # remove .srt/.vtt residuals + .part
    for ext in (".srt", ".vtt"):
        for f in tmp_dir.glob(f"{base_filename}*{ext}"):
            try:
                f.unlink()
            except Exception:
                pass
    for f in tmp_dir.glob(f"{base_filename}*.*.part"):
        try:
            f.unlink()
        except Exception:
            pass


def delete_intermediate_outputs(tmp_dir: Path, base_filename: str):
    """Cleans any final files before a retry (avoids confusion)."""
    for ext in (".mkv", ".mp4", ".webm"):
        p = tmp_dir / f"{base_filename}{ext}"
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


# === Helpers time ===


def customize_video_metadata(
    video_path: Path, user_title: str, original_title: str = None
) -> bool:
    """
    Customize video metadata using FFmpeg, replacing title with user-provided name
    and preserving original title in album field

    Args:
        video_path: Path to the video file
        user_title: Title provided by the user (from filename input)
        original_title: Original video title from yt-dlp (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        safe_push_log("📝 Customizing video metadata...")

        # Create temporary output file
        temp_output = video_path.with_suffix(f".temp{video_path.suffix}")

        # Build FFmpeg command
        cmd_metadata = [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-i",
            str(video_path),
            "-c",
            "copy",  # Copy streams without re-encoding (fast)
            "-metadata",
            f"title={user_title}",  # Use user-provided title
        ]

        # Add original title as album if available
        if original_title and original_title != user_title:
            cmd_metadata.extend(["-metadata", f"album={original_title}"])

        # Add output path
        cmd_metadata.append(str(temp_output))

        # Execute FFmpeg command
        result = run_subprocess_safe(
            cmd_metadata, timeout=120, error_context="Metadata customization"
        )

        if result.returncode == 0 and temp_output.exists():
            # Replace original file with metadata-customized version
            video_path.unlink()  # Remove original
            temp_output.rename(video_path)  # Rename temp to original
            safe_push_log(f"✅ Metadata customized - Title: {user_title}")
            return True
        else:
            error_msg = result.stderr.strip()
            safe_push_log(f"⚠️ Failed to customize metadata: {error_msg}")
            # Clean up temp file if it exists
            if temp_output.exists():
                temp_output.unlink()
            return False

    except Exception as e:
        safe_push_log(f"⚠️ Error customizing metadata: {e}")
        # Clean up temp file if it exists
        temp_output = video_path.with_suffix(f".temp{video_path.suffix}")
        if temp_output.exists():
            temp_output.unlink()
        return False


def run_subprocess_safe(
    cmd: List[str], timeout: int = 60, error_context: str = ""
) -> subprocess.CompletedProcess:
    """Run subprocess with standardized error handling and timeout"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result
    except subprocess.TimeoutExpired:
        error_msg = f"Command timed out after {timeout} seconds"
        if error_context:
            error_msg = f"{error_context}: {error_msg}"
        safe_push_log(f"⚠️ {error_msg}")
        # Return a fake result object for consistency
        return subprocess.CompletedProcess(cmd, 1, "", error_msg)
    except Exception as e:
        error_msg = f"Command failed: {str(e)}"
        if error_context:
            error_msg = f"{error_context}: {error_msg}"
        safe_push_log(f"❌ {error_msg}")
        return subprocess.CompletedProcess(cmd, 1, "", error_msg)


def get_keyframes(video_path: Path) -> list[float]:
    """
    Extract keyframe timestamps from a video using ffprobe.
    Returns a list of keyframe timestamps in seconds.
    """
    try:
        push_log(t("log_keyframes_extraction"))

        cmd_keyframes = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_packets",
            "-show_entries",
            "packet=pts_time,flags",
            "-of",
            "csv=p=0",
            str(video_path),
        ]

        result = run_subprocess_safe(
            cmd_keyframes, timeout=120, error_context="Keyframes extraction"
        )

        if result.returncode != 0:
            push_log(t("log_keyframes_failed", error=result.stderr))
            return []

        keyframes = []
        for line in result.stdout.strip().split("\n"):
            if line and "," in line:
                parts = line.split(",")
                if len(parts) >= 2 and "K" in parts[1]:
                    try:
                        timestamp = float(parts[0])
                        keyframes.append(timestamp)
                    except ValueError:
                        continue

        keyframes.sort()
        push_log(t("log_keyframes_count", count=len(keyframes)))
        return keyframes

    except Exception as e:
        push_log(t("log_keyframes_error", error=e))
        return []


def find_nearest_keyframes(
    keyframes: list[float], start_sec: int, end_sec: int
) -> tuple[float, float]:
    """
    Find the nearest keyframes to the requested start and end times.
    Returns (nearest_start_keyframe, nearest_end_keyframe).
    """
    if not keyframes:
        return float(start_sec), float(end_sec)

    # Find nearest keyframe to start_sec (can be before or after)
    start_kf = start_sec
    min_start_diff = float("inf")
    for kf in keyframes:
        diff = abs(kf - start_sec)
        if diff < min_start_diff:
            min_start_diff = diff
            start_kf = kf

    # Find nearest keyframe to end_sec (can be before or after)
    end_kf = end_sec
    min_end_diff = float("inf")
    for kf in keyframes:
        diff = abs(kf - end_sec)
        if diff < min_end_diff:
            min_end_diff = diff
            end_kf = kf

    push_log(t("log_keyframes_selected", start=start_kf, end=end_kf))
    push_log(
        t(
            "log_keyframes_offset",
            start_offset=abs(start_kf - start_sec),
            end_offset=abs(end_kf - end_sec),
        )
    )

    return start_kf, end_kf


def safe_push_log(message: str):
    """Safe logging function that works even if logs aren't initialized yet"""
    try:
        if "ALL_LOGS" in globals() and "logs_placeholder" in globals():
            push_log(message)
        else:
            # If logging isn't ready, just print to console for debugging
            print(f"[LOG] {message}")
    except Exception as e:
        print(f"[LOG] {message} (Error: {e})")


def log_title(title: str, underline_char: str = "─"):
    """
    Log a title with automatic underline of the same length

    Args:
        title: The title text to display
        underline_char: Character to use for underline (default: ─)
    """
    # Simply use the full string length - much more natural!
    underline_length = len(title)

    safe_push_log(title)
    safe_push_log(underline_char * underline_length)


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


def parse_format_line(line: str) -> Optional[Dict]:
    """Parse a single format line from yt-dlp output"""
    if not line or line.startswith("[") or line.startswith("Available"):
        return None

    parts = line.split()
    if len(parts) < 3:
        return None

    try:
        format_id = parts[0]
        ext = parts[1] if len(parts) > 1 else "unknown"
        resolution = parts[2] if len(parts) > 2 else "unknown"

        # Skip audio-only formats
        if "audio only" in line.lower() or resolution == "audio":
            return None

        return {
            "id": format_id,
            "ext": ext,
            "resolution": resolution,
            "description": line.strip(),
        }
    except (ValueError, IndexError):
        return None


def get_video_title(url: str, cookies_part: List[str]) -> str:
    """
    Get the title of the video using yt-dlp with retry strategy.
    Returns sanitized title suitable for filename
    """
    safe_push_log("📋 Retrieving video title...")

    # Simple retry strategies for title extraction
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
            result = run_subprocess_safe(
                strategy["cmd"],
                timeout=30,
                error_context=f"Title extraction ({strategy['name']})",
            )

            if result.returncode == 0 and result.stdout.strip():
                title = result.stdout.strip()
                # Sanitize title for filename
                sanitized = sanitize_filename(title)
                safe_push_log(f"✅ Title retrieved {strategy['name']}: {title}")
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

        except Exception as e:
            safe_push_log(f"⚠️ Title extraction {strategy['name']} error: {e}")
            continue

    # All strategies failed
    safe_push_log("⚠️ Could not retrieve video title, using default")
    return "video"


def get_video_formats(url: str, cookies_part: List[str]) -> List[Dict]:
    """
    Get available video formats for a URL using yt-dlp with robust retry strategy.
    Returns a list of format dictionaries with id, ext, resolution, description
    Ordered by quality (highest first)

    Retry strategy:
    1. Try with provided cookies + different YouTube clients
    2. Try without cookies + different YouTube clients
    3. Handle temporary failures with backoff
    """
    safe_push_log(t("log_formats_detecting"))

    # Define retry strategies
    strategies = []

    # Strategy 1: With cookies (if available)
    if cookies_part:
        for client in YOUTUBE_CLIENT_FALLBACKS:
            strategies.append(
                {
                    "name": f"cookies + {client['name']} client",
                    "cmd_base": ["yt-dlp", "--list-formats", "--no-download"]
                    + client["args"]
                    + cookies_part,
                    "auth_attempt": True,
                }
            )

    # Strategy 2: Without cookies
    for client in YOUTUBE_CLIENT_FALLBACKS:
        strategies.append(
            {
                "name": f"{client['name']} client (no auth)",
                "cmd_base": ["yt-dlp", "--list-formats", "--no-download"]
                + client["args"],
                "auth_attempt": False,
            }
        )

    last_error = ""

    # Try each strategy
    for i, strategy in enumerate(strategies, 1):
        try:
            # Clear status for each attempt
            auth_status = (
                "🔐 with authentication"
                if strategy["auth_attempt"]
                else "🌐 without authentication"
            )
            safe_push_log("")
            safe_push_log(f"🔁 Attempt {i}/{len(strategies)}: {strategy['name']}")
            safe_push_log(f"   💡 Testing format extraction {auth_status}")

            cmd_formats = strategy["cmd_base"] + [url]

            result = run_subprocess_safe(
                cmd_formats,
                timeout=60,
                error_context=f"Formats extraction ({strategy['name']})",
            )

            if result.returncode == 0:
                # Success! Parse the output
                formats = []
                for line in result.stdout.strip().split("\n"):
                    format_info = parse_format_line(line)
                    if format_info:
                        formats.append(format_info)

                if formats:  # Only return if we actually got formats
                    # Sort formats by quality (highest first)
                    formats.sort(
                        key=lambda x: extract_resolution_value(x["resolution"]),
                        reverse=True,
                    )

                    # Analyze quality of found formats
                    max_res = max(
                        extract_resolution_value(f["resolution"]) for f in formats
                    )
                    has_4k = max_res >= 2160
                    has_hd = max_res >= 1080

                    quality_note = ""
                    if has_4k:
                        quality_note = "🎬 4K+ formats available"
                    elif has_hd:
                        quality_note = "📺 HD formats available"
                    else:
                        quality_note = "📱 Standard definition formats"

                    safe_push_log(f"   ✅ SUCCESS! Found {len(formats)} video formats")
                    safe_push_log(f"   {quality_note} (max: {max_res}p)")
                    return formats
                else:
                    safe_push_log("   ⚠️ Connected but no parseable formats found")

            else:
                # Strategy failed, log and continue
                error_msg = result.stderr.strip()
                last_error = error_msg

                # Provide user-friendly error interpretation
                if "sign in" in error_msg.lower() or "login" in error_msg.lower():
                    safe_push_log("   🔐 Authentication required for this strategy")
                elif "private" in error_msg.lower():
                    safe_push_log("   🔒 Video appears to be private or restricted")
                elif (
                    "not available" in error_msg.lower()
                    or "unavailable" in error_msg.lower()
                ):
                    safe_push_log("   🌍 Video not available for this client/region")
                elif "cookies" in error_msg.lower():
                    safe_push_log("   🍪 Cookie authentication issue")
                else:
                    safe_push_log(f"   ❌ Failed: {error_msg[:80]}...")

                # For auth errors, only show detailed hint once (from first auth attempt)
                if strategy["auth_attempt"] and i == 1:
                    if is_format_unavailable_error(error_msg):
                        log_format_unavailable_error_hint(error_msg)
                    elif is_authentication_error(error_msg):
                        log_authentication_error_hint(error_msg)

                # Add small delay before next attempt to avoid rate limiting
                if i < len(strategies):
                    import time

                    time.sleep(0.5)

        except Exception as e:
            safe_push_log(f"   💥 Unexpected error: {str(e)[:60]}...")
            last_error = str(e)
            continue

    # All strategies failed - provide comprehensive guidance
    safe_push_log("")
    log_title("❌ Format detection failed")

    # Categorize the likely issue
    if cookies_part:
        safe_push_log(
            "🔍 DIAGNOSIS: Authentication was attempted but all methods failed"
        )
        safe_push_log("")
        safe_push_log("🆕 SOLUTIONS TO TRY:")
        safe_push_log("   1. 🍪 Refresh your cookies:")
        safe_push_log("      • Sign out and back into YouTube in your browser")
        safe_push_log("      • Clear browser cache and re-extract cookies")
        safe_push_log("      • Try a different browser (Chrome, Firefox, Safari)")
        safe_push_log("")
        safe_push_log("   2. 🔄 Check video accessibility:")
        safe_push_log("      • Open the video in your browser to confirm it works")
        safe_push_log("      • Make sure you're logged into the same YouTube account")
    else:
        safe_push_log("🔍 DIAGNOSIS: No authentication configured")
        safe_push_log("")
        safe_push_log("🛠️ SOLUTIONS TO TRY:")
        safe_push_log("   1. 🍪 Enable browser cookies:")
        safe_push_log("      • Many videos require authentication for format access")
        safe_push_log("      • Configure cookies in the app settings")
        safe_push_log("")
        safe_push_log("   2. 🔄 Check video accessibility:")
        safe_push_log("      • Open the video in your browser to confirm it exists")
        safe_push_log("      • Some videos may be region-locked or private")

    safe_push_log("")
    safe_push_log("🌍 OTHER POSSIBLE CAUSES:")
    safe_push_log("   • Video is private, unlisted, or deleted")
    safe_push_log("   • Video is region-locked (geo-blocked)")
    safe_push_log("   • Temporary YouTube API rate limiting")
    safe_push_log("   • Network connectivity issues")
    safe_push_log("   • YouTube changed their API (rare)")

    if last_error:
        safe_push_log("")
        safe_push_log("🔍 TECHNICAL DETAILS:")
        safe_push_log(f"   Last error: {last_error[:150]}...")

    safe_push_log("")
    safe_push_log("💡 If this continues happening:")
    safe_push_log("   • Try a different video to test if the issue is video-specific")
    safe_push_log("   • Check the HomeTube GitHub issues for known problems")
    safe_push_log("   • Report the issue with the video URL and error details")

    return []


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


# --- 3) Cleanup/sort/merge (optional) ---
def merge_overlaps(segments, margin=0.0):
    """Merge overlapping segments (keeping main 'sponsor' category as priority)."""
    segs = sorted(
        [
            (max(0.0, s["start"] - margin), s["end"] + margin, s["category"])
            for s in segments
        ]
    )
    merged = []
    for a, b, cat in segs:
        if not merged or a > merged[-1][1]:
            merged.append([a, b, {cat}])
        else:
            merged[-1][1] = max(merged[-1][1], b)
            merged[-1][2].add(cat)
    return [{"start": a, "end": b, "categories": sorted(cats)} for a, b, cats in merged]


# --- 4) Build intervals to keep + map timecodes after removal ---
def invert_segments(segments, total_duration):
    """Returns the intervals [start,end) to keep when removing 'segments'."""
    keep = []
    cur = 0.0
    for s in sorted(segments, key=lambda x: x["start"]):
        a, b = max(0.0, s["start"]), min(total_duration, s["end"])
        if a > cur:
            keep.append((cur, a))
        cur = max(cur, b)
    if cur < total_duration:
        keep.append((cur, total_duration))
    return keep


def build_time_remap(segments, total_duration):
    """
    Builds a mapping original_time -> time_after_cut.
    Returns a `remap(t)` function + a list of cumulative jumps.
    """
    keep = invert_segments(segments, total_duration)
    # Build pairs (orig_start, orig_end, new_start)
    mapping = []
    new_t = 0.0
    for a, b in keep:
        mapping.append((a, b, new_t))
        new_t += b - a

    def remap(t: float):
        for a, b, ns in mapping:
            if t < a:
                # We're in a cut zone before this block
                return ns
            if a <= t <= b:
                return ns + (t - a)
        # t beyond or in a final cut zone -> clamp to final duration
        return mapping[-1][2] if mapping else 0.0

    return remap, mapping


# --- 5) Helper to recalculate an interval (start,end) after cutting ---
def remap_interval(start, end, remap):
    s2 = remap(start)
    e2 = remap(end)
    # If start/end fall WITHIN a removed segment, remap returns to the useful edge.
    # We protect against s2>e2: we clamp and possibly signal an empty interval.
    if e2 < s2:
        e2 = s2
    return (s2, e2)


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

    def update_speed(self, speed: str):
        self.speed = speed

    def update_eta(self, eta: str):
        self.eta = eta

    def update_size(self, size: str):
        self.file_size = size

    def update_fragments(self, fragments: str):
        self.fragments_info = fragments

    def display(self, info_placeholder):
        """Display current metrics in the UI"""
        update_download_metrics(
            info_placeholder,
            speed=self.speed,
            eta=self.eta,
            size=self.file_size,
            fragments=self.fragments_info,
        )

    def reset(self):
        """Reset all metrics"""
        self.speed = ""
        self.eta = ""
        self.file_size = ""
        self.fragments_info = ""
        self.last_progress = 0


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
    cutting_mode = st.radio(
        t("cutting_mode_prompt"),
        options=["keyframes", "precise"],
        format_func=lambda x: {
            "keyframes": t("cutting_mode_keyframes"),
            "precise": t("cutting_mode_precise"),
        }[x],
        index=0,  # Default to keyframes (faster)
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

    # Button to detect formats (DYNAMIC!)
    if url:
        st.info(t("quality_auto_info"))

        if st.button(
            t("quality_detect_btn"),
            help=t("quality_detect_help"),
            key="detect_formats_btn",
        ):
            # Clean URL and get cookies for format detection
            clean_url = sanitize_url(url)
            cookies_part = build_cookies_params()

            # Get available formats
            with st.spinner(t("quality_detecting")):
                formats = get_video_formats(clean_url, cookies_part)
                st.session_state.available_formats = formats
                if formats:
                    st.success(t("formats_detected", count=len(formats)))
                    st.rerun()  # Refresh to show the new options
                else:
                    st.warning(t("no_formats_detected"))
                    # Provide helpful suggestions about cookies
                    # with st.expander("💡 Troubleshooting", expanded=True):
                    #     st.markdown(
                    #         """
                    #     **🇬🇧 English:**
                    #     - This video might be **age-restricted**, **private**, or **region-locked**
                    #     - Your **cookies might be invalid** or expired
                    #     - Try using **browser cookies** instead of file cookies
                    #     - Make sure you're signed in to YouTube in your browser

                    #     **Alternative suggestions:**
                    #     - This video might be **age-restricted**, **private**, or **geo-blocked**
                    #     - Your **cookies might be invalid** or expired
                    #     - Try using **browser cookies** instead of file cookies
                    #     - Make sure you're signed in to YouTube in your browser
                    #     """
                    #     )

                    # Quick link to cookies section
                    if st.button("🔧 Configure Cookies"):
                        st.rerun()

    # Quality Profile Selection
    st.subheader("🏆 Quality Profiles")

    # Download mode selection
    download_mode = st.radio(
        "Download mode:",
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

        # Show the profile order for transparency
        with st.expander("📋 Profile Order (Auto Mode)", expanded=False):
            for i, profile in enumerate(QUALITY_PROFILES, 1):
                st.write(f"{i}. **{profile['label']}** - {profile['description']}")

        # Store auto mode
        selected_profile = None

    else:
        st.warning(
            "🔒 **Forced Mode**: Only your selected profile will be tried. Download will fail if this specific combination is unavailable."
        )

        # Profile selection
        selected_profile = st.selectbox(
            "Select quality profile:",
            options=[profile["name"] for profile in QUALITY_PROFILES],
            format_func=lambda x: next(
                p["label"] for p in QUALITY_PROFILES if p["name"] == x
            ),
            index=0,
            help="Choose your exact quality target. No fallback will be attempted.",
            key="quality_profile",
        )

        # Show selected profile details
        profile = get_profile_by_name(selected_profile)
        if profile:
            st.info(f"🎯 **{profile['label']}**")
            st.write(f"📋 {profile['description']}")
            st.write(
                f"🎬 Video: **{profile['video_codec']}** | 🎵 Audio: **{profile['audio_codec']}** | 📦 Container: **{profile['container']}**"
            )

    # Advanced options
    with st.expander("⚙️ Advanced Profile Options", expanded=False):
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

    # Legacy manual format selection (for backward compatibility)
    with st.expander("🔧 Manual format selection (legacy)", expanded=False):
        st.warning(
            "⚠️ This overrides the profile system above. Only use if you need a specific format ID."
        )

        if st.session_state.available_formats:
            format_options = [t("quality_auto_option")] + [
                f"{fmt['resolution']} - {fmt['ext']} ({fmt['id']})"
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
            st.info("Click 'Detect formats' to see available options")


# Optional embedding section for chapter and subs
with st.expander(f"{t('embedding_title')}", expanded=False):
    # === SUBTITLES SECTION ===
    st.markdown(f"### {t('subtitles_section_title')}")
    st.info(t("subtitles_info"))

    embed_subs = st.checkbox(
        t("embed_subs"),
        value=True,  # Checked by default
        key="embed_subs",
        help=t("embed_subs_help"),
    )

    # === CHAPTERS SECTION ===
    st.markdown(f"### {t('chapters_section_title')}")
    st.info(t("chapters_info"))

    embed_chapters = st.checkbox(
        t("embed_chapters"),
        value=True,
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
        value=CONFIG.get("YTDLP_CUSTOM_ARGS", ""),
        placeholder=t("ytdlp_custom_args_placeholder"),
        help=t("ytdlp_custom_args_help"),
        key="ytdlp_custom_args",
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


def update_download_metrics(info_placeholder, speed="", eta="", size="", fragments=""):
    """Update the download metrics display"""
    if any([speed, eta, size, fragments]):
        metrics_parts = []
        if speed:
            metrics_parts.append(f"🚀 **Speed:** {speed}")
        if eta:
            metrics_parts.append(f"⏱️ **ETA:** {eta}")
        if size:
            metrics_parts.append(f"📦 **Size:** {size}")
        if fragments:
            metrics_parts.append(f"🧩 **Fragments:** {fragments}")

        if metrics_parts:
            with info_placeholder.container():
                cols = st.columns(len(metrics_parts))
                for i, metric in enumerate(metrics_parts):
                    cols[i].markdown(metric)


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

    # Get centralized configuration
    config = get_download_configuration()
    download_mode = config["download_mode"]
    selected_profile_name = config["selected_profile_name"]
    selected_format = config["selected_format"]
    refuse_quality_downgrade = config["refuse_quality_downgrade"]

    if download_mode == "forced" and selected_profile_name:
        selected_profile = get_profile_by_name(selected_profile_name)
        if selected_profile:
            push_log(f"🔒 Forced profile mode: {selected_profile['label']}")
            push_log(f"📋 Description: {selected_profile['description']}")
    else:
        push_log("🤖 Auto mode: Will try all profiles in quality order")

    if selected_format != "auto":
        # Manual format override
        format_spec = f"{selected_format}+ba/b"
        push_log(t("log_quality_selected", format_id=selected_format))
        quality_strategy_to_use = None  # Don't use profile system
    else:
        # Use profile system - determine format_spec based on mode
        if download_mode == "forced" and selected_profile_name:
            # Forced profile mode
            selected_profile = get_profile_by_name(selected_profile_name)
            if selected_profile:
                format_spec = selected_profile["format"]
                push_log(f"🎯 Format: {format_spec}")
                push_log(f"📊 Sort: {selected_profile['format_sort']}")
                quality_strategy_to_use = selected_profile
            else:
                # Fallback to auto if profile not found
                format_spec = "bv*+ba/b"
                quality_strategy_to_use = None
        else:
            # Auto mode - profiles will be tried in smart_download_with_profiles
            format_spec = (
                "bv*+ba/b"  # Placeholder, actual formats determined by profiles
            )
            quality_strategy_to_use = "auto_profiles"  # Signal to use profile system

    # --- yt-dlp base command construction
    force_mp4 = do_cut and subs_selected  # Force MP4 for sections with subtitles
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
    # Check if profile system should be used (new system vs legacy fallback)
    if quality_strategy_to_use == "auto_profiles" or isinstance(
        quality_strategy_to_use, dict
    ):
        # Premium quality mode: try all strategies with progressive fallback
        if download_mode == "forced" and selected_profile_name:
            push_log(f"🔒 FORCED PROFILE MODE: {selected_profile_name}")
            ret_dl, error_msg = smart_download_with_profiles(
                base_output,
                tmp_subfolder_dir,
                embed_chapters,
                embed_subs,
                force_mp4,
                ytdlp_custom_args,
                clean_url,
                "forced",
                selected_profile_name,
                refuse_quality_downgrade,
                do_cut,
                subs_selected,
                sb_choice,
                progress_placeholder,
                status_placeholder,
                info_placeholder,
            )
        else:
            push_log(
                "🤖 AUTO PROFILE MODE: Testing all profiles with intelligent fallback"
            )
            ret_dl, error_msg = smart_download_with_profiles(
                base_output,
                tmp_subfolder_dir,
                embed_chapters,
                embed_subs,
                force_mp4,
                ytdlp_custom_args,
                clean_url,
                "auto",
                None,
                refuse_quality_downgrade,
                do_cut,
                subs_selected,
                sb_choice,
                progress_placeholder,
                status_placeholder,
                info_placeholder,
            )
    else:
        # Standard quality mode: use existing fallback
        push_log("📺 STANDARD QUALITY MODE: Using classic client fallback")
        ret_dl, error_msg = smart_download_with_fallback(
            cmd_base,
            clean_url,
            progress_placeholder,
            status_placeholder,
            info_placeholder,
        )

    # Handle cancellation
    if ret_dl == -1:
        status_placeholder.info(t("cleaning_temp_files"))
        cleanup_temp_files(base_output, tmp_subfolder_dir)
        status_placeholder.success(t("cleanup_complete"))

        # Mark download as finished
        st.session_state.download_finished = True
        st.stop()

    # Search for the final file in TMP subfolder
    final_tmp = None
    for ext in (".mkv", ".mp4", ".webm"):
        p = tmp_subfolder_dir / f"{base_output}{ext}"
        if p.exists():
            final_tmp = p
            break

    if not final_tmp:
        status_placeholder.error(t("error_download_failed"))
        st.stop()

    # === Post-processing according to scenario ===
    final_source = final_tmp

    # If sections requested → cut with ffmpeg using selected mode
    if do_cut:
        # Get cutting mode from UI
        cut_mode = st.session_state.get("cutting_mode", "keyframes")
        push_log(t("log_cutting_mode_selected", mode=cut_mode))

        status_placeholder.info(t("status_cutting_video"))

        # Create the final cut output file - always use MKV to preserve AV1/Opus
        cut_output = tmp_subfolder_dir / f"{base_output}_cut.mkv"

        if cut_output.exists():
            try:
                cut_output.unlink()
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

        # === NEW 3-STEP CUTTING PROCESS FOR PERFECT SUBTITLES ===
        push_log("")
        push_log("🎯 Using 3-step cutting process for perfect subtitle synchronization")
        push_log("   1. TRIM: Cut subtitles with original timestamps")
        push_log("   2. REBASE: Shift subtitle timestamps to start at 00:00")
        push_log("   3. MUX: Cut video and add processed subtitles")
        push_log("")

        # Find subtitle files to process
        processed_subtitle_files = []
        if subs_selected:
            for lang in subs_selected:
                # Try multiple possible subtitle file patterns
                possible_srt_files = [
                    tmp_subfolder_dir / f"{base_output}.{lang}.srt",
                    tmp_subfolder_dir / f"{base_output}.srt",
                    tmp_subfolder_dir / f"{base_output}.{lang}.vtt",
                    tmp_subfolder_dir / f"{base_output}.vtt",
                ]

                srt_file = None
                for possible_file in possible_srt_files:
                    if possible_file.exists():
                        srt_file = possible_file
                        break

                if srt_file:
                    push_log(f"📝 Processing subtitle file: {srt_file.name} ({lang})")

                    # STEP 1: TRIM - Cut subtitle with original timestamps
                    cut_srt_file = tmp_subfolder_dir / f"{base_output}-cut.{lang}.srt"
                    cmd_trim = [
                        "ffmpeg",
                        "-y",
                        "-loglevel",
                        "warning",
                        "-i",
                        str(srt_file),
                        "-ss",
                        str(actual_start),
                        "-t",
                        str(duration),
                        "-c:s",
                        "srt",
                        str(cut_srt_file),
                    ]

                    push_log(
                        f"   📝 Step 1 - TRIM: Cutting {lang} subtitles ({actual_start:.3f}s + {duration:.3f}s)"
                    )
                    ret_trim = run_cmd(
                        cmd_trim,
                        progress_placeholder,
                        status_placeholder,
                        info_placeholder,
                    )
                    if ret_trim != 0 or not cut_srt_file.exists():
                        push_log(f"   ⚠️ Failed to trim subtitles for {lang}, skipping")
                        continue

                    # STEP 2: REBASE - Shift timestamps to start at 00:00
                    final_srt_file = (
                        tmp_subfolder_dir / f"{base_output}-cut-final.{lang}.srt"
                    )
                    cmd_rebase = [
                        "ffmpeg",
                        "-y",
                        "-loglevel",
                        "warning",
                        "-itsoffset",
                        f"-{actual_start}",
                        "-i",
                        str(cut_srt_file),
                        "-c:s",
                        "srt",
                        str(final_srt_file),
                    ]

                    push_log(
                        f"   🔄 Step 2 - REBASE: Shifting {lang} timestamps by -{actual_start:.3f}s"
                    )
                    ret_rebase = run_cmd(
                        cmd_rebase,
                        progress_placeholder,
                        status_placeholder,
                        info_placeholder,
                    )
                    if ret_rebase != 0 or not final_srt_file.exists():
                        push_log(
                            f"   ⚠️ Failed to rebase subtitles for {lang}, skipping"
                        )
                        continue

                    # Clean up intermediate file
                    try:
                        cut_srt_file.unlink()
                    except Exception:
                        pass

                    processed_subtitle_files.append((lang, final_srt_file))
                    push_log(f"   ✅ Successfully processed {lang} subtitles")
                else:
                    push_log(f"   ⚠️ Subtitle file not found for {lang}")

        # STEP 3: MUX - Cut video and add processed subtitles
        push_log("📹 Step 3 - MUX: Cutting video and adding processed subtitles")

        # Build video cutting command
        cmd_cut = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "warning",
            "-ss",
            str(actual_start),
            "-t",
            str(duration),
            "-i",
            str(final_tmp),
        ]

        # Add processed subtitle inputs
        for lang, srt_file in processed_subtitle_files:
            cmd_cut.extend(["-i", str(srt_file)])

        # Video and audio mappings
        cmd_cut.extend(
            [
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
            ]
        )

        # Subtitle mappings
        for i, (lang, _) in enumerate(processed_subtitle_files):
            cmd_cut.extend(["-map", f"{i+1}:0"])

        # Exclude attached pictures
        cmd_cut.extend(["-map", "-0:m:attached_pic"])

        # Always use stream copy to preserve AV1/Opus in MKV
        cmd_cut.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "srt"])

        # Subtitle metadata
        if processed_subtitle_files:
            first_lang = processed_subtitle_files[0][0]
            cmd_cut.extend(
                [
                    "-disposition:s:0",
                    "default",
                    "-metadata:s:s:0",
                    f"language={first_lang}",
                ]
            )

        # Additional options for perfect sync
        cmd_cut.extend(
            [
                "-shortest",
                "-avoid_negative_ts",
                "make_zero",
                "-max_interleave_delta",
                "0",
                str(cut_output),
            ]
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
                cleanup_temp_files(base_output, tmp_subfolder_dir)
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
        final_extension = cut_output.suffix  # .mkv or .mp4
        final_cut_name = tmp_subfolder_dir / f"{base_output}{final_extension}"
        if final_cut_name.exists():
            try:
                final_cut_name.unlink()
            except Exception:
                pass
        cut_output.rename(final_cut_name)

        # The renamed cut file becomes our final source
        final_source = final_cut_name

        # Delete the original complete file to save space
        try:
            if final_tmp.exists() and final_tmp != final_source:
                final_tmp.unlink()
        except Exception as e:
            push_log(t("log_cleanup_warning", error=e))
    else:
        # No cutting, use the original downloaded file
        final_source = final_tmp  # === Cleanup + move
    cleanup_extras(tmp_subfolder_dir, base_output)

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

        except Exception as e:
            push_log(f"⚠️ Error during metadata customization: {e}")

    try:
        final_moved = move_file(final_source, dest_dir)
        progress_placeholder.progress(100, text=t("status_completed"))

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

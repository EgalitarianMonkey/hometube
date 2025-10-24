"""
URL analysis utilities for HomeTube.

This module provides pure functions for URL analysis logic,
without Streamlit dependencies, making them easy to test.
"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Tuple

from app.logs_utils import safe_push_log


# === URL MANIPULATION ===


def sanitize_url(url: str) -> str:
    """
    Clean and validate URL, removing YouTube timestamp parameters.

    Args:
        url: URL to sanitize

    Returns:
        Cleaned URL
    """
    if not url:
        return ""

    url = url.strip()

    # Add protocol if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Remove YouTube timestamp parameters (HomeTube specific)
    url = url.split("&t=")[0]
    url = url.split("?t=")[0]

    return url


def video_id_from_url(url: str) -> str:
    """
    Extract video ID from YouTube URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID or empty string if not found
    """
    if not url:
        return ""

    # Standard YouTube URL patterns
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
        r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",  # Support for Shorts
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return ""


# === URL INFO FILE OPERATIONS ===


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


def save_url_info(json_path: Path, url_info: Dict) -> bool:
    """
    Save URL info to JSON file.

    Args:
        json_path: Path where to save the JSON file
        url_info: Dictionary with URL information

    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Ensure parent directory exists
        json_path.parent.mkdir(parents=True, exist_ok=True)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(url_info, f, indent=2, ensure_ascii=False)

        safe_push_log(f"💾 URL info saved to {json_path}")
        return True

    except Exception as e:
        safe_push_log(f"⚠️ Could not save URL info to file: {e}")
        return False


def check_url_info_integrity(url_info: Dict) -> bool:
    """
    Check if url_info contains premium formats (AV1 or VP9).

    Sometimes YouTube returns limited format information (only h264),
    even when premium formats are available. This function detects
    incomplete responses that should be retried.

    Args:
        url_info: Dictionary from yt-dlp JSON output

    Returns:
        bool: True if premium formats (AV1/VP9) are present, False if only h264
    """
    if not url_info or "error" in url_info:
        return False

    formats = url_info.get("formats", [])
    if not formats:
        return False

    # Check for premium codecs in video formats
    for fmt in formats:
        vcodec = fmt.get("vcodec", "").lower()

        # Skip audio-only formats
        if vcodec == "none":
            continue

        # Check for AV1 codec
        if "av01" in vcodec or "av1" in vcodec:
            return True

        # Check for VP9 codec
        if "vp9" in vcodec or "vp09" in vcodec:
            return True

    # If we only found h264/avc formats, this might be incomplete
    return False


# === INTELLIGENT CACHING ===


def is_url_info_complet(json_path: Path) -> Tuple[bool, Optional[Dict]]:
    """
    Check if existing url_info.json should be reused based on integrity.

    Strategy:
    1. If file doesn't exist → download needed (False, None)
    2. If file is corrupted → download needed (False, None)
    3. If it's a playlist → always reuse (True, data)
    4. If it's a video:
       - Has premium formats (AV1/VP9) → reuse (True, data)
       - Only h264 formats → download needed (False, None)

    Args:
        json_path: Path to url_info.json file

    Returns:
        Tuple[bool, Optional[Dict]]:
        - bool: True if should reuse, False if should download
        - Optional[Dict]: The loaded data if reusable, None otherwise
    """
    # Check if file exists
    if not json_path.exists():
        safe_push_log(f"📋 No existing url_info.json at {json_path}")
        return False, None

    # Try to load and parse the file
    try:
        safe_push_log("📋 Found existing url_info.json, checking integrity...")
        with open(json_path, "r", encoding="utf-8") as f:
            existing_info = json.load(f)

        # Check if it's a video or playlist
        is_video = existing_info.get("_type") == "video" or "duration" in existing_info
        is_playlist = existing_info.get("_type") == "playlist"

        # For playlists, always reuse
        if is_playlist:
            safe_push_log("✅ Existing url_info.json (playlist) - reusing it")
            return True, existing_info

        # For videos, check integrity (premium formats presence)
        if is_video:
            has_premium = check_url_info_integrity(existing_info)

            if has_premium:
                safe_push_log(
                    "✅ Existing url_info.json has premium formats - reusing it"
                )
                return True, existing_info
            else:
                safe_push_log(
                    "⚠️ Existing url_info.json has limited formats (h264 only) - will re-download"
                )
                return False, None

        # Unknown type, be safe and re-download
        safe_push_log(
            f"⚠️ Unknown content type in url_info.json: {existing_info.get('_type')} - will re-download"
        )
        return False, None

    except json.JSONDecodeError as e:
        safe_push_log(f"⚠️ Corrupted url_info.json: {e} - will re-download")
        return False, None
    except KeyError as e:
        safe_push_log(f"⚠️ Invalid url_info.json structure: {e} - will re-download")
        return False, None
    except Exception as e:
        safe_push_log(f"⚠️ Could not read url_info.json: {e} - will re-download")
        return False, None


# === URL INFO DOWNLOAD & BUILD ===


def build_url_info(
    clean_url: str,
    json_output_path: Path,
    cookies_params: list,
    youtube_cookies_file_path: str = "",
    cookies_from_browser: str = "",
    youtube_clients: list = None,
) -> Dict:
    """
    Download and build url_info.json with integrity checks and smart retries.

    This function:
    1. Runs yt-dlp to fetch video/playlist information
    2. Handles authentication errors with helpful messages
    3. Performs integrity checks for premium formats (AV1/VP9)
    4. Retries with enhanced options if limited formats detected
    5. Saves the result to json_output_path
    6. Records the YouTube client that succeeded (for consistent downloads)

    Args:
        clean_url: Sanitized video/playlist URL
        json_output_path: Path where to save url_info.json
        cookies_params: List of yt-dlp cookie parameters (from build_cookies_params)
        youtube_cookies_file_path: Path to cookies file (for error messages)
        cookies_from_browser: Browser name (for error messages)
        youtube_clients: List of YouTube client configs to try (from config.YOUTUBE_CLIENT_FALLBACKS)

    Returns:
        Dict with video/playlist information or {"error": "..."} if failed
    """
    import subprocess
    from app.config import YOUTUBE_CLIENT_FALLBACKS

    # Log cookie status for debugging
    if cookies_params:
        if "--cookies" in cookies_params:
            safe_push_log("🍪 URL analysis using cookies file")
        elif "--cookies-from-browser" in cookies_params:
            safe_push_log("🍪 URL analysis using browser cookies")
    else:
        safe_push_log("⚠️ URL analysis without cookies - may trigger bot detection")

    # Use provided clients or default from config
    clients_to_try = (
        youtube_clients if youtube_clients is not None else YOUTUBE_CLIENT_FALLBACKS
    )

    # Try with different YouTube clients to find one that works
    successful_client = "default"  # Track which client worked
    result = None
    info = None

    for client_config in clients_to_try:
        client_name = client_config["name"]
        client_args = client_config["args"]

        safe_push_log(f"🔍 Trying URL analysis with {client_name} client...")

        # Run yt-dlp with JSON output, skip download, flat playlist mode
        cmd = [
            "yt-dlp",
            "-J",  # JSON output
            "--skip-download",  # Don't download
            "--flat-playlist",  # For playlists, get basic info without extracting all videos
        ]

        # Add client-specific args
        cmd.extend(client_args)

        # Add URL
        cmd.append(clean_url)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            safe_push_log(f"⏱️ {client_name} client timed out, trying next...")
            continue

        if result.returncode == 0:
            # Success! Parse and check quality
            try:
                info = json.loads(result.stdout)
                successful_client = client_name
                safe_push_log(f"✅ URL analysis succeeded with {client_name} client")
                break  # Found a working client
            except json.JSONDecodeError:
                safe_push_log(f"⚠️ {client_name} returned invalid JSON, trying next...")
                continue

    # If all clients failed, fall back to old behavior with enhanced retry
    if result is None or result.returncode != 0 or info is None:
        safe_push_log(
            "⚠️ All YouTube clients failed, trying with cookies + enhancements..."
        )
        cmd = [
            "yt-dlp",
            "-J",  # JSON output
            "--skip-download",  # Don't download
            "--flat-playlist",  # For playlists, get basic info without extracting all videos
            clean_url,
        ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {
            "error": "Request timed out (max 30 seconds). Try again or check your connection."
        }

    if result.returncode != 0:
        # Check if error is authentication-related (age restriction, bot detection, etc.)
        error_msg = result.stderr if result.stderr else ""
        needs_auth = any(
            [
                "Sign in to confirm" in error_msg,
                "confirm your age" in error_msg,
                "age" in error_msg.lower() and "restricted" in error_msg.lower(),
                "inappropriate for some users" in error_msg,
                "requires authentication" in error_msg,
                "login required" in error_msg,
            ]
        )

        # If first attempt failed and we have cookies available, try with cookies
        if needs_auth and cookies_params:
            safe_push_log("🔐 Authentication required, retrying with cookies...")
            cmd_with_auth = [
                "yt-dlp",
                "-J",
                "--skip-download",
                "--flat-playlist",
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--extractor-retries",
                "3",
                "--no-cache-dir",
                *cookies_params,
                clean_url,
            ]

            try:
                result = subprocess.run(
                    cmd_with_auth, capture_output=True, text=True, timeout=45
                )

                if result.returncode == 0:
                    safe_push_log("✅ Authentication successful with cookies")
                    # Continue to JSON parsing below
                else:
                    error_msg = (
                        result.stderr[:400] if result.stderr else "Unknown error"
                    )
            except subprocess.TimeoutExpired:
                return {
                    "error": "Request timed out (max 45 seconds). Try again or check your connection."
                }

        # If still failing or no cookies available, try enhanced retry without auth
        if result.returncode != 0:
            safe_push_log("⚠️ Retrying with enhanced options...")
            cmd_retry = [
                "yt-dlp",
                "-J",
                "--skip-download",
                "--flat-playlist",
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "--extractor-retries",
                "3",
                "--no-cache-dir",
            ]
            # Only add cookies if we haven't tried them yet
            if not needs_auth and cookies_params:
                cmd_retry.extend(cookies_params)

            cmd_retry.append(clean_url)

            try:
                result = subprocess.run(
                    cmd_retry, capture_output=True, text=True, timeout=45
                )
            except subprocess.TimeoutExpired:
                return {
                    "error": "Request timed out (max 45 seconds). Try again or check your connection."
                }

        if result.returncode != 0:
            error_msg = result.stderr[:400] if result.stderr else "Unknown error"

            # Check for bot detection error
            if "Sign in to confirm you're not a bot" in error_msg:
                return _build_bot_detection_error(
                    youtube_cookies_file_path, cookies_from_browser
                )

            # Check for age restriction error
            elif "confirm your age" in error_msg or (
                "age" in error_msg.lower() and "restricted" in error_msg.lower()
            ):
                return _build_age_restriction_error(
                    youtube_cookies_file_path, cookies_from_browser
                )

            return {"error": f"yt-dlp failed: {error_msg}"}

    # Parse JSON output
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON: {str(e)}"}

    # === INTEGRITY CHECK WITH SMART RETRY ===
    # Check if we got premium formats (AV1/VP9) for videos (not playlists)
    is_video = info.get("_type") == "video" or "duration" in info

    if is_video:
        has_premium_formats = check_url_info_integrity(info)

        if not has_premium_formats:
            safe_push_log(
                "⚠️ Limited formats detected (h264 only), retrying for premium formats..."
            )

            # Try up to 2 additional attempts with different strategies
            best_info = info  # Keep first result as fallback
            max_retries = 2

            for retry_num in range(1, max_retries + 1):
                safe_push_log(
                    f"🔄 Retry {retry_num}/{max_retries} for premium formats..."
                )

                # Build retry command with enhanced parameters
                retry_cmd = [
                    "yt-dlp",
                    "-J",
                    "--skip-download",
                    "--user-agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "--extractor-retries",
                    "3",
                    "--no-cache-dir",  # Force fresh fetch
                ]

                # Add cookies if available
                if cookies_params:
                    retry_cmd.extend(cookies_params)

                retry_cmd.append(clean_url)

                try:
                    retry_result = subprocess.run(
                        retry_cmd, capture_output=True, text=True, timeout=45
                    )

                    if retry_result.returncode == 0:
                        retry_info = json.loads(retry_result.stdout)

                        # Check if this attempt got premium formats
                        if check_url_info_integrity(retry_info):
                            safe_push_log(
                                f"✅ Premium formats found on retry {retry_num}"
                            )
                            info = retry_info
                            break
                        else:
                            # Keep the result with most formats
                            retry_formats_count = len(retry_info.get("formats", []))
                            best_formats_count = len(best_info.get("formats", []))

                            if retry_formats_count > best_formats_count:
                                best_info = retry_info
                                safe_push_log(
                                    f"📊 Retry {retry_num} has more formats ({retry_formats_count} vs {best_formats_count})"
                                )

                except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
                    safe_push_log(f"⚠️ Retry {retry_num} failed: {str(e)[:100]}")
                    continue

            # If no retry succeeded with premium formats, use best result
            if not check_url_info_integrity(info):
                info = best_info
                safe_push_log(
                    "⚠️ No premium formats found after retries, using best available"
                )
        else:
            safe_push_log("✅ Premium formats (AV1/VP9) detected")

    # Add metadata about which client was used (for consistent download behavior)
    info["_hometube_successful_client"] = successful_client
    safe_push_log(f"📝 Recording successful client: {successful_client}")

    # Save JSON to file for later use with yt-dlp --load-info-json
    save_url_info(json_output_path, info)

    return info


def _build_bot_detection_error(
    youtube_cookies_file_path: str, cookies_from_browser: str
) -> Dict:
    """Build helpful error message for bot detection."""
    from pathlib import Path
    from app.file_system_utils import is_valid_browser

    cookie_file_exists = (
        youtube_cookies_file_path and Path(youtube_cookies_file_path).exists()
    )
    browser_configured = cookies_from_browser and is_valid_browser(cookies_from_browser)

    help_msg = "⚠️ YouTube bot detection triggered.\n\n"

    if not cookie_file_exists and not browser_configured:
        help_msg += (
            "🔐 **No cookies configured!** This is likely why you're blocked.\n\n"
            "**Solutions:**\n"
            "1. 📁 **Add cookies file** (recommended for servers):\n"
            "   - Export cookies from your browser (see docs/usage.md)\n"
            "   - Place file at: `cookies/youtube_cookies.txt`\n"
            "   - Set YOUTUBE_COOKIES_FILE_PATH in .env\n\n"
            "2. 🌐 **Use browser cookies** (local development):\n"
            "   - Set COOKIES_FROM_BROWSER=chrome (or firefox, brave, etc.)\n"
            "   - Works if browser is on same machine\n\n"
            "3. ⏳ **Wait a few minutes** and try again\n\n"
            "[Documentation](docs/usage.md#-authentication--private-content)"
        )
    else:
        help_msg += (
            "🔐 Cookies are configured but YouTube still blocked the request.\n\n"
            "**Try these solutions:**\n"
            "1. 🔄 **Refresh your cookies** (they may be expired)\n"
            "2. ⏳ **Wait 5-10 minutes** before retrying\n"
            "3. 🌐 **Try from a different IP** if using VPN/proxy\n"
            "4. 🍪 **Verify cookies file is valid** (not corrupted)\n\n"
        )

        if cookie_file_exists:
            help_msg += f"📁 Current cookies file: `{youtube_cookies_file_path}`\n"
        if browser_configured:
            help_msg += f"🌐 Browser configured: `{cookies_from_browser}`\n"

    return {"error": help_msg}


def _build_age_restriction_error(
    youtube_cookies_file_path: str, cookies_from_browser: str
) -> Dict:
    """Build helpful error message for age-restricted content."""
    from pathlib import Path
    from app.file_system_utils import is_valid_browser

    cookie_file_exists = (
        youtube_cookies_file_path and Path(youtube_cookies_file_path).exists()
    )
    browser_configured = cookies_from_browser and is_valid_browser(cookies_from_browser)

    help_msg = "🔞 Age-restricted content.\n\n"

    if not cookie_file_exists and not browser_configured:
        help_msg += (
            "🔐 **Authentication required!** This video requires sign-in to verify age.\n\n"
            "**Solutions:**\n"
            "1. 📁 **Add cookies file** (recommended):\n"
            "   - Export cookies from your browser while signed in to YouTube\n"
            "   - Place file at: `cookies/youtube_cookies.txt`\n"
            "   - Set YOUTUBE_COOKIES_FILE_PATH in .env\n\n"
            "2. 🌐 **Use browser cookies**:\n"
            "   - Set COOKIES_FROM_BROWSER=chrome (or firefox, brave, etc.)\n"
            "   - Make sure you're signed in to YouTube in that browser\n\n"
            "[Documentation](docs/usage.md#-authentication--private-content)"
        )
    else:
        help_msg += (
            "🔐 Cookies are configured but age verification failed.\n\n"
            "**Possible causes:**\n"
            "1. 🔄 **Cookies may be expired** - refresh them from your browser\n"
            "2. 👤 **Not signed in** - make sure you're logged into YouTube when exporting cookies\n"
            "3. 🔞 **Account age verification** - your YouTube account may need age verification\n\n"
        )

        if cookie_file_exists:
            help_msg += f"📁 Current cookies file: `{youtube_cookies_file_path}`\n"
        if browser_configured:
            help_msg += f"🌐 Browser configured: `{cookies_from_browser}`\n"

    return {"error": help_msg}

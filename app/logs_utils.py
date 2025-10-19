"""
Logging and Error Handling Utilities for HomeTube

Provides centralized logging functionality and error message analysis
for better user experience and debugging.
"""

import streamlit as st

try:
    from .utils import is_valid_cookie_file
except ImportError:
    from utils import is_valid_cookie_file


# Authentication error patterns (imported from main constants)
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


# === MESSAGE CLASSIFICATION FUNCTIONS ===


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

    return any(keyword in error_message.lower() for keyword in AUTH_ERROR_PATTERNS)


def is_http_403_error(error_message: str) -> bool:
    """Check if error is specifically HTTP 403 Forbidden"""
    error_lower = error_message.lower()
    return (
        "403" in error_lower and "forbidden" in error_lower
    ) or "unable to download video data" in error_lower


def is_format_unavailable_error(error_message: str) -> bool:
    """Check if error is specifically about requested format not being available"""
    error_lower = error_message.lower()
    return (
        "requested format is not available" in error_lower
        or "format is not available" in error_lower
    )


# === LOGGING FUNCTIONS ===


def safe_push_log(message: str):
    """Safe logging function that works even if logs aren't initialized yet"""
    try:
        # Check if we're in the main module context with logging available
        import sys

        main_module = sys.modules.get("__main__")
        if (
            main_module
            and hasattr(main_module, "ALL_LOGS")
            and hasattr(main_module, "push_log")
        ):
            main_module.push_log(message)
        else:
            # If logging isn't ready, just print to console for debugging
            print(f"[LOG] {message}")
    except Exception as e:
        print(f"[LOG] {message} (Error: {e})")


def log_title(title: str, underline_char: str = "─"):
    """
    Log a title with automatic underline matching the exact title length

    Args:
        title: The title text to display
        underline_char: Character to use for underline (default: ─)
    """
    # Use exact title length for natural, adaptive underlines
    underline_length = len(title)

    safe_push_log(title)
    safe_push_log(underline_char * underline_length)


# === HELPER FUNCTIONS ===


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


# === ERROR HINT FUNCTIONS ===


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

    # Get YOUTUBE_COOKIES_FILE_PATH from settings or environment
    try:
        from app.config import get_settings

        settings = get_settings()
        YOUTUBE_COOKIES_FILE_PATH = settings.YOUTUBE_COOKIES_FILE_PATH
    except ImportError:
        import os

        YOUTUBE_COOKIES_FILE_PATH = os.getenv("YOUTUBE_COOKIES_FILE_PATH", "")

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

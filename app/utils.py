"""
Utility functions extracted from main.py for testing.
These functions have no Streamlit dependencies.
"""

import re
from pathlib import Path
from typing import Optional, Tuple, List


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be safe for use as a filename or folder name.

    Args:
        name: The string to sanitize

    Returns:
        Sanitized string safe for filesystem use
    """
    if not name:
        return ""

    # Remove or replace problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name.strip())
    sanitized = re.sub(r"[^\w\s\-_\.]", "_", sanitized)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Limit length to prevent filesystem issues
    max_length = 200
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()

    return sanitized or "unnamed"


def parse_time_like(time_str: str) -> int:
    """
    Parse a time-like string and return the duration in seconds.

    Args:
        time_str: Time string in format like "1:23:45" or "123"

    Returns:
        Duration in seconds
    """
    if not time_str:
        return 0

    # Remove any whitespace
    time_str = time_str.strip()

    # If it's just a number, treat as seconds
    if time_str.isdigit():
        return int(time_str)

    # Parse formats like "1:23:45" or "23:45" or "45"
    parts = time_str.split(":")
    parts = [int(p) for p in parts if p.isdigit()]

    if len(parts) == 1:
        return parts[0]  # seconds
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]  # minutes:seconds
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]  # hours:minutes:seconds

    return 0


def fmt_hhmmss(seconds: int) -> str:
    """
    Format seconds as HH:MM:SS string.

    Args:
        seconds: Number of seconds

    Returns:
        Formatted time string
    """
    if seconds < 0:
        return "00:00:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def is_valid_browser(browser: str) -> bool:
    """
    Check if browser name is valid.

    Args:
        browser: Browser name to check

    Returns:
        True if valid browser name
    """
    valid_browsers = {
        "chrome",
        "firefox",
        "safari",
        "edge",
        "opera",
        "brave",
        "vivaldi",
        "chromium",
    }
    return browser.lower().strip() in valid_browsers


def extract_resolution_value(resolution_str: str) -> int:
    """
    Extract numeric resolution value from string.

    Args:
        resolution_str: String like "720p" or "1080"

    Returns:
        Numeric resolution value
    """
    if not resolution_str:
        return 0

    # Extract digits from the string
    match = re.search(r"(\d+)", str(resolution_str))
    return int(match.group(1)) if match else 0


def video_id_from_url(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL.

    Args:
        url: YouTube URL

    Returns:
        Video ID or None if not found
    """
    if not url:
        return None

    # Standard YouTube URL patterns
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def sanitize_url(url: str) -> str:
    """
    Clean and validate URL.

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

    return url


def invert_segments(
    segments: List[Tuple[int, int]], total_duration: int
) -> List[Tuple[int, int]]:
    """
    Invert segments (get the parts NOT in the segments).

    Args:
        segments: List of (start, end) tuples
        total_duration: Total duration in seconds

    Returns:
        Inverted segments
    """
    if not segments or total_duration <= 0:
        return [(0, total_duration)] if total_duration > 0 else []

    # Sort segments by start time
    sorted_segments = sorted(segments, key=lambda x: x[0])

    inverted = []
    last_end = 0

    for start, end in sorted_segments:
        # Add gap before this segment
        if start > last_end:
            inverted.append((last_end, start))
        last_end = max(last_end, end)

    # Add final segment if needed
    if last_end < total_duration:
        inverted.append((last_end, total_duration))

    return inverted


def is_valid_cookie_file(file_path: str) -> bool:
    """
    Check if cookie file exists and is valid.

    Args:
        file_path: Path to cookie file

    Returns:
        True if file exists and appears to be a valid cookie file
    """
    if not file_path:
        return False

    path = Path(file_path)

    # Check if file exists
    if not path.exists() or not path.is_file():
        return False

    # Check file size (should not be empty)
    if path.stat().st_size == 0:
        return False

    # Check file extension
    if path.suffix.lower() not in [".txt", ".cookies"]:
        return False

    return True

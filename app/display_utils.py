"""
Display and formatting utilities.

Functions for formatting time, durations, and other display-related utilities.
"""

from typing import Optional


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


def parse_time_like(time_str: str) -> Optional[int]:
    """
    Parse a time-like string and return the duration in seconds.
    Accepts: "11" (sec), "0:11", "00:00:11", "1:02:03"
    Returns seconds (int) or None for invalid input.

    Args:
        time_str: Time string in format like "1:23:45" or "123"

    Returns:
        Duration in seconds or None for invalid input
    """
    s = (time_str or "").strip()
    if not s:
        return None

    # Check for negative numbers
    if s.startswith("-"):
        return None

    if s.isdigit():
        return int(s)

    parts = s.split(":")
    if not all(p.isdigit() for p in parts):
        return None

    parts = [int(p) for p in parts]

    # Validate limits for MM:SS
    if len(parts) == 2:
        m, s_ = parts
        if s_ >= 60:  # Invalid seconds
            return None
        return m * 60 + s_

    # Validate limits for HH:MM:SS
    if len(parts) == 3:
        h, m, s_ = parts
        if m >= 60 or s_ >= 60:  # Invalid minutes or seconds
            return None
        return h * 3600 + m * 60 + s_

    return None

"""
Centralized constants for HomeTube.

This module contains all shared constants used across multiple modules.
Importing from here ensures consistency and eliminates duplication.
"""

import re
from typing import List, Pattern, Set

# === AUTHENTICATION ERROR PATTERNS ===
# Used to detect authentication-related errors in yt-dlp output.
# Shared between main.py and logs_utils.py
AUTH_ERROR_PATTERNS: List[str] = [
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

# === ANSI ESCAPE PATTERN ===
# Regular expression to strip ANSI color codes and control sequences from logs.
# Used in main.py and logs_utils.py for log cleaning.
ANSI_ESCAPE_PATTERN: Pattern = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)

# === BROWSER SUPPORT ===
# Valid browsers for cookie extraction (yt-dlp --cookies-from-browser).
# The set version is for O(1) lookups, the list is for iteration.
SUPPORTED_BROWSERS_SET: Set[str] = {
    "brave",
    "chrome",
    "chromium",
    "edge",
    "firefox",
    "opera",
    "safari",
    "vivaldi",
    "whale",
}

SUPPORTED_BROWSERS: List[str] = sorted(SUPPORTED_BROWSERS_SET)

# === FILE VALIDATION ===
# Minimum size for a valid cookie file (bytes)
MIN_COOKIE_FILE_SIZE: int = 100

# Video file extensions
VIDEO_EXTENSIONS: Set[str] = {".mkv", ".mp4", ".webm", ".avi", ".mov"}

# Subtitle file extensions
SUBTITLE_EXTENSIONS: Set[str] = {".srt", ".vtt", ".ass", ".ssa"}

# === DOWNLOAD PROFILE CONSTANTS ===
# Cache expiry for profile resolution (minutes)
CACHE_EXPIRY_MINUTES: int = 5

# Maximum optimal profiles to consider
MAX_OPTIMAL_PROFILES: int = 10

# === CSS STYLES ===
# Style for the logs container in Streamlit UI
LOGS_CONTAINER_STYLE: str = """
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

# === PROGRESS REGEX PATTERNS ===
# Patterns for parsing yt-dlp download progress output
DOWNLOAD_PROGRESS_PATTERN: Pattern = re.compile(
    r"\[download\]\s+(\d{1,3}\.\d+)%\s+of\s+([\d.]+\w+)\s+at\s+"
    r"([\d.]+\w+/s)\s+ETA\s+(\d{2}:\d{2})"
)

FRAGMENT_PROGRESS_PATTERN: Pattern = re.compile(
    r"\[download\]\s+Got fragment\s+(\d+)\s+of\s+(\d+)"
)

GENERIC_PERCENTAGE_PATTERN: Pattern = re.compile(
    r"(\d{1,3}(?:\.\d+)?)%"
)

"""
Text utilities for HomeTube.

This module provides text manipulation functions for creating
consistent, filesystem-safe filenames from video titles.
"""

import re
import unicodedata
from typing import Optional

# Windows reserved filenames (case-insensitive)
_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# Invalid on Windows + generally annoying across platforms
_INVALID_CHARS_RE = re.compile(r'[\\/:*?"<>|]+')
_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_DOTS_SPACES_RE = re.compile(r"[\. ]+$")


def _sanitize_common(text: str) -> str:
    """Normalize, remove control chars, sanitize invalid filename chars, collapse whitespace."""
    if text is None:
        return ""
    # Normalize unicode
    s = unicodedata.normalize("NFKC", str(text))

    # Remove control characters (incl. newlines/tabs)
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C" or ch in (" ",))

    # Replace invalid filename chars
    s = _INVALID_CHARS_RE.sub("-", s)

    # Collapse whitespace
    s = _WHITESPACE_RE.sub(" ", s).strip()

    # Avoid trailing dots/spaces (Windows)
    s = _TRAILING_DOTS_SPACES_RE.sub("", s).strip()

    return s


def _avoid_reserved_windows_name(s: str) -> str:
    """If the whole filename (without extension) is reserved, prefix underscore."""
    if s.upper() in _RESERVED:
        return f"_{s}"
    return s


def slug(text: str, max_length: int = 120) -> str:
    """
    Slugify into lowercase-kebab-case, safe for filenames.
    Keeps ASCII letters/digits; strips diacritics; replaces separators with '-'.

    Args:
        text: Input text to slugify
        max_length: Maximum length of the resulting slug (default: 120)

    Returns:
        str: Slugified text, safe for filenames and URLs

    Examples:
        >>> slug("Hello World!")
        'hello-world'
        >>> slug("Vidéo en français 🎬")
        'video-en-francais'
        >>> slug("  --Test-- ")
        'test'
        >>> slug("")
        'untitled'
    """
    s = _sanitize_common(text)

    # Strip accents/diacritics -> ASCII-ish
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    # Lowercase
    s = s.lower()

    # Replace anything not alnum with '-'
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")

    if not s:
        s = "untitled"

    # Enforce max length
    s = s[:max_length].rstrip("-")

    s = _avoid_reserved_windows_name(s)
    return s


def pretty(text: str, max_length: int = 120) -> str:
    """
    Pretty filename: Title Case with spaces, but sanitized for filesystem.
    Keeps accents (more human), removes invalid filename chars.

    Args:
        text: Input text to prettify
        max_length: Maximum length of the resulting text (default: 120)

    Returns:
        str: Prettified text in Title Case, safe for filenames

    Examples:
        >>> pretty("je regarde vos vidéos youtube")
        'Je Regarde Vos Vidéos Youtube'
        >>> pretty("hello world!")
        'Hello World'
        >>> pretty("")
        'Untitled'
    """
    s = _sanitize_common(text)
    if not s:
        s = "Untitled"

    # Title Case (simple heuristic)
    # NOTE: This will lowercase acronyms; if you care, we can preserve all-caps tokens.
    s = s.title()

    # Enforce max length
    if len(s) > max_length:
        s = s[:max_length].rstrip()

    s = _avoid_reserved_windows_name(s)
    return s


def idx(i: int, total: int, min_width: int = 2, max_width: int = 3) -> str:
    """
    Produce a zero-padded index width based on playlist size.

    The width is automatically determined based on the total number of videos:
    - For playlists with < 100 videos: 2 digits (01, 02, ...)
    - For playlists with 100-999 videos: 3 digits (001, 002, ...)
    - Capped at max_width to avoid excessive padding

    Args:
        i: Current index (1-based)
        total: Total number of videos in playlist
        min_width: Minimum padding width (default: 2)
        max_width: Maximum padding width (default: 3)

    Returns:
        str: Zero-padded index string

    Examples:
        >>> idx(1, 10)
        '01'
        >>> idx(5, 87)
        '05'
        >>> idx(42, 420)
        '042'
        >>> idx(1, 5)
        '01'
    """
    width = max(min_width, len(str(max(total, 1))))
    width = min(width, max_width)
    return str(i).zfill(width)


def render_title(
    pattern: str,
    *,
    i: int,
    title: str,
    video_id: str,
    ext: str,
    total: Optional[int] = None,
) -> str:
    """
    Render a video title from a pattern with placeholders.

    Supported placeholders:
    - {i} or {i:04d}: Video index (1-based), supports Python format spec
    - {idx}: Smart zero-padded index based on total (auto-width: 2-3 digits)
    - {title}: Raw video title
    - {slug(title)}: Slugified video title (lowercase-kebab-case)
    - {pretty(title)}: Prettified video title (Title Case with spaces)
    - {id}: Video ID
    - {ext}: File extension (without dot)

    Args:
        pattern: Pattern string with placeholders
        i: Video index (1-based recommended)
        title: Raw video title
        video_id: Video ID (required, used for safe fallback)
        ext: File extension without dot (e.g., "mkv", "mp4")
        total: Total number of videos in playlist (for {idx} placeholder, optional)

    Returns:
        str: Rendered filename

    Examples:
        >>> render_title("{idx} - {pretty(title)}.{ext}", i=1, title="je regarde vos vidéos", video_id="abc123", ext="mkv", total=10)
        '01 - Je Regarde Vos Vidéos.mkv'
        >>> render_title("{i:04d} - {slug(title)} [{id}].{ext}", i=1, title="Hello World!", video_id="abc123", ext="mkv")
        '0001 - hello-world [abc123].mkv'
    """
    # Ensure safe defaults
    safe_title = title if title else "Untitled"
    safe_id = video_id if video_id else "unknown"
    safe_ext = ext if ext else "mkv"
    safe_i = i if i >= 0 else 0
    safe_total = total if total and total > 0 else max(safe_i, 1)

    try:
        # Step 1: Replace custom placeholders that need special processing
        # These must happen before format() since they're custom placeholders
        processed_pattern = pattern

        # Replace {slug(title)}
        if "{slug(title)}" in processed_pattern:
            slugified_title = slug(safe_title)
            processed_pattern = processed_pattern.replace(
                "{slug(title)}", slugified_title
            )

        # Replace {pretty(title)}
        if "{pretty(title)}" in processed_pattern:
            prettified_title = pretty(safe_title)
            processed_pattern = processed_pattern.replace(
                "{pretty(title)}", prettified_title
            )

        # Replace {idx} with smart zero-padded index
        if "{idx}" in processed_pattern:
            idx_str = idx(safe_i, safe_total)
            processed_pattern = processed_pattern.replace("{idx}", idx_str)

        # Step 2: Apply Python's format with the remaining placeholders
        result = processed_pattern.format(
            i=safe_i,
            title=safe_title,
            id=safe_id,
            ext=safe_ext,
        )

        return result

    except (KeyError, ValueError, IndexError):
        # Pattern is malformed, use safe fallback
        # Fallback pattern: "{idx} - {pretty(title)}.{ext}"
        prettified_title = pretty(safe_title)
        idx_str = idx(safe_i, safe_total)
        return f"{idx_str} - {prettified_title}.{safe_ext}"


# Default pattern for playlist video titles
DEFAULT_PLAYLIST_TITLE_PATTERN = "{idx} - {pretty(title)}.{ext}"

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


def build_info_items(
    platform_emoji: str,
    platform_name: str,
    media_type: str,
    uploader: Optional[str] = None,
    duration: Optional[int] = None,
    view_count: Optional[int] = None,
    like_count: Optional[int] = None,
    entries_count: Optional[int] = None,
    first_video_title: Optional[str] = None,
) -> list:
    """
    Build a list of formatted info items for display.

    Args:
        platform_emoji: Emoji representing the platform
        platform_name: Name of the platform
        media_type: Type of media ("Video" or "Playlist")
        uploader: Channel/uploader name
        duration: Video duration in seconds
        view_count: Number of views
        like_count: Number of likes
        entries_count: Number of videos in playlist
        first_video_title: Title of first video in playlist

    Returns:
        List of HTML formatted info items
    """
    items = []

    # Platform info
    items.append(
        f'<span style="color: #e2e8f0;">&nbsp; {platform_emoji} &nbsp; {platform_name} {media_type}</span>'
    )

    # Uploader
    if uploader:
        items.append(f'<span style="color: #e2e8f0;">👤 &nbsp; {uploader}</span>')

    # Media-specific items
    if media_type == "Playlist":
        if entries_count:
            items.append(
                f'<span style="color: #e2e8f0;">📊 &nbsp; {entries_count} videos</span>'
            )
        if first_video_title:
            truncated = (
                first_video_title[:50] + "..."
                if len(first_video_title) > 50
                else first_video_title
            )
            items.append(
                f'<span style="color: #94a3b8; font-size: 0.85em;">📹 &nbsp; {truncated}</span>'
            )
    else:  # Video
        if duration and duration > 0:
            duration_str = fmt_hhmmss(int(duration))
            items.append(
                f'<span style="color: #e2e8f0;">⏱️ &nbsp; {duration_str}</span>'
            )
        if view_count:
            views_formatted = f"{view_count:,}".replace(",", " ")
            items.append(
                f'<span style="color: #e2e8f0;">👁️ &nbsp; {views_formatted}</span>'
            )
        if like_count is not None and like_count > 0:
            likes_formatted = f"{like_count:,}".replace(",", " ")
            items.append(
                f'<span style="color: #e2e8f0;">👍 &nbsp; {likes_formatted}</span>'
            )

    return items


def render_media_card(title: str, info_items: list) -> str:
    """
    Render a media card with title and info items.

    Args:
        title: Media title
        info_items: List of HTML formatted info items

    Returns:
        HTML string for the card
    """
    # Join info items with separator
    separator = ' <span style="color: #4ade80;">&nbsp; &nbsp;</span> '
    info_line = separator.join(info_items) if info_items else ""

    # Build card HTML
    return f"""
        <div style="
            background: linear-gradient(135deg, #1e3a2e 0%, #2d5a45 100%);
            border-radius: 12px;
            padding: 18px;
            border-left: 5px solid #4ade80;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin: 10px 0;
        ">
            <h2 style="
                color: #ffffff;
                font-size: 1.3em;
                font-weight: 600;
                margin: 0 0 12px 0;
                line-height: 1.3;
            ">
                {title}
            </h2>
            
            {f'''<div style="
                display: flex;
                flex-wrap: wrap;
                gap: 8px 12px;
                font-size: 0.9em;
                padding-left: 12px;
            ">
                {info_line}
            </div>''' if info_line else ''}
        </div>
    """

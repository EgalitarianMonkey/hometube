"""
SponsorBlock Integration Utilities for HomeTube

Provides functions for SponsorBlock segment retrieval, analysis, and configuration
for skipping sponsor segments, introductions, outros, and other video segments.
"""

import json
import requests
from typing import Dict, List, Tuple
from urllib.parse import urlparse

try:
    from .translations import t
    from .logs_utils import push_log_generic as push_log, safe_push_log
    from .utils import video_id_from_url, fmt_hhmmss
    from .core import (
        build_sponsorblock_params as core_build_sponsorblock_params,
        get_sponsorblock_config as core_get_sponsorblock_config,
    )
except ImportError:
    from translations import t
    from logs_utils import push_log_generic as push_log, safe_push_log
    from utils import video_id_from_url, fmt_hhmmss
    from core import (
        build_sponsorblock_params as core_build_sponsorblock_params,
        get_sponsorblock_config as core_get_sponsorblock_config,
    )

# SponsorBlock API configuration
SPONSORBLOCK_API = "https://sponsor.ajay.app"


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
    # Import here to avoid circular imports with Streamlit
    try:
        import streamlit as st

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
    except ImportError:
        pass

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

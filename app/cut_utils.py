"""
Video Cutting and Keyframes Utilities for HomeTube

Provides functions for video cutting operations, keyframe extraction,
segment manipulation, and time remapping for SponsorBlock integration.
"""

from pathlib import Path
from typing import Dict, List, Callable, Tuple

try:
    from .translations import t
    from .logs_utils import push_log_generic as push_log
    from .process_utils import run_subprocess_safe
except ImportError:
    from translations import t
    from logs_utils import push_log_generic as push_log
    from process_utils import run_subprocess_safe


# === KEYFRAME OPERATIONS ===


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


# === SEGMENT MANIPULATION ===


def merge_overlaps(segments: List[Dict], margin: float = 0.0) -> List[Dict]:
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


def invert_segments(
    segments: List[Dict], total_duration: float
) -> List[Tuple[float, float]]:
    """
    Returns the intervals [start,end) to keep when removing 'segments'.

    Args:
        segments: List of dicts with 'start' and 'end' keys
        total_duration: Total duration in seconds

    Returns:
        List of tuples (start, end) representing segments to keep
    """
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


def invert_segments_tuples(
    segments: List[Tuple[int, int]], total_duration: int
) -> List[Tuple[int, int]]:
    """
    LEGACY: Invert segments using tuple format (for backward compatibility).

    Inverts segments (get the parts NOT in the segments).

    Args:
        segments: List of (start, end) tuples
        total_duration: Total duration in seconds

    Returns:
        Inverted segments as list of (start, end) tuples
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


# === TIME REMAPPING ===


def build_time_remap(
    segments: List[Dict], total_duration: float
) -> Tuple[Callable[[float], float], List[Tuple[float, float, float]]]:
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

    def remap(t: float) -> float:
        for a, b, ns in mapping:
            if t < a:
                # We're in a cut zone before this block
                return ns
            if a <= t <= b:
                return ns + (t - a)
        # t beyond or in a final cut zone -> clamp to final duration
        return mapping[-1][2] if mapping else 0.0

    return remap, mapping


def remap_interval(
    start: float, end: float, remap: Callable[[float], float]
) -> Tuple[float, float]:
    """Helper to recalculate an interval (start,end) after cutting"""
    s2 = remap(start)
    e2 = remap(end)
    # If start/end fall WITHIN a removed segment, remap returns to the useful edge.
    # We protect against s2>e2: we clamp and possibly signal an empty interval.
    if e2 < s2:
        e2 = s2
    return (s2, e2)


# === VIDEO CUTTING COMMAND BUILDING ===


def build_cut_command(
    final_tmp: Path,
    actual_start: float,
    duration: float,
    processed_subtitle_files: List[Tuple[str, Path]],
    cut_output: Path,
    cut_ext: str,
) -> List[str]:
    """
    Build the ffmpeg command for cutting video with subtitles.

    Args:
        final_tmp: Path to the source video file
        actual_start: Start time in seconds for cutting
        duration: Duration in seconds for the cut
        processed_subtitle_files: List of (language, subtitle_file_path) tuples
        cut_output: Path for the output cut video file
        cut_ext: Extension of the output file (.mp4 or .mkv)

    Returns:
        List of command arguments for ffmpeg
    """
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
    # Map first video stream and ALL audio streams
    cmd_cut.extend(
        [
            "-map",
            "0:v:0",  # First video stream
            "-map",
            "0:a?",  # ALL audio streams (optional - won't fail if no audio exists)
        ]
    )

    # Subtitle mappings
    for i, (lang, _) in enumerate(processed_subtitle_files):
        cmd_cut.extend(["-map", f"{i+1}:0"])

    # Exclude attached pictures
    cmd_cut.extend(["-map", "-0:m:attached_pic"])

    # Stream copy to preserve quality, with format-appropriate subtitle codec
    if cut_ext == ".mp4":
        # MP4 format: use mov_text for subtitle compatibility
        cmd_cut.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text"])
    else:
        # MKV format: use SRT for maximum compatibility
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

    return cmd_cut

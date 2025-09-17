import os
import re
import shutil
import subprocess
import json
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from urllib.parse import urlparse, parse_qs

import requests
import streamlit as st

try:
    from translations import t
except ImportError:
    # Fallback for when running from app directory
    from .translations import t


# === CONSTANTS ===
SPONSORBLOCK_API = "https://sponsor.ajay.app"
DEFAULT_SUBTITLE_LANGUAGES = ["en", "fr"]
MIN_COOKIE_FILE_SIZE = 100  # bytes

# Supported browsers for cookie extraction
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

# Common authentication error keywords
AUTH_ERROR_KEYWORDS = [
    "sign in",
    "login",
    "private",
    "unavailable",
    "restricted",
    "age",
    "requires",
    "authentication",
    "cookies",
]

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


# === LOAD .env FILE ===
def load_env_file():
    """Load .env file from project root, create from sample if missing"""
    # Get the directory where main.py is located
    app_dir = Path(__file__).parent
    project_root = app_dir.parent
    env_file = project_root / ".env"
    env_sample_file = project_root / ".env.sample"

    # Create .env from .env.sample if .env doesn't exist
    if not env_file.exists() and env_sample_file.exists():
        try:
            print("📝 Creating .env file from .env.sample...")
            env_file.write_text(
                env_sample_file.read_text(encoding="utf-8"), encoding="utf-8"
            )
            print(f"✅ Created {env_file}")
            print("💡 Please review and customize the .env file for your setup")
        except Exception as e:
            print(f"⚠️ Could not create .env file: {e}")
            print("💡 Please manually copy .env.sample to .env")

    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            # Remove quotes if present
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            # Set environment variable only if not already set
                            if key not in os.environ:
                                os.environ[key] = value
        except Exception as e:
            print(f"⚠️ Error reading .env file: {e}")
    else:
        print("⚠️ No .env file found and .env.sample is missing")
        print("💡 Consider creating a .env file for better configuration")


# Load .env file before using environment variables
load_env_file()

# === ENV ===
# Determine the project root for robust default paths
app_dir = Path(__file__).parent
project_root = app_dir.parent

# Default downloads folder relative to project root (more robust than cwd)
default_videos_folder = project_root / "downloads"

VIDEOS_FOLDER = Path(
    os.getenv(
        "VIDEOS_FOLDER",
        str(default_videos_folder),
    )
)

# Ensure the videos folder exists
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

TMP_DOWNLOAD_FOLDER = Path(os.getenv("TMP_DOWNLOAD_FOLDER", str(VIDEOS_FOLDER / "tmp")))

# Ensure temp folder exists
try:
    TMP_DOWNLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"⚠️ Could not create temp folder {TMP_DOWNLOAD_FOLDER}: {e}")

# Cookies configuration with better defaults
YOUTUBE_COOKIES_FILE_PATH = os.getenv("YOUTUBE_COOKIES_FILE_PATH")
if YOUTUBE_COOKIES_FILE_PATH and not Path(YOUTUBE_COOKIES_FILE_PATH).is_absolute():
    # Make relative paths relative to project root
    YOUTUBE_COOKIES_FILE_PATH = str(project_root / YOUTUBE_COOKIES_FILE_PATH)

COOKIES_FROM_BROWSER = os.getenv("COOKIES_FROM_BROWSER", "").strip().lower()

# Validate and provide helpful feedback for subtitle choices
SUBTITLES_CHOICES = [
    x.strip().lower()
    for x in os.getenv("SUBTITLES_CHOICES", ",".join(DEFAULT_SUBTITLE_LANGUAGES)).split(
        ","
    )
    if x.strip()
]

# Ensure we have at least some default subtitle languages
if not SUBTITLES_CHOICES:
    SUBTITLES_CHOICES = DEFAULT_SUBTITLE_LANGUAGES
    print("⚠️ No valid subtitle languages found, using defaults:", SUBTITLES_CHOICES)


# === CONFIGURATION SUMMARY ===
def print_config_summary():
    """Print a summary of the current configuration for debugging"""
    print("\n🔧 HomeTube Configuration Summary:")
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

    # Environment file status
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print(f"✅ Configuration file: {env_file}")
    else:
        print("⚠️ No .env file found - using defaults")

    print()


# Print configuration summary in development mode
if __name__ == "__main__" or os.getenv("DEBUG"):
    print_config_summary()


# === UTILITY FUNCTIONS ===
def is_valid_cookie_file(file_path: Optional[str]) -> bool:
    """Check if cookie file exists and has valid size"""
    if not file_path:
        return False
    try:
        return (
            os.path.isfile(file_path)
            and os.path.getsize(file_path) > MIN_COOKIE_FILE_SIZE
        )
    except (OSError, TypeError):
        return False


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


def sanitize_url(url: str) -> str:
    url = url.split("&t=")[0]
    url = url.split("?t=")[0]
    return url


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

    return sanitized


def is_authentication_error(error_message: str) -> bool:
    """
    Check if an error message indicates an authentication/cookies issue.

    Args:
        error_message: The error message to check

    Returns:
        True if it's likely an authentication issue
    """
    return any(keyword in error_message.lower() for keyword in AUTH_ERROR_KEYWORDS)


def log_authentication_error_hint():
    """Log standard authentication error messages"""
    safe_push_log("🍪 This might be a cookies/authentication issue")
    safe_push_log("💡 Try using browser cookies or check your cookies file")


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
def parse_time_like(s: str) -> Optional[int]:
    """
    Accepte: "11" (sec), "0:11", "00:00:11", "1:02:03"
    Renvoie des secondes (int) ou None.
    """
    s = (s or "").strip()
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


def fmt_hhmmss(seconds: int) -> str:
    """Format seconds into HH:MM:SS format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


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
    Get the title of the video using yt-dlp
    Returns sanitized title suitable for filename
    """
    try:
        safe_push_log("📋 Retrieving video title...")

        cmd_title = [
            "yt-dlp",
            "--print",
            "title",
            "--no-download",
            *cookies_part,
            url,
        ]

        result = run_subprocess_safe(
            cmd_title, timeout=30, error_context="Video title extraction"
        )

        if result.returncode == 0 and result.stdout.strip():
            title = result.stdout.strip()
            # Sanitize title for filename
            sanitized = sanitize_filename(title)
            safe_push_log(f"📝 Video title: {title}")
            return sanitized
        else:
            error_msg = result.stderr.strip()
            safe_push_log(f"⚠️ Could not retrieve title: {error_msg}")

            # Check if this might be a cookies/authentication issue
            if is_authentication_error(error_msg):
                log_authentication_error_hint()

            return "video"

    except Exception as e:
        safe_push_log(f"⚠️ Error getting video title: {e}")
        return "video"


def get_video_formats(url: str, cookies_part: List[str]) -> List[Dict]:
    """
    Get available video formats for a URL using yt-dlp
    Returns a list of format dictionaries with id, ext, resolution, description
    Ordered by quality (highest first)
    """
    try:
        safe_push_log(t("log_formats_detecting"))

        cmd_formats = [
            "yt-dlp",
            "--list-formats",
            "--no-download",
            *cookies_part,
            url,
        ]

        result = run_subprocess_safe(
            cmd_formats, timeout=60, error_context="Video formats extraction"
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            safe_push_log(t("log_formats_failed", error=error_msg))

            # Check if this might be a cookies/authentication issue
            if is_authentication_error(error_msg):
                log_authentication_error_hint()

            return []

        # Parse yt-dlp format output
        formats = []
        for line in result.stdout.strip().split("\n"):
            format_info = parse_format_line(line)
            if format_info:
                formats.append(format_info)

        # Sort formats by quality (highest first)
        formats.sort(
            key=lambda x: extract_resolution_value(x["resolution"]),
            reverse=True,
        )

        safe_push_log(t("log_formats_count", count=len(formats)))

        # If no formats found, provide helpful suggestions
        if len(formats) == 0:
            safe_push_log("⚠️ No video formats detected")
            safe_push_log("🍪 This might indicate:")
            safe_push_log(
                "   • The video requires authentication (age-restricted, private, etc.)"
            )
            safe_push_log("   • Your cookies are invalid or expired")
            safe_push_log("   • The video is not available in your region")
            safe_push_log("💡 Try using browser cookies or updating your cookies file")

        return formats

    except Exception as e:
        safe_push_log(t("log_formats_error", error=e))
        return []


def video_id_from_url(url: str) -> str:
    """Extract video ID from any YouTube URL format"""
    if not url:
        return ""

    try:
        u = urlparse(url)

        # Check that it's a valid YouTube URL
        if not (u.netloc.endswith("youtube.com") or u.netloc.endswith("youtu.be")):
            return ""

        if u.netloc.endswith("youtu.be"):
            video_id = u.path.lstrip("/")
            # Validate that the ID looks correct (11 alphanumeric characters)
            if (
                len(video_id) == 11
                and video_id.replace("-", "").replace("_", "").isalnum()
            ):
                return video_id
            return ""

        qv = parse_qs(u.query).get("v", [])
        if qv and len(qv[0]) == 11:
            return qv[0]

        # Fallback for /shorts/<id> or other similar formats
        parts = [p for p in u.path.split("/") if p and p != "watch" and p != "shorts"]
        if parts:
            video_id = parts[-1]
            if (
                len(video_id) == 11
                and video_id.replace("-", "").replace("_", "").isalnum()
            ):
                return video_id

        return ""
    except Exception:
        return ""


# --- 2) Récupération bruts SponsorBlock ---
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
    Construit un mapping temps_original -> temps_après_coupe.
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
    Récupère les segments SponsorBlock d'une vidéo via l'API directe.
    Retourne une liste de segments avec 'start' et 'end' en secondes.

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
    Calcule le temps total de sponsors dans la section demandée et ajuste la fin.

    Args:
        start_sec: Début de section souhaité (secondes)
        end_sec: Fin de section souhaité (secondes)
        sponsor_segments: Liste des segments sponsors

    Returns:
        tuple: (temps_sponsors_supprimé, nouvelle_fin_ajustée_pour_vidéo_raccourcie)
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

    Args:
        sb_choice: User choice for SponsorBlock

    Returns:
        tuple: (remove_categories, mark_categories) - listes des catégories à
            retirer/marquer
    """
    # Check if we have dynamic sponsor detection results
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

    # Fallback to preset configurations
    # Option 1: Par défaut - Retirer: sponsor,interaction,selfpromo | Marquer:
    # intro,preview,"outro"
    if "Par défaut" in sb_choice or "Default" in sb_choice:
        return ["sponsor", "interaction", "selfpromo"], ["intro", "preview", "outro"]

    # Option 2: Modéré - Retirer: sponsor,interaction,outro | Marquer:
    # selfpromo,intro,preview
    elif "Modéré" in sb_choice or "Moderate" in sb_choice:
        return ["sponsor", "interaction", "outro"], ["selfpromo", "intro", "preview"]

    # Option 3: Agressif - Retirer: TOUT
    elif "Agressif" in sb_choice or "Aggressive" in sb_choice:
        return ["sponsor", "selfpromo", "interaction", "intro", "outro", "preview"], []

    # Option 4: Conservateur - Retirer: sponsor,outro | Marquer:
    # interaction,selfpromo,intro,preview
    elif "Conservateur" in sb_choice or "Conservative" in sb_choice:
        return ["sponsor", "outro"], ["interaction", "selfpromo", "intro", "preview"]

    # Option 5: Minimal - Retirer: sponsor seulement | Marquer: tous les autres
    elif "Minimal" in sb_choice:
        return ["sponsor"], ["selfpromo", "interaction", "intro", "outro", "preview"]

    # Option 6: Désactivé - Aucune gestion
    elif "Désactivé" in sb_choice or "Disabled" in sb_choice:
        return [], []

    # Fallback (should not happen)
    return ["sponsor", "interaction", "selfpromo"], ["intro", "preview", "outro"]


def build_sponsorblock_params(sb_choice: str) -> List[str]:
    """
    Builds yt-dlp parameters for SponsorBlock based on user choice.

    Args:
        sb_choice: User choice for SponsorBlock

    Returns:
        list: yt-dlp parameters for SponsorBlock
    """
    remove_cats, mark_cats = get_sponsorblock_config(sb_choice)

    # If disabled, return the deactivation
    if not remove_cats and not mark_cats:
        return ["--no-sponsorblock"]

    params = []

    # Add categories to remove
    if remove_cats:
        cats_str = ",".join(remove_cats)
        params.extend(
            [
                "--sponsorblock-remove",
                cats_str,
                "--no-force-keyframes-at-cuts",  # for smart cutting with no re-encoding
            ]
        )
        safe_push_log(f"SponsorBlock Remove: {cats_str}")

    # Ajouter les catégories à marquer
    if mark_cats:
        cats_str = ",".join(mark_cats)
        params.extend(["--sponsorblock-mark", cats_str])
        safe_push_log(f"SponsorBlock Mark: {cats_str}")

    return params


def build_cookies_params() -> List[str]:
    """
    Builds cookie parameters based on user selection.

    Returns:
        list: yt-dlp parameters for cookies
    """
    cookies_method = st.session_state.get("cookies_method", "none")

    if cookies_method == "file":
        if is_valid_cookie_file(YOUTUBE_COOKIES_FILE_PATH):
            safe_push_log(f"🍪 Using cookies from file: {YOUTUBE_COOKIES_FILE_PATH}")
            return ["--cookies", YOUTUBE_COOKIES_FILE_PATH]
        else:
            safe_push_log(
                f"⚠️ Cookies file not found, falling back to no cookies: "
                f"{YOUTUBE_COOKIES_FILE_PATH}"
            )
            return ["--no-cookies"]

    elif cookies_method == "browser":
        browser = st.session_state.get("browser_select", "chrome")
        profile = st.session_state.get("browser_profile", "").strip()

        browser_config = f"{browser}:{profile}" if profile else browser
        safe_push_log(f"🍪 Using cookies from browser: {browser_config}")
        return ["--cookies-from-browser", browser_config]

    else:  # none
        safe_push_log("🍪 No cookies authentication")
        return ["--no-cookies"]


def build_base_ytdlp_command(
    base_filename: str,
    temp_dir: Path,
    format_spec: str,
    embed_chapters: bool,
    embed_subs: bool,
    force_mp4: bool = False,
) -> List[str]:
    """Build base yt-dlp command with common options"""
    output_format = "mp4" if force_mp4 else "mkv"

    cmd = [
        "yt-dlp",
        "--newline",
        "-o",
        f"{base_filename}.%(ext)s",
        "--paths",
        f"home:{temp_dir}",
        "--merge-output-format",
        output_format,
        "-f",
        format_spec,
        "--format-sort",
        "res:4320,fps,codec:av01,codec:vp9.2,codec:vp9,codec:h264",
        "--embed-metadata",
        "--embed-thumbnail",
        "--no-write-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--ignore-errors",
        "--force-overwrites",
        "--concurrent-fragments",
        "1",
        "--sleep-requests",
        "1",
        "--retries",
        "10",
        "--retry-sleep",
        "2",
    ]

    # Add chapters option
    if embed_chapters:
        cmd.append("--embed-chapters")
    else:
        cmd.append("--no-embed-chapters")

    return cmd


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
#     help="Entrez l'URL de la vidéo YouTube",
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

        # Options de réencodage pour le mode précis (DYNAMIC!)
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
                    # with st.expander("💡 Troubleshooting / Dépannage", expanded=True):
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
                    if st.button("🔧 Configure Cookies / Configurer les cookies"):
                        st.rerun()

    # Format selection dropdown (DYNAMIC!)
    if st.session_state.available_formats:
        format_options = [t("quality_auto_option")] + [
            f"{fmt['resolution']} - {fmt['ext']} ({fmt['id']})"
            for fmt in st.session_state.available_formats
        ]

        selected_format_display = st.selectbox(
            t("quality_select_prompt"),
            options=format_options,
            index=0,
            help=t("quality_select_help"),
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
    # else:
    # st.info(t("quality_auto_info"))


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
    ALL_LOGS.append(line.rstrip("\n"))

    # Update logs display
    with logs_placeholder.container():
        # Scrollable logs container
        logs_content = (
            "\n".join(ALL_LOGS[-400:]).replace("<", "&lt;").replace(">", "&gt;")
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


def run_cmd(cmd: List[str], progress=None, status=None, info=None) -> int:
    """Execute command with enhanced progress tracking and metrics display"""
    start_time = time.time()
    push_log(f"$ {' '.join(cmd)}")

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
                push_log(line)

                # Skip processing if no UI components provided
                if not (progress and status):
                    continue

                # Calculate elapsed time
                elapsed = time.time() - start_time
                elapsed_str = fmt_hhmmss(int(elapsed))

                # === DOWNLOAD PROGRESS WITH DETAILS ===
                download_progress = parse_download_progress(line)
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
                fragment_progress = parse_fragment_progress(line)
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
                generic_percent = parse_generic_percentage(line)
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
                line_lower = line.lower()

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

    # Determine format based on user selection
    selected_format = st.session_state.get("selected_format", "auto")
    if selected_format == "auto":
        format_spec = "bv*+ba/b"
        push_log(t("log_quality_auto"))
    else:
        # Use specific format ID + best audio
        format_spec = f"{selected_format}+ba/b"
        push_log(t("log_quality_selected", format_id=selected_format))

    # --- yt-dlp base command construction
    force_mp4 = do_cut and subs_selected  # Force MP4 for sections with subtitles
    common_base = build_base_ytdlp_command(
        base_output,
        tmp_subfolder_dir,
        format_spec,
        embed_chapters,
        embed_subs,
        force_mp4,
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

    # --- Final yt-dlp command (always full download)
    push_log(t("log_download_with_sponsorblock"))
    cmd_full = [
        *common_base,
        *subs_part,
        *sb_part,
        *cookies_part,
        clean_url,
    ]

    progress_placeholder.progress(0, text=t("status_preparation"))
    status_placeholder.info(t("status_downloading_simple"))
    ret_dl = run_cmd(
        cmd_full,
        progress=progress_placeholder,
        status=status_placeholder,
        info=info_placeholder,
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

        # Create the final cut output file with a different name to avoid
        # input/output conflict
        cut_output = tmp_subfolder_dir / f"{base_output}_cut.mp4"
        if cut_output.exists():
            try:
                cut_output.unlink()
            except Exception:
                pass

        # === KEYFRAMES MODE (FAST) ===
        if cut_mode == "keyframes":
            push_log(t("log_mode_keyframes"))

            # Extract keyframes and find nearest ones
            keyframes = get_keyframes(final_tmp)
            if keyframes:
                actual_start, actual_end = find_nearest_keyframes(
                    keyframes, start_sec, end_sec
                )
                # Log the actual timestamps used for both video and subtitles
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

            # Build keyframes ffmpeg command (similar to your example)
            cmd_cut = [
                "ffmpeg",
                "-y",
                "-ss",
                str(actual_start),
                "-to",
                str(actual_end),
                "-i",
                str(final_tmp),
            ]

            # Add subtitle inputs if any
            # IMPORTANT: Use the same actual_start/actual_end timestamps as the video
            # to ensure perfect synchronization between video and subtitles
            subtitle_files = []
            if subs_selected:
                push_log("📝 Cutting subtitles with same keyframe timestamps as video")
                for lang in subs_selected:
                    srt_file = tmp_subfolder_dir / f"{base_output}.{lang}.srt"
                    if not srt_file.exists():
                        srt_file = tmp_subfolder_dir / f"{base_output}.srt"

                    if srt_file.exists():
                        cmd_cut.extend(
                            [
                                "-ss",
                                str(actual_start),  # Same timestamp as video
                                "-to",
                                str(actual_end),  # Same timestamp as video
                                "-f",
                                "srt",
                                "-i",
                                str(srt_file),
                            ]
                        )
                        subtitle_files.append((lang, srt_file))
                        push_log(f"📝 {lang}: {actual_start:.3f}s → {actual_end:.3f}s")
                    else:
                        push_log(t("log_srt_not_found", lang=lang))

            # Mappings for keyframes mode
            cmd_cut.extend(
                [
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                ]
            )

            # Add subtitle mappings
            sub_idx = 1
            for i, (lang, _) in enumerate(subtitle_files):
                cmd_cut.extend(["-map", f"{sub_idx}:0"])
                sub_idx += 1

            cmd_cut.extend(["-map", "-0:v:m:attached_pic"])

            # KEYFRAMES ENCODING: Stream copy (no re-encoding)
            cmd_cut.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text"])

            # Subtitle metadata for keyframes
            if subtitle_files:
                first_lang = subtitle_files[0][0]
                cmd_cut.extend(
                    [
                        "-disposition:s:0",
                        "default",
                        "-metadata:s:s:0",
                        f"language={first_lang}",
                    ]
                )

            cmd_cut.extend(["-movflags", "+faststart", str(cut_output)])

        # === PRECISE MODE (SLOW) ===
        else:
            push_log(t("log_mode_precise"))

            # Use exact timestamps for precise mode
            actual_start, actual_end = float(start_sec), float(end_sec)
            push_log(f"🎯 Precise timestamps: {actual_start:.3f}s → {actual_end:.3f}s")

            # Build precise ffmpeg command (current behavior)
            cmd_cut = [
                "ffmpeg",
                "-y",
                "-ss",
                str(actual_start),
                "-to",
                str(actual_end),
                "-i",
                str(final_tmp),
            ]

            # Add subtitle inputs if any
            # IMPORTANT: Use the same actual_start/actual_end timestamps as the video
            # to ensure perfect synchronization between video and subtitles
            subtitle_files = []
            if subs_selected:
                push_log("📝 Cutting subtitles with same precise timestamps as video")
                for lang in subs_selected:
                    srt_file = tmp_subfolder_dir / f"{base_output}.{lang}.srt"
                    if not srt_file.exists():
                        srt_file = tmp_subfolder_dir / f"{base_output}.srt"

                    if srt_file.exists():
                        cmd_cut.extend(
                            [
                                "-ss",
                                str(actual_start),  # Same timestamp as video
                                "-to",
                                str(actual_end),  # Same timestamp as video
                                "-f",
                                "srt",
                                "-i",
                                str(srt_file),
                            ]
                        )
                        subtitle_files.append((lang, srt_file))
                        push_log(f"📝 {lang}: {actual_start:.3f}s → {actual_end:.3f}s")
                    else:
                        push_log(t("log_srt_not_found", lang=lang))

            # Mappings for precise mode
            cmd_cut.extend(
                [
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                ]
            )

            # Add subtitle mappings
            sub_idx = 1
            for i, (lang, _) in enumerate(subtitle_files):
                cmd_cut.extend(["-map", f"{sub_idx}:0"])
                sub_idx += 1

            cmd_cut.extend(["-map", "-0:v:m:attached_pic"])

            # PRECISE ENCODING: Full re-encoding with quality settings
            # Get user-selected encoding options
            codec_choice = st.session_state.get("codec_choice", "h264")
            quality_preset = st.session_state.get("quality_preset", "balanced")

            # Determine CRF and preset values
            if quality_preset == "balanced":
                crf_value = "16"
                preset_value = "slow"
            else:  # high_quality
                crf_value = "14"
                preset_value = "slower"

            if codec_choice == "h264":
                # H.264 encoding
                cmd_cut.extend(
                    [
                        "-c:v",
                        "libx264",
                        "-preset",
                        preset_value,
                        "-crf",
                        crf_value,
                        "-r",
                        "24000/1001",
                        "-pix_fmt",
                        "yuv420p",
                        "-fps_mode",
                        "cfr",
                        "-x264-params",
                        "aq-mode=2:aq-strength=1.1:psy-rd=1.00:0.15:deblock=0,0",
                    ]
                )
                push_log(t("log_h264_encoding", preset=preset_value, crf=crf_value))
            else:
                # H.265 encoding with 10-bit
                cmd_cut.extend(
                    [
                        "-c:v",
                        "libx265",
                        "-pix_fmt",
                        "yuv420p10le",
                        "-preset",
                        preset_value,
                        "-crf",
                        crf_value,
                        "-x265-params",
                        "aq-mode=2:aq-strength=1.1:psy-rd=2.0:deblock=0,0",
                        "-tag:v",
                        "hvc1",
                        "-fps_mode",
                        "cfr",
                        "-r",
                        "24000/1001",
                    ]
                )
                push_log(t("log_h265_encoding", preset=preset_value, crf=crf_value))

            # Common audio and subtitle settings
            cmd_cut.extend(
                [
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-c:s",
                    "mov_text",
                ]
            )

            # Subtitle metadata for precise
            if subtitle_files:
                first_lang = subtitle_files[0][0]
                cmd_cut.extend(
                    [
                        "-disposition:s:0",
                        "default",
                        "-metadata:s:s:0",
                        f"language={first_lang}",
                    ]
                )

            cmd_cut.extend(["-movflags", "+faststart", str(cut_output)])

        # === COMMON EXECUTION FOR BOTH MODES ===
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
        final_cut_name = tmp_subfolder_dir / f"{base_output}.mp4"
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

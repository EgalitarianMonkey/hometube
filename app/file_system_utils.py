"""
File System Utilities for HomeTube

Provides centralized file and directory management functionality
including cleanup operations, directory listing, and file operations.
"""

import re
import shutil
from pathlib import Path
from typing import List

import streamlit as st

# === FILE NAMING AND SANITIZATION ===


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


def get_unique_video_folder_name_from_url(url: str) -> str:
    """
    Generate a unique folder name for a video or playlist based on its URL.

    DEPRECATED: This function returns a legacy flat folder name.
    For new code, use workspace.parse_url() and workspace.get_*_workspace() instead.

    The new folder structure is:
    - Videos: videos/{platform}/{id}/
    - Playlists: playlists/{platform}/{id}/

    This function is kept for backward compatibility.

    Args:
        url: Sanitized video URL (should be cleaned with sanitize_url first)

    Returns:
        Legacy folder name string (e.g., "youtube-dQw4w9WgXcQ")
    """
    from app.workspace import get_legacy_folder_name

    return get_legacy_folder_name(url)


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


def is_valid_browser(browser: str) -> bool:
    """
    Check if browser name is valid for cookie extraction.

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
        "whale",
    }
    return browser.lower().strip() in valid_browsers


# === DIRECTORY OPERATIONS ===


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


def ensure_dir(path: Path) -> None:
    """Create directory and all parent directories if they don't exist"""
    path.mkdir(parents=True, exist_ok=True)


# === FILE OPERATIONS ===


def move_file(src: Path, dest_dir: Path) -> Path:
    """Move file from source to destination directory"""
    target = dest_dir / src.name
    shutil.move(str(src), str(target))
    return target


def copy_file(src: Path, dest_dir: Path) -> Path:
    """
    Copy file from source to destination directory.

    This preserves the original file in tmp for debugging and resilience.
    Use this instead of move_file to keep all download artifacts for future reuse.

    Args:
        src: Source file path
        dest_dir: Destination directory path

    Returns:
        Path: Path to the copied file
    """
    target = dest_dir / src.name
    shutil.copy2(str(src), str(target))  # copy2 preserves metadata
    return target


def move_final_to_destination(
    source: Path,
    destination: Path,
    log_fn=None,
) -> Path:
    """
    Move the final processed video file to its destination.

    This is the centralized function for moving final.mkv (or similar) to
    the user's destination folder with the intended filename. Using move
    instead of copy saves disk space by avoiding duplication.

    The original downloaded file (video-{FORMAT_ID}.{ext}) is preserved
    in tmp for cache reuse.

    Args:
        source: Path to the source file (e.g., final.mkv in tmp)
        destination: Full destination path including filename
        log_fn: Optional logging function (e.g., push_log or safe_push_log)

    Returns:
        Path: Path to the moved file at destination

    Raises:
        FileNotFoundError: If source file doesn't exist
        OSError: If move operation fails
    """
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    # Ensure destination directory exists
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Try to move the file (atomic on same filesystem)
    # If move fails (e.g., cross-device in Docker), fallback to copy + delete
    try:
        shutil.move(str(source), str(destination))
    except OSError as e:
        # Cross-device move - fallback to copy + delete
        if log_fn:
            log_fn(f"ℹ️ Cross-device move detected, using copy+delete: {e}")
        shutil.copy2(str(source), str(destination))
        source.unlink()

    if log_fn:
        log_fn(f"✅ Moved to: {destination.name}")
        log_fn("💾 Disk space saved by moving instead of copying")

    return destination


def should_remove_tmp_files() -> bool:
    """
    Check if temporary files should be removed after successful download.

    Checks both the settings default and the UI session state override.
    The UI checkbox can override the default setting.

    Returns:
        bool: True if temp files should be removed, False otherwise
    """
    # Check if UI has overridden the setting
    if "remove_tmp_files" in st.session_state:
        return st.session_state.remove_tmp_files

    # Otherwise use the configuration default - get settings dynamically
    try:
        from app.config import get_settings

        settings = get_settings()
        return settings.REMOVE_TMP_FILES_AFTER_DOWNLOAD
    except ImportError:
        # Fallback if config not available
        return False


def _should_remove_file(file_path: Path, cleanup_type: str) -> bool:
    """Helper function to determine if a file should be removed based on cleanup type"""
    # Skip removing final output files during download cleanup
    if cleanup_type == "download" and file_path.suffix in (".mkv", ".mp4", ".webm"):
        # Only remove if it's clearly a temporary file (has additional suffixes)
        stem = file_path.stem
        return any(suffix in stem for suffix in [".temp", ".tmp", ".part", "-cut"])
    return True


# === CLEANUP OPERATIONS ===


def cleanup_tmp_files(
    base_filename: str, tmp_dir: Path = None, cleanup_type: str = "all"
) -> None:
    """
    Centralized cleanup function for temporary files

    Args:
        base_filename: Base filename for targeted cleanup
        tmp_dir: Directory to clean (defaults to TMP_DOWNLOAD_FOLDER from global settings)
        cleanup_type: Type of cleanup - "all", "download", "subtitles", "cutting", "outputs"
    """
    # Import logging here to avoid circular dependency
    try:
        from .logs_utils import safe_push_log
    except ImportError:
        from logs_utils import safe_push_log

    if not should_remove_tmp_files():
        safe_push_log(
            f"🔍 Debug mode: Skipping {cleanup_type} cleanup (REMOVE_TMP_FILES=false)"
        )
        return

    # Get TMP_DOWNLOAD_FOLDER if not provided
    if tmp_dir is None:
        try:
            from app.config import ensure_folders_exist

            _, tmp_dir = ensure_folders_exist()
        except ImportError:
            # Fallback - use current directory tmp folder
            tmp_dir = Path("tmp")
            ensure_dir(tmp_dir)

    safe_push_log(f"🧹 Cleaning {cleanup_type} temporary files...")

    try:
        files_cleaned = 0

        if cleanup_type in ("all", "download"):
            # Download temporary files (include generic track/final files)
            patterns = [
                f"{base_filename}.*",
                "*.part",
                "*.ytdl",
                "*.temp",
                "*.tmp",
                "video-*.*",
                "audio-*.*",
                "final.*",
            ]
            for pattern in patterns:
                for file_path in tmp_dir.glob(pattern):
                    if file_path.is_file() and _should_remove_file(
                        file_path, cleanup_type
                    ):
                        try:
                            file_path.unlink()
                            files_cleaned += 1
                        except Exception as e:
                            safe_push_log(f"⚠️ Could not remove {file_path.name}: {e}")

        if cleanup_type in ("all", "subtitles"):
            # Subtitle files (.srt/.vtt) and .part files
            for ext in (".srt", ".vtt"):
                for f in tmp_dir.glob(f"{base_filename}*{ext}"):
                    try:
                        f.unlink()
                        files_cleaned += 1
                    except Exception:
                        pass
            # Part files related to base_filename
            for f in tmp_dir.glob(f"{base_filename}*.*.part"):
                try:
                    f.unlink()
                    files_cleaned += 1
                except Exception:
                    pass

        if cleanup_type in ("all", "cutting"):
            # Cutting intermediate files
            for suffix in ("-cut", "-cut-final"):
                for ext in (".srt", ".vtt", ".mkv", ".mp4", ".webm"):
                    for f in tmp_dir.glob(f"{base_filename}*{suffix}*{ext}"):
                        try:
                            f.unlink()
                            files_cleaned += 1
                        except Exception:
                            pass

        if cleanup_type in ("all", "outputs"):
            # Final output files (for retry cleanup)
            for ext in (".mkv", ".mp4", ".webm"):
                p = tmp_dir / f"{base_filename}{ext}"
                if p.exists():
                    try:
                        p.unlink()
                        files_cleaned += 1
                    except Exception:
                        pass

            # Generic final files (final.{ext}) always cleaned when enabled
            for ext in (".mkv", ".mp4", ".webm", ".avi"):
                final_candidate = tmp_dir / f"final{ext}"
                if final_candidate.exists():
                    try:
                        final_candidate.unlink()
                        files_cleaned += 1
                    except Exception:
                        pass

        if files_cleaned > 0:
            safe_push_log(f"🧹 Cleaned {files_cleaned} {cleanup_type} temporary files")
        else:
            safe_push_log(f"✅ No {cleanup_type} files to clean")

    except Exception as e:
        safe_push_log(f"⚠️ Error during {cleanup_type} cleanup: {e}")


# === LEGACY COMPATIBILITY WRAPPERS ===


def cleanup_extras(tmp_dir: Path, base_filename: str):
    """Legacy wrapper for cleanup_tmp_files - maintained for compatibility"""
    cleanup_tmp_files(base_filename, tmp_dir, "subtitles")


def delete_intermediate_outputs(tmp_dir: Path, base_filename: str):
    """Legacy wrapper for cleanup_tmp_files - maintained for compatibility"""
    cleanup_tmp_files(base_filename, tmp_dir, "outputs")


def clean_all_tmp_folders(tmp_base_dir: Path = None) -> tuple[int, int]:
    """
    Clean ALL temporary folders in the tmp directory.

    This function removes all video-specific temporary folders to free up disk space.
    Use with caution - this will delete all cached files and interrupt any ongoing downloads.

    Args:
        tmp_base_dir: Base tmp directory (defaults to TMP_DOWNLOAD_FOLDER from settings)

    Returns:
        tuple[int, int]: (folders_removed, total_size_mb) - count and total size freed
    """
    # Import dependencies
    try:
        from .logs_utils import safe_push_log
    except ImportError:
        from logs_utils import safe_push_log

    import shutil

    # Get TMP_DOWNLOAD_FOLDER if not provided
    if tmp_base_dir is None:
        try:
            from app.config import ensure_folders_exist

            _, tmp_base_dir = ensure_folders_exist()
        except ImportError:
            # Fallback - use current directory tmp folder
            tmp_base_dir = Path("tmp")

    if not tmp_base_dir.exists():
        safe_push_log("✅ No tmp folder to clean")
        return 0, 0

    folders_removed = 0
    total_size = 0

    try:
        # Iterate through all items in tmp folder
        for item in tmp_base_dir.iterdir():
            if item.is_dir():
                # Calculate folder size before deletion
                folder_size = sum(
                    f.stat().st_size for f in item.rglob("*") if f.is_file()
                )
                total_size += folder_size

                # Remove the folder
                shutil.rmtree(item)
                folders_removed += 1
                safe_push_log(
                    f"🗑️ Removed: {item.name} ({folder_size / (1024*1024):.1f} MB)"
                )

        total_size_mb = total_size / (1024 * 1024)

        if folders_removed > 0:
            safe_push_log(
                f"✅ Cleaned {folders_removed} folder(s), freed {total_size_mb:.1f} MB"
            )
        else:
            safe_push_log("✅ No folders to clean")

        return folders_removed, int(total_size_mb)

    except Exception as e:
        safe_push_log(f"⚠️ Error during cleanup: {e}")
        return folders_removed, int(total_size / (1024 * 1024)) if total_size > 0 else 0

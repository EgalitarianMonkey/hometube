"""
File System Utilities for HomeTube

Provides centralized file and directory management functionality
including cleanup operations, directory listing, and file operations.
"""

import shutil
from pathlib import Path
from typing import List

import streamlit as st

try:
    from .logs_utils import safe_push_log
except ImportError:
    from logs_utils import safe_push_log


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


def should_remove_tmp_files() -> bool:
    """
    Check if temporary files should be removed.

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
        return settings.REMOVE_TMP_FILES
    except ImportError:
        # Fallback if config not available
        return True


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
            # Download temporary files
            patterns = [f"{base_filename}.*", "*.part", "*.ytdl", "*.temp", "*.tmp"]
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

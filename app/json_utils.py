"""
JSON utilities for HomeTube.

Provides centralized, safe JSON file operations with consistent
error handling across the entire codebase.

This module eliminates duplicated JSON load/save logic scattered
across status_utils.py, url_utils.py, playlist_utils.py, etc.
"""

import json
from pathlib import Path
from typing import Any, TypeVar

# Type alias for JSON-compatible data
JsonData = dict[str, Any]
T = TypeVar("T")


def safe_load_json(
    path: Path | str,
    default: T | None = None,
    log_errors: bool = True,
) -> JsonData | T | None:
    """
    Safely load JSON from a file with consistent error handling.

    This function provides a centralized, robust JSON loading mechanism
    that handles common error cases gracefully.

    Args:
        path: Path to the JSON file (Path object or string)
        default: Default value to return on error (default: None)
        log_errors: Whether to log errors (default: True)

    Returns:
        Parsed JSON data as a dict, or default value on error

    Examples:
        >>> data = safe_load_json(Path("config.json"))
        >>> data = safe_load_json("status.json", default={})
        >>> data = safe_load_json(path, default=[], log_errors=False)
    """
    path = Path(path) if isinstance(path, str) else path

    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        if log_errors:
            _log_error(f"Invalid JSON in {path.name}: {e}")
        return default
    except PermissionError:
        if log_errors:
            _log_error(f"Permission denied reading {path.name}")
        return default
    except Exception as e:
        if log_errors:
            _log_error(f"Error reading {path.name}: {e}")
        return default


def safe_save_json(
    path: Path | str,
    data: JsonData,
    indent: int = 2,
    ensure_ascii: bool = False,
    log_errors: bool = True,
    create_parents: bool = True,
) -> bool:
    """
    Safely save data to a JSON file with consistent formatting.

    This function provides a centralized, robust JSON saving mechanism
    with atomic-like behavior and proper error handling.

    Args:
        path: Path to the JSON file (Path object or string)
        data: Dictionary data to save
        indent: JSON indentation level (default: 2)
        ensure_ascii: Force ASCII output (default: False for UTF-8)
        log_errors: Whether to log errors (default: True)
        create_parents: Create parent directories if needed (default: True)

    Returns:
        True if saved successfully, False otherwise

    Examples:
        >>> success = safe_save_json(Path("config.json"), {"key": "value"})
        >>> success = safe_save_json("status.json", data, indent=4)
    """
    path = Path(path) if isinstance(path, str) else path

    try:
        # Create parent directories if needed
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        return True

    except PermissionError:
        if log_errors:
            _log_error(f"Permission denied writing {path.name}")
        return False
    except TypeError as e:
        if log_errors:
            _log_error(f"Data not JSON serializable for {path.name}: {e}")
        return False
    except Exception as e:
        if log_errors:
            _log_error(f"Error writing {path.name}: {e}")
        return False


def json_file_exists(path: Path | str) -> bool:
    """
    Check if a JSON file exists and appears valid.

    Performs a quick validation check without fully parsing the file.

    Args:
        path: Path to check

    Returns:
        True if file exists and is non-empty
    """
    path = Path(path) if isinstance(path, str) else path

    if not path.exists() or not path.is_file():
        return False

    # Check for non-empty file
    try:
        return path.stat().st_size > 2  # Minimum valid JSON is "{}"
    except Exception:
        return False


def update_json_file(
    path: Path | str,
    updates: JsonData,
    create_if_missing: bool = True,
    log_errors: bool = True,
) -> bool:
    """
    Update a JSON file with new key-value pairs.

    Loads existing data, merges updates, and saves back.
    Useful for updating status files or config files.

    Args:
        path: Path to the JSON file
        updates: Dictionary of updates to merge
        create_if_missing: Create file if it doesn't exist (default: True)
        log_errors: Whether to log errors (default: True)

    Returns:
        True if updated successfully, False otherwise

    Examples:
        >>> update_json_file("status.json", {"status": "completed"})
    """
    path = Path(path) if isinstance(path, str) else path

    # Load existing data or start with empty dict
    existing_data = safe_load_json(path, default={}, log_errors=False)

    if existing_data is None and not create_if_missing:
        if log_errors:
            _log_error(f"File not found: {path.name}")
        return False

    existing_data = existing_data or {}

    # Merge updates
    existing_data.update(updates)

    return safe_save_json(path, existing_data, log_errors=log_errors)


def _log_error(message: str) -> None:
    """
    Internal logging helper.

    Uses logs_utils if available, otherwise prints to console.
    """
    try:
        from app.logs_utils import safe_push_log

        safe_push_log(f"⚠️ {message}")
    except ImportError:
        print(f"[JSON Error] {message}")

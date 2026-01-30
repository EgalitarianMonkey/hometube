"""
Notification Engine for HomeTube.

This module provides a non-invasive notification system for:
- Update notifications (new major/minor versions)
- One-time announcements (e.g., cleanup suggestions)
- User-dismissible notifications with persistence

Notifications are stored in tmp/user_notifications.json to avoid spamming users.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional
import re


class NotificationType(Enum):
    """Types of notifications with associated styling."""

    INFO = "info"  # Blue - informational
    SUCCESS = "success"  # Green - positive/encouraging
    WARNING = "warning"  # Orange - attention needed
    ERROR = "error"  # Red - critical


@dataclass
class Notification:
    """A single notification to display to the user."""

    id: str  # Unique identifier for tracking dismissals
    title: str
    message: str
    notification_type: NotificationType = NotificationType.INFO
    action_label: Optional[str] = None  # Optional button label
    action_url: Optional[str] = None  # Optional URL for the action
    icon: str = "ℹ️"


# === NOTIFICATION STATE MANAGEMENT ===


def get_notifications_file_path() -> Path:
    """Get the path to the user notifications state file."""
    try:
        from app.config import ensure_folders_exist

        _, tmp_folder = ensure_folders_exist()
        return tmp_folder / "user_notifications.json"
    except Exception:
        return Path("tmp") / "user_notifications.json"


def load_notification_state() -> dict:
    """Load the notification state from disk."""
    state_file = get_notifications_file_path()

    if not state_file.exists():
        return {"dismissed": {}, "shown": {}}

    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"dismissed": {}, "shown": {}}


def save_notification_state(state: dict) -> None:
    """Save the notification state to disk."""
    state_file = get_notifications_file_path()

    try:
        # Ensure parent directory exists
        state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception:
        pass  # Silently fail - notifications are non-critical


def is_notification_dismissed(notification_id: str) -> bool:
    """Check if a notification has been dismissed by the user."""
    state = load_notification_state()
    return notification_id in state.get("dismissed", {})


def dismiss_notification(notification_id: str) -> None:
    """Mark a notification as dismissed."""
    state = load_notification_state()

    if "dismissed" not in state:
        state["dismissed"] = {}

    state["dismissed"][notification_id] = datetime.now(timezone.utc).isoformat()
    save_notification_state(state)


def mark_notification_shown(notification_id: str) -> None:
    """Mark a notification as shown (for tracking)."""
    state = load_notification_state()

    if "shown" not in state:
        state["shown"] = {}

    if notification_id not in state["shown"]:
        state["shown"][notification_id] = datetime.now(timezone.utc).isoformat()
        save_notification_state(state)


# === VERSION COMPARISON ===


def parse_version(version_str: str) -> tuple:
    """
    Parse a version string into a tuple of integers.

    Args:
        version_str: Version string like "2.5.0" or "v2.6.1"

    Returns:
        Tuple of (major, minor, patch)
    """
    # Remove 'v' prefix if present
    version_str = version_str.lstrip("v").strip()

    # Extract version numbers
    match = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", version_str)
    if match:
        major = int(match.group(1))
        minor = int(match.group(2))
        patch = int(match.group(3)) if match.group(3) else 0
        return (major, minor, patch)

    return (0, 0, 0)


def is_major_or_minor_update(current: str, latest: str) -> bool:
    """
    Check if latest version is a major or minor update (not just patch).

    Examples:
        2.5.0 -> 2.6.0 = True (minor update)
        2.5.0 -> 3.0.0 = True (major update)
        2.5.0 -> 2.5.1 = False (patch only)
    """
    current_tuple = parse_version(current)
    latest_tuple = parse_version(latest)

    # Check if major or minor version increased
    if latest_tuple[0] > current_tuple[0]:  # Major update
        return True
    if latest_tuple[0] == current_tuple[0] and latest_tuple[1] > current_tuple[1]:
        # Minor update
        return True

    return False


def get_current_version() -> str:
    """Get the current HomeTube version."""
    try:
        from app import __version__

        return __version__
    except Exception:
        return "0.0.0"


def get_latest_version() -> Optional[str]:
    """
    Get the latest version from GitHub releases.

    Returns None if unable to fetch.
    """
    try:
        from app.ytdlp_version_check import get_latest_hometube_version

        return get_latest_hometube_version()
    except Exception:
        return None


# === NOTIFICATION GENERATORS ===


def check_update_notification() -> Optional[Notification]:
    """
    Check if there's a new major/minor version and return a notification.

    Only returns a notification if:
    - A new major or minor version is available
    - The user hasn't dismissed this notification
    """
    current = get_current_version()
    latest = get_latest_version()

    if not latest:
        return None

    # Create unique notification ID based on the target version
    notification_id = f"update_{latest}"

    # Check if already dismissed
    if is_notification_dismissed(notification_id):
        return None

    # Check if it's a significant update
    if not is_major_or_minor_update(current, latest):
        return None

    return Notification(
        id=notification_id,
        title="New version available!",
        message=f"HomeTube {latest} is available. You're running {current}.",
        notification_type=NotificationType.SUCCESS,
        action_label="View release",
        action_url=f"https://github.com/music-mash/hometube/releases/tag/v{latest}",
        icon="🎉",
    )


def check_cleanup_notification_v260() -> Optional[Notification]:
    """
    One-time notification for v2.6.0 cleanup suggestion.

    This notification encourages users to clean up old temporary files
    since the organization structure has changed in v2.6.0.
    """
    notification_id = "cleanup_v260_new_tmp_structure"

    # Check if already dismissed
    if is_notification_dismissed(notification_id):
        return None

    # Only show if user has existing tmp files (more than just the notifications file)
    try:
        from app.config import ensure_folders_exist

        _, tmp_folder = ensure_folders_exist()

        if not tmp_folder.exists():
            return None

        # Count items in tmp folder (excluding our notifications file)
        items = [
            f
            for f in tmp_folder.iterdir()
            if f.name != "user_notifications.json"
            and f.name not in ["videos", "playlists"]
        ]

        # Only show if there are old-style folders to clean
        if len(items) == 0:
            return None

    except Exception:
        return None

    return Notification(
        id=notification_id,
        title="Clean up recommended",
        message=(
            "HomeTube v2.6 introduces a new temporary files organization. "
            "Consider cleaning up old temporary files to benefit from the improved structure."
        ),
        notification_type=NotificationType.INFO,
        action_label="Learn more",
        action_url=None,  # Will trigger sidebar cleanup
        icon="🧹",
    )


# === MAIN NOTIFICATION ENGINE ===


def get_active_notifications() -> List[Notification]:
    """
    Get all active notifications that should be displayed.

    This function checks all notification sources and returns
    only the ones that haven't been dismissed.
    """
    notifications = []

    # Check for update notification
    update_notif = check_update_notification()
    if update_notif:
        notifications.append(update_notif)

    # Check for v2.6.0 cleanup notification
    cleanup_notif = check_cleanup_notification_v260()
    if cleanup_notif:
        notifications.append(cleanup_notif)

    return notifications


def render_notifications_streamlit() -> None:
    """
    Render all active notifications in Streamlit.

    This function should be called right after the page header.
    """
    import streamlit as st

    notifications = get_active_notifications()

    if not notifications:
        return

    for notif in notifications:
        # Create a unique key for this notification's dismiss button
        dismiss_key = f"dismiss_{notif.id}"

        # Check if dismiss was clicked in this session
        if st.session_state.get(dismiss_key):
            dismiss_notification(notif.id)
            st.session_state[dismiss_key] = False
            st.rerun()

        # Render the notification
        _render_single_notification(notif, dismiss_key)


def _render_single_notification(notif: Notification, dismiss_key: str) -> None:
    """Render a single notification with dismiss button."""
    import streamlit as st

    # Map notification types to Streamlit components
    type_map = {
        NotificationType.INFO: st.info,
        NotificationType.SUCCESS: st.success,
        NotificationType.WARNING: st.warning,
        NotificationType.ERROR: st.error,
    }

    render_func = type_map.get(notif.notification_type, st.info)

    # Create the notification container
    col1, col2 = st.columns([20, 1])

    with col1:
        # Build message with optional action
        message_parts = [f"{notif.icon} **{notif.title}**", "", notif.message]

        if notif.action_label and notif.action_url:
            message_parts.append("")
            message_parts.append(f"[{notif.action_label}]({notif.action_url})")

        full_message = "\n".join(message_parts)
        render_func(full_message)

    with col2:
        # Dismiss button (styled as a small X)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✕", key=dismiss_key, help="Dismiss this notification"):
            st.session_state[dismiss_key] = True
            st.rerun()

"""
HomeTube Configuration Management

Centralized configuration handling for all environment variables.
Provides type-safe access to settings with proper defaults and validation.
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


# === Container Detection ===
def in_container() -> bool:
    """Detect if we are running inside a container (Docker/Podman)"""
    return Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


IN_CONTAINER = in_container()


# === YouTube Client Fallback Chain ===
# YouTube client fallback chain (ordered by reliability)
# Note: Android client removed as it requires po_token (not implemented)
YOUTUBE_CLIENT_FALLBACKS = [
    {"name": "default", "args": []},
    {"name": "ios", "args": ["--extractor-args", "youtube:player_client=ios"]},
    {"name": "web", "args": ["--extractor-args", "youtube:player_client=web"]},
]


# === Early .env Loading (only if not in container) ===
if not IN_CONTAINER:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_file, override=False)
            print(f"✅ Loaded environment variables from {env_file}")
        except ImportError:
            print("⚠️ python-dotenv not installed — skipping .env loading")
        except Exception as e:
            print(f"⚠️ Failed to load .env file: {e}")


# === Default Configuration ===
_DEFAULTS = {
    # === Core Paths ===
    "VIDEOS_FOLDER": "/data/videos" if IN_CONTAINER else "./downloads",
    "TMP_DOWNLOAD_FOLDER": "/data/tmp" if IN_CONTAINER else "./tmp",
    # === Authentication ===
    "YOUTUBE_COOKIES_FILE_PATH": "",
    "COOKIES_FROM_BROWSER": "",
    # === Localization ===
    "UI_LANGUAGE": "en",
    # === Audio Language Preferences ===
    "LANGUAGE_PRIMARY": "en",  # Primary audio language (e.g., "fr", "en", "es")
    "LANGUAGES_SECONDARIES": "",  # Secondary languages, comma-separated (e.g., "en,es,de")
    "LANGUAGE_PRIMARY_INCLUDE_SUBTITLES": "true",  # Include subtitles for primary language
    "VO_FIRST": "true",  # Prioritize original voice (VO) first before primary language
    # === Quality & Download Preferences ===
    "VIDEO_QUALITY_MAX": "max",  # Maximum video resolution: "max" for highest available, or "2160", "1440", "1080", "720", "480", "360"
    "QUALITY_DOWNGRADE": "true",  # Allow quality downgrade on profile failure (false = stop at first failure)
    "EMBED_CHAPTERS": "true",  # Embed chapters by default
    "EMBED_SUBTITLES": "true",  # Embed subtitles by default
    # === Debug Options ===
    "REMOVE_TMP_FILES_AFTER_DOWNLOAD": "false",  # Keep temporary files by default for debugging and resilience (set to true to auto-cleanup after successful download)
    "NEW_DOWNLOAD_WITHOUT_TMP_FILES": "false",  # Clean tmp folder before new download (set to true to start fresh, useful after errors)
    # === Safety Options ===
    "ALLOW_OVERWRITE_EXISTING_VIDEO": "false",  # Prevent overwriting existing videos by default (set to true to allow overwrites)
    # === Advanced Options ===
    "YTDLP_CUSTOM_ARGS": "",
    "CUTTING_MODE": "keyframes",  # keyframes or precise
    "BROWSER_SELECT": "chrome",  # Default browser for cookie extraction
    # === Playlist Options ===
    "PLAYLIST_VIDEOS_TITLES_PATTERN": "",  # Pattern for playlist video titles (empty = uses default: {idx} - {pretty(title)}.{ext})
    "PLAYLIST_KEEP_OLD_VIDEOS": "false",  # Keep videos removed from playlist (archive instead of delete)
    # === System ===
    "DEBUG": "false",
    # === Jellyfin Integration ===
    "JELLYFIN_BASE_URL": "",
    "JELLYFIN_API_KEY": "",
}


# === Helper Functions ===
def _to_bool(v: str | None, default: bool = False) -> bool:
    """Convert string to boolean"""
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def _to_list(v: str | None, separator: str = ",") -> list[str]:
    """Convert comma-separated string to list of lowercase strings"""
    if not v:
        return []
    return [x.strip().lower() for x in v.split(separator) if x.strip()]


# === Settings Dataclass ===
@dataclass(frozen=True)
class Settings:
    """
    Immutable configuration settings for HomeTube.

    All settings are loaded once and cached for the lifetime of the application.
    Use get_settings() to access the singleton instance.
    """

    # Paths
    VIDEOS_FOLDER: Path
    TMP_DOWNLOAD_FOLDER: Path
    YOUTUBE_COOKIES_FILE_PATH: Optional[str]
    COOKIES_FROM_BROWSER: str

    # Localization
    UI_LANGUAGE: str

    # Audio Language Preferences
    LANGUAGE_PRIMARY: str
    LANGUAGES_SECONDARIES: list[str]
    LANGUAGE_PRIMARY_INCLUDE_SUBTITLES: bool
    VO_FIRST: bool

    # Quality & Download
    VIDEO_QUALITY_MAX: str
    QUALITY_DOWNGRADE: bool
    EMBED_CHAPTERS: bool
    EMBED_SUBTITLES: bool

    # Debug & Advanced
    REMOVE_TMP_FILES_AFTER_DOWNLOAD: bool
    NEW_DOWNLOAD_WITHOUT_TMP_FILES: bool
    ALLOW_OVERWRITE_EXISTING_VIDEO: bool
    YTDLP_CUSTOM_ARGS: str
    CUTTING_MODE: str
    BROWSER_SELECT: str
    DEBUG: bool

    # Playlist Options
    PLAYLIST_VIDEOS_TITLES_PATTERN: str
    PLAYLIST_KEEP_OLD_VIDEOS: bool

    # Integrations
    JELLYFIN_BASE_URL: str
    JELLYFIN_API_KEY: str

    # System info
    IN_CONTAINER: bool = IN_CONTAINER


# === Configuration Loader ===
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Read configuration once, merging defaults and environment variables.

    This function is cached and will only run once per application lifetime.

    Returns:
        Settings: Immutable settings object with all configuration values
    """
    project_root = Path(__file__).resolve().parent.parent
    config = _DEFAULTS.copy()

    # 1️⃣ Override defaults with environment variables
    for key in config:
        env_value = os.getenv(key)
        if env_value is not None:
            config[key] = env_value

    # 2️⃣ Normalize paths
    videos_folder = Path(config["VIDEOS_FOLDER"])
    if not videos_folder.is_absolute():
        videos_folder = (project_root / videos_folder).resolve()

    tmp_folder = Path(config["TMP_DOWNLOAD_FOLDER"])
    if not tmp_folder.is_absolute():
        tmp_folder = (project_root / tmp_folder).resolve()

    cookies_path = config["YOUTUBE_COOKIES_FILE_PATH"].strip()
    if cookies_path and not Path(cookies_path).is_absolute():
        cookies_path = str((project_root / cookies_path).resolve())
    if not cookies_path:
        cookies_path = None

    # 3️⃣ Parse lists and booleans
    languages_secondaries = _to_list(config["LANGUAGES_SECONDARIES"])

    return Settings(
        VIDEOS_FOLDER=videos_folder,
        TMP_DOWNLOAD_FOLDER=tmp_folder,
        YOUTUBE_COOKIES_FILE_PATH=cookies_path,
        COOKIES_FROM_BROWSER=config["COOKIES_FROM_BROWSER"].strip().lower(),
        UI_LANGUAGE=config["UI_LANGUAGE"],
        LANGUAGE_PRIMARY=config["LANGUAGE_PRIMARY"].strip().lower(),
        LANGUAGES_SECONDARIES=languages_secondaries,
        LANGUAGE_PRIMARY_INCLUDE_SUBTITLES=_to_bool(
            config["LANGUAGE_PRIMARY_INCLUDE_SUBTITLES"], True
        ),
        VO_FIRST=_to_bool(config["VO_FIRST"], True),
        VIDEO_QUALITY_MAX=config["VIDEO_QUALITY_MAX"].strip().lower(),
        QUALITY_DOWNGRADE=_to_bool(config["QUALITY_DOWNGRADE"], True),
        EMBED_CHAPTERS=_to_bool(config["EMBED_CHAPTERS"], True),
        EMBED_SUBTITLES=_to_bool(config["EMBED_SUBTITLES"], True),
        REMOVE_TMP_FILES_AFTER_DOWNLOAD=_to_bool(
            config["REMOVE_TMP_FILES_AFTER_DOWNLOAD"], False
        ),
        NEW_DOWNLOAD_WITHOUT_TMP_FILES=_to_bool(
            config["NEW_DOWNLOAD_WITHOUT_TMP_FILES"], False
        ),
        ALLOW_OVERWRITE_EXISTING_VIDEO=_to_bool(
            config["ALLOW_OVERWRITE_EXISTING_VIDEO"], False
        ),
        YTDLP_CUSTOM_ARGS=config["YTDLP_CUSTOM_ARGS"],
        CUTTING_MODE=config["CUTTING_MODE"],
        BROWSER_SELECT=config["BROWSER_SELECT"],
        DEBUG=_to_bool(config["DEBUG"], False),
        PLAYLIST_VIDEOS_TITLES_PATTERN=config["PLAYLIST_VIDEOS_TITLES_PATTERN"].strip(),
        PLAYLIST_KEEP_OLD_VIDEOS=_to_bool(config["PLAYLIST_KEEP_OLD_VIDEOS"], False),
        JELLYFIN_BASE_URL=config["JELLYFIN_BASE_URL"].strip(),
        JELLYFIN_API_KEY=config["JELLYFIN_API_KEY"].strip(),
    )


# === Helper Functions ===
def ensure_folders_exist() -> tuple[Path, Path]:
    """
    Ensure VIDEOS_FOLDER and TMP_DOWNLOAD_FOLDER exist.

    Returns:
        tuple[Path, Path]: (videos_folder, tmp_folder) - both guaranteed to exist

    Raises:
        RuntimeError: If folders cannot be created
    """
    settings = get_settings()

    # Try to create videos folder
    videos_folder = settings.VIDEOS_FOLDER
    try:
        videos_folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # Fallback to user's home directory
        fallback_folder = Path.home() / "HomeTube_Downloads"
        print(f"⚠️ Could not create videos folder {videos_folder}: {e}")
        print(f"💡 Using fallback folder: {fallback_folder}")
        videos_folder = fallback_folder
        try:
            videos_folder.mkdir(parents=True, exist_ok=True)
        except Exception as e2:
            # Last resort: current directory
            videos_folder = Path.cwd() / "downloads"
            print(f"⚠️ Could not create fallback folder: {e2}")
            print(f"💡 Using current directory: {videos_folder}")
            videos_folder.mkdir(parents=True, exist_ok=True)

    # Create temp folder
    tmp_folder = settings.TMP_DOWNLOAD_FOLDER
    try:
        tmp_folder.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"⚠️ Could not create temp folder {tmp_folder}: {e}")
        # Use a subfolder in videos folder as fallback
        tmp_folder = videos_folder / "tmp"
        tmp_folder.mkdir(parents=True, exist_ok=True)

    return videos_folder, tmp_folder


def get_default_subtitle_languages() -> list[str]:
    """
    Get the list of subtitle languages to download based on audio preferences.

    This determines which subtitles should be pre-selected in the UI based on:
    - LANGUAGE_PRIMARY: Primary audio language
    - LANGUAGE_PRIMARY_INCLUDE_SUBTITLES: Whether to include subtitles for primary language
    - LANGUAGES_SECONDARIES: Additional audio languages that should have subtitles

    The returned list is used to:
    1. Pre-check subtitle checkboxes in the UI
    2. Download subtitles automatically when embedding is enabled

    Returns:
        list[str]: Deduplicated list of language codes (e.g., ['en', 'fr', 'es'])
                   Empty list if no languages should be auto-selected

    Examples:
        >>> # With LANGUAGE_PRIMARY="fr", LANGUAGE_PRIMARY_INCLUDE_SUBTITLES=true
        >>> get_default_subtitle_languages()
        ['fr']

        >>> # With LANGUAGE_PRIMARY="en", LANGUAGES_SECONDARIES="fr,es", INCLUDE=true
        >>> get_default_subtitle_languages()
        ['en', 'fr', 'es']

        >>> # With LANGUAGE_PRIMARY="en", INCLUDE=false, SECONDARIES="fr"
        >>> get_default_subtitle_languages()
        ['fr']
    """
    settings = get_settings()
    subtitle_langs = []

    # Add primary language if requested
    if settings.LANGUAGE_PRIMARY_INCLUDE_SUBTITLES and settings.LANGUAGE_PRIMARY:
        subtitle_langs.append(settings.LANGUAGE_PRIMARY.lower())

    # Add secondary languages (they always get subtitles)
    for lang in settings.LANGUAGES_SECONDARIES:
        if lang and lang.lower() not in subtitle_langs:
            subtitle_langs.append(lang.lower())

    return subtitle_langs


def print_config_summary() -> None:
    """Print a summary of the current configuration for debugging"""
    s = get_settings()

    print("\n" + "=" * 80)
    print("🔧 HomeTube Configuration Summary")
    print("=" * 80)

    # System
    print(f"🏃 Running mode: {'Container 📦' if s.IN_CONTAINER else 'Local 💻'}")
    print(f"🐞 Debug mode: {'ON' if s.DEBUG else 'OFF'}")

    # Paths
    print("\n📁 Paths:")
    print(f"   Videos: {s.VIDEOS_FOLDER}")
    if s.VIDEOS_FOLDER.exists():
        if os.access(s.VIDEOS_FOLDER, os.W_OK):
            print("   ✅ Videos folder is ready and writable")
        else:
            print("   ⚠️ Videos folder exists but is not writable!")
    else:
        print("   ⚠️ Videos folder does not exist yet (will be created)")

    print(f"   Temp: {s.TMP_DOWNLOAD_FOLDER}")

    # Authentication
    print("\n🍪 Authentication:")
    if s.YOUTUBE_COOKIES_FILE_PATH and Path(s.YOUTUBE_COOKIES_FILE_PATH).exists():
        print(f"   Cookies file: {s.YOUTUBE_COOKIES_FILE_PATH} ✅")
    elif s.COOKIES_FROM_BROWSER:
        print(f"   Browser cookies: {s.COOKIES_FROM_BROWSER} ✅")
    else:
        print("   ⚠️ No authentication configured (may limit video access)")

    # Localization
    print("\n🌐 Localization:")
    print(f"   UI Language: {s.UI_LANGUAGE}")

    # Audio preferences
    print("\n🎵 Audio Language Preferences:")
    print(f"   Primary: {s.LANGUAGE_PRIMARY or '(none)'}")
    print(f"   Secondaries: {', '.join(s.LANGUAGES_SECONDARIES) or '(none)'}")
    print(f"   VO first: {s.VO_FIRST}")
    print(f"   Include subtitles for primary: {s.LANGUAGE_PRIMARY_INCLUDE_SUBTITLES}")

    # Show computed default subtitle languages
    default_subs = get_default_subtitle_languages()
    if default_subs:
        print(f"   → Default subtitles: {', '.join(default_subs)}")

    # Quality
    print("\n🎬 Video Quality:")
    print(f"   Max resolution: {s.VIDEO_QUALITY_MAX}")
    print(f"   Quality downgrade allowed: {s.QUALITY_DOWNGRADE}")
    print(f"   Embed chapters: {s.EMBED_CHAPTERS}")
    print(f"   Embed subtitles: {s.EMBED_SUBTITLES}")

    # Advanced
    print("\n⚙️ Advanced:")
    print(f"   Cutting mode: {s.CUTTING_MODE}")
    print(f"   Browser select: {s.BROWSER_SELECT}")
    print(f"   Remove temp files after download: {s.REMOVE_TMP_FILES_AFTER_DOWNLOAD}")
    print(f"   New download without tmp files: {s.NEW_DOWNLOAD_WITHOUT_TMP_FILES}")
    print(f"   Allow overwrite existing: {s.ALLOW_OVERWRITE_EXISTING_VIDEO}")
    if s.YTDLP_CUSTOM_ARGS:
        print(f"   Custom yt-dlp args: {s.YTDLP_CUSTOM_ARGS}")

    # Environment file (only in local mode)
    if not s.IN_CONTAINER:
        print("\n📄 Configuration file:")
        import importlib.util

        if importlib.util.find_spec("dotenv") is not None:
            print("   ✅ python-dotenv available: .env files supported")
        else:
            print(
                "   ⚠️ python-dotenv not available - install with: pip install python-dotenv"
            )

        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            print(f"   ✅ Configuration file found: {env_file}")
        else:
            print("   ⚠️ No .env file found - using defaults and environment variables")

    print("=" * 80 + "\n")


# === Auto-print on direct execution ===
if __name__ == "__main__":
    print_config_summary()

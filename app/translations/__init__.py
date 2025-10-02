"""
Translation system for the YouTube downloader app
"""

import os
from typing import Dict, Any

# Cache for translations to avoid repeated loading
_translations_cache = None
_configured_language = None


def configure_language(language: str) -> None:
    """
    Configure the UI language programmatically (used by main.py)

    Args:
        language: Language code (e.g., 'en', 'fr')
    """
    global _configured_language, _translations_cache
    _configured_language = language.lower() if language else "en"
    _translations_cache = None  # Clear cache to force reload


def get_translations() -> Dict[str, Any]:
    """Get translations based on configured language or UI_LANGUAGE environment variable"""
    global _translations_cache

    # Use cached translations if available
    if _translations_cache is not None:
        return _translations_cache

    # Priority: configured language > environment variable > default
    if _configured_language is not None:
        language = _configured_language
    else:
        language = os.getenv("UI_LANGUAGE", "en").lower()

    if language == "en":
        try:
            from .en import TRANSLATIONS
        except ImportError:
            from en import TRANSLATIONS
    else:
        # Default to French for any other language
        try:
            from .fr import TRANSLATIONS
        except ImportError:
            from fr import TRANSLATIONS

    # Cache the translations
    _translations_cache = TRANSLATIONS
    return TRANSLATIONS


def t(key: str, **kwargs) -> str:
    """
    Translate a key with optional formatting

    Args:
        key: Translation key
        **kwargs: Format arguments for string formatting

    Returns:
        Translated string with optional formatting applied
    """
    translations = get_translations()
    text = translations.get(key, f"[MISSING: {key}]")

    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text

    return text

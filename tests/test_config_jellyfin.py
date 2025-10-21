"""
Tests for Jellyfin-related configuration defaults and overrides.
"""


def test_jellyfin_settings_defaults(monkeypatch):
    """Ensure Jellyfin settings default to empty strings when not configured."""
    monkeypatch.delenv("JELLYFIN_BASE_URL", raising=False)
    monkeypatch.delenv("JELLYFIN_API_KEY", raising=False)

    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.JELLYFIN_BASE_URL == ""
    assert settings.JELLYFIN_API_KEY == ""


def test_jellyfin_settings_env_overrides(monkeypatch):
    """Ensure Jellyfin settings respect environment overrides and strip whitespace."""
    monkeypatch.setenv("JELLYFIN_BASE_URL", " https://jellyfin.example:8096/ ")
    monkeypatch.setenv("JELLYFIN_API_KEY", " super-secret ")

    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.JELLYFIN_BASE_URL == "https://jellyfin.example:8096/"
    assert settings.JELLYFIN_API_KEY == "super-secret"

"""Regression tests for profile analysis when yt-dlp reports no filesize.

yt-dlp's --print template prints the bare sentinel ``NA`` for a missing field.
An unquoted ``NA`` is not valid JSON, so if the profile-probe template left its
numeric fields unguarded, ``json.loads`` would reject the whole line and every
profile would be discarded — the download then fails with the misleading
"No profiles available for download", pointing the user at the UI instead of at
the analysis step. HLS sources that report no size (e.g. Loom) hit this on every
link; YouTube is unaffected because its formats carry a size.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.medias_utils import (  # noqa: E402
    YTDLP_FORMAT_PROBE_PRINT_TEMPLATE,
    get_profiles_with_formats_id_to_download,
)


class TestProbeTemplateIsAlwaysValidJson:
    """These run everywhere (no yt-dlp needed): they pin the root cause."""

    def test_unquoted_numeric_fields_have_a_default(self):
        # The two numeric (unquoted) fields must default to 0 so a missing value
        # renders as `0`, never the bare `NA` that breaks json.loads.
        assert "%(height|0)s" in YTDLP_FORMAT_PROBE_PRINT_TEMPLATE
        assert "%(filesize_approx|0)s" in YTDLP_FORMAT_PROBE_PRINT_TEMPLATE

    def test_no_unguarded_numeric_field_remains(self):
        assert "%(height)s" not in YTDLP_FORMAT_PROBE_PRINT_TEMPLATE
        assert "%(filesize_approx)s" not in YTDLP_FORMAT_PROBE_PRINT_TEMPLATE

    def test_template_with_na_substituted_still_parses(self):
        # Simulate exactly what yt-dlp emits once the `|0` defaults apply: the
        # numeric fields resolve to 0, the (quoted) string fields may be "NA".
        rendered = (
            YTDLP_FORMAT_PROBE_PRINT_TEMPLATE.replace("%(format_id)s", "v+a")
            .replace("%(ext)s", "mp4")
            .replace("%(height|0)s", "0")
            .replace("%(vcodec)s", "NA")
            .replace("%(protocol)s", "m3u8_native")
            .replace("%(filesize_approx|0)s", "0")
        )
        parsed = json.loads(rendered)
        assert parsed["filesize_approx"] == 0
        assert parsed["height"] == 0
        assert parsed["vcodec"] == "NA"


@pytest.mark.external
class TestProfilesForSizelessHlsSource:
    """End-to-end through real yt-dlp (offline, --load-info-json)."""

    def test_a_sizeless_source_still_yields_a_profile(self):
        json_path = Path(__file__).parent / "ytdlp-json" / "video-hls-no-filesize.json"

        # mono-lang path: no separate audio tracks to combine
        profiles = get_profiles_with_formats_id_to_download(json_path, False, [])

        assert isinstance(profiles, list)
        assert len(profiles) >= 1, (
            "a source that reports no filesize must still produce a profile; "
            "regression for the NA-in-JSON parse failure"
        )
        best = profiles[0]
        assert best["format_id"], "profile must carry a usable format_id"
        # A video+audio spec is what makes the file playable; a video-only id
        # would download a silent file.
        assert "+" in best["format_id"]

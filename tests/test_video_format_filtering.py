"""
Tests for video format filtering on the vcodec field.

yt-dlp distinguishes two cases that must not be conflated:
- vcodec == "none": the format definitively has no video stream (audio-only)
  and must be excluded from any video format list.
- vcodec is None (or missing): the codec is unknown but the format may still
  carry video (common with HLS/generic extractors). It must be kept.
"""

from app.medias_utils import analyze_video_formats, get_available_formats


def _url_info(formats):
    return {"formats": formats}


AUDIO_ONLY = {
    "format_id": "251",
    "ext": "webm",
    "vcodec": "none",
    "acodec": "opus",
    "abr": 160,
}

KNOWN_VIDEO = {
    "format_id": "248",
    "ext": "webm",
    "vcodec": "vp9",
    "acodec": "none",
    "height": 1080,
    "fps": 30,
}

# Real-world shape from HLS/generic extractors: video format whose codec
# metadata is absent, reported as an explicit null (see issue #137).
UNKNOWN_CODEC_VIDEO = {
    "format_id": "hls-720",
    "ext": "mp4",
    "vcodec": None,
    "acodec": None,
    "height": 720,
    "width": 1280,
    "protocol": "m3u8_native",
}


class TestAnalyzeVideoFormats:
    """analyze_video_formats must only exclude vcodec == 'none'."""

    def test_excludes_audio_only_formats(self):
        result = analyze_video_formats(_url_info([AUDIO_ONLY, KNOWN_VIDEO]))
        assert [fmt["format_id"] for fmt in result] == ["248"]

    def test_keeps_formats_with_null_vcodec(self):
        result = analyze_video_formats(_url_info([AUDIO_ONLY, UNKNOWN_CODEC_VIDEO]))
        assert [fmt["format_id"] for fmt in result] == ["hls-720"]

    def test_keeps_formats_with_missing_vcodec(self):
        no_vcodec_key = {"format_id": "raw-480", "ext": "mp4", "height": 480}
        result = analyze_video_formats(_url_info([no_vcodec_key]))
        assert [fmt["format_id"] for fmt in result] == ["raw-480"]

    def test_sorting_survives_null_vcodec(self):
        result = analyze_video_formats(
            _url_info([UNKNOWN_CODEC_VIDEO, KNOWN_VIDEO, AUDIO_ONLY])
        )
        assert [fmt["format_id"] for fmt in result] == ["248", "hls-720"]


class TestGetAvailableFormats:
    """The user-facing list keeps null-vcodec formats (regression guard)."""

    def test_excludes_audio_only_but_keeps_null_vcodec(self):
        result = get_available_formats(
            _url_info([AUDIO_ONLY, KNOWN_VIDEO, UNKNOWN_CODEC_VIDEO])
        )
        format_ids = [fmt["format_id"] for fmt in result]
        assert "251" not in format_ids
        assert set(format_ids) == {"248", "hls-720"}

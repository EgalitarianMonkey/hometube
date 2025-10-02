"""
Quality profiles configuration for HomeTube.

This module contains the quality profiles matrix used by HomeTube for video downloads.
It's separated from main.py to avoid Streamlit import issues in tests.
"""

QUALITY_PROFILES = [
    {
        "name": "mkv_av1_opus",
        "label": "🏆 MKV – AV1 + Opus (Ultimate Quality)",
        "video_codec": "AV1",
        "audio_codec": "Opus",
        "container": "MKV",
        "format": "bv*[vcodec^=av01][ext=webm]+ba*[acodec^=opus][ext=webm]/bv*[vcodec^=av01][ext=webm]+ba*[acodec^=opus]",
        "format_sort": "res:8640,fps,codec:av01,+size,br,acodec:opus",
        "extra_args": ["--prefer-free-formats", "--remux-video", "mkv"],
        "description": "Best quality with next-gen codecs, fast remux, excellent subtitle support",
        "priority": 1,
        "requires_probe": ["av01", "opus"],  # Must have these codecs available
    },
    {
        "name": "mkv_vp9_opus",
        "label": "🥇 MKV – VP9 + Opus (Premium Fallback)",
        "video_codec": "VP9",
        "audio_codec": "Opus",
        "container": "MKV",
        "format": "bv*[vcodec^=vp9.2][ext=webm]+ba*[acodec^=opus][ext=webm]/bv*[vcodec^=vp9][ext=webm]+ba*[acodec^=opus]",
        "format_sort": "res:8640,fps,codec:vp9.2,codec:vp9,+size,br,acodec:opus",
        "extra_args": ["--prefer-free-formats", "--remux-video", "mkv"],
        "description": "Premium fallback when AV1 unavailable, excellent quality and subtitle support",
        "priority": 2,
        "requires_probe": ["vp9", "opus"],
    },
    {
        "name": "mp4_av1_aac",
        "label": "🥈 MP4 – AV1 + AAC (Mobile/TV Compatible)",
        "video_codec": "AV1",
        "audio_codec": "AAC",
        "container": "MP4",
        "format": "bv*[vcodec^=av01]+ba*[acodec^=aac]/bv*[vcodec^=av01]+ba*",
        "format_sort": "res:8640,fps,codec:av01,+size,br,acodec:aac",
        "extra_args": ["--remux-video", "mp4"],
        "description": "Next-gen video with universal audio, great mobile/TV compatibility",
        "priority": 3,
        "requires_probe": ["av01"],
        "audio_transcode": True,  # May need to transcode Opus → AAC
    },
    {
        "name": "mp4_h264_aac",
        "label": "🥉 MP4 – H.264 + AAC (Maximum Compatibility)",
        "video_codec": "H.264",
        "audio_codec": "AAC",
        "container": "MP4",
        "format": "bv*[vcodec^=h264]+ba*[acodec^=aac]/bv*[vcodec^=h264]+ba*",
        "format_sort": "res:8640,fps,codec:h264,+size,br,acodec:aac",
        "extra_args": ["--remux-video", "mp4"],
        "description": "Universal compatibility, works on all devices and platforms",
        "priority": 4,
        "requires_probe": ["h264"],
        "audio_transcode": True,
    },
]

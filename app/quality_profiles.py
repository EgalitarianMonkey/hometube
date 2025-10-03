"""
Quality profiles configuration for HomeTube.

This module contains the quality profiles matrix used by HomeTube for video downloads.
It's separated from main.py to avoid Streamlit import issues in tests.
"""

QUALITY_PROFILES = [
    {
        "name": "mkv_av1_opus",
        "label": "🏆 MKV – AV1 + Opus (Ultimate Quality)",
        "video_codec_ext": [
            {"vcodec": ["av01"], "ext": ["webm", "mp4", None]},
        ],
        "audio_codec_ext": [
            {"acodec": ["opus"], "ext": ["webm", "ogg", None]},
        ],
        "container": "mkv",
        "extra_args": ["--prefer-free-formats", "--remux-video", "mkv"],
        "description": "Best quality with next-gen codecs, fast remux, excellent subtitle support",
        "priority": 1,
    },
    {
        "name": "mkv_vp9_opus",
        "label": "🥇 MKV – VP9 + Opus (Premium Fallback)",
        "video_codec_ext": [
            {"vcodec": ["vp9.2", "vp9"], "ext": ["webm", None]},
        ],
        "audio_codec_ext": [
            {"acodec": ["opus"], "ext": ["webm", "ogg", None]},
        ],
        "container": "mkv",
        "extra_args": ["--prefer-free-formats", "--remux-video", "mkv"],
        "description": "Premium fallback when AV1 unavailable, excellent quality and subtitle support",
        "priority": 2,
    },
    {
        "name": "mp4_av1_aac",
        "label": "🥈 MP4 – AV1 + AAC (Mobile/TV Compatible)",
        "video_codec_ext": [
            {"vcodec": ["av01"], "ext": ["mp4", None]},
        ],
        "audio_codec_ext": [
            {"acodec": ["mp4a", "aac"], "ext": ["m4a", "mp4", None]},
        ],
        "container": "mp4",
        "extra_args": ["--remux-video", "mp4"],
        "description": "Next-gen video with universal audio, great mobile/TV compatibility",
        "priority": 3,
        "audio_transcode": True,  # May need to transcode Opus → AAC
    },
    {
        "name": "mp4_h264_aac",
        "label": "🥉 MP4 – H.264 + AAC (Maximum Compatibility)",
        "video_codec_ext": [
            {"vcodec": ["avc1", "h264"], "ext": ["mp4", None]},
        ],
        "audio_codec_ext": [
            {"acodec": ["mp4a", "aac"], "ext": ["m4a", "mp4", None]},
        ],
        "container": "mp4",
        "extra_args": ["--remux-video", "mp4"],
        "description": "Universal compatibility, works on all devices and platforms",
        "priority": 4,
        "audio_transcode": True,
    },
]

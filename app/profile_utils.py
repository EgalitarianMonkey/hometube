"""
Utility functions for quality profile matching.
Separated from main.py to avoid Streamlit imports in tests.
"""

from typing import List, Dict, Optional


def parse_format_line(line: str) -> Optional[Dict]:
    """
    Parse a line from yt-dlp --list-formats output.

    Args:
        line: Line from the formats list

    Returns:
        Dict in EXAMPLE_FORMATS format or None if not a valid format
    """
    line = line.strip()

    # Ignore headers and empty lines
    if (
        not line
        or line.startswith("ID")
        or line.startswith("─")
        or "Available formats" in line
        or "storyboard" in line
        or "mhtml" in line
    ):
        return None

    parts = line.split()
    if len(parts) < 3:
        return None

    try:
        format_id = parts[0]
        ext = parts[1]

        # Detect resolution and type
        resolution_str = "unknown"
        height = 0
        fps = None
        vcodec = "none"
        acodec = "none"

        # Look for resolution
        for i, part in enumerate(parts):
            if "x" in part and part.replace("x", "").replace(".", "").isdigit():
                resolution_str = part
                try:
                    height = int(part.split("x")[1])
                except (ValueError, IndexError):
                    height = 0
                # FPS often after resolution
                if i + 1 < len(parts) and parts[i + 1].isdigit():
                    fps = int(parts[i + 1])
                break
            elif part == "audio" and i + 1 < len(parts) and parts[i + 1] == "only":
                resolution_str = "audio only"
                height = 0
                break

        # Detect codecs in line content
        line_lower = line.lower()

        # Video codecs
        if "avc1" in line_lower or "h264" in line_lower:
            vcodec = "avc1"
        elif "vp9" in line_lower:
            vcodec = "vp9"
        elif "av01" in line_lower:
            vcodec = "av01"

        # Audio codecs
        if "mp4a" in line_lower or "aac" in line_lower:
            acodec = "aac"
        elif "opus" in line_lower:
            acodec = "opus"

        # Look for bitrates (numbers followed by 'k')
        tbr = None
        abr = None
        vbr = None

        for part in parts:
            if part.endswith("k") and part[:-1].replace(".", "").isdigit():
                rate = int(float(part[:-1]))
                if resolution_str == "audio only":
                    abr = rate
                    tbr = rate
                elif vcodec != "none" and acodec == "none":
                    vbr = rate
                    tbr = rate
                elif tbr is None:
                    tbr = rate

        return {
            "format_id": format_id,
            "ext": ext,
            "resolution": resolution_str,
            "height": height,
            "fps": fps,
            "vcodec": vcodec,
            "acodec": acodec,
            "abr": abr,
            "vbr": vbr,
            "tbr": tbr,
            "protocol": "https",
            "format_note": (
                f"{height}p"
                if height > 0
                else ("audio" if resolution_str == "audio only" else "unknown")
            ),
        }

    except (ValueError, IndexError):
        return None


def get_max_allowed_resolution(
    video_quality_max: str, available_formats: List[Dict]
) -> int:
    """
    Détermine la résolution maximale autorisée basée sur VIDEO_QUALITY_MAX.

    Args:
        video_quality_max: Valeur de VIDEO_QUALITY_MAX ("max", "2160", "1440", "1080", etc.)
        available_formats: Liste des formats vidéo disponibles

    Returns:
        int: Résolution maximale autorisée en pixels (hauteur)
    """
    if not available_formats:
        return 1080  # Default fallback

    # Find max available resolution
    max_available = max(
        f.get("height", 0) for f in available_formats if f.get("height", 0) > 0
    )

    # If VIDEO_QUALITY_MAX = "max", return the max available
    if video_quality_max == "max":
        return max_available

    # Otherwise, try to parse as integer
    try:
        max_requested = int(video_quality_max)
        # Return minimum between requested and available
        return min(max_requested, max_available)
    except (ValueError, TypeError):
        # If parsing fails, use max available
        return max_available


def match_profiles_to_formats(
    formats: List[Dict], quality_profiles: List[Dict], video_quality_max: str = "max"
) -> List[Dict]:
    """
    Logique simple et prévisible de matching des profils.

    Pour chaque profil :
    1. Trouve les 2 meilleurs formats vidéo qui correspondent aux codecs du profil
    2. Trouve les 2 meilleurs formats audio qui correspondent aux codecs du profil
    3. Crée toutes les combinaisons (2 vidéo × 2 audio = max 4 par profil)
    4. Au total : 4 profils × 4 combinaisons = max 16 combinaisons

    Args:
        formats: Liste des formats récupérés par get_video_formats()
        quality_profiles: Liste des profils de qualité définis
        video_quality_max: Résolution max autorisée ("max", "2160", "1080", etc.)

    Returns:
        Liste des combinaisons dans l'ordre strict de QUALITY_PROFILES
    """
    if not formats or not quality_profiles:
        return []

    # Séparer les formats vidéo et audio (formats purs uniquement)
    video_formats = [
        f for f in formats if f["vcodec"] != "none" and f["acodec"] == "none"
    ]
    audio_formats = [
        f for f in formats if f["acodec"] != "none" and f["vcodec"] == "none"
    ]

    if not video_formats or not audio_formats:
        return []

    # Déterminer la résolution max autorisée
    max_resolution = get_max_allowed_resolution(video_quality_max, video_formats)

    # Filtrer les formats vidéo à cette résolution
    target_video_formats = [
        f for f in video_formats if f.get("height", 0) == max_resolution
    ]

    if not target_video_formats:
        return []

    # Trier tous les formats par qualité
    target_video_formats.sort(
        key=lambda x: (x.get("fps", 0) or 0, x.get("vbr", 0) or x.get("tbr", 0) or 0),
        reverse=True,
    )
    audio_formats.sort(key=lambda x: x.get("abr", 0) or 0, reverse=True)

    all_combinations = []

    # Pour chaque profil, trouver les formats compatibles
    for profile in quality_profiles:
        profile_name = profile["name"]

        # Trouver les 2 meilleurs formats vidéo pour ce profil
        matching_video_formats = []
        for video_spec in profile.get("video_codec_ext", []):
            required_video_codecs = video_spec.get("vcodec", [])
            allowed_video_exts = video_spec.get("ext", [])

            for fmt in target_video_formats:
                fmt_codec = fmt["vcodec"]
                fmt_ext = fmt["ext"]

                # Vérifier si le codec correspond
                codec_match = False
                for required_codec in required_video_codecs:
                    if (
                        fmt_codec == required_codec
                        or fmt_codec.startswith(required_codec + ".")
                        or (required_codec == "h264" and fmt_codec == "avc1")
                    ):
                        codec_match = True
                        break

                # Vérifier l'extension si spécifiée
                ext_match = True
                if allowed_video_exts and None not in allowed_video_exts:
                    ext_match = fmt_ext in allowed_video_exts

                if codec_match and ext_match:
                    matching_video_formats.append(fmt)
                    if len(matching_video_formats) >= 2:  # Max 2 formats vidéo
                        break

            if len(matching_video_formats) >= 2:
                break

        # Trouver les 2 meilleurs formats audio pour ce profil
        matching_audio_formats = []
        for audio_spec in profile.get("audio_codec_ext", []):
            required_audio_codecs = audio_spec.get("acodec", [])
            allowed_audio_exts = audio_spec.get("ext", [])

            for fmt in audio_formats:
                fmt_codec = fmt["acodec"]
                fmt_ext = fmt["ext"]

                # Vérifier si le codec correspond
                codec_match = False
                for required_codec in required_audio_codecs:
                    if fmt_codec == required_codec or (
                        required_codec == "mp4a" and fmt_codec == "aac"
                    ):
                        codec_match = True
                        break

                # Vérifier l'extension si spécifiée
                ext_match = True
                if allowed_audio_exts and None not in allowed_audio_exts:
                    ext_match = fmt_ext in allowed_audio_exts

                if codec_match and ext_match:
                    matching_audio_formats.append(fmt)
                    if len(matching_audio_formats) >= 2:  # Max 2 formats audio
                        break

            if len(matching_audio_formats) >= 2:
                break

        # Créer toutes les combinaisons pour ce profil (2×2 = max 4)
        if matching_video_formats and matching_audio_formats:
            for video_format in matching_video_formats:
                for audio_format in matching_audio_formats:
                    combination = {
                        "profile_name": profile_name,
                        "profile_label": profile["label"],
                        "video_format": video_format,
                        "audio_format": audio_format,
                        "format_spec": f"{video_format['format_id']}+{audio_format['format_id']}",
                        "container": profile["container"],
                        "extra_args": profile.get("extra_args", []),
                        "priority": profile["priority"],
                        "target_resolution": max_resolution,
                    }
                    all_combinations.append(combination)

    return all_combinations


def generate_profile_combinations(
    profiles: List[Dict], formats: List[Dict], video_quality_max: str = "max"
) -> List[Dict]:
    """
    Generate combinations for specific profiles with available formats.

    Args:
        profiles: List of specific profiles to match (instead of all QUALITY_PROFILES)
        formats: List of formats retrieved by get_video_formats()
        video_quality_max: Maximum video resolution

    Returns:
        List of combinations for the specified profiles
    """
    if not formats or not profiles:
        return []

    # Use the main matching function with specific profiles
    combinations = match_profiles_to_formats(formats, profiles, video_quality_max)

    return combinations

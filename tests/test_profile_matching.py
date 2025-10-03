import pytest
from app.profile_utils import match_profiles_to_formats
from app.quality_profiles import QUALITY_PROFILES

# Sample yt-dlp format data for testing (format demandé par l'utilisateur)
# Data includes all common codec combinations for comprehensive testing
SAMPLE_FORMATS = [
    {
        "format_id": "249",
        "ext": "webm",
        "resolution": "audio only",
        "height": 0,
        "fps": None,
        "vcodec": "none",
        "acodec": "opus",
        "abr": 49,
        "vbr": None,
        "tbr": 49,
        "protocol": "https",
        "format_note": "audio",
    },
    {
        "format_id": "250",
        "ext": "webm",
        "resolution": "audio only",
        "height": 0,
        "fps": None,
        "vcodec": "none",
        "acodec": "opus",
        "abr": 64,
        "vbr": None,
        "tbr": 64,
        "protocol": "https",
        "format_note": "audio",
    },
    {
        "format_id": "140",
        "ext": "m4a",
        "resolution": "audio only",
        "height": 0,
        "fps": None,
        "vcodec": "none",
        "acodec": "aac",
        "abr": 128,
        "vbr": None,
        "tbr": 128,
        "protocol": "https",
        "format_note": "audio",
    },
    {
        "format_id": "394",
        "ext": "mp4",
        "resolution": "144x256",
        "height": 144,
        "fps": 30,
        "vcodec": "av01",
        "acodec": "none",
        "abr": None,
        "vbr": 80,
        "tbr": 80,
        "protocol": "https",
        "format_note": "144p",
    },
    {
        "format_id": "399",
        "ext": "mp4",
        "resolution": "1080x1920",
        "height": 1080,
        "fps": 30,
        "vcodec": "av01",
        "acodec": "none",
        "abr": None,
        "vbr": 2000,
        "tbr": 2000,
        "protocol": "https",
        "format_note": "1080p",
    },
    {
        "format_id": "315",
        "ext": "webm",
        "resolution": "2160x3840",
        "height": 2160,
        "fps": 30,
        "vcodec": "vp9",
        "acodec": "none",
        "abr": None,
        "vbr": 15000,
        "tbr": 15000,
        "protocol": "https",
        "format_note": "2160p",
    },
    {
        "format_id": "136",
        "ext": "mp4",
        "resolution": "720x1280",
        "height": 720,
        "fps": 30,
        "vcodec": "avc1",
        "acodec": "none",
        "abr": None,
        "vbr": 1200,
        "tbr": 1200,
        "protocol": "https",
        "format_note": "720p",
    },
    # Additional test data for more codec coverage
    {
        "format_id": "313",
        "ext": "webm",
        "resolution": "2160x3840",
        "height": 2160,
        "fps": 30,
        "vcodec": "vp9",
        "acodec": "none",
        "abr": None,
        "vbr": 18000,
        "tbr": 18000,
        "protocol": "https",
        "format_note": "2160p",
    },
    {
        "format_id": "401",
        "ext": "mp4",
        "resolution": "2160x3840",
        "height": 2160,
        "fps": 25,
        "vcodec": "av01",
        "acodec": "none",
        "abr": None,
        "vbr": 8947,
        "tbr": 8947,
        "protocol": "https",
        "format_note": "2160p",
    },
]


def test_match_profiles_basic():
    """Test du matching basique des profils."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES)

    # Doit retourner une liste de combinaisons
    assert isinstance(combinations, list)
    assert len(combinations) > 0

    # Chaque combinaison doit avoir la structure attendue
    combo = combinations[0]
    required_keys = [
        "profile_name",
        "profile_label",
        "video_format",
        "audio_format",
        "format_spec",
        "container",
        "extra_args",
        "priority",
        "target_resolution",
    ]
    for key in required_keys:
        assert key in combo, f"Missing required key: {key}"

    # Vérifier les types des données
    assert isinstance(combo["profile_name"], str)
    assert isinstance(combo["profile_label"], str)
    assert isinstance(combo["video_format"], dict)
    assert isinstance(combo["audio_format"], dict)
    assert isinstance(combo["format_spec"], str)
    assert isinstance(combo["container"], str)
    assert isinstance(combo["extra_args"], list)
    assert isinstance(combo["priority"], int)
    assert isinstance(combo["target_resolution"], int)

    # Vérifier que format_spec a la bonne forme (video+audio)
    assert "+" in combo["format_spec"]
    video_id, audio_id = combo["format_spec"].split("+")
    assert video_id == combo["video_format"]["format_id"]
    assert audio_id == combo["audio_format"]["format_id"]


def test_match_profiles_empty():
    """Test avec une liste de formats vide."""
    combinations = match_profiles_to_formats([], QUALITY_PROFILES)
    assert combinations == []


def test_match_profiles_no_profiles():
    """Test avec une liste de profils vide."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, [])
    assert combinations == []


def test_match_profiles_invalid_input():
    """Test avec des entrées invalides."""
    # None input
    combinations = match_profiles_to_formats(None, QUALITY_PROFILES)
    assert combinations == []

    combinations = match_profiles_to_formats(SAMPLE_FORMATS, None)
    assert combinations == []


def test_av1_opus_priority():
    """Test que AV1+Opus est prioritaire (profil mkv_av1_opus)."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES)

    # Doit trouver une combinaison AV1+Opus
    av1_opus_combos = [
        combo
        for combo in combinations
        if (
            combo["video_format"]["vcodec"] == "av01"
            and combo["audio_format"]["acodec"] == "opus"
        )
    ]

    assert len(av1_opus_combos) > 0, "Aucune combinaison AV1+Opus trouvée"

    # La première combinaison AV1+Opus doit être du profil mkv_av1_opus
    best_av1_opus = av1_opus_combos[0]
    assert best_av1_opus["profile_name"] == "mkv_av1_opus"
    assert best_av1_opus["priority"] == 1, "AV1+Opus devrait avoir la priorité 1"

    # Vérifier que le format_spec correspond bien aux formats choisis
    format_spec = best_av1_opus["format_spec"]
    video_id, audio_id = format_spec.split("+")
    assert best_av1_opus["video_format"]["format_id"] == video_id
    assert best_av1_opus["audio_format"]["format_id"] == audio_id


def test_priority_ordering():
    """Test que les combinaisons sont triées par priorité."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES)

    # Les priorités doivent être dans l'ordre croissant (1 = plus haute)
    priorities = [combo["priority"] for combo in combinations]
    assert priorities == sorted(priorities), f"Priorités mal triées: {priorities}"

    # Le premier élément doit avoir la priorité 1 (si disponible)
    if combinations:
        assert combinations[0]["priority"] >= 1


def test_resolution_based_matching():
    """Test du matching basé sur la résolution."""

    # Tester avec les formats d'exemple et tous les profils
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES, "max")

    assert len(combinations) > 0, "Aucune combinaison trouvée"

    # Vérifier que chaque combinaison a une résolution cible
    for combo in combinations:
        target_res = combo["target_resolution"]
        assert isinstance(target_res, int), f"Résolution cible invalide: {target_res}"
        assert target_res > 0, f"Résolution cible négative: {target_res}"

        # La résolution vidéo ne doit pas dépasser la cible
        video_height = combo["video_format"].get("height", 0)
        assert (
            video_height <= target_res
        ), f"Résolution vidéo {video_height} > cible {target_res}"


def test_codec_matching():
    """Test que les codecs sont correctement matchés selon les profils."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES)

    # Vérifier que chaque combinaison respecte les contraintes du profil
    for combo in combinations:
        profile_name = combo["profile_name"]
        video_codec = combo["video_format"]["vcodec"]
        audio_codec = combo["audio_format"]["acodec"]

        # Trouver le profil correspondant
        profile = None
        for p in QUALITY_PROFILES:
            if p["name"] == profile_name:
                profile = p
                break

        assert (
            profile is not None
        ), f"Profil {profile_name} non trouvé dans QUALITY_PROFILES"

        # Vérifier que les codecs matchent (structure réelle: vcodec/acodec dans les listes)
        if "video_codec_ext" in profile:
            expected_video_codecs = []
            for ext in profile["video_codec_ext"]:
                expected_video_codecs.extend(ext.get("vcodec", []))
            assert (
                video_codec in expected_video_codecs
            ), f"Codec vidéo {video_codec} non supporté par profil {profile_name}. Attendus: {expected_video_codecs}"

        if "audio_codec_ext" in profile:
            expected_audio_codecs = []
            for ext in profile["audio_codec_ext"]:
                expected_audio_codecs.extend(ext.get("acodec", []))
            assert (
                audio_codec in expected_audio_codecs
            ), f"Codec audio {audio_codec} non supporté par profil {profile_name}. Attendus: {expected_audio_codecs}"


def test_no_duplicate_combinations():
    """Test qu'il n'y a pas de combinaisons dupliquées."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES)

    format_specs = [combo["format_spec"] for combo in combinations]
    unique_specs = set(format_specs)

    assert len(format_specs) == len(unique_specs), "Combinaisons dupliquées détectées"


def test_combination_logic():
    """Test que toutes les combinaisons 2×2 sont générées pour chaque profil."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES, "max")

    # Grouper par profile name
    by_profile = {}
    for combo in combinations:
        profile_name = combo["profile_name"]
        if profile_name not in by_profile:
            by_profile[profile_name] = []
        by_profile[profile_name].append(combo)

    # Pour chaque profil, vérifier les combinaisons
    for profile_name, profile_combos in by_profile.items():
        # On s'attend à avoir jusqu'à 4 combinaisons (2 vidéo × 2 audio)
        assert (
            len(profile_combos) <= 4
        ), f"Trop de combinaisons pour {profile_name}: {len(profile_combos)}"

        # Vérifier que les combinaisons sont uniques
        format_specs = [combo["format_spec"] for combo in profile_combos]
        assert len(format_specs) == len(
            set(format_specs)
        ), f"Doublons dans {profile_name}"


def test_format_spec_validity():
    """Test que tous les format_spec sont valides et référencent des formats existants."""
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES)

    format_ids = {fmt["format_id"] for fmt in SAMPLE_FORMATS}

    for combo in combinations:
        format_spec = combo["format_spec"]
        assert "+" in format_spec, f"Format spec invalide (pas de +): {format_spec}"

        video_id, audio_id = format_spec.split("+")
        assert (
            video_id in format_ids
        ), f"Format vidéo {video_id} non trouvé dans SAMPLE_FORMATS"
        assert (
            audio_id in format_ids
        ), f"Format audio {audio_id} non trouvé dans SAMPLE_FORMATS"


if __name__ == "__main__":
    # Test de base
    combinations = match_profiles_to_formats(SAMPLE_FORMATS, QUALITY_PROFILES)
    print(f"Combinaisons générées: {len(combinations)}")

    for i, combo in enumerate(combinations, 1):
        print(f"{i}. {combo['profile_label']}")
        print(f"   Format: {combo['format_spec']}")
        print(
            f"   Vidéo: {combo['video_format']['vcodec']} {combo['video_format']['height']}p"
        )
        print(
            f"   Audio: {combo['audio_format']['acodec']} {combo['audio_format']['abr']}kbps"
        )
        print()

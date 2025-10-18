"""
Test get_formats_id_to_download function with real yt-dlp JSON files.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.medias_utils import analyze_audio_formats, get_formats_id_to_download


def test_mono_lang_video():
    """Test avec une vidéo mono-langue (Stressed Out)"""
    print("\n" + "=" * 80)
    print("🎬 Test 1: Video mono-langue (Stressed Out)")
    print("=" * 80)

    json_path = (
        Path(__file__).parent / "ytdlp-json" / "video-mono-lang-stressedout.json"
    )

    # Analyser les audios
    import json

    with open(json_path) as f:
        url_info = json.load(f)

    vo_lang, audio_formats, multiple_langs = analyze_audio_formats(url_info)

    print("\n📊 Analyse audio:")
    print(f"   VO: {vo_lang}")
    print(f"   Nombre d'audios: {len(audio_formats)}")
    print(f"   Multiple langs: {multiple_langs}")

    # Récupérer les profils de téléchargement
    print("\n🔍 Récupération des profils de téléchargement...")
    profiles = get_formats_id_to_download(json_path, multiple_langs, audio_formats)

    print(f"\n✅ Profils trouvés: {len(profiles)}")
    for i, profile in enumerate(profiles, 1):
        print(f"\n   Profile {i}:")
        print(f"      format_id: {profile.get('format_id')}")
        print(f"      ext: {profile.get('ext')}")
        print(f"      height: {profile.get('height')}p")
        print(f"      vcodec: {profile.get('vcodec')}")
        print(f"      protocol: {profile.get('protocol')}")


def test_multi_lang_video():
    """Test avec une vidéo multi-langues (Disk.org)"""
    print("\n" + "=" * 80)
    print("🎬 Test 2: Video multi-langues (Disk.org)")
    print("=" * 80)

    json_path = Path(__file__).parent / "ytdlp-json" / "video-multi-lang-disk.json"

    # Analyser les audios
    import json

    with open(json_path) as f:
        url_info = json.load(f)

    vo_lang, audio_formats, multiple_langs = analyze_audio_formats(
        url_info, language_primary="fr", languages_secondaries="en,es", vo_first=True
    )

    print("\n📊 Analyse audio:")
    print(f"   VO: {vo_lang}")
    print(f"   Nombre d'audios: {len(audio_formats)}")
    print(f"   Multiple langs: {multiple_langs}")
    print(f"   Langues (top 5): {[a.get('language') for a in audio_formats[:5]]}")

    # Récupérer les profils de téléchargement
    print("\n🔍 Récupération des profils de téléchargement...")
    profiles = get_formats_id_to_download(json_path, multiple_langs, audio_formats)

    print(f"\n✅ Profils trouvés: {len(profiles)}")
    for i, profile in enumerate(profiles, 1):
        print(f"\n   Profile {i}:")
        print(f"      format_id: {profile.get('format_id')}")
        print(f"      ext: {profile.get('ext')}")
        print(f"      height: {profile.get('height')}p")
        print(f"      vcodec: {profile.get('vcodec')}")
        print(f"      protocol: {profile.get('protocol')}")


def test_instagram_video():
    """Test avec une vidéo Instagram (mono audio)"""
    print("\n" + "=" * 80)
    print("🎬 Test 3: Video Instagram (mono audio)")
    print("=" * 80)

    json_path = Path(__file__).parent / "ytdlp-json" / "video-instagram.json"

    # Analyser les audios
    import json

    with open(json_path) as f:
        url_info = json.load(f)

    vo_lang, audio_formats, multiple_langs = analyze_audio_formats(url_info)

    print("\n📊 Analyse audio:")
    print(f"   VO: {vo_lang}")
    print(f"   Nombre d'audios: {len(audio_formats)}")
    print(f"   Multiple langs: {multiple_langs}")

    # Récupérer les profils de téléchargement
    print("\n🔍 Récupération des profils de téléchargement...")
    profiles = get_formats_id_to_download(json_path, multiple_langs, audio_formats)

    print(f"\n✅ Profils trouvés: {len(profiles)}")
    for i, profile in enumerate(profiles, 1):
        print(f"\n   Profile {i}:")
        print(f"      format_id: {profile.get('format_id')}")
        print(f"      ext: {profile.get('ext')}")
        print(f"      height: {profile.get('height')}p")
        print(f"      vcodec: {profile.get('vcodec')}")
        print(f"      protocol: {profile.get('protocol')}")


if __name__ == "__main__":
    try:
        test_mono_lang_video()
        test_multi_lang_video()
        test_instagram_video()

        print("\n" + "=" * 80)
        print("✅ Tous les tests terminés avec succès!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Erreur durant les tests: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

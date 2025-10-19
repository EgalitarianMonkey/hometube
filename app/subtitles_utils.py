"""
Subtitle embedding utilities.

This module provides utilities for checking and embedding subtitles into video files,
independent of the Streamlit UI framework.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


# Import logging functions from centralized module
try:
    from .logs_utils import safe_push_log
except ImportError:
    from logs_utils import safe_push_log


def find_subtitle_files_optimized(
    base_output: str,
    tmp_subfolder_dir: Path,
    subtitle_languages: List[str],
    is_cut: bool = False,
) -> List[Path]:
    """
    Find subtitle files using optimized search patterns.

    Args:
        base_output: Base filename for outputs
        tmp_subfolder_dir: Directory containing subtitle files
        subtitle_languages: List of language codes to find
        is_cut: Whether to look for cut subtitle files

    Returns:
        List of found subtitle file paths
    """
    found_files = []

    for lang in subtitle_languages:
        # Define search patterns in order of preference
        if is_cut:
            # For cut videos, prioritize processed files
            patterns = [
                f"{base_output}-cut-final.{lang}.srt",
                f"{base_output}-cut.{lang}.srt",
                f"{base_output}.{lang}.srt",
                f"{base_output}_{lang}.srt",
                f"{base_output}-{lang}.srt",
                f"{base_output}.{lang}.vtt",
                # Fallback to generic if no language-specific file
                (
                    f"{base_output}-cut-final.srt"
                    if len(subtitle_languages) == 1
                    else None
                ),
                f"{base_output}.srt" if len(subtitle_languages) == 1 else None,
            ]
        else:
            # For uncut videos, look for original files
            patterns = [
                f"{base_output}.{lang}.srt",
                f"{base_output}_{lang}.srt",
                f"{base_output}-{lang}.srt",
                f"{base_output}.{lang}.vtt",
                f"{base_output}_{lang}.vtt",
                f"{base_output}-{lang}.vtt",
                # Fallback to generic if only one language requested
                f"{base_output}.srt" if len(subtitle_languages) == 1 else None,
                f"{base_output}.vtt" if len(subtitle_languages) == 1 else None,
            ]

        # Remove None values
        patterns = [p for p in patterns if p is not None]

        # Search for files
        found_file = None
        for pattern in patterns:
            candidate = tmp_subfolder_dir / pattern
            if candidate.exists():
                # Validate the file
                if validate_subtitle_file(candidate):
                    found_file = candidate
                    safe_push_log(f"✅ Found subtitle file: {candidate.name} ({lang})")
                    break
                else:
                    safe_push_log(f"⚠️ Invalid subtitle file: {candidate.name}")

        if found_file:
            found_files.append(found_file)
        else:
            safe_push_log(f"❌ No valid subtitle file found for language: {lang}")
            safe_push_log(f"   Searched patterns: {', '.join(patterns[:3])}...")

    return found_files


def process_subtitles_for_cutting(
    base_output: str,
    tmp_subfolder_dir: Path,
    subtitle_languages: List[str],
    start_time: float,
    duration: float,
) -> List[tuple]:
    """
    Process multiple subtitle files for video cutting.

    Args:
        base_output: Base filename for outputs
        tmp_subfolder_dir: Directory containing subtitle files
        subtitle_languages: List of language codes to process
        start_time: Start time in seconds
        duration: Duration in seconds

    Returns:
        List of tuples (language, processed_subtitle_path) for successful processing
    """
    processed_subtitle_files = []

    safe_push_log(
        "🎯 Using 3-step cutting process for perfect subtitle synchronization"
    )
    safe_push_log("   1. TRIM: Cut subtitles with original timestamps")
    safe_push_log("   2. REBASE: Shift timestamps to start at 00:00")
    safe_push_log("   3. MUX: Cut video and add processed subtitles")

    # Use optimized file finding
    subtitle_files = find_subtitle_files_optimized(
        base_output, tmp_subfolder_dir, subtitle_languages, is_cut=False
    )

    for i, srt_file in enumerate(subtitle_files):
        lang = subtitle_languages[i] if i < len(subtitle_languages) else "unknown"
        safe_push_log(f"📝 Processing subtitle file: {srt_file.name} ({lang})")

        # Process this subtitle file
        final_srt_file = tmp_subfolder_dir / f"{base_output}-cut-final.{lang}.srt"

        if cut_subtitle_file(srt_file, start_time, duration, final_srt_file):
            processed_subtitle_files.append((lang, final_srt_file))
            safe_push_log(f"✅ Successfully processed {lang} subtitles")
        else:
            safe_push_log(f"⚠️ Failed to process {lang} subtitles")

    return processed_subtitle_files


def get_embedded_subtitle_info(video_path: Path) -> tuple:
    """
    Get detailed information about embedded subtitles using ffprobe.

    Args:
        video_path: Path to the video file to check

    Returns:
        tuple: (has_subtitles: bool, subtitle_count: int, languages: List[str])
    """
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "s",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        # Check subtitle streams
        subtitle_streams = data.get("streams", [])
        subtitle_count = len(subtitle_streams)

        # Extract languages
        languages = []
        for stream in subtitle_streams:
            # Try to get language from tags
            tags = stream.get("tags", {})
            lang = tags.get("language") or tags.get("LANGUAGE") or "unknown"
            languages.append(lang)

        has_subs = subtitle_count > 0

        if has_subs:
            lang_str = ", ".join(languages) if languages else "unknown"
            safe_push_log(
                f"📝 Found {subtitle_count} embedded subtitle stream(s): {lang_str}"
            )
        else:
            safe_push_log("🔍 No embedded subtitles detected")

        return has_subs, subtitle_count, languages

    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        safe_push_log(
            "⚠️ Could not check embedded subtitles (ffprobe not available or failed)"
        )
        return False, 0, []


def has_embedded_subtitles(video_path: Path) -> bool:
    """
    Check if a video file has embedded subtitles using ffprobe.

    Args:
        video_path: Path to the video file to check

    Returns:
        bool: True if embedded subtitles are found, False otherwise
    """
    has_subs, _, _ = get_embedded_subtitle_info(video_path)
    return has_subs


def check_required_subtitles_embedded(
    video_path: Path, required_languages: List[str]
) -> bool:
    """
    Check if all required subtitle languages are embedded in the video.

    Args:
        video_path: Path to the video file to check
        required_languages: List of required language codes (e.g., ['en', 'fr'])

    Returns:
        bool: True if all required languages are embedded, False otherwise
    """
    has_subs, subtitle_count, embedded_languages = get_embedded_subtitle_info(
        video_path
    )

    if not has_subs:
        safe_push_log("❌ No embedded subtitles found")
        return False

    if not required_languages:
        safe_push_log("✅ No specific languages required - subtitles are present")
        return True

    # Check if all required languages are present
    missing_languages = []
    for required_lang in required_languages:
        # Match language codes (case insensitive)
        found = any(
            embedded_lang.lower() == required_lang.lower()
            for embedded_lang in embedded_languages
        )
        if not found:
            missing_languages.append(required_lang)

    if missing_languages:
        safe_push_log(f"❌ Missing subtitle languages: {', '.join(missing_languages)}")
        safe_push_log(f"📝 Embedded languages: {', '.join(embedded_languages)}")
        return False
    else:
        safe_push_log(
            f"✅ All required subtitle languages are embedded: {', '.join(required_languages)}"
        )
        return True


def get_optimal_subtitle_codec(container_format: str) -> tuple:
    """
    Get the optimal subtitle codec and format for a given container.

    Args:
        container_format: Container extension (e.g., ".mp4", ".mkv", ".webm")

    Returns:
        tuple: (codec_name, supports_multiple_formats, preferred_format)
    """
    container = container_format.lower()

    if container == ".mp4":
        return "mov_text", False, "srt"  # MP4 only supports mov_text
    elif container == ".mkv":
        return "srt", True, "srt"  # MKV supports multiple subtitle formats
    elif container == ".webm":
        return "webvtt", False, "vtt"  # WebM prefers WebVTT
    elif container == ".avi":
        return "srt", False, "srt"  # AVI typically uses SRT
    else:
        return "srt", True, "srt"  # Default fallback


def get_language_names(lang_code: str) -> Tuple[str, str]:
    """
    Get the ISO code and native name for a language.

    Args:
        lang_code: Language code (2 or 3 letters)

    Returns:
        Tuple[str, str]: (ISO_code, Native_name)
    """
    # Extended language mapping with native names
    language_map = {
        # Common European languages
        "en": ("en", "English"),
        "fr": ("fr", "Français"),
        "es": ("es", "Español"),
        "de": ("de", "Deutsch"),
        "it": ("it", "Italiano"),
        "pt": ("pt", "Português"),
        "nl": ("nl", "Nederlands"),
        "sv": ("sv", "Svenska"),
        "no": ("no", "Norsk"),
        "da": ("da", "Dansk"),
        "fi": ("fi", "Suomi"),
        "is": ("is", "Íslenska"),
        "pl": ("pl", "Polski"),
        "cs": ("cs", "Čeština"),
        "sk": ("sk", "Slovenčina"),
        "hu": ("hu", "Magyar"),
        "ro": ("ro", "Română"),
        "bg": ("bg", "Български"),
        "hr": ("hr", "Hrvatski"),
        "sr": ("sr", "Српски"),
        "sl": ("sl", "Slovenščina"),
        "et": ("et", "Eesti"),
        "lv": ("lv", "Latviešu"),
        "lt": ("lt", "Lietuvių"),
        "el": ("el", "Ελληνικά"),
        "tr": ("tr", "Türkçe"),
        "ru": ("ru", "Русский"),
        "uk": ("uk", "Українська"),
        "be": ("be", "Беларуская"),
        # Asian languages
        "ja": ("ja", "日本語"),
        "ko": ("ko", "한국어"),
        "zh": ("zh", "中文"),
        "th": ("th", "ไทย"),
        "vi": ("vi", "Tiếng Việt"),
        "id": ("id", "Bahasa Indonesia"),
        "ms": ("ms", "Bahasa Melayu"),
        "tl": ("tl", "Filipino"),
        "hi": ("hi", "हिन्दी"),
        "bn": ("bn", "বাংলা"),
        "ta": ("ta", "தமிழ்"),
        "te": ("te", "తెలుగు"),
        "ml": ("ml", "മലയാളം"),
        "kn": ("kn", "ಕನ್ನಡ"),
        "ur": ("ur", "اردو"),
        "fa": ("fa", "فارسی"),
        "ar": ("ar", "العربية"),
        "he": ("he", "עברית"),
        # Others
        "ca": ("ca", "Català"),
        "eu": ("eu", "Euskera"),
        "gl": ("gl", "Galego"),
        "cy": ("cy", "Cymraeg"),
        "ga": ("ga", "Gaeilge"),
        "mt": ("mt", "Malti"),
        "mk": ("mk", "Македонски"),
        "sq": ("sq", "Shqip"),
        "bs": ("bs", "Bosanski"),
        "me": ("me", "Crnogorski"),
    }

    return language_map.get(lang_code.lower(), (lang_code, lang_code.upper()))


def get_iso639_2_code(lang_code: str) -> str:
    """
    Get ISO 639-2 (3-letter) language code for MP4 metadata.
    MP4 containers prefer 3-letter codes for better compatibility.

    Args:
        lang_code: 2 or 3 letter language code

    Returns:
        str: ISO 639-2 (3-letter) language code
    """
    iso639_2_map = {
        # Common languages with their ISO 639-2 codes
        "en": "eng",
        "fr": "fre",
        "es": "spa",
        "de": "ger",
        "it": "ita",
        "pt": "por",
        "nl": "dut",
        "sv": "swe",
        "no": "nor",
        "da": "dan",
        "fi": "fin",
        "is": "ice",
        "pl": "pol",
        "cs": "cze",
        "sk": "slo",
        "hu": "hun",
        "ro": "rum",
        "bg": "bul",
        "hr": "scr",  # Croatian
        "sr": "scc",  # Serbian
        "sl": "slv",
        "et": "est",
        "lv": "lav",
        "lt": "lit",
        "el": "gre",
        "tr": "tur",
        "ru": "rus",
        "uk": "ukr",
        "be": "bel",
        "ja": "jpn",
        "ko": "kor",
        "zh": "chi",
        "th": "tha",
        "vi": "vie",
        "id": "ind",
        "ms": "may",
        "tl": "tgl",
        "hi": "hin",
        "bn": "ben",
        "ta": "tam",
        "te": "tel",
        "ml": "mal",
        "kn": "kan",
        "ur": "urd",
        "fa": "per",
        "ar": "ara",
        "he": "heb",
        "ca": "cat",
        "eu": "baq",
        "gl": "glg",
        "cy": "wel",
        "ga": "gle",
        "mt": "mlt",
    }

    # If already 3 letters, check if it's valid
    if len(lang_code) == 3:
        return lang_code.lower()

    # Convert 2-letter to 3-letter
    return iso639_2_map.get(lang_code.lower(), "und")  # "und" = undefined


def validate_subtitle_files(subtitle_files: List[Path]) -> List[Path]:
    """
    Validate a list of subtitle files and return only valid ones.

    Args:
        subtitle_files: List of subtitle file paths to validate

    Returns:
        List[Path]: List of valid subtitle files
    """
    if not subtitle_files:
        safe_push_log("⚠️ No subtitle files provided for embedding")
        return []

    valid_subtitle_files = []
    for sub_file in subtitle_files:
        if validate_subtitle_file(sub_file):
            valid_subtitle_files.append(sub_file)
        else:
            safe_push_log(f"❌ Skipping invalid subtitle file: {sub_file.name}")

    if not valid_subtitle_files:
        safe_push_log("❌ No valid subtitle files found")

    return valid_subtitle_files


def create_backup_and_temp_paths(video_path: Path) -> Tuple[Path, Path]:
    """
    Create backup and temporary output paths for video processing.

    Args:
        video_path: Original video file path

    Returns:
        Tuple[Path, Path]: (backup_path, temp_output_path)
    """
    backup_path = video_path.with_suffix(video_path.suffix + ".backup")
    temp_output = video_path.parent / (video_path.stem + "_tmp" + video_path.suffix)
    return backup_path, temp_output


def create_backup(video_path: Path, backup_path: Path) -> None:
    """Create backup of original video file."""
    shutil.copy2(str(video_path), str(backup_path))


def restore_backup_on_error(
    video_path: Path, backup_path: Path, temp_output: Path
) -> None:
    """Restore backup and clean up temp files on error."""
    if backup_path and backup_path.exists():
        if video_path.exists():
            video_path.unlink()
        backup_path.rename(video_path)
    if temp_output and temp_output.exists():
        temp_output.unlink()


def finalize_video_processing(
    video_path: Path, backup_path: Path, temp_output: Path
) -> None:
    """Finalize video processing by replacing original with processed version."""
    video_path.unlink()
    temp_output.rename(video_path)
    backup_path.unlink()


def add_subtitle_metadata(
    cmd: List[str], subtitle_files: List[Path], use_mp4_optimized: bool = False
) -> None:
    """
    Add subtitle metadata to ffmpeg command.

    Args:
        cmd: ffmpeg command list to modify
        subtitle_files: List of subtitle files
        use_mp4_optimized: Whether to use MP4-optimized metadata format
    """
    for i, sub_file in enumerate(subtitle_files):
        lang = extract_language_from_filename(sub_file.name)
        if lang:
            short_name, full_name = get_language_names(lang)

            if use_mp4_optimized:
                # Use ISO 639-2 codes for MP4
                iso639_2_code = get_iso639_2_code(lang)
                cmd.extend([f"-metadata:s:s:{i}", f"language={iso639_2_code}"])
                cmd.extend([f"-metadata:s:s:{i}", f"handler_name={full_name}"])
                cmd.extend([f"-metadata:s:s:{i}", f"title={full_name}"])
                safe_push_log(
                    f"   📝 MP4 Subtitle {i+1}: {sub_file.name} → {iso639_2_code} ({full_name})"
                )
            else:
                # Use standard 2-letter codes for other formats
                cmd.extend([f"-metadata:s:s:{i}", f"language={short_name}"])
                cmd.extend([f"-metadata:s:s:{i}", f"title={full_name}"])
                safe_push_log(
                    f"   📝 Subtitle {i+1}: {sub_file.name} → {short_name} ({full_name})"
                )
        else:
            # Fallback for unknown languages
            cmd.extend([f"-metadata:s:s:{i}", "language=und"])
            if use_mp4_optimized:
                cmd.extend([f"-metadata:s:s:{i}", "handler_name=Subtitle"])
            cmd.extend([f"-metadata:s:s:{i}", "title=Subtitle"])
            safe_push_log(f"   📝 Subtitle {i+1}: {sub_file.name} → Unknown")


def extract_language_from_filename(filename: str) -> Optional[str]:
    """
    Extract language code from subtitle filename using various patterns.

    Args:
        filename: Subtitle filename

    Returns:
        Optional[str]: Language code if found, None otherwise
    """
    # Common patterns: file.en.srt, file.eng.srt, file_en.srt, file-en.srt
    patterns = [
        r"\.([a-z]{2,3})\.(?:srt|vtt|ass|ssa)$",  # file.en.srt
        r"[_-]([a-z]{2,3})\.(?:srt|vtt|ass|ssa)$",  # file_en.srt, file-en.srt
        r"\.([a-z]{2,3})_(?:srt|vtt|ass|ssa)$",  # file.en_srt
    ]

    import re

    filename_lower = filename.lower()

    for pattern in patterns:
        match = re.search(pattern, filename_lower)
        if match:
            lang = match.group(1)
            # Convert common 3-letter codes to 2-letter
            lang_map = {
                "eng": "en",
                "fre": "fr",
                "ger": "de",
                "spa": "es",
                "ita": "it",
                "por": "pt",
                "rus": "ru",
                "jpn": "ja",
                "chi": "zh",
                "kor": "ko",
                "ara": "ar",
                "heb": "he",
            }
            return lang_map.get(lang, lang)

    return None


def validate_subtitle_file(subtitle_path: Path) -> bool:
    """
    Validate that a subtitle file is readable and has content.

    Args:
        subtitle_path: Path to subtitle file

    Returns:
        bool: True if file is valid, False otherwise
    """
    try:
        if not subtitle_path.exists():
            return False

        # Check file size (should be > 0)
        if subtitle_path.stat().st_size == 0:
            safe_push_log(f"⚠️ Empty subtitle file: {subtitle_path.name}")
            return False

        # Try to read first few lines to check format
        content = subtitle_path.read_text(encoding="utf-8", errors="ignore")[:1000]

        # Basic format validation
        if subtitle_path.suffix.lower() == ".srt":
            # SRT should have timestamps like 00:00:01,000 --> 00:00:05,000
            import re

            if not re.search(
                r"\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}",
                content,
            ):
                safe_push_log(f"⚠️ Invalid SRT format: {subtitle_path.name}")
                return False
        elif subtitle_path.suffix.lower() == ".vtt":
            # VTT should start with WEBVTT
            if not content.strip().startswith("WEBVTT"):
                safe_push_log(f"⚠️ Invalid VTT format: {subtitle_path.name}")
                return False

        return True

    except Exception as e:
        safe_push_log(f"⚠️ Error validating subtitle file {subtitle_path.name}: {e}")
        return False


def embed_subtitles_manually_mp4_optimized(
    video_path: Path, subtitle_files: List[Path]
) -> bool:
    """
    MP4-optimized subtitle embedding with enhanced metadata support.

    Args:
        video_path: Path to the MP4 video file
        subtitle_files: List of subtitle file paths to embed

    Returns:
        bool: True if embedding was successful, False otherwise
    """
    # Validate subtitle files
    valid_subtitle_files = validate_subtitle_files(subtitle_files)
    if not valid_subtitle_files:
        return False

    # Setup paths
    backup_path, temp_output = create_backup_and_temp_paths(video_path)

    try:
        # Create backup
        create_backup(video_path, backup_path)
        safe_push_log("🎯 Using enhanced MP4 subtitle embedding with proper metadata")

        # Build MP4-optimized ffmpeg command
        cmd = ["ffmpeg", "-y", "-i", str(video_path)]

        # Add subtitle inputs
        for sub_file in valid_subtitle_files:
            cmd.extend(["-i", str(sub_file)])

        # Map video and audio streams only (skip existing subtitles)
        cmd.extend(["-map", "0:v", "-map", "0:a"])

        # MP4-specific codec and options
        cmd.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text"])

        # Map new subtitle streams
        for i, sub_file in enumerate(valid_subtitle_files):
            cmd.extend(["-map", f"{i+1}:s"])

        # Add MP4-optimized metadata
        add_subtitle_metadata(cmd, valid_subtitle_files, use_mp4_optimized=True)

        # Final MP4 options
        cmd.extend(["-movflags", "+faststart", str(temp_output)])

        safe_push_log("🔧 Running MP4-optimized subtitle embedding...")
        safe_push_log("   Command: ffmpeg -i video.mp4 -i sub1.srt ... -c:s mov_text")

        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            finalize_video_processing(video_path, backup_path, temp_output)
            safe_push_log(
                "✅ Successfully embedded subtitles with enhanced MP4 metadata"
            )
            return True
        else:
            restore_backup_on_error(video_path, backup_path, temp_output)
            safe_push_log(f"❌ Failed to embed subtitles: {result.stderr}")
            return False

    except Exception as e:
        restore_backup_on_error(video_path, backup_path, temp_output)
        safe_push_log(f"❌ Error during MP4 subtitle embedding: {str(e)}")
        return False


def embed_subtitles_manually(video_path: Path, subtitle_files: List[Path]) -> bool:
    """
    Manually embed subtitle files into video using ffmpeg with format-optimized settings.

    Args:
        video_path: Path to the video file
        subtitle_files: List of subtitle file paths to embed

    Returns:
        bool: True if embedding was successful, False otherwise
    """
    # Use specialized MP4 embedding for MP4 files
    if video_path.suffix.lower() in [".mp4", ".m4v", ".mov"]:
        return embed_subtitles_manually_mp4_optimized(video_path, subtitle_files)

    # For non-MP4 files, continue with general embedding
    # Validate subtitle files
    valid_subtitle_files = validate_subtitle_files(subtitle_files)
    if not valid_subtitle_files:
        return False

    # Setup paths
    backup_path, temp_output = create_backup_and_temp_paths(video_path)

    try:
        # Create backup
        create_backup(video_path, backup_path)

        # Get optimal codec for container format
        ext = video_path.suffix.lower()
        codec, supports_multiple, preferred_format = get_optimal_subtitle_codec(ext)

        safe_push_log(f"🎯 Using subtitle codec '{codec}' for {ext} container")

        # Create temporary output with proper extension
        temp_output = video_path.parent / (video_path.stem + "_tmp" + video_path.suffix)

        # Build optimized ffmpeg command
        cmd = ["ffmpeg", "-y", "-i", str(video_path)]

        # Add subtitle inputs with validation
        valid_inputs = []
        for sub_file in valid_subtitle_files:
            cmd.extend(["-i", str(sub_file)])
            valid_inputs.append(sub_file)

        # Map video and audio streams (copy existing)
        cmd.extend(["-map", "0:v", "-map", "0:a"])

        # Map subtitle streams with enhanced metadata
        for i, sub_file in enumerate(valid_inputs):
            cmd.extend(["-map", f"{i+1}:s"])

            # Extract language using enhanced detection
            lang = extract_language_from_filename(sub_file.name)
            if lang:
                # Get clean language names
                short_name, full_name = get_language_names(lang)

                # Add enhanced metadata with clean names
                cmd.extend([f"-metadata:s:s:{i}", f"language={short_name}"])
                cmd.extend([f"-metadata:s:s:{i}", f"title={full_name}"])

                # For MP4/MOV containers, use multiple metadata approaches
                if ext in [".mp4", ".mov", ".m4v"]:
                    # Try multiple metadata keys for maximum compatibility
                    cmd.extend([f"-metadata:s:s:{i}", f"handler_name={full_name}"])
                    cmd.extend([f"-metadata:s:s:{i}", f"handler={full_name}"])
                    cmd.extend([f"-metadata:s:s:{i}", f"name={full_name}"])
                    # Set as default if it's the first subtitle
                    if i == 0:
                        cmd.extend([f"-disposition:s:s:{i}", "default"])

                safe_push_log(
                    f"   📝 Subtitle {i+1}: {sub_file.name} → {short_name} ({full_name})"
                )
            else:
                # Fallback for unknown languages
                cmd.extend([f"-metadata:s:s:{i}", "language=und"])
                cmd.extend([f"-metadata:s:s:{i}", "title=Unknown"])
                if ext in [".mp4", ".mov", ".m4v"]:
                    cmd.extend([f"-metadata:s:s:{i}", "handler_name=Unknown"])
                    cmd.extend([f"-metadata:s:s:{i}", "handler=Unknown"])
                    cmd.extend([f"-metadata:s:s:{i}", "name=Unknown"])
                safe_push_log(
                    f"   📝 Subtitle {i+1}: {sub_file.name} → language=unknown"
                )

        # Container-specific optimizations
        if ext == ".mp4":
            # MP4-specific optimizations
            cmd.extend(
                [
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-c:s",
                    codec,
                    "-movflags",
                    "+faststart",  # Optimize for streaming
                ]
            )
        elif ext == ".mkv":
            # MKV-specific optimizations
            cmd.extend(
                [
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-c:s",
                    codec,
                    "-disposition:s",
                    "default",  # Mark first subtitle as default
                ]
            )
        elif ext == ".webm":
            # WebM-specific optimizations
            cmd.extend(
                [
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-c:s",
                    codec,
                ]
            )
        else:
            # Generic container
            cmd.extend(
                [
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-c:s",
                    codec,
                ]
            )

        cmd.append(str(temp_output))

        safe_push_log("🔧 Manually embedding subtitles using ffmpeg...")
        safe_push_log(f"   Command: {' '.join(cmd[:10])}...")

        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            # Replace original with new file
            video_path.unlink()
            temp_output.rename(video_path)
            backup_path.unlink()
            safe_push_log("✅ Successfully embedded subtitles manually")
            return True
        else:
            # Restore backup on failure
            if temp_output and temp_output.exists():
                temp_output.unlink()
            if backup_path and backup_path.exists():
                backup_path.rename(video_path)
            safe_push_log(f"❌ Failed to embed subtitles manually: {result.stderr}")
            return False

    except Exception as e:
        # Restore backup on any error
        if backup_path and backup_path.exists():
            backup_path.rename(video_path)
        if temp_output and temp_output.exists():
            temp_output.unlink()
        safe_push_log(f"❌ Error during manual subtitle embedding: {str(e)}")
        return False


def find_subtitle_files(
    video_path: Path, search_patterns: Optional[List[str]] = None
) -> List[Path]:
    """
    Find subtitle files matching the video file.

    Args:
        video_path: Path to the video file
        search_patterns: Optional list of subtitle filename patterns to search for.
                        If None, will search for common patterns based on video filename.

    Returns:
        List[Path]: List of found subtitle files, sorted by name
    """
    video_dir = video_path.parent
    video_stem = video_path.stem

    # Default search patterns if none provided
    if search_patterns is None:
        search_patterns = [
            f"{video_stem}.*.srt",  # e.g., video.en.srt, video.fr.srt
            f"{video_stem}.srt",  # e.g., video.srt
        ]

    # Search for subtitle files
    subtitle_files = []
    for pattern in search_patterns:
        for sub_file in video_dir.glob(pattern):
            if sub_file.is_file() and sub_file not in subtitle_files:
                subtitle_files.append(sub_file)
                safe_push_log(f"📝 Found subtitle file: {sub_file.name}")

    # Sort subtitle files by name for consistent order
    subtitle_files.sort(key=lambda x: x.name)
    return subtitle_files


def cut_subtitle_file(
    subtitle_path: Path,
    start_time: float,
    duration: float,
    output_path: Path,
    rebase_timestamps: bool = True,
) -> bool:
    """
    Cut a subtitle file to a specific time range.

    Args:
        subtitle_path: Path to the input subtitle file
        start_time: Start time in seconds
        duration: Duration in seconds
        output_path: Path for the output subtitle file
        rebase_timestamps: If True, shift timestamps to start at 00:00

    Returns:
        bool: True if cutting was successful, False otherwise
    """
    if not subtitle_path.exists():
        safe_push_log(f"❌ Subtitle file not found: {subtitle_path}")
        return False

    try:
        # Step 1: Cut subtitle with original timestamps
        temp_cut_path = output_path.with_suffix(".tmp.srt")

        cmd_trim = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "warning",
            "-i",
            str(subtitle_path),
            "-ss",
            str(start_time),
            "-t",
            str(duration),
            "-c:s",
            "srt",
            str(temp_cut_path),
        ]

        safe_push_log(
            f"📝 Cutting subtitle file: {subtitle_path.name} ({start_time:.3f}s + {duration:.3f}s)"
        )
        result = subprocess.run(cmd_trim, capture_output=True, text=True)

        if result.returncode != 0 or not temp_cut_path.exists():
            safe_push_log(f"❌ Failed to cut subtitle file: {result.stderr}")
            return False

        # Step 2: Rebase timestamps if requested
        if rebase_timestamps:
            cmd_rebase = [
                "ffmpeg",
                "-y",
                "-loglevel",
                "warning",
                "-itsoffset",
                f"-{start_time}",
                "-i",
                str(temp_cut_path),
                "-c:s",
                "srt",
                str(output_path),
            ]

            safe_push_log(f"🔄 Rebasing timestamps by -{start_time:.3f}s")
            result = subprocess.run(cmd_rebase, capture_output=True, text=True)

            # Clean up temp file
            try:
                temp_cut_path.unlink()
            except Exception:
                pass

            if result.returncode != 0 or not output_path.exists():
                safe_push_log(
                    f"❌ Failed to rebase subtitle timestamps: {result.stderr}"
                )
                return False
        else:
            # Just move the temp file to final location
            temp_cut_path.rename(output_path)

        safe_push_log(f"✅ Successfully cut subtitle file: {output_path.name}")
        return True

    except Exception as e:
        safe_push_log(f"❌ Error cutting subtitle file: {e}")
        return False


def ensure_subtitles_embedded(
    video_path: Path, search_patterns: Optional[List[str]] = None
) -> bool:
    """
    Ensure subtitles are embedded in video file. If not, find and embed available subtitle files.

    Args:
        video_path: Path to the video file
        search_patterns: Optional list of subtitle filename patterns to search for.
                        If None, will search for common patterns based on video filename.

    Returns:
        bool: True if subtitles are already embedded or successfully embedded, False otherwise
    """
    if not video_path.exists():
        safe_push_log(f"❌ Video file not found: {video_path}")
        return False

    # Check if subtitles are already embedded
    if has_embedded_subtitles(video_path):
        safe_push_log("✅ Subtitles already embedded")
        return True

    # Find available subtitle files
    subtitle_files = find_subtitle_files(video_path, search_patterns)

    if not subtitle_files:
        safe_push_log("⚠️ No subtitle files found for embedding")
        return False

    # Attempt manual embedding
    safe_push_log(f"🔧 Attempting to embed {len(subtitle_files)} subtitle file(s)...")
    success = embed_subtitles_manually(video_path, subtitle_files)

    if success:
        safe_push_log("✅ Subtitles successfully embedded")
        return True
    else:
        safe_push_log("❌ Failed to embed subtitles")
        return False

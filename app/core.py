"""
Core HomeTube functions without Streamlit dependencies.
This module contains the essential business logic for testing.
"""

import shlex
from pathlib import Path
from typing import Optional, Dict, List, Tuple

try:
    from .utils import is_valid_cookie_file
except ImportError:
    from utils import is_valid_cookie_file


def build_base_ytdlp_command(
    base_filename: str,
    temp_dir: Path,
    format_spec: str,
    embed_chapters: bool,
    embed_subs: bool,
    force_mp4: bool = False,
    custom_args: str = "",
    quality_strategy: Optional[Dict] = None,
) -> List[str]:
    """Build base yt-dlp command with common options and premium quality strategies"""

    # Use premium strategy if provided
    if quality_strategy:
        output_format = "mkv"  # Premium strategies always use MKV unless forced
        if force_mp4:
            output_format = "mp4"
        format_spec = quality_strategy["format"]
        format_sort = quality_strategy["format_sort"]
    else:
        output_format = "mp4" if force_mp4 else "mkv"
        format_sort = "res:4320,fps,codec:av01,codec:vp9.2,codec:vp9,codec:h264"

    base_cmd = [
        "yt-dlp",
        "--newline",
        "-o",
        f"{base_filename}.%(ext)s",
        "--paths",
        f"home:{temp_dir}",
        "--merge-output-format",
        output_format,
        "-f",
        format_spec,
        "--format-sort",
        format_sort,
        "--embed-metadata",
        "--embed-thumbnail",
        "--no-write-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--ignore-errors",
        "--force-overwrites",
        "--concurrent-fragments",
        "1",
        "--sleep-requests",
        "1",
        "--retries",
        "15" if quality_strategy else "10",  # More retries for premium
        "--retry-sleep",
        "3" if quality_strategy else "2",  # Longer retry sleep for premium
    ]

    # Add premium strategy extra arguments
    if quality_strategy and quality_strategy.get("extra_args"):
        base_cmd.extend(quality_strategy["extra_args"])

    # Add chapters option
    if embed_chapters:
        base_cmd.append("--embed-chapters")
    else:
        base_cmd.append("--no-embed-chapters")

    # Parse and resolve custom arguments if provided
    if custom_args and custom_args.strip():
        try:
            # Parse custom arguments safely using shlex
            parsed_custom_args = shlex.split(custom_args.strip())

            # Resolve conflicts between base and custom arguments
            final_cmd = resolve_ytdlp_argument_conflicts(base_cmd, parsed_custom_args)

            return final_cmd

        except ValueError:
            # Invalid custom arguments format, return base command
            return base_cmd

    return base_cmd


def resolve_ytdlp_argument_conflicts(
    base_args: List[str], custom_args: List[str]
) -> List[str]:
    """
    Resolve conflicts between base yt-dlp arguments and custom arguments.
    Custom arguments take precedence over base arguments.

    Args:
        base_args: Base yt-dlp command arguments
        custom_args: Custom arguments from user input

    Returns:
        List of resolved arguments with conflicts removed
    """
    if not custom_args:
        return base_args

    # Arguments that can have values
    ARGS_WITH_VALUES = {
        "--format",
        "-f",
        "--output",
        "-o",
        "--paths",
        "--merge-output-format",
        "--format-sort",
        "--convert-thumbnails",
        "--concurrent-fragments",
        "--sleep-requests",
        "--retries",
        "--retry-sleep",
        "--proxy",
        "--max-filesize",
        "--min-filesize",
        "--limit-rate",
        "--user-agent",
        "--cookies",
        "--fragment-retries",
        "--socket-timeout",
        "--geo-bypass-country",
        "--output-template",
        "--batch-file",
        "--load-info-json",
        "--write-info-json",
    }

    # Boolean/flag arguments that can conflict
    BOOLEAN_ARGS = {
        "--embed-metadata",
        "--no-embed-metadata",
        "--embed-thumbnail",
        "--no-embed-thumbnail",
        "--write-thumbnail",
        "--no-write-thumbnail",
        "--embed-chapters",
        "--no-embed-chapters",
        "--ignore-errors",
        "--no-ignore-errors",
        "--force-overwrites",
        "--no-force-overwrites",
        "--newline",
        "--no-newline",
    }

    # Extract custom argument names (with and without values)
    custom_arg_names = set()
    i = 0
    while i < len(custom_args):
        arg = custom_args[i]
        if arg.startswith("--") or arg.startswith("-"):
            custom_arg_names.add(arg)
            # If this argument typically takes a value, skip the next item
            if arg in ARGS_WITH_VALUES and i + 1 < len(custom_args):
                i += 1
        i += 1

    # Build resolved command, filtering out conflicting base arguments
    resolved_args = []
    i = 0

    while i < len(base_args):
        arg = base_args[i]

        # Check if this base argument conflicts with a custom argument
        if arg in custom_arg_names:
            # Skip this argument and its value if it has one
            if arg in ARGS_WITH_VALUES and i + 1 < len(base_args):
                i += 1  # Skip the value too
        else:
            # Check for boolean argument conflicts
            conflict_found = False
            for custom_arg in custom_arg_names:
                if arg in BOOLEAN_ARGS and custom_arg in BOOLEAN_ARGS:
                    # Check if they are opposite boolean flags
                    base_name = (
                        arg[5:] if arg.startswith("--no-") else arg[2:]
                    )  # Remove --no- or --
                    custom_name = (
                        custom_arg[5:]
                        if custom_arg.startswith("--no-")
                        else custom_arg[2:]
                    )  # Remove --no- or --

                    # If they control the same feature but with opposite values
                    if base_name == custom_name and (
                        (arg.startswith("--no-") and not custom_arg.startswith("--no-"))
                        or (
                            not arg.startswith("--no-")
                            and custom_arg.startswith("--no-")
                        )
                    ):
                        conflict_found = True
                        break

            if not conflict_found:
                resolved_args.append(arg)

        i += 1

    # Add custom arguments at the end
    resolved_args.extend(custom_args)

    return resolved_args


def build_cookies_params(
    cookies_method: str = "file",
    browser_select: str = "chrome",
    browser_profile: str = "",
    cookies_file_path: str = "cookies/youtube_cookies.txt",
) -> List[str]:
    """
    Builds cookie parameters based on configuration.
    Simplified version for testing without Streamlit dependencies.

    Args:
        cookies_method: 'file', 'browser', or 'none'
        browser_select: Browser name for browser cookies
        browser_profile: Browser profile (optional)
        cookies_file_path: Path to cookies file

    Returns:
        list: yt-dlp parameters for cookies
    """
    if cookies_method == "file":
        if is_valid_cookie_file(cookies_file_path):
            return ["--cookies", cookies_file_path]
        else:
            return ["--no-cookies"]

    elif cookies_method == "browser":
        browser_config = (
            f"{browser_select}:{browser_profile}" if browser_profile else browser_select
        )
        return ["--cookies-from-browser", browser_config]

    else:  # none
        return ["--no-cookies"]


def build_sponsorblock_params(sb_choice: str) -> List[str]:
    """
    Builds yt-dlp parameters for SponsorBlock based on user choice.
    Simplified version for testing without Streamlit dependencies.

    Args:
        sb_choice: User choice for SponsorBlock

    Returns:
        list: yt-dlp parameters for SponsorBlock
    """
    remove_cats, mark_cats = get_sponsorblock_config(sb_choice)

    # If disabled, return the deactivation
    if not remove_cats and not mark_cats:
        return ["--no-sponsorblock"]

    params = []

    # Add categories to remove
    if remove_cats:
        cats_str = ",".join(remove_cats)
        params.extend(
            [
                "--sponsorblock-remove",
                cats_str,
                "--no-force-keyframes-at-cuts",  # for smart cutting with no re-encoding
            ]
        )

    # Add categories to mark
    if mark_cats:
        cats_str = ",".join(mark_cats)
        params.extend(["--sponsorblock-mark", cats_str])

    return params


def get_sponsorblock_config(sb_choice: str) -> Tuple[List[str], List[str]]:
    """
    Returns the SponsorBlock configuration based on user choice.
    Simplified version for testing without Streamlit dependencies.

    Args:
        sb_choice: User choice for SponsorBlock

    Returns:
        tuple: (remove_categories, mark_categories) - lists of categories to remove/mark
    """
    # Option 1: Default - Remove: sponsor,interaction,selfpromo | Mark: intro,preview,outro
    if "Default" in sb_choice or "Par défaut" in sb_choice:
        return ["sponsor", "interaction", "selfpromo"], ["intro", "preview", "outro"]

    # Option 2: Moderate - Remove: sponsor,interaction,outro | Mark: selfpromo,intro,preview
    elif "Moderate" in sb_choice or "Modéré" in sb_choice:
        return ["sponsor", "interaction", "outro"], ["selfpromo", "intro", "preview"]

    # Option 3: Agressif - Retirer: TOUT
    elif "Agressif" in sb_choice or "Aggressive" in sb_choice:
        return ["sponsor", "selfpromo", "interaction", "intro", "outro", "preview"], []

    # Option 4: Conservateur - Retirer: sponsor,outro | Marquer: interaction,selfpromo,intro,preview
    elif "Conservateur" in sb_choice or "Conservative" in sb_choice:
        return ["sponsor", "outro"], ["interaction", "selfpromo", "intro", "preview"]

    # Option 5: Minimal - Retirer: sponsor seulement | Marquer: tous les autres
    elif "Minimal" in sb_choice:
        return ["sponsor"], ["selfpromo", "interaction", "intro", "outro", "preview"]

    # Option 6: Disabled - No management
    elif "Disabled" in sb_choice or "Désactivé" in sb_choice:
        return [], []

    # Fallback (should not happen)
    return ["sponsor", "interaction", "selfpromo"], ["intro", "preview", "outro"]

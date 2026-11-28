"""
Core HomeTube functions without Streamlit dependencies.
This module contains the essential business logic for testing.
"""

import shlex
from pathlib import Path

from app.file_system_utils import is_valid_cookie_file

# === CUSTOM yt-dlp ARGUMENTS: THE ALLOWLIST ===
#
# The "Custom yt-dlp arguments" field used to be a pass-through: whatever the
# user typed was shlex-split and appended to yt-dlp's argv. yt-dlp's own CLI
# contains "run this program" (--exec, --downloader), "take your options from
# this file" (--config-location, --plugin-dirs) and "write here" (-o, --paths),
# so the field handed anyone who could reach the interface the ability to run
# commands as the process owner. The app serves 8501 with no authentication of
# its own, which made it reachable pre-auth.
#
# A denylist cannot fix this. Blocking --exec leaves --downloader, and
# --config-location re-opens --exec from any file an attacker can first write;
# every yt-dlp release may add another. So the field is an allowlist: a closed
# set, and anything not in it is refused. Adding an option here is a deliberate
# act, which is the property that survives yt-dlp growing new options.
#
# What is in, and why: the two things the product already advertises as examples
# (--proxy, --max-filesize), the throttling and retry knobs, the two request
# headers, and the format selection the base command already sets — none of them
# names a program, reads a file or writes to a path. Nothing here can execute
# anything: HomeTube never invokes a shell (no shell=True anywhere), so these
# values reach yt-dlp as argv elements and go no further.
ALLOWED_ARGS_WITH_VALUES = frozenset(
    {
        # Format selection — the base command sets all of these itself
        "-f",
        "--format",
        "--format-sort",
        "--merge-output-format",
        "--convert-thumbnails",
        # Throttling, retries and timeouts
        "--concurrent-fragments",
        "--sleep-requests",
        "--retries",
        "--retry-sleep",
        "--fragment-retries",
        "--socket-timeout",
        "--limit-rate",
        "--max-filesize",
        "--min-filesize",
        # Network identity
        "--proxy",
        "--user-agent",
        "--referer",
        "--geo-bypass-country",
    }
)

# Flags taking no value. These are the ones resolve_ytdlp_argument_conflicts()
# already knew how to reconcile against the base command, plus the "write a
# sidecar file" family and --verbose.
#
# The sidecar flags are in because the documentation already promises them —
# .env.sample's own worked example of this field is
# "--max-filesize 100M --write-info-json", and docs/usage.md offers
# "--write-info-json --write-description --write-thumbnail --write-sub" as its
# archival recipe. None takes a value, and with -o and --paths refused the file
# each writes can only land in the workspace the app chose, so admitting them
# costs nothing and refusing them would have broken the project's own examples.
#
# --simulate and --print-json were in that documentation too and are *not*
# here: they are harmless but they make the download produce no file, so the
# field would appear to work while the product silently stopped doing its job.
# docs/usage.md no longer suggests them.
ALLOWED_BOOLEAN_ARGS = frozenset(
    {
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
        "--write-info-json",
        "--no-write-info-json",
        "--write-description",
        "--no-write-description",
        "--write-subs",
        "--write-sub",
        "--no-write-subs",
        "--verbose",
    }
)


def _log_custom_args(message: str) -> None:
    """Report a custom-argument decision to the user's download log.

    Deferred import: app.logs_utils pulls in Streamlit, and this module is
    imported by paths that do not need it. Same pattern as
    app/file_system_utils.py.
    """
    from app.logs_utils import safe_push_log

    safe_push_log(message)


def unsafe_custom_args_enabled() -> bool:
    """Whether the operator has turned the allowlist off.

    ``YTDLP_UNSAFE_CUSTOM_ARGS=true`` restores the old pass-through. It exists
    because people use --exec on purpose, and a fix that removes a capability
    with no path back is one that gets worked around by pinning the old image.
    It is off by default and it is not a grey area: enabling it gives anyone who
    can reach the web interface the ability to run commands in the container.
    """
    from app.config import get_settings

    return bool(get_settings().YTDLP_UNSAFE_CUSTOM_ARGS)


def filter_allowed_ytdlp_args(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Split already-shlex-split custom arguments into (accepted, refused).

    The default is refuse. A token is accepted only by being named in
    ALLOWED_BOOLEAN_ARGS, or in ALLOWED_ARGS_WITH_VALUES and followed by a
    value.

    A value must not itself begin with "-". No option on the allowlist takes
    one that does, and the rule removes a whole class of confusion: without it
    ``--proxy --exec`` would be accepted, because yt-dlp would consume --exec as
    the proxy's value. A bare token that is not consumed as a value is refused
    too — to yt-dlp that would be a positional URL.

    Args:
        tokens: the user's arguments, as produced by shlex.split

    Returns:
        (accepted, refused), each in the order the user wrote them. ``accepted``
        holds only allowlisted options and their values, by construction.
    """
    accepted: list[str] = []
    refused: list[str] = []

    index = 0
    while index < len(tokens):
        token = tokens[index]

        if token in ALLOWED_BOOLEAN_ARGS:
            accepted.append(token)
            index += 1
            continue

        if token in ALLOWED_ARGS_WITH_VALUES:
            value = tokens[index + 1] if index + 1 < len(tokens) else None
            if value is None or value.startswith("-"):
                # A dangling option, or one whose value looks like another
                # option: refuse it rather than guess what was meant.
                refused.append(token)
                index += 1
                continue
            accepted.extend([token, value])
            index += 2
            continue

        refused.append(token)
        index += 1

    return accepted, refused


def build_base_ytdlp_command(
    base_filename: str,
    temp_dir: Path,
    format_spec: str,
    embed_chapters: bool,
    embed_subs: bool,
    force_mp4: bool = False,
    custom_args: str = "",
    quality_strategy: dict | None = None,
) -> list[str]:
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

    # Detect if we have multiple audio streams (e.g., "313+251-0+251-1+251-2")
    # Count audio format IDs by looking for multiple "+" after the first video format
    # Only the first alternative counts: "/" separates yt-dlp fallbacks
    parts = format_spec.split("/")[0].split("+")
    # If we have more than 2 parts (video + first audio + additional audios), enable multi-audio
    if len(parts) > 2:
        base_cmd.append("--audio-multistreams")

    # Add premium strategy extra arguments
    if quality_strategy and quality_strategy.get("extra_args"):
        base_cmd.extend(quality_strategy["extra_args"])

    # Add chapters option
    if embed_chapters:
        base_cmd.append("--embed-chapters")
    else:
        base_cmd.append("--no-embed-chapters")

    # Parse, screen and resolve custom arguments if provided
    if custom_args and custom_args.strip():
        try:
            # Parse custom arguments safely using shlex
            parsed_custom_args = shlex.split(custom_args.strip())
        except ValueError as error:
            # An unbalanced quote used to drop the whole field in silence, which
            # reads as "my flag does nothing" rather than as a typo.
            _log_custom_args(
                f"⚠️ Custom yt-dlp arguments ignored — they could not be parsed ({error}). "
                "Check for an unbalanced quote."
            )
            return base_cmd

        if unsafe_custom_args_enabled():
            # The operator has opted out. Say so on every download: this is the
            # one state in which the field can run commands.
            _log_custom_args(
                "🚨 YTDLP_UNSAFE_CUSTOM_ARGS is enabled — custom yt-dlp arguments are "
                "passed through unchecked. Anyone who can reach this interface can run "
                "commands in the container."
            )
            return resolve_ytdlp_argument_conflicts(base_cmd, parsed_custom_args)

        accepted_custom_args, refused_custom_args = filter_allowed_ytdlp_args(
            parsed_custom_args
        )

        if refused_custom_args:
            _log_custom_args(
                "🚫 Refused custom yt-dlp arguments: "
                f"{' '.join(refused_custom_args)}. Only a reviewed allowlist is "
                "accepted, because options such as --exec, --downloader, "
                "--config-location, -o and --paths can run programs or write "
                "anywhere. Set YTDLP_UNSAFE_CUSTOM_ARGS=true to pass arguments "
                "through unchecked, which gives anyone who can reach this interface "
                "a shell in the container."
            )

        if not accepted_custom_args:
            return base_cmd

        # Resolve conflicts between base and custom arguments
        return resolve_ytdlp_argument_conflicts(base_cmd, accepted_custom_args)

    return base_cmd


def resolve_ytdlp_argument_conflicts(
    base_args: list[str], custom_args: list[str]
) -> list[str]:
    """
    Resolve conflicts between base yt-dlp arguments and custom arguments.
    Custom arguments take precedence over base arguments.

    Args:
        base_args: Base yt-dlp command arguments
        custom_args: Custom arguments from user input

    Returns:
        List of resolved arguments with conflicts removed

    Note:
        Reached only with arguments that passed filter_allowed_ytdlp_args(), or
        with the raw field when YTDLP_UNSAFE_CUSTOM_ARGS is on. The two sets
        below decide which *base* argument a custom one replaces, so they still
        name options the base command sets and the allowlist refuses (-o,
        --paths): those entries are now unreachable from the field, and harmless.
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
        "--referer",
        "--cookies",
        "--fragment-retries",
        "--socket-timeout",
        "--geo-bypass-country",
        "--output-template",
        "--batch-file",
        "--load-info-json",
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
        # --write-info-json takes no value; it sat in ARGS_WITH_VALUES above,
        # which made it swallow whichever flag the user wrote after it.
        "--write-info-json",
        "--no-write-info-json",
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
) -> list[str]:
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


def build_sponsorblock_params(sb_choice: str) -> list[str]:
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


def get_sponsorblock_config(sb_choice: str) -> tuple[list[str], list[str]]:
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

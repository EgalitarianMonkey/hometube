"""Guards on the contract between the documented environment variables and the
configuration the application actually reads.

These are not characterisation tests. They pin a defect that was public and
silent, in the same family as the Makefile's catch-all and the deployment
guide's absent files: *a setting that does nothing instead of failing.*

``get_settings()`` builds its configuration by iterating over the keys of
``_DEFAULTS`` and asking the environment for each one. A variable that is not a
key of ``_DEFAULTS`` is therefore not merely unsupported — it is unreachable.
Nothing reads it, nothing warns about it, and the application starts normally
with its default behaviour. Three documented variables were in that state:

* ``DOWNLOAD_FOLDER`` and ``HOMETUBE_LANGUAGE``, in the "Core Configuration"
  table of ``docs/usage.md``, where the real names are ``VIDEOS_FOLDER`` and
  ``UI_LANGUAGE``. A reader who set ``DOWNLOAD_FOLDER`` to their media library
  got their downloads in the default folder instead, without a message.
* ``QUALITY_PROFILE``, in ``.env.sample`` and in ``docs/docker.md``, documented
  with a default and four valid profile names, and absent from both
  ``_DEFAULTS`` and ``Settings``.

The first two tests close that loop in the direction that reaches strangers: a
variable may be documented only if the configuration reads it. The exemptions
are derived from the tree rather than listed by hand, so they cannot rot —
``PORT``, ``TZ`` and the three ``*_DOCKER_HOST`` paths are consumed by the
compose file, not by Python, and ``STREAMLIT_*`` belongs to Streamlit.

The last two tests guard the other half of the same defect. ``QUALITY_PROFILE``
survives in two functions of ``app/quality_profiles.py`` that read
``settings.QUALITY_PROFILE`` — an attribute the frozen ``Settings`` dataclass
does not have, so both raise ``AttributeError`` on their first use of it.
Neither has a caller anywhere, which is the only reason the crash has never
been seen. Removing them pulls three more functions with them, so they are left
alone deliberately; what is *not* left to chance is that they stay unreachable.
Wire either one up without adding the field first and the suite fails and says
so.
"""

import dataclasses
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.config import _DEFAULTS, _ENV_ALIASES, Settings

REPO_ROOT = Path(__file__).resolve().parent.parent

# Only the two tests that enumerate the documentation need git; the settings
# checks read the sources directly and stay useful without it.
requires_git = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not available on this machine"
)

# `#VAR=value` or `VAR=value` at the start of a line in .env.sample.
ENV_SAMPLE_VAR = re.compile(r"(?m)^\s*#?\s*([A-Z][A-Z_0-9]{2,})=")

# A documentation table row whose first cell is an upper-snake name in
# backticks: `| `VIDEOS_FOLDER` | /data/videos | ... |`. Anchoring on the row
# start and requiring the closing pipe is what keeps ordinary inline code out
# of the results — only the variable column of a real table matches.
DOC_TABLE_VAR = re.compile(r"(?m)^\|\s*`([A-Z][A-Z_0-9]{2,})`\s*\|")

# `settings.SOME_NAME` anywhere in the application sources.
SETTINGS_ACCESS = re.compile(r"\bsettings\.([A-Z][A-Z_0-9]*)\b")

# Variables that are documented for HomeTube but deliberately never reach
# app/config.py, because something other than Python consumes them. The compose
# exemption is computed below from the files themselves; this prefix covers
# Streamlit's own namespace, which the server reads directly.
EXTERNAL_PREFIXES = ("STREAMLIT_",)

# Files that consume environment variables without going through the loader.
INFRASTRUCTURE_FILES = (
    "docker-compose.yml.sample",
    "docker-compose.yml",
    "Dockerfile",
)

# Read by code that nothing calls. See the module docstring: these are allowed
# to name a missing Settings field only for as long as they remain unreachable,
# which the last test enforces.
KNOWN_UNWIRED = {"QUALITY_PROFILE"}

UNWIRED_HELPERS = ("get_default_profile_index", "resolve_download_profiles")


def tracked_files(pattern):
    """Files git actually tracks, so an untracked scratch file cannot fail the suite."""
    out = subprocess.run(
        ["git", "ls-files", pattern],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [REPO_ROOT / p for p in out]


def configured_variables():
    """Every variable name the configuration loader can actually honour."""
    return set(_DEFAULTS) | set(_ENV_ALIASES)


def infrastructure_variables():
    """Variables referenced by the compose files or the Dockerfile.

    Derived from the files rather than hard-coded: a new bind mount or published
    port documents its own variable, and this test does not have to be edited.
    """
    found = set()
    for name in INFRASTRUCTURE_FILES:
        path = REPO_ROOT / name
        if path.exists():
            found |= set(re.findall(r"\b([A-Z][A-Z_0-9]{2,})\b", path.read_text()))
    return found


def is_exempt(variable):
    return (
        variable.startswith(EXTERNAL_PREFIXES) or variable in infrastructure_variables()
    )


def documented_in_env_sample():
    return set(ENV_SAMPLE_VAR.findall((REPO_ROOT / ".env.sample").read_text()))


def documented_in_tables():
    """Every env-var table row across the tracked Markdown, with its file."""
    found = {}
    for path in tracked_files("*.md"):
        for variable in DOC_TABLE_VAR.findall(path.read_text(encoding="utf-8")):
            found.setdefault(variable, set()).add(str(path.relative_to(REPO_ROOT)))
    return found


def test_every_variable_in_env_sample_is_read_by_the_config():
    """.env.sample is the file users copy; every line in it must do something."""
    known = configured_variables()
    broken = sorted(
        v for v in documented_in_env_sample() if v not in known and not is_exempt(v)
    )
    assert not broken, (
        "These variables are offered in .env.sample but are not keys of "
        f"app/config.py's _DEFAULTS, so setting them has no effect: {broken}. "
        "Add them to _DEFAULTS and Settings, or remove them from the sample."
    )


@requires_git
def test_every_variable_in_a_documentation_table_is_read_by_the_config():
    """A documented variable that the loader cannot see is a silent no-op."""
    known = configured_variables()
    tables = documented_in_tables()
    broken = {
        variable: sorted(files)
        for variable, files in tables.items()
        if variable not in known and not is_exempt(variable)
    }
    assert not broken, (
        "These variables are documented as configuration but app/config.py "
        f"never reads them, so they do nothing: {broken}. The loader only "
        "iterates over _DEFAULTS, so a name absent from it is unreachable."
    )


@requires_git
def test_the_parsers_find_the_variables_they_are_meant_to_police():
    """Guard on the guards: neither test above may pass by matching nothing.

    VIDEOS_FOLDER is the most load-bearing setting in the project and is both
    sampled and tabulated, so its absence means a parser has stopped working
    rather than that the documentation became clean.
    """
    assert "VIDEOS_FOLDER" in documented_in_env_sample()
    tables = documented_in_tables()
    assert "VIDEOS_FOLDER" in tables
    assert len(tables) > 10, f"only {len(tables)} table variables found"


def test_every_settings_attribute_access_resolves_to_a_field():
    """`settings.X` for an X that is not a field raises AttributeError at runtime."""
    fields = {f.name for f in dataclasses.fields(Settings)}
    missing = {}
    for path in sorted((REPO_ROOT / "app").rglob("*.py")):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for name in SETTINGS_ACCESS.findall(line):
                if name not in fields and name not in KNOWN_UNWIRED:
                    missing.setdefault(name, []).append(
                        f"{path.relative_to(REPO_ROOT)}:{number}"
                    )
    assert not missing, (
        "These attributes are read off the settings object but are not fields "
        f"of the Settings dataclass, so each access raises AttributeError: {missing}."
    )


@pytest.mark.parametrize("helper", UNWIRED_HELPERS)
def test_the_unwired_quality_profile_helpers_remain_unreachable(helper):
    """They read a field that does not exist; nothing may call them until it does."""
    callers = []
    for path in sorted((REPO_ROOT / "app").rglob("*.py")):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if helper in line and not line.lstrip().startswith(("def ", "#", "*")):
                callers.append(f"{path.relative_to(REPO_ROOT)}:{number}")
    assert not callers, (
        f"{helper}() reads settings.QUALITY_PROFILE, which is not a Settings "
        f"field, so it raises AttributeError when called — found at {callers}. "
        "Add QUALITY_PROFILE to _DEFAULTS and Settings before wiring it up, "
        "and document it again in .env.sample and docs/docker.md."
    )


def test_the_unwired_helpers_still_raise_rather_than_silently_working():
    """Pins *why* the helpers above are quarantined, so the reason cannot drift."""
    from app.quality_profiles import get_default_profile_index

    with pytest.raises(AttributeError, match="QUALITY_PROFILE"):
        get_default_profile_index()

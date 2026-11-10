"""Guards on the contract between pyproject.toml and the setup a stranger is told to build.

The sibling of ``test_requirements_contract.py``, which closed this loop for the
two *generated* requirements files. Two setup surfaces were never compared with
the project's own declarations at all, and both had drifted away from them.

1. **The documented Python floor was 3.10, in eleven places, while
   ``requires-python`` has been ``>=3.11``.** Measured rather than read, on
   2026-11-10: on a real 3.10 interpreter every documented path fails. ``uv
   sync`` and ``pip install -e .`` are refused outright ("hometube==2.13.3
   depends on Python>=3.11 ... your requirements are unsatisfiable"), and
   ``pip install -r requirements/requirements-dev.txt`` dies on
   ``No matching distribution found for altair==6.3.0 ... Requires-Python
   >=3.11``. So ``README.md``'s own conda recipe — ``conda create -n hometube
   python=3.10`` followed by ``pip install ".[local]"`` — could not work, and
   the failure arrives one step after the wrong prerequisite that caused it,
   reading like a broken repository rather than a stale instruction.

2. **``environment.yml`` — Option B of docs/contributing.md, titled "Best for
   Contributors" — restated five dependency decisions and all five had
   drifted.** The sharpest is an omission: ``python-dotenv`` is a *direct* core
   dependency, not a streamlit transitive, and it was absent. ``app/config.py``
   catches the ``ImportError``, prints "python-dotenv not installed — skipping
   .env loading" and carries on, so the contributor's whole ``.env`` was
   ignored behind one warning line in Streamlit's output — measured on the real
   loader, ``VIDEOS_FOLDER`` resolved to ``./downloads`` with a ``.env`` on disk
   saying otherwise. ``requests`` was missing too; ``streamlit>=1.49.1`` dropped
   the ``<1.67`` ceiling (so this path installed streamlit 1.67.0); ``black``
   was unpinned against an exact pin CI enforces; ``ruff`` was absent while
   ``flake8`` and ``mypy``, which this project does not use, were installed.

Both are the family #150, #156, #157, #160, #161, #164, #171, #176, #182, #188,
#190 and #192 belong to — a thing that silently does the wrong thing instead of
failing — and neither was visible to CI, which installs ``-e ".[test,dev]"``
from ``pyproject.toml`` and reads neither the documents nor ``environment.yml``.

The fix to (2) is structural rather than a re-pinning: the pip section now
installs the project's own extras, so there is no second list left to drift.
Rule 3 below is what keeps it that way, and it is the reason this module creates
no friction on a dependency bump — a bump edits ``pyproject.toml`` only, and
nothing here restates a version.

The last three tests exist only to stop the others passing on nothing.
"""

import re
import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
ENVIRONMENT_YML = REPO_ROOT / "environment.yml"

# The extras a contributor environment is *not* expected to carry, with the
# reason, so that a newly added extra fails rule 2 and forces the decision
# rather than being silently excluded:
#   local  — a single entry, yt-dlp, expected as a system tool (like ffmpeg)
#   docker — the image's own copy of the core set, installed by the Dockerfile
CONTRIBUTOR_EXTRAS_EXCLUDED = {"local", "docker"}

# A Python version stated next to the word "python". The 12-character window
# absorbs the markup these statements are wrapped in — `**Python**: version
# 3.11+`, `|**Python**|3.11+|`, `Python-3.11+-blue.svg` — without reaching the
# next sentence. Group 1 is a `>=` if one is present, group 2 the version,
# group 3 a trailing `+`.
PYTHON_VERSION = re.compile(r"[Pp]ython[^\n]{0,12}?(>=)?\s*(\d+\.\d+)(\+?)")

# The `python` entry of environment.yml's conda dependencies.
CONDA_PYTHON = re.compile(r"^python\s*(>=|==|=)\s*(\d+\.\d+)")

# An editable install of this project, with or without extras: `-e .[test,dev]`.
PROJECT_INSTALL = re.compile(r"^(?:-e|--editable)\s+\.(?:\[([^\]]*)\])?$")


def pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def python_floor() -> tuple[int, int]:
    """The lower bound of requires-python as a comparable pair, e.g. (3, 11)."""
    requires = pyproject()["project"]["requires-python"]
    match = re.search(r">=\s*(\d+)\.(\d+)", requires)
    assert match, f"requires-python has no lower bound to resolve against: {requires!r}"
    return int(match.group(1)), int(match.group(2))


def tracked_markdown() -> list[Path]:
    """Every Markdown file git tracks.

    `git ls-files` rather than a glob, for the reason `test_docs_file_references`
    exists: what matters is what a stranger receives in a clone, not what sits
    in this working tree.
    """
    listing = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [REPO_ROOT / name for name in listing.stdout.split()]


def documented_python_versions() -> list[tuple[str, int, tuple[int, int], bool]]:
    """Every Python version the tracked Markdown states.

    Returns `(file, line number, (major, minor), is_a_floor_claim)`. A statement
    counts as a floor claim when it is written as one — `3.11+` or `>=3.11` —
    and those must equal `requires-python`. An exact version (`python=3.11`, or
    `Python 3.11` in a prose sentence) is a claim about what is used rather than
    about what is required, so it only has to be a version the project accepts.
    """
    found = []
    for path in tracked_markdown():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in PYTHON_VERSION.finditer(line):
                at_least, version, plus = match.groups()
                major, minor = version.split(".")
                found.append(
                    (
                        path.relative_to(REPO_ROOT).as_posix(),
                        number,
                        (int(major), int(minor)),
                        bool(at_least or plus),
                    )
                )
    return found


def conda_environment() -> tuple[list[str], list[str]]:
    """environment.yml's conda dependencies and its pip sub-list.

    Hand-parsed on purpose: PyYAML is in no dependency file of this project and
    adding one to run a test would be a worse trade than reading twenty lines of
    YAML. Comment-only lines and trailing comments are dropped first, which also
    keeps the explanatory comments in that file — they quote the old
    `python>=3.10` — from being read as entries.
    """
    conda: list[str] = []
    pip: list[str] = []
    in_dependencies = False
    in_pip = False
    for raw in ENVIRONMENT_YML.read_text(encoding="utf-8").splitlines():
        line = re.sub(r"\s+#.*$", "", raw).rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\S", line):  # a new top-level key ends the block
            in_dependencies = line.startswith("dependencies:")
            in_pip = False
            continue
        if not in_dependencies:
            continue
        indent = len(line) - len(line.lstrip())
        item = line.lstrip()
        if not item.startswith("- "):
            continue
        entry = item[2:].strip()
        if entry == "pip:":
            in_pip = True
            pip_indent = indent
            continue
        if in_pip and indent > pip_indent:
            pip.append(entry)
        else:
            in_pip = False
            conda.append(entry)
    return conda, pip


# --- The substantive rules -------------------------------------------------


def test_conda_python_floor_matches_requires_python():
    """environment.yml must not offer a Python the project refuses to install on.

    This is half of defect 1. `python>=3.10` let conda build a 3.10 environment
    in which the pip section below it is unsatisfiable, so Option B failed one
    step after the line that caused it.
    """
    conda, _ = conda_environment()
    specs = [CONDA_PYTHON.match(entry) for entry in conda]
    stated = [match for match in specs if match]
    assert stated, (
        "environment.yml's conda dependencies state no python version — "
        f"found {conda}"
    )
    floor = python_floor()
    for match in stated:
        major, minor = match.group(2).split(".")
        assert (int(major), int(minor)) == floor, (
            f"environment.yml asks for python{match.group(1)}{match.group(2)} "
            f"while requires-python is >={floor[0]}.{floor[1]}. conda will build "
            "an environment the pip section cannot install into."
        )


def test_conda_pip_section_installs_the_project_itself():
    """Option B must install what pyproject declares, not a copy of it.

    The extras are derived from pyproject rather than listed, so adding one
    fails here until somebody decides whether a contributor needs it.
    """
    _, pip = conda_environment()
    extras_available = set(pyproject()["project"]["optional-dependencies"])
    expected = extras_available - CONTRIBUTOR_EXTRAS_EXCLUDED
    installed = set()
    for entry in pip:
        match = PROJECT_INSTALL.match(entry)
        if match:
            installed |= {
                extra.strip() for extra in (match.group(1) or "").split(",") if extra
            }
            break
    else:
        raise AssertionError(
            "environment.yml's pip section does not install this project "
            f"(expected an `-e .[...]` entry, found {pip}). Without it the file "
            "is a second copy of pyproject.toml's dependencies and will drift "
            "from it again."
        )
    missing = expected - installed
    assert not missing, (
        f"environment.yml installs `-e .[{','.join(sorted(installed))}]` and so "
        f"omits the {sorted(missing)} extra(s). Either add them or record why a "
        f"contributor does not need them in CONTRIBUTOR_EXTRAS_EXCLUDED."
    )


def test_conda_pip_section_pins_nothing_of_its_own():
    """The pip section must name no distribution other than this project.

    This is the rule that makes defect 2 unrepeatable, and the one that keeps
    this module from taxing every dependency bump: a version written here is a
    second source of truth that nothing regenerates and dependabot never sees.
    All five that lived here had drifted — python-dotenv and requests missing
    altogether, streamlit without its ceiling, black unpinned against an exact
    pin, no ruff but flake8 and mypy, which this project does not use.
    """
    _, pip = conda_environment()
    strays = [entry for entry in pip if not PROJECT_INSTALL.match(entry)]
    assert not strays, (
        f"environment.yml's pip section names {strays} on its own account. "
        "Declare dependencies in pyproject.toml and let `-e .[...]` pull them "
        "in, or this file drifts from the project again."
    )


def test_documented_python_floors_match_requires_python():
    """A document that states the required Python must state the real one.

    This is the other half of defect 1, and the direction that reaches a
    stranger: `README.md`'s system-requirements table, the prerequisites of
    three guides and the badge all answer the question "can I run this on the
    Python I have".
    """
    floor = python_floor()
    wrong = [
        (where, line, version)
        for where, line, version, is_floor in documented_python_versions()
        if is_floor and version != floor
    ]
    assert not wrong, (
        f"requires-python is >={floor[0]}.{floor[1]}, but these state a "
        "different floor: "
        + ", ".join(f"{w}:{line} says {v[0]}.{v[1]}+" for w, line, v in wrong)
    )


def test_documented_python_versions_are_installable():
    """No document may name a Python the project cannot be installed on.

    Separate from the rule above because the claims are different: `conda create
    -n hometube python=3.11` and "Runs on: Ubuntu, Python 3.11" say what is
    used, not what is required, so they are free to be above the floor — but
    never below it. "Runs on: Ubuntu, Python 3.10-3.12" was below it.
    """
    floor = python_floor()
    unusable = [
        (where, line, version)
        for where, line, version, _ in documented_python_versions()
        if version < floor
    ]
    assert not unusable, (
        f"these name a Python below the >={floor[0]}.{floor[1]} floor, where "
        "installing this project is unsatisfiable: "
        + ", ".join(f"{w}:{line} says {v[0]}.{v[1]}" for w, line, v in unusable)
    )


# --- The rules that stop the ones above passing on nothing -----------------


def test_the_environment_parser_reads_both_sections():
    """A parser that silently matches nothing would satisfy every rule above."""
    conda, pip = conda_environment()
    assert conda, "the environment.yml conda parser found no dependencies"
    assert pip, "the environment.yml pip parser found no entries"
    assert any(entry.startswith("ffmpeg") for entry in conda), (
        "the conda parser no longer finds ffmpeg, which environment.yml exists "
        f"to install — found {conda}"
    )
    assert any(
        CONDA_PYTHON.match(entry) for entry in conda
    ), f"the conda parser no longer finds a python spec — found {conda}"


def test_the_markdown_scanner_still_finds_the_known_statements():
    """The floor rules are a filter over this scan; an empty scan passes both.

    Anchored on README.md's badge as well as on a count, because a regex can
    keep matching something while losing the shape that matters.
    """
    found = documented_python_versions()
    assert len(found) >= 10, (
        f"the Python-version scanner found only {len(found)} statements across "
        "the tracked Markdown; it used to find 13. It has probably stopped "
        "matching rather than the documents having stopped claiming."
    )
    assert (
        len({where for where, _, _, _ in found}) >= 4
    ), "the scanner found statements in fewer than four files"
    assert any(
        where == "README.md" and is_floor for where, _, _, is_floor in found
    ), "the scanner no longer reads README.md's Python floor"


def test_pyproject_declares_what_the_contributor_install_resolves_to():
    """Rule 2 derives its expectation from pyproject; here it must be non-empty."""
    project = pyproject()["project"]
    extras = project["optional-dependencies"]
    expected = set(extras) - CONTRIBUTOR_EXTRAS_EXCLUDED
    assert expected, (
        "every extra pyproject declares is excluded from the contributor "
        "install, so rule 2 asserts nothing"
    )
    for extra in expected:
        assert extras[extra], f"the {extra} extra is declared empty"
    assert project["dependencies"], "pyproject declares no core dependencies"
    assert python_floor() >= (3, 0), "the floor did not parse"

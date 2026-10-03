"""Guards on the Makefile's contract with the documentation.

These are not characterisation tests. They pin two things that broke silently
and stayed broken for months:

1. An unconditional catch-all rule (``%:`` with a ``@:`` body) made *every*
   target the Makefile does not define succeed and do nothing. ``make tets``
   exited 0. So did ``make test-fast``, ``make uv-test-fast`` and
   ``make type-check`` — three commands ``docs/`` told contributors to run
   before committing, which therefore ran no tests and no checks while
   reporting success. The rule exists for a real reason (``make version-update
   2.14.0`` passes the version as a bare goal), so it is kept but guarded; the
   tests below hold both halves of that: unknown targets fail, version
   arguments are still absorbed.

2. Nothing connected the commands the documentation promises to the targets
   that exist. Twelve references across three files named six commands that
   were not in the Makefile, and because of (1) each one exited 0 instead of
   complaining. The last test closes that loop: a ``make`` command may appear
   in the docs only if the Makefile defines it.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"

# A line inside a fenced code block that *starts* with `make <target>`. Anchoring
# at the start of the line is what keeps English prose out of the results:
# CONTRIBUTING.md's "make your contribution" and "make a difference" are not
# commands, and a looser pattern would collect them.
DOC_COMMAND = re.compile(r"^make\s+([a-zA-Z][a-zA-Z0-9_-]*)")

pytestmark = pytest.mark.skipif(
    shutil.which("make") is None, reason="make is not available on this machine"
)


def makefile_targets():
    """Every target the Makefile actually defines with a rule."""
    text = MAKEFILE.read_text(encoding="utf-8")
    targets = set(re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]*):", text, re.MULTILINE))
    # A .PHONY entry with no rule is not a usable target — make answers
    # "Nothing to be done" and exits 0 — so .PHONY is deliberately *not* read
    # as a source of targets here.
    return targets


def run_make(*args):
    """Run make in dry-run mode so no recipe has a side effect on the tree.

    The locale is forced to C because make translates its diagnostics: on a
    French machine the missing-target error reads "Aucune règle pour fabriquer
    la cible", so asserting on the English text would pass in CI and fail for
    any contributor whose shell is not in English.
    """
    return subprocess.run(
        ["make", "-n", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "LC_ALL": "C", "LANGUAGE": "C"},
    )


def documented_commands():
    """`make <target>` commands promised by the docs, as (file, line, target)."""
    found = []
    sources = sorted((REPO_ROOT / "docs").glob("*.md"))
    sources += [REPO_ROOT / "README.md", REPO_ROOT / "CONTRIBUTING.md"]
    for path in sources:
        if not path.exists():
            continue
        in_fence = False
        for lineno, raw in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if raw.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if not in_fence:
                continue
            match = DOC_COMMAND.match(raw.strip())
            if match:
                found.append((path.relative_to(REPO_ROOT), lineno, match.group(1)))
    return found


def test_unknown_target_fails_instead_of_succeeding_silently():
    """The defect itself: `make <typo>` must not exit 0."""
    result = run_make("definitely-not-a-target")
    assert result.returncode != 0, (
        "An undefined target succeeded. The catch-all rule is unguarded again, "
        "which makes every typo and every stale documented command a silent no-op."
    )
    assert "No rule to make target" in result.stderr


@pytest.mark.parametrize(
    "target",
    [
        "test-fast",
        "uv-test-fast",
        "type-check",
        "docs-serve",
        "docs-build",
        "docker-run",
    ],
)
def test_the_six_commands_that_used_to_lie_now_fail(target):
    """Each of these was documented, undefined, and exited 0 regardless.

    They are gone from the docs now. Should one come back as a real target this
    test is the place to delete the name from — but it must never again be a
    name that answers "success" without running anything.
    """
    assert target not in makefile_targets()
    assert run_make(target).returncode != 0


def test_phony_declares_no_target_without_a_recipe():
    """`type-check` sat in .PHONY with no body, so it exited 0 doing nothing."""
    text = MAKEFILE.read_text(encoding="utf-8")
    phony = set()
    for line in re.findall(r"^\.PHONY:(.*)$", text, re.MULTILINE):
        phony.update(line.split())
    missing = sorted(phony - makefile_targets())
    assert not missing, (
        f"declared .PHONY but defined by no rule: {missing}. "
        "make answers 'Nothing to be done' and exits 0 for these."
    )


@pytest.mark.parametrize("goal", ["version-update", "version-tag"])
def test_version_argument_is_still_absorbed(goal):
    """The reason the catch-all exists — guarding it must not break this.

    `make version-update 2.14.0` passes the version as a second goal, and make
    would otherwise try to build `2.14.0` as a target of its own.
    """
    result = run_make(goal, "2.14.0")
    assert result.returncode == 0, (
        f"`make {goal} 2.14.0` no longer works: {result.stderr}. The guard on "
        "the catch-all rule is too narrow."
    )


def test_every_documented_make_command_exists():
    """A command the docs hand to a stranger must be a target that runs.

    This is the guard that keeps the drift from coming back: six commands had
    accumulated across docs/testing.md, docs/contributing.md and
    docs/development.md that the Makefile never defined.
    """
    targets = makefile_targets()
    broken = [
        f"{path}:{lineno} → `make {name}`"
        for path, lineno, name in documented_commands()
        if name not in targets
    ]
    assert not broken, "documented commands with no Makefile target:\n" + "\n".join(
        broken
    )


def test_documented_commands_were_actually_found():
    """Guard the guard: a parser that finds nothing would pass vacuously."""
    names = {name for _, _, name in documented_commands()}
    assert len(names) > 10, f"only found {names} — the code-fence parser is broken"
    assert "test" in names and "lint" in names

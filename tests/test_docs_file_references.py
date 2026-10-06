"""Guards on what the documentation promises exists in the repository.

The sibling of ``test_makefile_contract.py``. That file closed the loop for
``make`` targets: a command the docs hand to a stranger must be a target that
runs. This one closes the same loop for *files*: a file the docs tell a reader
to execute, pass to ``docker compose -f``, copy, or download from this
repository must actually be in the repository.

What it was written for. ``docs/deployment.md`` is the production guide
``README.md`` links to twice, and eight of its commands referenced files that do
not exist on ``main``:

* ``curl -sSL .../main/deploy.sh | bash`` — ``deploy.sh`` is in ``.gitignore``
  on purpose ("Deployment scripts (may contain sensitive info)"), so the URL
  answered 404 and the pipe fed ``404: Not Found`` into ``bash``.
* ``./deploy.sh`` five more times, with flags no script in the tree parses.
* ``docker-compose -f docker-compose.prod.yml up -d`` — a name nothing creates.
* ``cp .env.example .env`` — the file shipped is ``.env.sample``.

Nothing connected the two lists, which is the same defect ``#150``, ``#156`` and
``#157`` were: a thing that silently does nothing instead of failing. The rules
below are deliberately narrow — each requires a file *extension* or a ``.sample``
counterpart — so that files the reader is told to create (``docker-compose.yml``,
``.env``, ``nginx.conf``) do not register as broken promises.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# A script the docs tell the reader to execute from the repository root. The
# extension is what keeps plain directory listings out: docs/testing.md shows
# `./tmp/tests/videos/` as a path, not as a command, and a looser pattern would
# report it.
SCRIPT_CALL = re.compile(r"\./([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:sh|py))\b")

# A compose/conda file handed to `-f`.
DASH_F_FILE = re.compile(r"-f\s+([A-Za-z0-9_][A-Za-z0-9_./-]*\.ya?ml)\b")

# A `cp <source> <dest>` whose source is a sample shipped by the repository.
SAMPLE_COPY = re.compile(
    r"\bcp\s+([A-Za-z0-9_.][A-Za-z0-9_./-]*\.(?:sample|example))\b"
)

# A raw.githubusercontent.com URL pointing into *this* repository's own tree.
# Scoped to the owner/repo so that URLs for Yann's other projects (README.md
# links one for LatentNoise/content) are not read as promises made here.
OWN_RAW_URL = re.compile(
    r"raw\.githubusercontent\.com/EgalitarianMonkey/hometube/[^/\s]+/([^\s)\"']+)"
)

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git is not available on this machine"
)


def tracked_files():
    """Every path git actually tracks.

    `Path.exists()` is the wrong question and is the trap this whole module
    exists for: `deploy.sh` sits in the working tree of anyone who wrote one,
    while being absent from every clone because `.gitignore` excludes it.
    """
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.split())


def doc_sources():
    sources = sorted((REPO_ROOT / "docs").glob("*.md"))
    sources += sorted((REPO_ROOT / "docs").glob("**/*.md"))
    sources += [REPO_ROOT / "README.md", REPO_ROOT / "CONTRIBUTING.md"]
    return [path for path in dict.fromkeys(sources) if path.exists()]


def fenced_lines():
    """Every (file, lineno, line) inside a fenced code block in the docs.

    Only fenced blocks, for the reason test_makefile_contract.py gives: prose
    mentions commands in passing, code blocks promise them.
    """
    for path in doc_sources():
        in_fence = False
        for lineno, raw in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if raw.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                yield path.relative_to(REPO_ROOT), lineno, raw


def references(pattern):
    """(file, lineno, captured path) for every fenced line matching `pattern`."""
    found = []
    for path, lineno, line in fenced_lines():
        for match in pattern.finditer(line):
            found.append((path, lineno, match.group(1)))
    return found


def report(broken):
    return "\n".join(f"{path}:{lineno} → {target}" for path, lineno, target in broken)


def test_every_documented_script_is_in_the_repository():
    """`./deploy.sh` was documented six times and is in no clone."""
    tracked = tracked_files()
    broken = [
        (path, lineno, f"`./{target}`")
        for path, lineno, target in references(SCRIPT_CALL)
        if target not in tracked
    ]
    assert not broken, (
        "the docs tell the reader to run scripts the repository does not ship:\n"
        + report(broken)
        + "\n(a file present in your working tree but gitignored is not shipped)"
    )


def test_every_compose_file_passed_to_dash_f_exists_or_has_a_sample():
    """`-f docker-compose.prod.yml` named a file no documented step creates.

    A file the reader is told to create is legitimate — but only if the
    repository ships the sample it is created from, which is what the
    prerequisites section copies.
    """
    tracked = tracked_files()
    broken = [
        (path, lineno, f"`-f {target}`")
        for path, lineno, target in references(DASH_F_FILE)
        if target not in tracked and f"{target}.sample" not in tracked
    ]
    assert not broken, (
        "the docs pass files to -f that are neither tracked nor generated from a "
        "tracked .sample:\n" + report(broken)
    )


def test_every_copied_sample_is_in_the_repository():
    """`cp .env.example .env` — the shipped file is `.env.sample`."""
    tracked = tracked_files()
    broken = [
        (path, lineno, f"`cp {target}`")
        for path, lineno, target in references(SAMPLE_COPY)
        if target not in tracked
    ]
    assert (
        not broken
    ), "the docs copy sample files the repository does not ship:\n" + report(broken)


def test_every_self_referencing_raw_url_resolves():
    """The worst of the family: `curl -sSL <404> | bash`.

    `curl -sSL` has neither `-f` nor a visible error, so a 404 exits 0 and the
    body — GitHub's `404: Not Found` — goes straight into the interpreter.
    """
    tracked = tracked_files()
    broken = [
        (path, lineno, f"raw URL → {target}")
        for path, lineno, target in references(OWN_RAW_URL)
        if target not in tracked
    ]
    assert not broken, (
        "the docs download files from this repository that are not on main:\n"
        + report(broken)
        + "\n(these URLs return 404, and a piped `curl -sSL` feeds that to a shell)"
    )


def test_the_parsers_actually_find_something():
    """Guard the guards: four rules that match nothing would all pass."""
    assert len(tracked_files()) > 50, "git ls-files returned almost nothing"
    assert any(True for _ in fenced_lines()), "the code-fence parser found no lines"

    copies = {target for _, _, target in references(SAMPLE_COPY)}
    assert (
        ".env.sample" in copies and "docker-compose.yml.sample" in copies
    ), f"the `cp <sample>` parser is broken — found {copies}"

    dash_f = {target for _, _, target in references(DASH_F_FILE)}
    assert "environment.yml" in dash_f, f"the `-f` parser is broken — found {dash_f}"


def test_a_gitignored_script_does_not_count_as_shipped():
    """Pin the distinction the whole module rests on.

    `deploy.sh` is matched by `.gitignore`, so even when it exists on a
    maintainer's disk it reaches nobody who clones. If this ever starts failing,
    `deploy.sh` became a tracked file and the docs may reference it again.
    """
    assert "deploy.sh" not in tracked_files()
    ignored = subprocess.run(
        ["git", "check-ignore", "deploy.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0, (
        "deploy.sh is no longer gitignored — if it is now shipped, this test and "
        "the deployment guide should both be revisited"
    )

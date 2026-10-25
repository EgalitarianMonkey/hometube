"""Guards on the labels the release workflows stamp into the published image.

These are not characterisation tests. They pin a defect that shipped to the
registry, in the same family as the Makefile's catch-all, the deployment guide's
absent files, the unreadable environment variables and the ``[MISSING: ...]``
status messages: *a thing that silently does nothing instead of failing.*

``build-image.yml``'s "Prepare build labels" step built its label list inside a
heredoc whose delimiter is quoted — ``<< 'EOF'`` — and put a command
substitution in it:

    org.opencontainers.image.created=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

A quoted delimiter is what stops the shell expanding anything in the body, which
is deliberate and correct: the values substituted into those lines come from
GitHub expressions and must not be interpreted. But it applies to the date too,
so the label was emitted as its own source text. Nothing failed — ``buildx``
accepts any string as a label value — so every image the refresh workflow has
ever pushed carries the literal ``"$(date -u +'%Y-%m-%dT%H:%M:%SZ')"`` as its
standard OCI ``created`` annotation. Read from GHCR, not inferred.

It survived because exactly one of the two callers masked it. ``release.yml``
builds its labels with ``docker/metadata-action``, which emits its own
``created``, and the caller's labels are appended *after* the base ones, so the
real timestamp wins on the release path. ``refresh-ytdlp.yml`` passes only a
version pair — and it is the workflow that pushes ``:latest`` whenever yt-dlp
moves.

The first rule is the general one: no quoted heredoc anywhere in the workflows
may contain shell that will not be expanded. The next four run the real step
under ``bash`` and read the labels it emits, on both callers' input, because the
text of a workflow is not the behaviour of a workflow. The last two refuse to
pass on nothing: a parser that stops matching is a guard that has stopped
guarding.
"""

import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
BUILD_IMAGE = WORKFLOWS / "build-image.yml"

requires_bash = pytest.mark.skipif(
    shutil.which("bash") is None, reason="bash is not available on this machine"
)

# A heredoc opened with a quoted delimiter: `<< 'EOF'`, `<<-"END"`. The quotes
# are the whole point — they are what tells the shell to expand nothing in the
# body.
QUOTED_HEREDOC = re.compile(r"<<-?\s*(['\"])(\w+)\1")

# A GitHub expression. These are substituted into the file before any shell sees
# it, so they are not shell and must be removed before looking for shell.
GH_EXPRESSION = re.compile(r"\$\{\{.*?\}\}")

# What would have had to expand, and will not: a command substitution, a
# backquote, or a parameter expansion.
UNEXPANDED_SHELL = (
    (re.compile(r"\$\("), "command substitution $(...)"),
    (re.compile(r"`"), "backquoted command"),
    (re.compile(r"\$\{?[A-Za-z_]"), "parameter expansion $VAR"),
)

# The tracked workflow files. Read from disk rather than from git: a workflow is
# not useful to anyone until GitHub runs it from the repository, and these all
# live there.
WORKFLOW_FILES = sorted(WORKFLOWS.glob("*.yml"))


def quoted_heredoc_bodies(text):
    """Yield ``(line_number, line)`` for every line inside a quoted heredoc.

    Deliberately textual. The repository has no YAML parser among its
    dependencies, and a heredoc inside a ``run: |`` block is shell nested in a
    YAML scalar — reading it as lines is what the shell itself will do.
    """
    delimiter = None
    for number, line in enumerate(text.splitlines(), start=1):
        if delimiter is None:
            match = QUOTED_HEREDOC.search(line)
            if match:
                delimiter = match.group(2)
            continue
        if line.strip() == delimiter:
            delimiter = None
            continue
        yield number, line


def step_script(workflow_text, step_name):
    """Return the shell of the ``run:`` block of a named step, dedented."""
    lines = workflow_text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == f"- name: {step_name}":
            break
    else:
        raise AssertionError(f"no step named {step_name!r} in the workflow")

    # Find the `run: |` that belongs to this step, i.e. before the next step.
    for run_index in range(index + 1, len(lines)):
        stripped = lines[run_index].strip()
        if stripped.startswith("- name:"):
            raise AssertionError(f"step {step_name!r} has no run: block")
        if stripped in ("run: |", "run: |-"):
            break
    else:
        raise AssertionError(f"step {step_name!r} has no run: block")

    indent = len(lines[run_index]) - len(lines[run_index].lstrip())
    body = []
    for line in lines[run_index + 1 :]:
        if line.strip() and (len(line) - len(line.lstrip())) <= indent:
            break
        body.append(line[indent + 2 :] if line.strip() else "")
    return "\n".join(body)


def run_label_step(additional_labels):
    """Run the real "Prepare build labels" step and return the labels it emits.

    ``additional_labels`` is what a caller passes as the ``labels`` input:
    ``refresh-ytdlp.yml`` passes a version pair, ``release.yml`` passes the
    output of ``docker/metadata-action``.
    """
    script = step_script(BUILD_IMAGE.read_text(), "Prepare build labels")

    substitutions = {
        "github.sha": "c5e440f776a7c6c9a536208a96faa71f382b3ca0",
        "steps.ytdlp-version.outputs.version": "2026.08.19",
        "github.event_name": "schedule",
        "github.run_id": "32339525476",
        "inputs.labels": additional_labels,
    }

    def substitute(match):
        expression = match.group(0)[3:-2].strip()
        assert expression in substitutions, f"unknown expression {expression!r}"
        return substitutions[expression]

    script = GH_EXPRESSION.sub(substitute, script)

    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "github_output"
        output.touch()
        completed = subprocess.run(
            ["bash", "-e", "-c", script],
            capture_output=True,
            text=True,
            env={"GITHUB_OUTPUT": str(output), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        )
        assert completed.returncode == 0, completed.stderr
        emitted = output.read_text()

    # The step writes a multi-line GITHUB_OUTPUT value delimited by LABELS_EOF.
    body = re.search(r"^all-labels<<LABELS_EOF$(.*?)^LABELS_EOF$", emitted, re.S | re.M)
    assert body, f"the step emitted no all-labels block:\n{emitted}"

    labels = {}
    for line in body.group(1).strip().splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition("=")
        # A later line wins, which is how buildx resolves a repeated label.
        labels[key.strip()] = value
    return labels


# The two callers of build-image.yml, as they pass their labels today.
REFRESH_LABELS = (
    "org.opencontainers.image.version=v2.13.0\nio.hometube.app.version=2.13.0"
)
RELEASE_LABELS = (
    "org.opencontainers.image.title=HomeTube\n"
    "org.opencontainers.image.description=Universal Video Downloader for HomeLab\n"
    "org.opencontainers.image.version=v2.13.0\n"
    "org.opencontainers.image.created=2026-09-22T13:11:01.765Z"
)


@pytest.mark.unit
def test_no_quoted_heredoc_contains_shell_that_will_not_expand():
    """The defect itself, as a class rather than as one line.

    A quoted heredoc expands nothing. Shell written inside one is emitted as
    text, and nothing complains — which is exactly how a command substitution
    became the value of an OCI annotation on every published image.
    """
    offenders = []
    for path in WORKFLOW_FILES:
        for number, line in quoted_heredoc_bodies(path.read_text()):
            shell = GH_EXPRESSION.sub("", line)
            for pattern, description in UNEXPANDED_SHELL:
                if pattern.search(shell):
                    offenders.append(
                        f"{path.relative_to(REPO_ROOT)}:{number} has a "
                        f"{description} inside a quoted heredoc, which the "
                        f"shell will emit as text: {line.strip()}"
                    )
                    break

    assert not offenders, "\n".join(offenders)


@requires_bash
@pytest.mark.unit
def test_the_created_label_is_a_timestamp_on_the_refresh_path():
    """The path that actually shipped the defect.

    ``refresh-ytdlp.yml`` passes only a version pair, so whatever
    ``build-image.yml`` puts in ``created`` is what reaches the registry — and
    that workflow is the one that pushes ``:latest`` when yt-dlp moves.
    """
    labels = run_label_step(REFRESH_LABELS)
    created = labels.get("org.opencontainers.image.created")

    assert created, f"no created label was emitted at all: {sorted(labels)}"
    assert "$" not in created and "`" not in created, (
        "the created label carries unexpanded shell rather than a date: " f"{created!r}"
    )
    datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")


@requires_bash
@pytest.mark.unit
def test_the_caller_still_wins_on_a_label_it_sets_itself():
    """The mechanism that hid the defect for a year, now pinned.

    ``release.yml`` passes ``docker/metadata-action``'s labels, ``created``
    among them, and the caller's list is appended after the base one — so the
    caller's value is the one buildx keeps. That is why the release images are
    correct and the refresh images are not, and it is worth a test: reverse the
    order and the release path starts reporting the wrong provenance instead.
    """
    labels = run_label_step(RELEASE_LABELS)

    assert labels["org.opencontainers.image.created"] == "2026-09-22T13:11:01.765Z"
    assert labels["org.opencontainers.image.version"] == "v2.13.0"
    assert labels["org.opencontainers.image.title"] == "HomeTube"


@requires_bash
@pytest.mark.unit
def test_a_caller_that_passes_no_labels_still_gets_a_full_set():
    """``labels`` is an optional input with an empty default.

    So the branch that takes no caller labels has to stand on its own: a future
    caller added without a ``labels:`` block must still produce an image whose
    provenance can be read.
    """
    labels = run_label_step("")

    for key in (
        "org.opencontainers.image.created",
        "org.opencontainers.image.revision",
        "io.hometube.ytdlp.version",
        "io.hometube.build.trigger",
        "io.hometube.build.run",
    ):
        assert key in labels, f"{key} is missing: {sorted(labels)}"
        assert labels[key].strip(), f"{key} was emitted with an empty value"

    datetime.strptime(labels["org.opencontainers.image.created"], "%Y-%m-%dT%H:%M:%SZ")


@requires_bash
@pytest.mark.unit
def test_every_emitted_label_is_a_key_value_pair():
    """A label line the build step cannot parse is a label buildx drops.

    This catches the shape of the defect from the other side: a line that lost
    its ``=``, or a key with a space in it, reaches ``docker/build-push-action``
    and is silently ignored there too.
    """
    labels = run_label_step(REFRESH_LABELS)

    assert labels, "the step emitted no labels"
    for key, value in labels.items():
        assert key, f"a label was emitted with an empty key: {value!r}"
        assert " " not in key, f"label key {key!r} contains a space"
        assert re.fullmatch(r"[a-z0-9._-]+", key), f"label key {key!r} is not a key"
        assert value.strip(), f"label {key} was emitted with an empty value"


@pytest.mark.unit
def test_the_heredoc_scanner_actually_finds_heredocs():
    """Refuse to pass vacuously.

    If a change to the workflows' shape stops ``QUOTED_HEREDOC`` matching, the
    first test above finds no offenders for the wrong reason. These workflows do
    contain quoted heredocs — the label list and the job summary among them —
    and the scanner must see their bodies.
    """
    assert WORKFLOW_FILES, "no workflow files were found at all"

    found = {
        path.relative_to(REPO_ROOT).name: len(
            list(quoted_heredoc_bodies(path.read_text()))
        )
        for path in WORKFLOW_FILES
    }
    assert found.get("build-image.yml"), (
        "the label heredoc of build-image.yml is no longer seen by the scanner: "
        f"{found}"
    )
    assert sum(found.values()) >= 5, f"the scanner is barely matching anything: {found}"


@pytest.mark.unit
def test_the_scanner_catches_the_defect_it_was_written_for():
    """The rule, run against the line that shipped.

    Without this, a regex that stopped recognising ``$(`` would leave the first
    test green on a tree carrying the original defect.
    """
    original = (
        "          org.opencontainers.image.created=" "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    )
    text = "run: |\n  base_labels=$(cat << 'EOF'\n" + original + "\n  EOF\n  )\n"

    bodies = list(quoted_heredoc_bodies(text))
    assert bodies, "the scanner found no heredoc body in the reconstructed defect"

    shell = GH_EXPRESSION.sub("", bodies[0][1])
    assert any(pattern.search(shell) for pattern, _ in UNEXPANDED_SHELL), (
        "the rule no longer recognises the command substitution it was written " "for"
    )

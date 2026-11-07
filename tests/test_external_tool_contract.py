"""The suite must not fail for a tool the project never asked you to install.

`external` marks a test that drives a real external binary -- pyproject declares
it as "Tests requiring external tools (yt-dlp, ffmpeg, etc.)". Those binaries are
not part of a dev install: yt-dlp sits in the `local` extra, so `uv sync`,
requirements.txt and requirements-dev.txt all omit it, and none of the three
setup paths in docs/contributing.md installs it.

A marker only deselects, it does not skip. CI and `make test-ci` deselect
`external`; `make test` does not, and `make test` is what docs/contributing.md
names for "Verify setup" and again in the PR checklist. Before the skip hook in
conftest, a contributor on a clean checkout got 4 failures for a missing binary,
and they read as a code regression rather than as a missing tool.

These rules are behavioural: they run the real suite in a subprocess with the
tools hidden from PATH, because the text of a marker is not the behaviour of a
marker.
"""

import os
import shutil
import subprocess
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from conftest import EXTERNAL_TOOLS  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent


def _path_without_external_tools() -> str:
    """PATH with every directory that provides an external tool removed."""
    keep = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        if any((Path(entry) / tool).exists() for tool in EXTERNAL_TOOLS):
            continue
        keep.append(entry)
    return os.pathsep.join(keep)


def _run_external_suite(tmp_path, path_value):
    """Run only the `external` tests with the given PATH; return junit counts."""
    report = tmp_path / "report.xml"
    env = dict(os.environ, PATH=path_value)
    # The suite imports `app` from the project root, as pytest itself does.
    env.pop("PYTHONPATH", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-m",
            "external",
            "-p",
            "no:cacheprovider",
            "-q",
            "--tb=no",
            f"--junitxml={report}",
        ],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert report.exists(), f"pytest wrote no report:\n{proc.stdout}\n{proc.stderr}"
    suite = ET.parse(report).getroot().find("testsuite")
    # Count <testcase> elements, not the <testsuite> attributes, and keep only
    # real tests. A module skipped at collection time is recorded as a testcase
    # with an empty `classname` (its `name` holds the module path), and
    # tests/test_subtitles_utils.py is one whenever its media fixtures are
    # absent -- that happens before `-m` deselection, so it is reported even
    # when nothing is selected. Counting it would leave the "some test is
    # actually marked external" rule below unfalsifiable.
    cases = [case for case in suite.findall("testcase") if case.get("classname")]
    return {
        "tests": len(cases),
        "failures": sum(1 for case in cases if case.find("failure") is not None),
        "errors": sum(1 for case in cases if case.find("error") is not None),
        "skipped": sum(1 for case in cases if case.find("skipped") is not None),
    }


@pytest.fixture(scope="module")
def without_tools(tmp_path_factory):
    return _run_external_suite(
        tmp_path_factory.mktemp("without"), _path_without_external_tools()
    )


# === THE RULES ===


def test_external_tests_skip_when_their_tool_is_absent(without_tools):
    """The defect this file exists for: a missing binary must skip, not fail."""
    assert without_tools["failures"] == 0 and without_tools["errors"] == 0, (
        "with the external tools hidden from PATH the suite must not fail: "
        f"{without_tools['failures']} failure(s), {without_tools['errors']} error(s). "
        "A tool no documented setup path installs is not a regression."
    )
    assert without_tools["skipped"] == without_tools["tests"], (
        "every external test must skip when its tool is absent; "
        f"{without_tools['tests'] - without_tools['skipped']} of "
        f"{without_tools['tests']} did not"
    )


def test_external_tests_run_when_their_tool_is_present(tmp_path):
    """The other direction: the skip must be conditional, not unconditional.

    Without this, making `pytest_runtest_setup` skip every external test
    unconditionally would satisfy the rule above and quietly delete coverage.
    """
    missing = [tool for tool in EXTERNAL_TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.skip(f"needs the real tool(s) to check this direction: {missing}")

    result = _run_external_suite(tmp_path, os.environ.get("PATH", ""))
    assert result["failures"] == 0 and result["errors"] == 0, (
        "the external tests must pass where the tool exists: "
        f"{result['failures']} failure(s), {result['errors']} error(s)"
    )
    assert result["skipped"] < result["tests"], (
        "the external tests were all skipped on a machine that has "
        f"{EXTERNAL_TOOLS}: the skip is unconditional, so it is hiding them "
        "from CI and from anyone running `make test-all`"
    )


# === THE RULES THAT STOP THE OTHERS PASSING ON NOTHING ===


def test_the_suite_actually_marks_some_tests_external(without_tools):
    """Both rules above are satisfied by an empty selection."""
    assert without_tools["tests"] > 0, (
        "no test is marked `external`, so the rules above prove nothing. "
        "Either the marker was renamed or the selection stopped matching."
    )


def test_hiding_the_tools_from_path_really_hides_them():
    """If the stripped PATH still finds yt-dlp, the main rule is vacuous."""
    stripped = _path_without_external_tools()
    for tool in EXTERNAL_TOOLS:
        assert shutil.which(tool, path=stripped) is None, (
            f"{tool} is still reachable on the stripped PATH, so "
            "test_external_tests_skip_when_their_tool_is_absent never exercised "
            "the absent case"
        )


def test_the_external_marker_is_declared_and_means_external_tools():
    """`--strict-markers` is on, so the marker must stay declared and documented."""
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())
    markers = pyproject["tool"]["pytest"]["ini_options"]["markers"]
    external = [m for m in markers if m.startswith("external:")]
    assert external, "pyproject no longer declares the `external` marker"
    assert "tool" in external[0].lower(), (
        "the `external` marker must keep documenting that it is about external "
        f"tools, so its skip hook stays justified; got: {external[0]!r}"
    )
    assert EXTERNAL_TOOLS, "conftest.EXTERNAL_TOOLS is empty, so nothing is checked"

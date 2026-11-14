"""Guards on the contract between the launchers, the port the project
documents, and the files those launchers point at.

These are not characterisation tests. They pin a defect that was public and
silent, in the same family as the Makefile's catch-all, the deployment guide's
absent files and the conda environment's drifted pin list: *a thing that
silently does the wrong thing instead of failing.*

``PORT`` is the one port variable this project documents. ``.env.sample`` ships
it, ``docs/installation.md`` describes it as "Application port (default: 8501)",
and ``docker-compose.yml.sample`` publishes ``"${PORT:-8501}:8501"`` with it.
It worked for Docker and nowhere else:

* **run.py read ``STREAMLIT_PORT``**, a name that appears nowhere else in the
  repository and that Streamlit does not honour either — its own name is
  ``STREAMLIT_SERVER_PORT``. So the launch ``docs/contributing.md`` names under
  "Running the Application" never saw the user's ``PORT`` and always fell back
  to a hardcoded 8502, while printing "✅ .env file found" and "🌐 Open your
  browser at: http://localhost:8502". The guide's own next line says 8501.
* **``PORT=8502 streamlit run app/main.py``** was documented under "# Custom
  port" and cannot work: Streamlit reads ``STREAMLIT_SERVER_PORT``.
* **app/hometube.py resolved both of its paths as if it lived at the repo
  root**, which is where run.py lives. ``Path(__file__).parent / "app" /
  "main.py"`` is ``app/app/main.py``, which does not exist, and
  ``Path(__file__).parent / ".env"`` is ``app/.env``, which nothing writes.
  ``python app/hometube.py`` therefore printed Streamlit's "File does not
  exist" and **exited 0**, because ``subprocess.run()``'s return code was
  discarded — a launcher that launched nothing reported success.

Why ``test_env_var_contract.py`` could not catch it: that module closes the loop
in the direction that reaches strangers (a variable may be *documented* only if
the configuration reads it), and its exemptions are what hid this one. ``PORT``
is exempt there because the compose file consumes it, which is true and says
nothing about the local launcher; and the ``STREAMLIT_`` prefix is exempt as
"Streamlit's own namespace", on the assumption that every name in it is honoured
by Streamlit. ``STREAMLIT_PORT`` is not. This module closes the opposite
direction: a variable a *launcher reads* must be one the project ships.

The rules are behavioural wherever they can be. A launcher is run for real in a
throwaway copy of the project layout, against a stub ``streamlit`` that records
the argv it was handed and a stub ``yt-dlp`` that satisfies run.py's
availability check — because the text of a path expression is not the path a
launcher computes, and the only way to know which port reaches Streamlit is to
look at what Streamlit was asked for. Three of the ten rules exist only to stop
the other seven passing on nothing: a harness that silently fails to reach the
stub would make every assertion below vacuously true.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="the harness installs POSIX executable stubs on PATH",
)

# A subprocess command list that launches Streamlit: `"-m", "streamlit", "run",`.
# Specific enough that the Streamlit application itself does not match, and
# whitespace-tolerant so reformatting does not drop a launcher from the set.
LAUNCH_CALL = re.compile(r'"-m"\s*,\s*"streamlit"\s*,\s*"run"\s*,')

# The default the compose sample publishes: `"${PORT:-8501}:8501"`.
COMPOSE_DEFAULT_PORT = re.compile(r"\$\{PORT:-(\d+)\}")

# Every way the launchers actually reach for an environment variable, including
# the hand-rolled `.env` scan that read STREAMLIT_PORT.
ENV_READS = re.compile(
    r"""os\.environ\.get\(\s*["']([A-Z][A-Z_0-9]*)["']"""
    r"""|os\.getenv\(\s*["']([A-Z][A-Z_0-9]*)["']"""
    r"""|os\.environ\[\s*["']([A-Z][A-Z_0-9]*)["']"""
    r"""|startswith\(\s*["']([A-Z][A-Z_0-9]*)=["']"""
)

# `#VAR=` or `VAR=` at the start of a line in .env.sample.
ENV_SAMPLE_VAR = re.compile(r"(?m)^\s*#?\s*([A-Z][A-Z_0-9]{2,})=")

# A `python foo.py` command inside a fenced block.
DOC_PYTHON_SCRIPT = re.compile(r"(?m)^(?:[A-Z_]+=\S+\s+)*python3?\s+(\S+\.py)\b")

# Recorded by the stub so a test can read what Streamlit was handed.
ARGV_FILE = "LAUNCHER_ARGV_FILE"
STUB_EXIT = "LAUNCHER_STUB_EXIT"

STREAMLIT_STUB = """\
import json
import os
import sys

with open(os.environ["LAUNCHER_ARGV_FILE"], "w", encoding="utf-8") as handle:
    json.dump(sys.argv, handle)

sys.exit(int(os.environ.get("LAUNCHER_STUB_EXIT", "0")))
"""

YTDLP_STUB = """\
#!{python}
print("2026.10.26")
"""


def tracked_files(pattern):
    """Files git actually tracks, so an untracked scratch file cannot fail the suite."""
    out = subprocess.run(
        ["git", "ls-files", pattern],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [REPO_ROOT / path for path in out]


def launchers():
    """Every tracked module that launches Streamlit as a subprocess.

    Discovered rather than listed, so a new launcher is covered the day it is
    added and a renamed one cannot quietly leave the set.
    """
    found = []
    for path in tracked_files("*.py"):
        if path.parts[len(REPO_ROOT.parts)] == "tests":
            continue
        if LAUNCH_CALL.search(path.read_text(encoding="utf-8")):
            found.append(path.relative_to(REPO_ROOT))
    return sorted(found)


def compose_default_port():
    """The port the compose sample publishes when PORT is unset."""
    sample = (REPO_ROOT / "docker-compose.yml.sample").read_text(encoding="utf-8")
    match = COMPOSE_DEFAULT_PORT.search(sample)
    return match.group(1) if match else ""


def shipped_variables():
    """Every environment variable this project offers a user, from the files."""
    names = set(ENV_SAMPLE_VAR.findall((REPO_ROOT / ".env.sample").read_text()))
    for name in ("docker-compose.yml.sample", "Dockerfile"):
        path = REPO_ROOT / name
        if path.exists():
            names |= set(re.findall(r"\b([A-Z][A-Z_0-9]{2,})\b", path.read_text()))
    from app.config import _DEFAULTS, _ENV_ALIASES

    return names | set(_DEFAULTS) | set(_ENV_ALIASES)


def build_project(tmp_path, env_text=None):
    """A throwaway copy of the project layout the launchers resolve against.

    Only the launchers and an empty `app/main.py` are real; everything a
    launcher reaches for — the Streamlit entry point, the `.env`, the
    `streamlit` module, the `yt-dlp` binary — exists here and nowhere else, so
    a path computed one directory off resolves to nothing and the test says so.
    """
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "main.py").write_text("# stub Streamlit entry point\n")
    for launcher in launchers():
        destination = tmp_path / launcher
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / launcher, destination)

    if env_text is not None:
        (tmp_path / ".env").write_text(env_text, encoding="utf-8")

    stub_root = tmp_path / "_stub"
    (stub_root / "streamlit").mkdir(parents=True)
    (stub_root / "streamlit" / "__init__.py").write_text("")
    (stub_root / "streamlit" / "__main__.py").write_text(STREAMLIT_STUB)

    bin_dir = tmp_path / "_bin"
    bin_dir.mkdir()
    ytdlp = bin_dir / "yt-dlp"
    ytdlp.write_text(YTDLP_STUB.format(python=sys.executable))
    ytdlp.chmod(0o755)

    return stub_root, bin_dir


def launch(tmp_path, launcher, env=None, stub_exit=0):
    """Run one launcher for real and report what it handed Streamlit.

    Returns (returncode, argv or None, output). ``argv is None`` means the stub
    was never reached, which the vacuity rule below refuses to tolerate.
    """
    env = dict(env or {})
    # `_ENV` is the content of the .env file to drop at the project root, not a
    # variable to export.
    stub_root, bin_dir = build_project(tmp_path, env_text=env.pop("_ENV", None))
    argv_file = tmp_path / "argv.json"

    environ = dict(os.environ)
    environ.pop("PORT", None)
    environ.update(
        {
            "PYTHONPATH": str(stub_root),
            "PATH": f"{bin_dir}{os.pathsep}{environ.get('PATH', '')}",
            ARGV_FILE: str(argv_file),
            STUB_EXIT: str(stub_exit),
        }
    )
    environ.update(env or {})

    completed = subprocess.run(
        [sys.executable, "-u", str(tmp_path / launcher)],
        cwd=tmp_path,
        env=environ,
        capture_output=True,
        text=True,
        timeout=120,
    )
    argv = json.loads(argv_file.read_text()) if argv_file.exists() else None
    return completed.returncode, argv, completed.stdout + completed.stderr


def port_handed_to_streamlit(argv):
    """The value of `--server.port` in what the launcher asked Streamlit for."""
    return argv[argv.index("--server.port") + 1] if "--server.port" in argv else None


def target_handed_to_streamlit(argv):
    """The script the launcher told Streamlit to run."""
    return argv[argv.index("run") + 1] if "run" in argv else None


# --- The rules -------------------------------------------------------------


@pytest.mark.parametrize("launcher", launchers(), ids=str)
def test_every_launcher_hands_streamlit_a_target_that_exists(tmp_path, launcher):
    """app/hometube.py asked for app/app/main.py, one directory too deep."""
    _, argv, output = launch(tmp_path, launcher)
    assert argv is not None, f"{launcher} never reached Streamlit at all:\n{output}"

    target = target_handed_to_streamlit(argv)
    assert target, f"{launcher} handed Streamlit no target: {argv}"
    assert Path(target).is_file(), (
        f"{launcher} told Streamlit to run {target}, which does not exist. "
        "A launcher resolving its paths relative to the wrong directory starts "
        "nothing; app/hometube.py computed app/app/main.py for nine months."
    )


@pytest.mark.parametrize("launcher", launchers(), ids=str)
def test_every_launcher_defaults_to_the_port_the_compose_sample_publishes(
    tmp_path, launcher
):
    """run.py defaulted to an undocumented 8502 the README assigns elsewhere."""
    expected = compose_default_port()
    _, argv, output = launch(tmp_path, launcher)
    assert argv is not None, f"{launcher} never reached Streamlit at all:\n{output}"

    assert port_handed_to_streamlit(argv) == expected, (
        f"{launcher} defaults to port {port_handed_to_streamlit(argv)} while "
        f"docker-compose.yml.sample publishes {expected} and every document "
        "names it. The expected value is read from the compose sample, not "
        "written here, so moving one moves both."
    )


@pytest.mark.parametrize("launcher", launchers(), ids=str)
def test_every_launcher_honours_the_port_variable(tmp_path, launcher):
    """PORT is the variable .env.sample ships and the docs describe."""
    _, argv, output = launch(tmp_path, launcher, env={"PORT": "8531"})
    assert argv is not None, f"{launcher} never reached Streamlit at all:\n{output}"

    assert port_handed_to_streamlit(argv) == "8531", (
        f"{launcher} ignored PORT=8531 and used "
        f"{port_handed_to_streamlit(argv)}. PORT is the only port variable this "
        "project documents; a launcher that reads another name silently starts "
        "somewhere the user did not ask for."
    )


@pytest.mark.parametrize("launcher", launchers(), ids=str)
def test_every_launcher_reads_the_env_file_at_the_project_root(tmp_path, launcher):
    """app/hometube.py looked for app/.env, which nothing writes."""
    _, argv, output = launch(tmp_path, launcher, env={"_ENV": "PORT=8542\n"})
    assert argv is not None, f"{launcher} never reached Streamlit at all:\n{output}"

    assert port_handed_to_streamlit(argv) == "8542", (
        f"{launcher} did not read the .env at the project root: it asked for "
        f"port {port_handed_to_streamlit(argv)} instead of the 8542 the file "
        "sets. app/config.py resolves that file as parent.parent/'.env'; a "
        "launcher that resolves it anywhere else ignores the user's whole "
        "configuration behind no message at all."
    )


@pytest.mark.parametrize("launcher", launchers(), ids=str)
def test_an_explicit_environment_port_wins_over_the_env_file(tmp_path, launcher):
    """The precedence app/config.py uses: load_dotenv(override=False)."""
    _, argv, output = launch(
        tmp_path, launcher, env={"_ENV": "PORT=8542\n", "PORT": "8553"}
    )
    assert argv is not None, f"{launcher} never reached Streamlit at all:\n{output}"

    assert port_handed_to_streamlit(argv) == "8553", (
        f"{launcher} let the .env file override an explicit PORT. "
        "app/config.py calls load_dotenv with override=False, so an explicit "
        "environment variable wins there and must win here too."
    )


@pytest.mark.parametrize("launcher", launchers(), ids=str)
def test_no_launcher_reports_success_when_streamlit_could_not_start(tmp_path, launcher):
    """Both launchers discarded the return code and exited 0 regardless."""
    returncode, argv, output = launch(tmp_path, launcher, stub_exit=3)
    assert argv is not None, f"{launcher} never reached Streamlit at all:\n{output}"

    assert returncode != 0, (
        f"{launcher} exited 0 after Streamlit failed with 3. "
        "subprocess.run() does not raise on a non-zero code; discarding it "
        "turns a launch that started nothing into a command that succeeded."
    )


def test_every_environment_variable_a_launcher_reads_is_one_the_project_ships():
    """The rule that names the defect: STREAMLIT_PORT was shipped nowhere.

    Textual rather than behavioural on purpose — the point is the *name*, and a
    name nothing ships can only ever be read as its own default.
    """
    shipped = shipped_variables()
    unknown = {}
    for launcher in launchers():
        source = (REPO_ROOT / launcher).read_text(encoding="utf-8")
        names = {name for match in ENV_READS.findall(source) for name in match if name}
        missing = sorted(name for name in names if name not in shipped)
        if missing:
            unknown[str(launcher)] = missing

    assert not unknown, (
        "These launchers read environment variables this project ships nowhere "
        f"— not in .env.sample, not in the compose sample, not in app/config.py: "
        f"{unknown}. A variable nobody can set is a hardcoded default wearing a "
        "configuration's clothes; run.py read STREAMLIT_PORT for exactly that long."
    )


# --- The rules that refuse to pass on nothing ------------------------------


def test_the_launcher_set_is_not_empty_and_holds_what_the_guide_names():
    """Without this, every rule above is a loop over an empty list.

    The expected members are derived from the "Running the Application" section
    of docs/contributing.md rather than listed here, so the guide and the set
    cannot drift apart.
    """
    found = {str(path) for path in launchers()}
    assert found, (
        "No launcher was discovered, so every rule in this module passed over "
        f"an empty list. Has {LAUNCH_CALL.pattern} stopped matching?"
    )

    guide = (REPO_ROOT / "docs" / "contributing.md").read_text(encoding="utf-8")
    section = guide.split("## 🏃 Running the Application", 1)
    assert len(section) == 2, "the 'Running the Application' heading has moved"
    body = section[1].split("\n## ", 1)[0]
    named = set(DOC_PYTHON_SCRIPT.findall(body))
    assert named, "that section names no `python <script>.py` command any more"

    assert named <= found, (
        f"docs/contributing.md tells a contributor to run {sorted(named - found)} "
        "under 'Running the Application', but that is not a launcher this module "
        "found. Either the guide names the wrong script or the discovery broke."
    )


@pytest.mark.parametrize("launcher", launchers(), ids=str)
def test_the_stub_streamlit_is_actually_reached(tmp_path, launcher):
    """The harness's own guard: no capture means nothing above was tested."""
    returncode, argv, output = launch(tmp_path, launcher)
    assert argv is not None, (
        f"{launcher} ran without ever invoking the stub Streamlit, so every "
        f"behavioural rule in this module is vacuously true for it. Output:\n{output}"
    )
    assert argv[0].endswith("__main__.py"), f"unexpected stub invocation: {argv}"
    assert returncode == 0, f"{launcher} failed in the harness:\n{output}"


def test_the_compose_default_port_is_actually_parsed():
    """Without this, the default-port rule compares every launcher to ''."""
    default = compose_default_port()
    assert default.isdigit() and 1 <= int(default) <= 65535, (
        "docker-compose.yml.sample no longer publishes a ${PORT:-NNNN} default, "
        f"so the default-port rule has nothing to compare against (got {default!r})."
    )

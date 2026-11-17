"""Guards on the contract between ``.streamlit/config.toml``, the launch
command the published image runs, and the options Streamlit actually honours.

These are not characterisation tests. They pin a defect that was public and
silent, in the same family as the Makefile's catch-all, the deployment guide's
absent files, the conda environment's drifted pin list and ``run.py``'s
``STREAMLIT_PORT``: *a thing that silently does the wrong thing instead of
failing.*

``.streamlit/config.toml`` is copied into the image (``Dockerfile``, ``COPY
.streamlit/ /app/.streamlit/``) and read from the working directory Streamlit
starts in, so it governs the published image as much as a local run. But the
image's ``CMD`` passes ``--server.enableCORS=false`` and
``--server.enableXsrfProtection=false``, and a command-line flag wins over the
file. Both protections were therefore *off* in the image while the file set
them ``true`` and its comments advised keeping them so — the same repository
running with opposite postures depending on how it was launched, with nothing
anywhere saying which one applied where.

The rules below do not decide what the image's posture should be. They make the
two sides state the same thing: an option the launch command contradicts must
say so on its own line, and an option that says so must really be contradicted.
A flag added, removed, or flipped on either side breaks one of them.

Everything is derived from the tree. The option set comes from the file, the
flags come from the ``CMD`` line of the Dockerfile, and the resolved values come
from ``streamlit.web.bootstrap.load_config_options()`` — the function
``streamlit run`` itself calls — rather than from this module's reading of
Streamlit's precedence rules. The resolution runs in a subprocess whose
``cwd`` is a throwaway copy of ``.streamlit/`` and whose ``HOME`` is a throwaway
directory, so neither a developer's global ``~/.streamlit/config.toml`` nor a
stray ``STREAMLIT_*`` variable can change the answer. Streamlit is a core
dependency of this project, so the harness needs no network and no external
tool, and runs in CI.

Three of the eight rules exist only to stop the other five passing on nothing: a
parser that silently matched zero options, a ``CMD`` that was never found, or a
subprocess that read some other config file would make every assertion above
vacuously true.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO_ROOT / ".streamlit" / "config.toml"
DOCKERFILE = REPO_ROOT / "Dockerfile"

# A `[section]` header, and an `option = value` line with its optional trailing
# comment. Whitespace-tolerant so reformatting the file does not drop an option
# from the set.
SECTION_HEADER = re.compile(r"^\s*\[([A-Za-z][\w.]*)\]\s*$")
OPTION_LINE = re.compile(r"^\s*([A-Za-z]\w*)\s*=\s*[^#]+?(?:\s*#\s*(.*))?$")

# What an option's own line says when the launch command contradicts it. The
# phrase, not the exact wording of the rest of the comment.
DECLARES_OVERRIDE = re.compile(r"overridden by the image", re.IGNORECASE)

# `CMD ["python","-m","streamlit", ...]` — the exec form, which is what the
# Dockerfile uses and the only form whose arguments can be read without a shell.
CMD_LINE = re.compile(r"^\s*CMD\s+(\[.*\])\s*$", re.MULTILINE)

# `--server.enableCORS=false` as Streamlit's own CLI accepts it.
CMD_FLAG = re.compile(r"^--([A-Za-z]\w*\.\w+)=(.*)$")

# `WORKDIR /app`, and `COPY .streamlit/ /app/.streamlit/` — the directory
# Streamlit starts in, and where this file lands in the image. Trailing slashes
# are normalised away by PurePosixPath so `/app/.streamlit` and
# `/app/.streamlit/` are the same destination.
WORKDIR_LINE = re.compile(r"^\s*WORKDIR\s+(\S+)\s*$", re.MULTILINE)
COPY_STREAMLIT_DIR = re.compile(
    r"^\s*COPY\s+(?:--\S+\s+)*\.streamlit/?\s+(\S+)\s*$", re.MULTILINE
)


def _parse_config_file():
    """Every option of ``.streamlit/config.toml``, with the comment on its line.

    Values come from ``tomllib`` so this module never reinterprets TOML; the
    line scan contributes only the comments, which TOML discards.
    """
    text = CONFIG_FILE.read_text(encoding="utf-8")
    values = tomllib.loads(text)

    comments: dict[str, str] = {}
    section = None
    for line in text.splitlines():
        header = SECTION_HEADER.match(line)
        if header:
            section = header.group(1)
            continue
        if section is None or line.lstrip().startswith("#"):
            continue
        option = OPTION_LINE.match(line)
        if option:
            comments[f"{section}.{option.group(1)}"] = option.group(2) or ""

    flat = {
        f"{section}.{key}": value
        for section, body in values.items()
        for key, value in body.items()
    }
    return flat, comments


def _parse_cmd_flags():
    """The config options the image's launch command sets, and their values.

    Returns ``(argv, flags)`` so a rule can assert the command found is really
    a Streamlit launch before trusting the flags read out of it.
    """
    match = CMD_LINE.search(DOCKERFILE.read_text(encoding="utf-8"))
    if match is None:
        return [], {}
    argv = json.loads(match.group(1))

    flags: dict[str, object] = {}
    for token in argv:
        flag = CMD_FLAG.match(token)
        if flag is None:
            continue
        raw = flag.group(2)
        # Streamlit's CLI coerces by the option's declared type; booleans are
        # the only ones this project's flags use, and the only ones a string
        # would silently compare unequal to.
        if raw.lower() in ("true", "false"):
            flags[flag.group(1)] = raw.lower() == "true"
        else:
            flags[flag.group(1)] = raw
    return argv, flags


RESOLVER = r"""
import json, sys
from streamlit.web import bootstrap
import streamlit.config as config

options, scenarios = json.load(sys.stdin)
out = {}
for label, flags in scenarios.items():
    bootstrap.load_config_options({k.replace(".", "_"): v for k, v in flags.items()})
    out[label] = {
        name: {
            "value": config.get_option(name),
            "where": config._config_options[name].where_defined,
        }
        for name in options
        if name in config._config_options
    }
out["known"] = sorted(config.get_config_options())
json.dump(out, sys.stdout)
"""


@pytest.fixture(scope="module")
def resolved(tmp_path_factory):
    """What Streamlit resolves for each option, locally and under the image's
    launch command, asked of Streamlit's own loader.

    The subprocess runs in a throwaway copy of ``.streamlit/`` with a throwaway
    ``HOME`` and no inherited ``STREAMLIT_*`` variable, so the only config file
    in play is this repository's.
    """
    sandbox = tmp_path_factory.mktemp("stconfig")
    (sandbox / ".streamlit").mkdir()
    shutil.copy(CONFIG_FILE, sandbox / ".streamlit" / "config.toml")
    home = tmp_path_factory.mktemp("home")

    options, _ = _parse_config_file()
    _, flags = _parse_cmd_flags()

    env = {k: v for k, v in os.environ.items() if not k.startswith("STREAMLIT_")}
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)

    completed = subprocess.run(
        [sys.executable, "-c", RESOLVER],
        input=json.dumps([sorted(options), {"local": {}, "image": flags}]),
        capture_output=True,
        text=True,
        cwd=sandbox,
        env=env,
        timeout=180,
    )
    assert completed.returncode == 0, (
        "the resolution harness did not run; Streamlit is a core dependency of "
        f"this project, so this is a broken harness, not a skip:\n{completed.stderr}"
    )
    answer = json.loads(completed.stdout)
    answer["sandbox_config"] = str(sandbox / ".streamlit" / "config.toml")
    return answer


def test_every_configured_option_is_known_to_streamlit(resolved):
    """An option Streamlit does not define is inert: nothing reads it, nothing
    warns, and the application starts with its default behaviour. A Streamlit
    release that renames or removes one must fail here and not in production.
    """
    options, _ = _parse_config_file()
    unknown = sorted(set(options) - set(resolved["known"]))
    assert not unknown, (
        f".streamlit/config.toml sets options Streamlit does not define: {unknown}. "
        "Either the name is wrong or this Streamlit release dropped it; a setting "
        "Streamlit does not know is silently ignored."
    )


def test_every_launch_flag_is_known_to_streamlit(resolved):
    """Same defect on the other side: a mistyped ``--server.enableCors=false``
    in the image's CMD would configure nothing at all.
    """
    _, flags = _parse_cmd_flags()
    unknown = sorted(set(flags) - set(resolved["known"]))
    assert (
        not unknown
    ), f"the Dockerfile's CMD passes flags Streamlit does not define: {unknown}"


def test_a_local_launch_resolves_every_option_from_this_file(resolved):
    """With no flags — ``streamlit run app/main.py`` from the repository root,
    which is what ``run.py`` and ``docs/contributing.md`` do — every option must
    come from this file and carry the value written in it. This is what makes
    the file authoritative locally, and what gives the next rule a baseline.
    """
    options, _ = _parse_config_file()
    local = resolved["local"]

    # An option Streamlit does not define is not reported at all; that is the
    # first rule's failure and the last rule's, not this one's.
    wrong = {
        name: (written, local[name]["value"])
        for name, written in options.items()
        if name in local and local[name]["value"] != written
    }
    assert not wrong, (
        "a local launch does not resolve these options to the value "
        f".streamlit/config.toml writes: {wrong}"
    )

    elsewhere = {
        name: local[name]["where"]
        for name in options
        if name in local and local[name]["where"] != resolved["sandbox_config"]
    }
    assert (
        not elsewhere
    ), f"these options were resolved from somewhere other than this file: {elsewhere}"


def test_the_options_the_image_contradicts_are_exactly_those_the_file_declares(
    resolved,
):
    """The rule this module exists for.

    An option the image's launch command resolves to a *different* value than
    the file writes must say so on its own line, and an option whose line says
    so must really be contradicted. Removing a flag from the CMD without
    removing the note, or adding one without adding the note, breaks this.
    """
    options, comments = _parse_config_file()
    image = resolved["image"]

    contradicted = {
        name
        for name, written in options.items()
        if name in image and image[name]["value"] != written
    }
    declared = {
        name for name, comment in comments.items() if DECLARES_OVERRIDE.search(comment)
    }

    assert contradicted == declared, (
        "the launch command and the file disagree about which options the image "
        f"overrides.\n  contradicted by the CMD: {sorted(contradicted)}\n"
        f"  declared in config.toml:  {sorted(declared)}\n"
        "Every option the image overrides must say so on its line, and nothing else may."
    )


def test_the_image_copies_this_file_to_where_streamlit_reads_it():
    """Everything above is about what the file says. This is about whether the
    image has it at all.

    Streamlit reads ``./.streamlit/config.toml`` relative to the directory it
    starts in, which in the image is the ``WORKDIR``. Drop the ``COPY``, or
    change either side of it, and the image silently falls back to Streamlit's
    defaults — a dark-themed application turning light, telemetry back on, and
    not one error anywhere. Nothing else in this repository would notice.
    """
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    workdirs = WORKDIR_LINE.findall(dockerfile)
    assert (
        workdirs
    ), "the Dockerfile sets no WORKDIR, so Streamlit's config path is unknown"
    workdir = PurePosixPath(workdirs[-1].strip().strip("\"'"))

    destinations = [
        PurePosixPath(destination.strip().strip("\"'"))
        for destination in COPY_STREAMLIT_DIR.findall(dockerfile)
    ]
    assert destinations, (
        "the Dockerfile never copies .streamlit/ into the image, so none of the "
        "settings in this file reach a published container"
    )
    assert workdir / ".streamlit" in destinations, (
        f"the Dockerfile copies .streamlit/ to {[str(d) for d in destinations]}, but "
        f"Streamlit reads it from {workdir / '.streamlit'} — the WORKDIR it starts in"
    )


def test_the_config_file_parse_is_not_vacuous():
    """Three of the five rules above iterate the options this module parses out
    of the file. A broken regex would make all three pass on an empty set, which
    is the failure ``run.py``'s port contract hit from the other side: the
    discovery vanished and every behavioural assertion passed on nothing.

    The line scan must therefore account for every option ``tomllib`` finds.
    """
    options, comments = _parse_config_file()
    assert options, "no option was parsed out of .streamlit/config.toml"
    missed = sorted(set(options) - set(comments))
    assert not missed, (
        "the line scan did not find these options that tomllib did, so their "
        f"comments — and the override declarations in them — were never read: {missed}"
    )


def test_the_launch_command_parse_is_not_vacuous():
    """The override rule compares against the flags read out of the Dockerfile.
    If the CMD is not found, or is not a Streamlit launch, or yields no flags,
    that comparison is between two empty sets and proves nothing.
    """
    argv, flags = _parse_cmd_flags()
    assert argv, "no exec-form CMD was found in the Dockerfile"
    assert (
        "streamlit" in argv and "run" in argv
    ), f"the CMD found is not a Streamlit launch: {argv}"
    assert flags, f"no --section.option=value flag was read out of the CMD: {argv}"


def test_the_resolver_really_read_this_repositorys_config(resolved):
    """The two resolution rules trust a subprocess. If it had read a global
    ``~/.streamlit/config.toml``, or no file at all, its answers would be
    Streamlit's defaults and both rules would compare defaults to defaults.

    So at least one option must be reported as coming from the sandbox copy,
    and the two scenarios must actually differ — a harness that ignored the
    flags would otherwise satisfy the override rule by accident.
    """
    options, _ = _parse_config_file()
    assert set(resolved["local"]) == set(options), (
        "the resolver did not report on every option: "
        f"{sorted(set(options) - set(resolved['local']))}"
    )
    assert resolved["sandbox_config"] in {
        entry["where"] for entry in resolved["local"].values()
    }, "no option was resolved from the sandbox copy of .streamlit/config.toml"

    _, flags = _parse_cmd_flags()
    assert any(
        resolved["image"][name]["where"] != resolved["local"][name]["where"]
        for name in flags
        if name in resolved["image"]
    ), "passing the CMD's flags changed nothing, so the harness ignored them"

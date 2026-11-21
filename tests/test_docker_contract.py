"""Guards on the contract between the published image, the sample compose file
and the documents that describe them.

These are not characterisation tests. They pin defects that were public and
silent, in the same family as the Makefile's catch-all, the deployment guide's
absent files, the conda environment's drifted pin list, ``run.py``'s
``STREAMLIT_PORT`` and the Streamlit config the image's ``CMD`` overrode: *a
thing that silently does the wrong thing instead of failing.*

``docs/docker.md`` is the guide a stranger reads before running anything, and it
described a container this project does not publish:

* It offered three image tags, and **two of them do not exist**. Nothing builds
  a ``main`` tag — only ``release.yml`` (on a ``v*`` tag) and
  ``refresh-ytdlp.yml`` (daily, when yt-dlp moves) call ``build-image.yml`` with
  ``push: true``, while ``ci.yml`` builds with ``push: false`` — and ``2.4.1``,
  the version it gave as an example, was never released. ``docker pull`` on
  either answers ``manifest unknown``.
* The yaml block presented as *the content of* ``docker-compose.yml.sample`` was
  not that file: no ``env_file``, no ``TZ``, volumes the file does not use, two
  ``STREAMLIT_*`` variables it does not set, and none of the three
  ``*_DOCKER_HOST`` variables it requires — two of them declared ``:?``, which
  stops ``docker compose up`` outright when they are unset. Those three were
  documented nowhere in the guide.
* It listed ``STREAMLIT_SERVER_PORT`` and ``STREAMLIT_SERVER_ADDRESS`` as
  configuration knobs. The address is not one: the ``CMD`` passes
  ``--server.address`` and a command-line flag wins over an environment
  variable. The port is worse than not working — it works, and leaves ``EXPOSE``
  and the ``HEALTHCHECK``'s hard-coded port behind, so the container runs
  reported unhealthy.
* And the ``ENV`` block set ``STREAMLIT_HEADLESS``, which is not a name
  Streamlit reads. It builds one variable per option, always
  ``STREAMLIT_<SECTION>_<OPTION>``, so the name is ``STREAMLIT_SERVER_HEADLESS``.
  The ``CMD`` passes ``--server.headless=true`` too, which is why no container
  ever showed the omission.

The rules below decide nothing about how the image should be configured. They
make the two sides state the same thing: a tag a document offers must be one the
workflows publish, a variable the sample file requires must be documented, a
variable the tree sets must be one something reads, and a knob the documents
offer must be one the launch command leaves alone.

Everything is derived from the tree. The flags, ports and environment come from
the Dockerfile; the tag shapes from the two workflows that publish; the required
variables from the sample compose file; and the set of environment variables
Streamlit honours from ``streamlit.web.cli`` — the click command ``streamlit
run`` is, which is what actually reads the environment — rather than from this
module's reading of Streamlit's naming rules. Streamlit is a core dependency, so
the harness needs no network, no container runtime and no external tool, and it
runs in CI.

``tests/`` is outside the scan on purpose: this module and
``test_launcher_contract.py`` both name dead variables in prose in order to pin
them, and a scan that read its own docstring would have nothing to say. For the
same reason the scan matches *assignments* (``NAME=`` and ``"NAME"``) rather
than any occurrence of a name — the Dockerfile's comment names the dead variable
deliberately.

Two of the ten rules exist only to stop the other eight passing on nothing: a
``CMD`` that was never found, a table parser that silently matched zero rows or
a tag scan that found no image reference would make every assertion above
vacuously true.
"""

import functools
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = REPO_ROOT / "Dockerfile"
COMPOSE_SAMPLE = REPO_ROOT / "docker-compose.yml.sample"
DOCKER_GUIDE = REPO_ROOT / "docs" / "docker.md"
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
REFRESH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "refresh-ytdlp.yml"

# The files that configure or describe the container. `tests/` is excluded (see
# the module docstring), and so is everything untracked: a developer's own
# `docker-compose.yml` or `.env` is not a claim this project makes.
SCANNED_TEXT_FILES = (
    [DOCKERFILE, COMPOSE_SAMPLE, REPO_ROOT / ".env.sample", REPO_ROOT / "run.py"]
    + sorted((REPO_ROOT / "docs").rglob("*.md"))
    + [REPO_ROOT / "README.md"]
)

# `CMD ["python","-m","streamlit", ...]` — the exec form, which is what the
# Dockerfile uses and the only form whose arguments can be read without a shell.
CMD_LINE = re.compile(r"^\s*CMD\s+(\[.*\])\s*$", re.MULTILINE)

# `--server.enableCORS=false`, as Streamlit's own CLI accepts it.
CMD_FLAG = re.compile(r"^--([A-Za-z]\w*\.\w+)=(.*)$")

# The `ENV` instruction, including its backslash continuations, and one
# `NAME=value` out of it.
ENV_INSTRUCTION = re.compile(r"^\s*ENV\s+((?:[^\n]*\\\n)*[^\n]*)$", re.MULTILINE)
ENV_ASSIGNMENT = re.compile(r"\b([A-Z][A-Z0-9_]*)=(\S*)")

# `EXPOSE 8501`, and the port the health check probes out of
# `wget -qO- http://127.0.0.1:8501/_stcore/health`.
EXPOSE_LINE = re.compile(r"^\s*EXPOSE\s+(\d+)\s*$", re.MULTILINE)
HEALTHCHECK_URL_PORT = re.compile(r"https?://[\w.]+:(\d+)/")

# A `STREAMLIT_*` variable the tree *sets*: `NAME=value` in a Dockerfile, a
# compose file or a shell line, or `"NAME"` in the JSON of a task definition.
STREAMLIT_ASSIGNED = re.compile(r"\b(STREAMLIT_[A-Z0-9_]+)(?=\s*=)")
STREAMLIT_QUOTED = re.compile(r'"(STREAMLIT_[A-Z0-9_]+)"')

# A row of one of the guide's variable tables: the first cell, backticked.
TABLE_ROW_VARIABLE = re.compile(r"^\|\s*`([A-Z][A-Z0-9_]*)`\s*\|", re.MULTILINE)

# `${VAR}`, `${VAR:-default}`, `${VAR:?message}` as compose interpolates them.
COMPOSE_INTERPOLATION = re.compile(r"\$\{([A-Z][A-Z0-9_]*)[:}\-?]")

# The container side of a published port: `- "${PORT:-8501}:8501"`.
COMPOSE_PUBLISHED_PORT = re.compile(r'^\s*-\s*"[^"]*:(\d+)"\s*$', re.MULTILINE)

# A full image reference with a tag, as a document offers it to a reader.
IMAGE_REFERENCE = re.compile(r"ghcr\.io/[\w-]+/hometube:([A-Za-z0-9._<>-]+)")

# The tag templates the publishing workflows feed to the registry:
# `type=semver,pattern={{version}}` and `type=raw,value=latest` in release.yml,
# and `${BASE}:yt-dlp-${YTDLP}` in the refresh workflow's shell heredoc.
METADATA_SEMVER_PATTERN = re.compile(r"type=semver,pattern=(\S+)")
METADATA_RAW_VALUE = re.compile(r"type=raw,value=(\S+)")
SHELL_TAG_TEMPLATE = re.compile(r"^\s*\$\{BASE\}:(\S+)\s*$", re.MULTILINE)

# What a version looks like in a published tag, and how a document is allowed to
# spell the same thing as a placeholder. This is the one piece of knowledge the
# module supplies rather than derives: a workflow template says `{{version}}`,
# and only a human knows that `X.Y.Z` is how a guide writes an example of one.
_VERSION = r"(?:\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.]+)?|X\.Y\.Z|<version>)"
_MAJOR_MINOR = r"(?:\d+\.\d+|X\.Y)"
_MAJOR = r"(?:\d+|X)"
_YTDLP_VERSION = r"(?:\d{4}\.\d{2}\.\d{2}|<version>|<date>)"
TEMPLATE_TOKENS = {
    "{{version}}": _VERSION,
    "{{major}}.{{minor}}": _MAJOR_MINOR,
    "{{major}}": _MAJOR,
    "${APP}": _VERSION,
    "${YTDLP}": _YTDLP_VERSION,
}


def _dockerfile_text():
    return DOCKERFILE.read_text(encoding="utf-8")


def _parse_cmd_flags():
    """The config options the image's launch command sets, and their values.

    Returns ``(argv, flags)`` so a rule can assert the command found is really a
    Streamlit launch before trusting the flags read out of it.
    """
    match = CMD_LINE.search(_dockerfile_text())
    if match is None:
        return [], {}
    argv = json.loads(match.group(1))
    flags = {}
    for token in argv:
        flag = CMD_FLAG.match(token)
        if flag:
            flags[flag.group(1)] = flag.group(2)
    return argv, flags


def _parse_env_assignments():
    """Every ``NAME=value`` of every ``ENV`` instruction in the Dockerfile."""
    assignments = {}
    for instruction in ENV_INSTRUCTION.finditer(_dockerfile_text()):
        body = instruction.group(1).replace("\\\n", " ")
        for name, value in ENV_ASSIGNMENT.findall(body):
            assignments[name] = value
    return assignments


PROBE = """
import json
from streamlit.web import cli as streamlit_cli
from streamlit import config as streamlit_config

run_command = streamlit_cli.main.commands["run"]
env_vars = sorted(
    parameter.envvar
    for parameter in run_command.params
    if isinstance(getattr(parameter, "envvar", None), str)
)
option_of_env_var = {
    option.env_var: key
    for key, option in streamlit_config._config_options_template.items()
}
print(
    json.dumps(
        {
            "env_vars": env_vars,
            "option_of": {
                name: option_of_env_var[name]
                for name in env_vars
                if name in option_of_env_var
            },
        }
    )
)
"""


@functools.lru_cache(maxsize=1)
def _streamlit_cli_facts():
    """The environment variables ``streamlit run`` reads, and their options.

    Streamlit builds one variable per config option — ``config_option.env_var``
    is ``STREAMLIT_`` plus the snake-cased key — and ``streamlit.web.cli`` hands
    each one to click as that parameter's ``envvar``. The click command is
    therefore the authoritative list of names that have any effect, which is why
    this module asks it instead of recomputing the naming rule.

    It asks in a subprocess for two reasons. ``tests/conftest.py`` replaces
    ``sys.modules["streamlit"]`` with a ``MagicMock`` for the whole suite, so the
    real package cannot be imported in process at all; and a throwaway ``HOME``
    and a scrubbed environment mean no developer's ``~/.streamlit/config.toml``
    and no stray ``STREAMLIT_*`` can change the answer.
    """
    with tempfile.TemporaryDirectory() as sandbox:
        completed = subprocess.run(
            [sys.executable, "-c", PROBE],
            capture_output=True,
            text=True,
            cwd=sandbox,
            env={"PATH": os.environ.get("PATH", ""), "HOME": sandbox},
            check=False,
        )
    assert (
        completed.returncode == 0
    ), f"could not ask Streamlit what it reads: {completed.stderr[-2000:]}"
    facts = json.loads(completed.stdout)
    return frozenset(facts["env_vars"]), facts["option_of"]


def _streamlit_env_vars_read_by_the_cli():
    return _streamlit_cli_facts()[0]


def _env_var_name_to_option(env_var, cli_env_vars):
    """``STREAMLIT_SERVER_HEADLESS`` → ``server.headless``, or ``None``.

    Derived by matching against the options the CLI knows rather than by
    splitting the name, which cannot be done unambiguously: ``server.headless``
    and a hypothetical ``server.head.less`` would share a variable name.
    """
    if env_var not in cli_env_vars:
        return None
    return _streamlit_cli_facts()[1].get(env_var)


def _streamlit_variables_the_tree_sets():
    """Every ``STREAMLIT_*`` variable the scanned files set, with its origin."""
    found = {}
    for path in SCANNED_TEXT_FILES:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for name in STREAMLIT_ASSIGNED.findall(text) + STREAMLIT_QUOTED.findall(text):
            found.setdefault(name, set()).add(path.relative_to(REPO_ROOT).as_posix())
    return found


def _documented_table_variables(path=DOCKER_GUIDE):
    """The variables the guide presents in a table, i.e. offers as knobs."""
    return set(TABLE_ROW_VARIABLE.findall(path.read_text(encoding="utf-8")))


def _quoted_compose_block():
    """The fenced yaml block the guide presents as the sample compose file.

    Found by its caption rather than by position: the block that follows the
    line naming ``docker-compose.yml.sample``.
    """
    lines = DOCKER_GUIDE.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if "docker-compose.yml.sample" not in line or not line.startswith("**"):
            continue
        for start in range(index + 1, min(index + 4, len(lines))):
            if lines[start].startswith("```"):
                body = []
                for text in lines[start + 1 :]:
                    if text.startswith("```"):
                        return "\n".join(body)
                    body.append(text)
    return None


def _published_tag_templates():
    """The tag shapes the two publishing workflows produce, as regexes."""
    release = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    refresh = REFRESH_WORKFLOW.read_text(encoding="utf-8")

    templates = (
        METADATA_SEMVER_PATTERN.findall(release)
        + METADATA_RAW_VALUE.findall(release)
        + SHELL_TAG_TEMPLATE.findall(refresh)
    )

    patterns = []
    for template in templates:
        pattern = ""
        rest = template
        while rest:
            for token, fragment in TEMPLATE_TOKENS.items():
                if rest.startswith(token):
                    pattern += fragment
                    rest = rest[len(token) :]
                    break
            else:
                pattern += re.escape(rest[0])
                rest = rest[1:]
        patterns.append((template, re.compile(f"^{pattern}$")))
    return patterns


def _documented_image_tags():
    """Every tag a document offers inside a full ``ghcr.io/...`` reference."""
    found = {}
    for path in SCANNED_TEXT_FILES:
        if not path.is_file():
            continue
        for tag in IMAGE_REFERENCE.findall(path.read_text(encoding="utf-8")):
            found.setdefault(tag, set()).add(path.relative_to(REPO_ROOT).as_posix())
    return found


# --------------------------------------------------------------------------- #
# The image's own declarations
# --------------------------------------------------------------------------- #


def test_every_streamlit_variable_the_tree_sets_is_one_streamlit_reads():
    """A ``STREAMLIT_*`` name that matches no option is read by nothing.

    This is the rule ``STREAMLIT_HEADLESS`` failed, in the ``ENV`` block of every
    published image, for as long as the line existed. The valid names come from
    the click command ``streamlit run`` is, so a Streamlit release that renames
    an option moves this rule with it.
    """
    cli_env_vars = _streamlit_env_vars_read_by_the_cli()
    unread = {
        name: sorted(origins)
        for name, origins in _streamlit_variables_the_tree_sets().items()
        if name not in cli_env_vars
    }
    assert not unread, (
        "these STREAMLIT_* variables are set but Streamlit reads none of them "
        f"(it reads STREAMLIT_<SECTION>_<OPTION>, {len(cli_env_vars)} names in "
        f"this version): {unread}"
    )


def test_the_env_block_never_contradicts_the_launch_command():
    """An ``ENV`` default and a ``CMD`` flag for the same option must agree.

    A command-line flag wins, so a contradiction here is a declaration the image
    silently ignores — the shape of the defect ``.streamlit/config.toml`` carried
    before the launch command's overrides were written down on their own lines.
    """
    _, flags = _parse_cmd_flags()
    cli_env_vars = _streamlit_env_vars_read_by_the_cli()

    contradictions = {}
    for name, value in _parse_env_assignments().items():
        if not name.startswith("STREAMLIT_"):
            continue
        option = _env_var_name_to_option(name, cli_env_vars)
        if option is None or option not in flags:
            continue
        if value.strip().lower() != flags[option].strip().lower():
            contradictions[name] = {"ENV": value, f"--{option}": flags[option]}

    assert not contradictions, (
        "the ENV block and the CMD set the same option to different values, and "
        f"the flag wins: {contradictions}"
    )


def test_the_container_port_is_the_same_on_all_three_sides():
    """``EXPOSE``, the health check and the sample's mapping name one port.

    The health check's URL is hard-coded, so a port changed anywhere else leaves
    it probing the old one and the container is reported unhealthy for as long as
    it runs — a failure that looks like a broken application.
    """
    text = _dockerfile_text()
    exposed = EXPOSE_LINE.search(text)
    probed = HEALTHCHECK_URL_PORT.search(text)
    published = COMPOSE_PUBLISHED_PORT.search(
        COMPOSE_SAMPLE.read_text(encoding="utf-8")
    )

    assert exposed and probed and published, (
        "could not read the three ports to compare: "
        f"EXPOSE={exposed}, health check={probed}, compose={published}"
    )
    assert exposed.group(1) == probed.group(1) == published.group(1), (
        f"EXPOSE says {exposed.group(1)}, the health check probes "
        f"{probed.group(1)} and the sample compose file publishes "
        f"{published.group(1)} on the container side"
    )


# --------------------------------------------------------------------------- #
# What the documents offer a reader
# --------------------------------------------------------------------------- #


def test_the_guide_offers_no_knob_the_launch_command_overrides():
    """A variable in a table is an offer; the ``CMD`` must leave it alone.

    ``STREAMLIT_SERVER_ADDRESS`` was offered with a default of ``0.0.0.0`` while
    the ``CMD`` passed ``--server.address`` itself, so setting it did nothing and
    said nothing. Prose may still *name* such a variable to explain why it is
    not a knob, which is why only table rows are read here.
    """
    _, flags = _parse_cmd_flags()
    cli_env_vars = _streamlit_env_vars_read_by_the_cli()

    overridden = {}
    for variable in _documented_table_variables():
        if not variable.startswith("STREAMLIT_"):
            continue
        option = _env_var_name_to_option(variable, cli_env_vars)
        if option in flags:
            overridden[variable] = f"--{option}={flags[option]}"

    assert not overridden, (
        "docs/docker.md offers these variables as configuration, but the image's "
        f"CMD sets the same options and a flag wins: {overridden}"
    )


def test_the_guide_does_not_offer_the_port_inside_the_container():
    """``STREAMLIT_SERVER_PORT`` works, and that is the problem.

    Nothing in the ``CMD`` pins it, so setting it really does move the server —
    away from the port ``EXPOSE`` and the health check name. The knob a reader
    wants is the host side of the mapping, so the guide must not present the
    internal port as configurable.
    """
    _, flags = _parse_cmd_flags()
    cli_env_vars = _streamlit_env_vars_read_by_the_cli()
    port_variable = next(
        (
            name
            for name in cli_env_vars
            if _env_var_name_to_option(name, cli_env_vars) == "server.port"
        ),
        None,
    )

    assert port_variable, "Streamlit no longer has a server.port option"
    assert "server.port" not in flags, (
        "the CMD now pins server.port, so this rule and the guide's explanation "
        "both need rewriting"
    )
    assert port_variable not in _documented_table_variables(), (
        f"docs/docker.md offers {port_variable} as configuration: setting it "
        "moves the server away from the port the health check probes"
    )


def test_the_quoted_sample_compose_block_is_the_sample_file():
    """A block captioned with a file name must be that file.

    The guide's block had drifted into a different container: no ``env_file``,
    volumes the file does not use, and none of the variables it requires. Same
    family as the deployment guide's absent scripts and the testing guide's
    absent modules — a document quoting the repository, wrongly.
    """
    quoted = _quoted_compose_block()
    assert quoted is not None, (
        "no fenced block follows the line naming docker-compose.yml.sample in "
        "docs/docker.md — the caption or the block moved"
    )
    assert quoted.strip() == COMPOSE_SAMPLE.read_text(encoding="utf-8").strip(), (
        "the yaml block docs/docker.md presents as docker-compose.yml.sample is "
        "not that file's content"
    )


def test_every_variable_the_sample_compose_needs_is_documented():
    """A variable the sample interpolates must be in the guide's tables.

    Two of the three host paths are declared ``:?``, so ``docker compose up``
    stops at once when they are unset — and all three were documented nowhere.
    The rule is one-directional on purpose: it requires that what the sample
    *needs* be documented, not that everything documented be used by the sample.
    """
    needed = set(
        COMPOSE_INTERPOLATION.findall(COMPOSE_SAMPLE.read_text(encoding="utf-8"))
    )
    undocumented = sorted(needed - _documented_table_variables())
    assert not undocumented, (
        "docker-compose.yml.sample interpolates these variables and "
        f"docs/docker.md documents none of them: {undocumented}"
    )


def test_every_image_tag_the_documents_offer_is_one_the_workflows_publish():
    """A tag a document names must be a tag something pushes.

    ``:main`` was offered as the development image and no workflow has ever
    built it: only ``release.yml`` and ``refresh-ytdlp.yml`` publish, and
    ``ci.yml`` builds with ``push: false``. The accepted shapes are derived from
    those two workflows, so adding a tag there makes it legal here.
    """
    patterns = _published_tag_templates()
    unpublished = {}
    for tag, origins in _documented_image_tags().items():
        if not any(pattern.match(tag) for _, pattern in patterns):
            unpublished[tag] = sorted(origins)

    assert not unpublished, (
        "these image tags are offered by a document and produced by no "
        f"workflow: {unpublished} (publishable shapes: "
        f"{[template for template, _ in patterns]})"
    )


# --------------------------------------------------------------------------- #
# Rules that exist so the ones above cannot pass on nothing
# --------------------------------------------------------------------------- #


def test_the_dockerfile_harness_reads_a_real_launch_command():
    argv, flags = _parse_cmd_flags()
    assert argv[:3] == [
        "python",
        "-m",
        "streamlit",
    ], f"the CMD read from the Dockerfile is not a Streamlit launch: {argv}"
    assert len(flags) >= 3, f"expected the CMD to pin several options, got {flags}"

    env = _parse_env_assignments()
    streamlit_env = {k: v for k, v in env.items() if k.startswith("STREAMLIT_")}
    assert (
        len(streamlit_env) >= 2
    ), f"expected the ENV block to set several STREAMLIT_* variables, got {env}"
    # The probe answered with a real option list, not an empty or stub one.
    # Anchors rather than a count, because the count moves with Streamlit: the
    # declared floor 1.49.0 exposes exactly 100 of these variables and 1.67.0
    # exposes 360, so a threshold read off one version fails on another. These
    # two options have existed for as long as the CLI has.
    cli_env_vars = _streamlit_env_vars_read_by_the_cli()
    assert {"STREAMLIT_SERVER_PORT", "STREAMLIT_SERVER_HEADLESS"} <= cli_env_vars, (
        "the click command does not report the two most basic server options, "
        f"so the name check above would accept anything: {sorted(cli_env_vars)[:10]}"
    )
    assert len(cli_env_vars) >= 50, (
        f"the click command yielded only {len(cli_env_vars)} environment "
        "variables, so the name check above would accept almost anything"
    )


def test_the_document_harness_reads_real_tables_and_references():
    documented = _documented_table_variables()
    assert (
        len(documented) >= 20
    ), f"expected docs/docker.md to document many variables, found {documented}"

    needed = COMPOSE_INTERPOLATION.findall(COMPOSE_SAMPLE.read_text(encoding="utf-8"))
    assert len(set(needed)) >= 4, (
        f"expected the sample compose file to interpolate several variables, "
        f"found {needed}"
    )

    tags = _documented_image_tags()
    assert (
        "latest" in tags
    ), f"the tag scan did not even find :latest in the documents: {tags}"
    assert len(_published_tag_templates()) >= 4, (
        "fewer tag templates were derived from the workflows than the two of "
        "them declare"
    )

    assert _streamlit_variables_the_tree_sets(), (
        "the scan found no STREAMLIT_* variable set anywhere, so the name check "
        "above would pass on an empty set"
    )


if __name__ == "__main__":  # pragma: no cover - parity with the other modules
    pytest.main([__file__, "-v"])

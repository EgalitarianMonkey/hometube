"""Guards on the contract between the translation keys the application asks for
and the keys the language files define.

These are not characterisation tests. They pin a defect that was public and
silent, in the same family as the Makefile's catch-all, the deployment guide's
absent files and the unreachable environment variables: *a string that renders
something wrong instead of failing.*

``t()`` resolves a key against the active language and falls back to the literal
string ``[MISSING: <key>]`` when the key is absent. That fallback never raises,
never logs, and is indistinguishable from a working message until somebody looks
at the screen. Four call sites in ``app/main.py`` were in that state, and three
of them had been since the initial commit:

* ``status_command_success`` — written to the status box by ``run_cmd()`` after
  every command that exits 0, so it is what a user saw at the end of every
  successful download,
* ``status_command_failed`` and ``status_command_exception`` — the same box on
  the failure and exception paths,
* ``status_reusing_existing_file`` — shown when an already-downloaded file is
  reused instead of fetched again.

The first two tests close the loop in the direction that reaches users: a key
the application asks for must exist in *both* languages. The call sites are
found by walking the AST of every module under ``app/`` rather than by grepping,
so a key split across a concatenation or hidden in a comment cannot produce a
false result either way.

The next two pin the two dictionaries to each other — same keys, same
placeholders per key. Placeholder parity is the subtler of the pair: ``t()``
swallows a ``KeyError`` from ``str.format`` and returns the *unformatted*
template, so a key that says ``{count}`` in one language and ``{n}`` in the
other shows raw braces to half the users and nothing to the rest.

``test_a_call_site_supplies_every_placeholder_of_its_template`` checks the
remaining direction, and its exemption is derived from the implementation
instead of being listed by hand: ``t()`` calls ``str.format`` only when it
receives keyword arguments, so a call that passes none can neither raise nor
misrender, and the braces it displays are deliberate. ``playlist_title_pattern_help``
is exactly that case — help text whose whole purpose is to show ``{title}`` and
``{channel}`` to the reader.

The last three refuse to pass vacuously. Two check that the scanner still finds
what is known to be there — a substantial number of keys, and at least one in
every module that imports ``t`` — and one pins the ``[MISSING: ]`` fallback
itself, so the signature of the original defect cannot change without a test
saying so.
"""

import ast
import string
from pathlib import Path

import pytest

from app.translations import configure_language, t
from app.translations import en, fr

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "app"

EN = en.TRANSLATIONS
FR = fr.TRANSLATIONS

# The scan below is complete only because `t` is imported as a bare name
# (`from app.translations import t`) in every module that uses it, is never
# reached through an attribute, and is defined nowhere else in `app/`. The last
# two tests of this module are what keep that assumption honest.
TRANSLATE_FUNCTION = "t"


def _app_modules():
    """Every Python source under `app/`, excluding bytecode caches."""
    return sorted(p for p in APP_DIR.rglob("*.py") if "__pycache__" not in p.parts)


class _Call:
    """One `t(...)` call site: its key, its keyword arguments, its location."""

    def __init__(self, key, keywords, has_star_kwargs, path, lineno):
        self.key = key
        self.keywords = keywords
        self.has_star_kwargs = has_star_kwargs
        self.where = f"{path.relative_to(REPO_ROOT)}:{lineno}"


def _collect_calls():
    """Walk every module under `app/` and return its `t()` call sites.

    Returns `(literal_calls, dynamic_sites)`. A dynamic site is a `t()` call
    whose first argument is not a string literal; there are none today, and the
    vacuity guard below is what makes their appearance visible rather than
    silently shrinking what the first two tests check.
    """
    literal_calls = []
    dynamic_sites = []
    for path in _app_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id != TRANSLATE_FUNCTION or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                literal_calls.append(
                    _Call(
                        key=first.value,
                        keywords={kw.arg for kw in node.keywords if kw.arg is not None},
                        has_star_kwargs=any(kw.arg is None for kw in node.keywords),
                        path=path,
                        lineno=node.lineno,
                    )
                )
            else:
                dynamic_sites.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    return literal_calls, dynamic_sites


CALLS, DYNAMIC_SITES = _collect_calls()


def _placeholders(template):
    """The named fields of a format template, e.g. `{"time", "code"}`."""
    return {field for _, field, _, _ in string.Formatter().parse(template) if field}


@pytest.mark.parametrize("language,table", [("en", EN), ("fr", FR)])
def test_every_requested_key_exists_in_the_language(language, table):
    """A key the application asks for must be defined, or `t()` renders
    `[MISSING: <key>]` into the interface."""
    missing = sorted(
        {(call.key, call.where) for call in CALLS if call.key not in table}
    )
    assert not missing, (
        f"{len(missing)} t() call site(s) ask for a key absent from "
        f"app/translations/{language}.py, so the interface shows "
        f"'[MISSING: <key>]' instead of a message:\n"
        + "\n".join(f"  {key}  ({where})" for key, where in missing)
    )


def test_the_two_languages_define_the_same_keys():
    """Neither language may carry a key the other lacks: the missing side falls
    back to `[MISSING: <key>]` for its users only."""
    only_en = sorted(set(EN) - set(FR))
    only_fr = sorted(set(FR) - set(EN))
    assert not only_en and not only_fr, (
        "the two translation tables have diverged:\n"
        f"  only in en.py: {only_en}\n"
        f"  only in fr.py: {only_fr}"
    )


def test_a_key_uses_the_same_placeholders_in_both_languages():
    """`t()` swallows the `KeyError` from `str.format` and returns the raw
    template, so a placeholder renamed in one language shows braces to its
    users and nothing to the others."""
    divergent = {}
    for key in sorted(set(EN) & set(FR)):
        value_en, value_fr = EN[key], FR[key]
        if not isinstance(value_en, str) or not isinstance(value_fr, str):
            continue
        fields_en, fields_fr = _placeholders(value_en), _placeholders(value_fr)
        if fields_en != fields_fr:
            divergent[key] = (sorted(fields_en), sorted(fields_fr))
    assert (
        not divergent
    ), "these keys interpolate different names in the two languages:\n" + "\n".join(
        f"  {key}: en={fields_en} fr={fields_fr}"
        for key, (fields_en, fields_fr) in divergent.items()
    )


def test_a_call_site_supplies_every_placeholder_of_its_template():
    """A call that passes keyword arguments must cover every placeholder of the
    template in both languages.

    Calls that pass none are exempt by construction rather than by a list:
    `t()` reaches `str.format` only when `kwargs` is non-empty, so a
    keyword-less call cannot raise and the braces it shows are intended — which
    is what `playlist_title_pattern_help` relies on to document the pattern
    fields to the reader.
    """
    unmet = []
    for call in CALLS:
        if not call.keywords or call.has_star_kwargs:
            continue
        for language, table in (("en", EN), ("fr", FR)):
            template = table.get(call.key)
            if not isinstance(template, str):
                continue
            missing = _placeholders(template) - call.keywords
            if missing:
                unmet.append(
                    f"  {call.where}  {call.key} [{language}] never receives "
                    f"{sorted(missing)} (passes {sorted(call.keywords)})"
                )
    assert not unmet, (
        "these call sites leave a placeholder unfilled, so t() returns the "
        "template with its braces intact:\n" + "\n".join(unmet)
    )


def test_an_unknown_key_still_renders_the_missing_sentinel():
    """Pin the fallback that made the original defect invisible, so its shape
    cannot drift without this file being updated alongside."""
    configure_language("en")
    try:
        assert t("a_key_that_is_not_translated") == (
            "[MISSING: a_key_that_is_not_translated]"
        )
        # The sentinel survives formatting arguments, which is precisely why
        # `t("status_command_success", time=...)` looked harmless for so long.
        assert t("a_key_that_is_not_translated", time="00:00:01") == (
            "[MISSING: a_key_that_is_not_translated]"
        )
    finally:
        configure_language("en")


def test_the_scan_finds_the_call_sites_it_is_meant_to_check():
    """Without this, a change to `t`'s name or import style would empty `CALLS`
    and leave the tests above passing on nothing."""
    assert not DYNAMIC_SITES, (
        "t() is called with a non-literal key at these sites, which the checks "
        "above cannot see; they must be covered another way before this is "
        "relaxed:\n" + "\n".join(f"  {site}" for site in DYNAMIC_SITES)
    )
    distinct_keys = {call.key for call in CALLS}
    assert len(distinct_keys) > 200, (
        f"the AST scan found only {len(distinct_keys)} distinct translation "
        "keys in app/; it used to find well over 200, so it has stopped "
        "matching the call sites"
    )


def test_every_module_that_imports_the_translator_contributes_a_call():
    """A module that imports `t` and in which the scan sees no call means the
    scan, not the module, is wrong."""
    importers = set()
    for path in _app_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and ("translations" in node.module)
            ):
                if any(alias.name == TRANSLATE_FUNCTION for alias in node.names):
                    importers.add(path.relative_to(REPO_ROOT))
    scanned = {Path(call.where.rsplit(":", 1)[0]) for call in CALLS}
    assert importers, "no module under app/ imports t(); the scan has no subject"
    silent = sorted(str(module) for module in importers - scanned)
    assert not silent, (
        "these modules import t() but the scan found no call in them, so it is "
        "no longer matching the call syntax: " + ", ".join(silent)
    )

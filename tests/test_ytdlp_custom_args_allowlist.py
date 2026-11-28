"""Guards on the "Custom yt-dlp arguments" field, which used to be a shell.

``build_base_ytdlp_command()`` shlex-split whatever the user typed into that
field and appended it to yt-dlp's argv, with no allowlist and no denylist. The
reported proof of concept was ``--exec 'touch /tmp/testfile'``: the file
appeared when the download finished. The app serves 8501 with no authentication
of its own, so the field was reachable by anyone who could reach the interface,
and the commands ran as the process owner.

**The reported flag was the doorbell, not the hole.** yt-dlp's CLI contains
several independent routes to execution and to arbitrary file read and write,
and the field granted all of them. Measured on the code before the fix, each of
these reached argv:

* ``--exec`` and ``--exec-before-download`` — run a command, the reported one
* ``--downloader`` / ``--external-downloader`` — name an arbitrary program
* ``--postprocessor-args`` — inject arguments into the ffmpeg invocation
* ``--config-location`` — load an arbitrary file *as yt-dlp options*, which
  re-opens ``--exec`` from any file an attacker can first write
* ``--plugin-dirs`` — load arbitrary Python from a directory
* ``-o`` / ``--paths`` — arbitrary file write by path traversal, and note that
  overriding these was a *designed* use of the field: both were listed in
  ``resolve_ytdlp_argument_conflicts()``'s ``ARGS_WITH_VALUES`` precisely so a
  custom one would replace the base one
* ``--cookies-from-browser``, ``--batch-file``, ``--load-info-json`` —
  arbitrary file read, browser profiles included

That list is why a denylist would have been the wrong fix, and worse than no
fix: it would have converted a known hole into one believed closed. So the field
is an allowlist, and the test that matters most here is
``test_an_option_nobody_has_reviewed_is_refused`` — it is the one that still
holds after yt-dlp invents an option this file has never heard of.

The tests are organised as the fix is: one class per property. Every refusal
test below failed before the fix, by letting the argument through.
"""

from pathlib import Path

import pytest

from app.core import (
    ALLOWED_ARGS_WITH_VALUES,
    ALLOWED_BOOLEAN_ARGS,
    build_base_ytdlp_command,
    filter_allowed_ytdlp_args,
)

# The families from the advisory's table. Each entry is a payload a user could
# type into the field, and the option it must not deliver to yt-dlp.
EXECUTION_VECTORS = [
    pytest.param("--exec 'touch /tmp/testfile'", "--exec", id="exec-the-reported-one"),
    pytest.param(
        "--exec-before-download 'id'", "--exec-before-download", id="exec-before"
    ),
    pytest.param("--downloader /bin/sh", "--downloader", id="downloader"),
    pytest.param(
        "--external-downloader /bin/sh", "--external-downloader", id="external"
    ),
    pytest.param(
        "--downloader-args 'aria2c:--on-download-complete=/bin/sh'",
        "--downloader-args",
        id="downloader-args",
    ),
    pytest.param(
        "--postprocessor-args 'ffmpeg:-y /etc/passwd'",
        "--postprocessor-args",
        id="postprocessor-args",
    ),
    pytest.param("--ppa 'ffmpeg:-y /etc/passwd'", "--ppa", id="ppa"),
    pytest.param(
        "--config-location /data/videos/evil.conf",
        "--config-location",
        id="config-location-reopens-exec",
    ),
    pytest.param("--plugin-dirs /data/videos/plugins", "--plugin-dirs", id="plugins"),
]

FILE_VECTORS = [
    pytest.param("-o ../../../../tmp/owned.%(ext)s", "-o", id="output-traversal-short"),
    pytest.param(
        "--output ../../../../tmp/owned.%(ext)s", "--output", id="output-traversal-long"
    ),
    pytest.param("--paths home:/etc", "--paths", id="paths-redirect"),
    pytest.param("--cookies /etc/shadow", "--cookies", id="cookies-read"),
    pytest.param(
        "--cookies-from-browser chrome",
        "--cookies-from-browser",
        id="browser-profile-read",
    ),
    pytest.param("--batch-file /etc/passwd", "--batch-file", id="batch-file-read"),
    pytest.param(
        "--load-info-json /etc/passwd", "--load-info-json", id="load-info-json-read"
    ),
]


def command(custom_args: str) -> list[str]:
    """The real command builder, with the field's content as a user would type it."""
    return build_base_ytdlp_command(
        base_filename="video",
        temp_dir=Path("/tmp/hometube-workspace"),
        format_spec="bv*+ba/b",
        embed_chapters=False,
        embed_subs=False,
        custom_args=custom_args,
    )


@pytest.fixture
def logged(monkeypatch):
    """Collect what the builder reports to the user's download log."""
    messages: list[str] = []
    monkeypatch.setattr("app.logs_utils.safe_push_log", messages.append)
    return messages


@pytest.fixture
def unsafe_passthrough(monkeypatch):
    """Turn the documented escape hatch on, and make sure it goes off again."""
    from app.config import get_settings

    monkeypatch.setenv("YTDLP_UNSAFE_CUSTOM_ARGS", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestTheReportedHole:
    """The proof of concept from GHSA-cr4h-q4vm-2gmg, and its whole family."""

    @pytest.mark.parametrize("payload,option", EXECUTION_VECTORS)
    def test_an_option_that_runs_a_program_is_refused(self, payload, option):
        assert option not in command(payload)

    @pytest.mark.parametrize("payload,option", FILE_VECTORS)
    def test_an_option_that_reads_or_writes_a_path_is_refused(self, payload, option):
        """Counted rather than tested for absence, because of ``-o`` and ``--paths``.

        Those two are in the *base* command — the app sets its own output
        template and workspace — so "absent from argv" is the wrong assertion
        for them and would be unfalsifiable. What must hold is that the user's
        occurrence was not added to the app's own.
        """
        built = command(payload)
        assert built.count(option) == command("").count(option)

    @pytest.mark.parametrize(
        "payload,option", EXECUTION_VECTORS + FILE_VECTORS, ids=str
    )
    def test_the_value_does_not_reach_argv_either(self, payload, option):
        """Refusing the option and keeping its value would be no fix at all.

        A lone ``/bin/sh`` left in argv is a positional argument, which yt-dlp
        reads as a URL to download.
        """
        import shlex

        built = command(payload)
        for token in shlex.split(payload):
            assert token not in built or token in command(""), (
                f"{token!r} from {payload!r} survived into the command; "
                "the option and its value must be refused together"
            )

    def test_the_output_target_stays_the_workspace_the_app_chose(self):
        """-o is the one refusal with a second half worth asserting.

        Overriding ``-o`` used to be supported, so refusing it must not leave
        the command with no output template at all.
        """
        built = command("-o ../../../../tmp/owned.%(ext)s")
        assert built.count("-o") == 1
        assert built[built.index("-o") + 1] == "video.%(ext)s"
        assert "../../../../tmp/owned.%(ext)s" not in built


class TestTheAllowlistIsClosed:
    """The property that survives yt-dlp adding options this file never saw."""

    def test_an_option_nobody_has_reviewed_is_refused(self):
        """The default is refuse. This is the test the whole fix rests on."""
        assert "--totally-new-option" not in command("--totally-new-option value")

    def test_a_bare_token_is_refused(self):
        """To yt-dlp a positional argument is another URL to download."""
        built = command("https://evil.example/video")
        assert "https://evil.example/video" not in built

    def test_a_value_that_looks_like_an_option_is_refused_with_its_option(self):
        """``--proxy --exec`` would otherwise be accepted whole.

        yt-dlp's parser would consume ``--exec`` as the proxy's value, so the
        pair is harmless in itself — but accepting it means the accepted list
        can contain a token nobody reviewed, and that property is worth more
        than the one payload.
        """
        built = command("--proxy --exec")
        assert "--exec" not in built
        assert "--proxy" not in built

    def test_a_dangling_option_is_refused(self):
        assert "--proxy" not in command("--proxy")

    def test_the_allowlist_names_nothing_from_the_dangerous_family(self):
        """Guard on the guard: the lists themselves must stay clean.

        Prefix matching, so ``--exec-before-download`` and
        ``--external-downloader-args`` are caught by their stems.
        """
        forbidden_stems = (
            "--exec",
            "--downloader",
            "--external-downloader",
            "--postprocessor-args",
            "--ppa",
            "--config-location",
            "--plugin-dirs",
            "--cookies",
            "--batch-file",
            "--load-info-json",
            "-o",
            "--output",
            "--paths",
        )
        for option in ALLOWED_ARGS_WITH_VALUES | ALLOWED_BOOLEAN_ARGS:
            assert not option.startswith(forbidden_stems), (
                f"{option} is on the allowlist and names a program, a path or a "
                "file of options"
            )

    def test_the_refusal_tests_are_not_passing_on_an_empty_allowlist(self):
        """Refuse-everything would pass every test above and ship a broken field."""
        assert len(ALLOWED_ARGS_WITH_VALUES) > 10
        assert len(ALLOWED_BOOLEAN_ARGS) > 10


class TestWhatTheFieldStillDoes:
    """A fix that breaks the documented uses is a fix that gets reverted."""

    def test_the_two_examples_the_interface_advertises_still_work(self):
        """app/translations/en.py:150 promises exactly these two."""
        built = command("--proxy socks5://127.0.0.1:1080 --max-filesize 500M")
        assert built[built.index("--proxy") + 1] == "socks5://127.0.0.1:1080"
        assert built[built.index("--max-filesize") + 1] == "500M"

    def test_the_example_env_sample_ships_still_works(self):
        """.env.sample offers `--max-filesize 100M --write-info-json`."""
        built = command("--max-filesize 100M --write-info-json")
        assert built[built.index("--max-filesize") + 1] == "100M"
        assert "--write-info-json" in built

    def test_a_quoted_value_survives_as_one_token(self):
        built = command('--user-agent "Mozilla/5.0 (X11; Linux x86_64)"')
        assert (
            built[built.index("--user-agent") + 1] == "Mozilla/5.0 (X11; Linux x86_64)"
        )

    def test_the_accepted_arguments_keep_the_order_they_were_written_in(self):
        accepted, refused = filter_allowed_ytdlp_args(
            ["--retries", "3", "--exec", "id", "--limit-rate", "1M"]
        )
        assert accepted == ["--retries", "3", "--limit-rate", "1M"]
        assert refused == ["--exec", "id"]

    @pytest.mark.parametrize(
        "option",
        sorted(
            option
            for option in ALLOWED_ARGS_WITH_VALUES
            if option
            in build_base_ytdlp_command(
                "video",
                Path("/tmp/hometube-workspace"),
                "bv*+ba/b",
                False,
                False,
            )
        ),
    )
    def test_overriding_a_base_option_replaces_it_rather_than_duplicating_it(
        self, option
    ):
        """Derived from the base command, so it cannot go stale.

        Every allowlisted option the base command also sets must still be
        overridable: that is what ``resolve_ytdlp_argument_conflicts()`` is
        for, and the allowlist must not have put an option out of its reach.
        """
        built = command(f"{option} 7")
        assert built.count(option) == 1, f"{option} appears twice"
        assert built[built.index(option) + 1] == "7"

    def test_the_boolean_flags_still_toggle_their_base_counterpart(self):
        built = command("--embed-chapters")
        assert "--no-embed-chapters" not in built
        assert "--embed-chapters" in built


class TestTheUserIsTold:
    """A refused flag that fails silently reads as "this field does nothing"."""

    def test_a_refusal_is_logged_with_the_tokens_it_refused(self, logged):
        command("--exec 'touch /tmp/testfile'")
        assert logged, "a refused argument must not be silent"
        assert "--exec" in logged[0]

    def test_the_refusal_says_how_to_opt_out(self, logged):
        command("--exec id")
        assert "YTDLP_UNSAFE_CUSTOM_ARGS" in logged[0]

    def test_an_accepted_argument_is_not_reported_as_refused(self, logged):
        command("--max-filesize 500M")
        assert logged == []

    def test_an_unbalanced_quote_is_no_longer_silent(self, logged):
        """It used to drop the whole field and return the base command."""
        built = command("--max-filesize '500M")
        assert built == command("")
        assert logged, "a field that could not be parsed must say so"
        assert "quote" in logged[0].lower()


class TestTheEscapeHatch:
    """Off by default, documented for what it is, and loud when on."""

    def test_it_is_off_by_default(self):
        from app.config import get_settings

        get_settings.cache_clear()
        assert get_settings().YTDLP_UNSAFE_CUSTOM_ARGS is False

    def test_the_default_is_what_makes_the_refusal_tests_meaningful(self):
        """Guard on the guard: every test above runs with the hatch off."""
        from app.core import unsafe_custom_args_enabled
        from app.config import get_settings

        get_settings.cache_clear()
        assert unsafe_custom_args_enabled() is False

    def test_with_it_on_the_old_behaviour_is_restored(self, unsafe_passthrough):
        """Deliberate: this is the operator's informed opt-out, not a bypass."""
        built = command("--exec 'touch /tmp/testfile'")
        assert "--exec" in built
        assert "touch /tmp/testfile" in built

    def test_turning_it_on_is_announced_on_every_download(
        self, unsafe_passthrough, logged
    ):
        command("--exec id")
        assert logged, "the unchecked state must never be quiet"
        assert "YTDLP_UNSAFE_CUSTOM_ARGS" in logged[0]

    @pytest.mark.parametrize("value", ["false", "", "0", "no", "off", "maybe"])
    def test_only_an_affirmative_value_turns_it_on(self, monkeypatch, value):
        from app.config import get_settings

        monkeypatch.setenv("YTDLP_UNSAFE_CUSTOM_ARGS", value)
        get_settings.cache_clear()
        try:
            assert get_settings().YTDLP_UNSAFE_CUSTOM_ARGS is False
            assert "--exec" not in command("--exec id")
        finally:
            get_settings.cache_clear()


class TestTheOperatorsOwnConfiguration:
    """YTDLP_CUSTOM_ARGS is the same field, pre-filled from the compose file.

    It is not an attack path — it is the operator's own file — but it goes
    through the same validation, deliberately: two code paths for one field is
    how one of them rots. The consequence is that an operator who had ``--exec``
    in their compose file sees it refused after upgrading, with the log line
    naming the hatch. That is the behaviour change, and it is the point.
    """

    def test_the_env_var_is_screened_by_the_same_allowlist(self, monkeypatch):
        from app.config import get_settings

        monkeypatch.setenv("YTDLP_CUSTOM_ARGS", "--exec id --max-filesize 100M")
        get_settings.cache_clear()
        try:
            settings = get_settings()
            built = command(settings.YTDLP_CUSTOM_ARGS)
            assert "--exec" not in built
            assert built[built.index("--max-filesize") + 1] == "100M"
        finally:
            get_settings.cache_clear()

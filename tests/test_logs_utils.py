"""Tests for logging helpers."""

from app.logs_utils import (
    DOWNLOAD_BUTTON_REFRESH_EVERY,
    LOG_TRUNCATION_MARKER,
    MAX_LOG_LINES,
    next_download_button_key,
    sanitize_log_line,
    should_refresh_download_button,
    trim_log_buffer,
)


class TestDownloadButtonKey:
    """Keys for the "download logs" button.

    Reproduces issue #123: the key used to be built from len(ALL_LOGS), which
    stops changing once the buffer hits MAX_LOG_LINES, so a second render in the
    same script run reused a key Streamlit had already registered and raised
    StreamlitDuplicateElementKey — killing the download in progress.
    """

    def test_consecutive_renders_get_different_keys(self):
        keys = [next_download_button_key(2) for _ in range(5)]

        assert len(set(keys)) == 5, keys

    def test_key_does_not_depend_on_the_log_count(self):
        """The saturated-buffer case: nothing about the logs feeds the key.

        A capped counter is exactly what broke before, so the key must be
        derived from something that cannot plateau.
        """
        before = next_download_button_key(7)
        after = next_download_button_key(7)

        assert before != after

    def test_key_carries_the_run_sequence(self):
        """Runs stay distinguishable, as they were with the old scheme."""
        key = next_download_button_key(42)

        assert key.startswith("download_logs_btn_42_")

    def test_keys_stay_unique_across_runs(self):
        first_run = [next_download_button_key(1) for _ in range(3)]
        second_run = [next_download_button_key(2) for _ in range(3)]

        assert len(set(first_run + second_run)) == 6


class TestLogBufferCap:
    """The bounded log buffer, reproducing issue #82.

    Dailymotion streams in small HLS fragments and yt-dlp emits one progress
    line per fragment, so an unbounded buffer grew for the whole download until
    the machine became unresponsive. The cap is what keeps memory flat, and
    nothing pinned it before these tests.
    """

    def test_buffer_stays_capped_under_a_fragment_flood(self):
        logs = []
        for i in range(MAX_LOG_LINES * 3):
            logs.append(f"[download] fragment {i}")
            trim_log_buffer(logs)

            assert len(logs) <= MAX_LOG_LINES

    def test_untrimmed_buffer_is_left_alone(self):
        logs = [f"line {i}" for i in range(10)]

        trim_log_buffer(logs)

        assert logs == [f"line {i}" for i in range(10)]

    def test_oldest_lines_go_first_and_the_newest_survive(self):
        logs = [f"line {i}" for i in range(MAX_LOG_LINES + 500)]

        trim_log_buffer(logs)

        assert len(logs) == MAX_LOG_LINES
        assert logs[-1] == f"line {MAX_LOG_LINES + 499}"
        assert logs[0] == LOG_TRUNCATION_MARKER

    def test_truncation_is_announced_rather_than_silent(self):
        logs = [f"line {i}" for i in range(MAX_LOG_LINES + 1)]

        trim_log_buffer(logs)

        assert LOG_TRUNCATION_MARKER in logs

    def test_trimming_mutates_in_place(self):
        """main.py's ALL_LOGS is held by reference elsewhere (it is .clear()ed).

        A version that rebound the name instead of mutating would leave those
        references pointing at the unbounded list, and the cap would silently
        stop applying.
        """
        logs = [f"line {i}" for i in range(MAX_LOG_LINES + 5)]
        same_list = logs

        returned = trim_log_buffer(logs)

        assert returned is logs
        assert same_list is logs
        assert len(same_list) == MAX_LOG_LINES


class TestDownloadButtonRefreshThrottle:
    """Throttling the download-button payload, the other half of issue #82.

    Every refresh copies the whole buffer into a widget payload Streamlit keeps
    until the end of the run, so refreshing on each progress line made memory
    grow quadratically with download progress.
    """

    def test_progress_lines_do_not_refresh_on_every_line(self):
        refreshes = sum(
            should_refresh_download_button("[download]   1.0% of 40MiB", count)
            for count in range(1, 1001)
        )

        assert refreshes == 1000 // DOWNLOAD_BUTTON_REFRESH_EVERY

    def test_ordinary_lines_always_refresh(self):
        for line in ("✅ Title retrieved", "[youtube] Extracting URL", "ERROR: boom"):
            assert should_refresh_download_button(line, 7) is True

    def test_every_known_progress_prefix_is_throttled(self):
        """yt-dlp emits "[download]", ffmpeg emits "frame=" and "size=" ."""
        for line in ("[download] 50%", "frame=  120 fps=30", "size=   4096kB"):
            assert should_refresh_download_button(line, 7) is False

    def test_progress_lines_still_refresh_periodically(self):
        """Throttled is not never: the button must stay usable mid-download."""
        assert (
            should_refresh_download_button(
                "[download] 50%", DOWNLOAD_BUTTON_REFRESH_EVERY
            )
            is True
        )


class TestSanitizeLogLine:
    """Lines reach the log window as raw yt-dlp/ffmpeg output."""

    def test_ansi_colour_codes_are_stripped(self):
        assert sanitize_log_line("\x1b[0;32mdone\x1b[0m") == "done"

    def test_trailing_newline_is_dropped(self):
        assert sanitize_log_line("downloading\n") == "downloading"

    def test_control_characters_are_removed(self):
        assert sanitize_log_line("a\x00b\x07c") == "abc"

    def test_tabs_survive(self):
        assert sanitize_log_line("col\tcol") == "col\tcol"

    def test_unicode_is_untouched(self):
        """Titles and HomeTube's own log lines are full of accents and emoji."""
        assert sanitize_log_line("✅ Arrêtons Mélenchon") == "✅ Arrêtons Mélenchon"

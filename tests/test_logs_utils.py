"""Tests for logging helpers."""

from app.logs_utils import next_download_button_key


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

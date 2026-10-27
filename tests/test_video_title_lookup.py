"""Tests for the url_info.json title lookup.

The analysis step writes url_info.json inside a per-URL workspace
(``<TMP>/videos/<platform>/<id>/url_info.json``), while
``get_video_title_from_json()`` defaults to ``<TMP>/url_info.json``. A caller
that omits the path therefore never finds the file, silently falls back to a
yt-dlp network call, and logs "url_info.json not found" right after a
successful analysis. These tests pin the path that is actually written and the
callers that have to pass it.
"""

import ast
import json
from pathlib import Path

from app.medias_utils import get_video_title, get_video_title_from_json
from app.workspace import ensure_workspace_from_url

VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
MAIN_PY = Path(__file__).resolve().parents[1] / "app" / "main.py"


def _write_url_info(workspace: Path, title: str) -> Path:
    """Write a minimal url_info.json the way url_analysis() does."""
    json_path = workspace / "url_info.json"
    json_path.write_text(
        json.dumps({"title": title, "_type": "video"}), encoding="utf-8"
    )
    return json_path


class TestTitleFromWorkspaceJson:
    """The title must come from the workspace file, with no network call."""

    def test_reads_title_from_workspace_path(self, tmp_path):
        """An explicit workspace path yields the stored title."""
        workspace, _ = ensure_workspace_from_url(tmp_path, VIDEO_URL)
        _write_url_info(workspace, "A Real Title")

        assert get_video_title_from_json(workspace / "url_info.json") == "A Real Title"

    def test_get_video_title_uses_json_and_skips_ytdlp(self, tmp_path, monkeypatch):
        """With json_path given, no yt-dlp subprocess is spawned."""
        workspace, _ = ensure_workspace_from_url(tmp_path, VIDEO_URL)
        _write_url_info(workspace, "A Real Title")

        def _fail(*args, **kwargs):
            raise AssertionError("yt-dlp was called although url_info.json existed")

        monkeypatch.setattr("subprocess.run", _fail)

        title = get_video_title(VIDEO_URL, json_path=workspace / "url_info.json")
        assert title == "A Real Title"

    def test_workspace_json_is_not_at_tmp_root(self, tmp_path):
        """The regression itself: the default lookup path is never written.

        ``get_video_title_from_json()`` defaults to ``<TMP>/url_info.json``.
        The analysis writes into a per-URL subdirectory, so the default can
        only ever miss — which is why callers must pass the workspace path.
        """
        workspace, _ = ensure_workspace_from_url(tmp_path, VIDEO_URL)
        _write_url_info(workspace, "A Real Title")

        assert workspace != tmp_path
        assert not (tmp_path / "url_info.json").exists()


class TestMainPassesJsonPath:
    """Every get_video_title() call in main.py must pass json_path."""

    def test_all_call_sites_pass_json_path(self):
        tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))

        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "get_video_title"
        ]

        assert calls, "no get_video_title() call found in app/main.py"

        missing = [
            node.lineno
            for node in calls
            if not any(kw.arg == "json_path" for kw in node.keywords)
            and len(node.args) < 3
        ]

        assert not missing, (
            "get_video_title() called without json_path at "
            f"app/main.py:{missing} — it would look in the TMP root, where no "
            "url_info.json is ever written, and fall back to a yt-dlp call."
        )

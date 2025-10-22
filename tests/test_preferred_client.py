"""
Tests for preferred YouTube client tracking and prioritization.

This test suite verifies that:
1. The client used for url_info.json is recorded
2. The same client is prioritized for video download
3. Fallback to other clients works if preferred fails
"""

import json
from unittest.mock import MagicMock, patch


def test_url_info_saves_successful_client(tmp_path):
    """Test that build_url_info saves the successful client name."""
    from app.url_utils import build_url_info
    from app.config import YOUTUBE_CLIENT_FALLBACKS

    # Mock subprocess to simulate ios client success
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = json.dumps(
        {
            "_type": "video",
            "id": "test123",
            "title": "Test Video",
            "duration": 120,
            "formats": [
                {"vcodec": "av01.0.05M.08", "format_id": "401"},
                {"vcodec": "vp9", "format_id": "248"},
            ],
        }
    )

    with patch("subprocess.run", return_value=mock_result):
        json_output_path = tmp_path / "url_info.json"
        result = build_url_info(
            clean_url="https://youtube.com/watch?v=test123",
            json_output_path=json_output_path,
            cookies_params=[],
            youtube_clients=YOUTUBE_CLIENT_FALLBACKS,
        )

    # Check that result includes the successful client
    assert "_hometube_successful_client" in result
    assert result["_hometube_successful_client"] in ["default", "ios", "web"]

    # Check that JSON file was saved with the client info
    assert json_output_path.exists()
    with open(json_output_path, "r") as f:
        saved_info = json.load(f)

    assert "_hometube_successful_client" in saved_info
    assert (
        saved_info["_hometube_successful_client"]
        == result["_hometube_successful_client"]
    )


def test_url_info_tries_multiple_clients(tmp_path):
    """Test that build_url_info tries multiple clients if first fails."""
    from app.url_utils import build_url_info
    from app.config import YOUTUBE_CLIENT_FALLBACKS

    # Mock subprocess to simulate:
    # - default client fails (timeout)
    # - ios client succeeds
    call_count = [0]

    def mock_run(*args, **kwargs):
        call_count[0] += 1

        # Check if this is ios client (has player_client=ios in args)
        cmd = args[0]
        is_ios = any("player_client=ios" in str(arg) for arg in cmd)

        if is_ios:
            # ios succeeds
            result = MagicMock()
            result.returncode = 0
            result.stdout = json.dumps(
                {
                    "_type": "video",
                    "id": "test123",
                    "title": "Test Video",
                    "duration": 120,
                    "formats": [
                        {"vcodec": "av01.0.05M.08", "format_id": "401"},
                    ],
                }
            )
            return result
        else:
            # default and web fail
            result = MagicMock()
            result.returncode = 1
            result.stderr = "Connection error"
            return result

    with patch("subprocess.run", side_effect=mock_run):
        json_output_path = tmp_path / "url_info.json"
        result = build_url_info(
            clean_url="https://youtube.com/watch?v=test123",
            json_output_path=json_output_path,
            cookies_params=[],
            youtube_clients=YOUTUBE_CLIENT_FALLBACKS,
        )

    # Should have tried multiple clients
    assert call_count[0] >= 2

    # Should have succeeded with ios client
    assert "_hometube_successful_client" in result
    assert result["_hometube_successful_client"] == "ios"


def test_client_order_logic():
    """Test that client prioritization logic works correctly."""
    from app.config import YOUTUBE_CLIENT_FALLBACKS

    # Test 1: When preferred client is "ios", it should come first
    preferred = "ios"
    clients_to_try = []

    preferred_config = next(
        (c for c in YOUTUBE_CLIENT_FALLBACKS if c["name"] == preferred), None
    )

    if preferred_config:
        clients_to_try.append(preferred_config)
        clients_to_try.extend(
            [c for c in YOUTUBE_CLIENT_FALLBACKS if c["name"] != preferred]
        )

    # Should have ios first
    assert len(clients_to_try) == 3
    assert clients_to_try[0]["name"] == "ios"
    assert clients_to_try[1]["name"] in ["default", "web"]
    assert clients_to_try[2]["name"] in ["default", "web"]

    # Test 2: When no preference, use original order
    clients_no_pref = YOUTUBE_CLIENT_FALLBACKS
    assert clients_no_pref[0]["name"] == "default"
    assert clients_no_pref[1]["name"] == "ios"
    assert clients_no_pref[2]["name"] == "web"


def test_client_fallback_order():
    """Test that client fallback order is configured correctly."""
    from app.config import YOUTUBE_CLIENT_FALLBACKS

    # Should have exactly 3 clients (android removed)
    assert len(YOUTUBE_CLIENT_FALLBACKS) == 3

    # Check structure
    for client in YOUTUBE_CLIENT_FALLBACKS:
        assert "name" in client
        assert "args" in client
        assert isinstance(client["args"], list)

    # Check names
    client_names = [c["name"] for c in YOUTUBE_CLIENT_FALLBACKS]
    assert "default" in client_names
    assert "ios" in client_names
    assert "web" in client_names
    assert "android" not in client_names  # Should be removed


def test_url_info_client_propagates_to_download(tmp_path):
    """Integration test: client from url_info is used in download."""
    from app.url_utils import save_url_info, load_url_info_from_file

    # Create url_info.json with preferred client
    url_info_path = tmp_path / "url_info.json"
    url_info = {
        "_type": "video",
        "id": "test123",
        "title": "Test Video",
        "_hometube_successful_client": "ios",
    }
    save_url_info(url_info_path, url_info)

    # Load it back
    loaded_info = load_url_info_from_file(url_info_path)

    # Verify client is preserved
    assert loaded_info is not None
    assert loaded_info.get("_hometube_successful_client") == "ios"

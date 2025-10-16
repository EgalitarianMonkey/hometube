"""
Tests for yt-dlp version detection using crane.

Simple, focused tests that validate version coherence between
upstream (jauderho/yt-dlp) and HomeTube images.

These tests gracefully skip if:
- crane is not installed
- Network is unavailable
- Images don't exist yet (before release)
"""

import json
import pytest
import shutil
import subprocess
from typing import Optional


def get_crane_path() -> Optional[str]:
    """Check if crane is available in PATH."""
    return shutil.which("crane")


def get_image_label(image: str, label: str, use_docker: bool = False) -> Optional[str]:
    """
    Get a label value from an OCI image using crane or docker inspect.

    Args:
        image: Image reference (e.g., "jauderho/yt-dlp:latest")
        label: Label key to retrieve (e.g., "org.opencontainers.image.version")
        use_docker: If True, use docker inspect instead of crane (for local images)

    Returns:
        Label value or None if not found or tool not available
    """
    if use_docker:
        # Use docker inspect for local images
        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    image,
                    "--format",
                    f'{{{{index .Config.Labels "{label}"}}}}',
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            value = result.stdout.strip()
            return value if value and value != "<no value>" else None
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
            FileNotFoundError,
        ):
            return None

    # Use crane for remote images
    crane_path = get_crane_path()
    if not crane_path:
        return None

    try:
        # Get image config as JSON
        result = subprocess.run(
            [crane_path, "config", image],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )

        config = json.loads(result.stdout)
        labels = config.get("config", {}).get("Labels", {})
        return labels.get(label)

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        json.JSONDecodeError,
        KeyError,
    ):
        return None


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.

    Args:
        v1: First version (e.g., "2025.10.14")
        v2: Second version (e.g., "2025.10.15")

    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """
    # Split versions into components
    parts1 = [int(x) for x in v1.split(".")]
    parts2 = [int(x) for x in v2.split(".")]

    # Pad shorter version with zeros
    max_len = max(len(parts1), len(parts2))
    parts1 += [0] * (max_len - len(parts1))
    parts2 += [0] * (max_len - len(parts2))

    # Compare component by component
    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1

    return 0


@pytest.mark.unit
class TestVersionComparisonLogic:
    """Unit tests for version comparison logic (no dependencies needed)."""

    def test_simple_versions(self):
        """Test simple version comparisons."""
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("1.0.1", "1.0.0") == 1
        assert compare_versions("1.0.0", "1.0.1") == -1

    def test_multi_digit_components(self):
        """Test versions with multi-digit components."""
        assert compare_versions("2025.12.31", "2025.12.30") == 1
        assert compare_versions("2025.12.31", "2025.11.30") == 1
        assert compare_versions("2024.12.31", "2025.1.1") == -1

    def test_realistic_ytdlp_versions(self):
        """Test with realistic yt-dlp version strings."""
        assert compare_versions("2025.10.14", "2025.10.13") == 1
        assert compare_versions("2025.10.14", "2025.10.14") == 0
        assert compare_versions("2025.10.14", "2025.10.15") == -1

        # Cross month boundary
        assert compare_versions("2025.11.1", "2025.10.31") == 1

        # Cross year boundary
        assert compare_versions("2026.1.1", "2025.12.31") == 1

    def test_version_comparison_padding(self):
        """Test version comparison handles different component counts."""
        # Should treat missing components as 0
        assert compare_versions("2025.10", "2025.10.0") == 0
        assert compare_versions("2025", "2025.0.0") == 0


@pytest.mark.network
class TestVersionCoherence:
    """
    Simple coherence tests for version detection.

    These tests skip gracefully if crane is not available or if
    labels don't exist yet (expected before next release).
    """

    def test_upstream_ytdlp_version_readable(self):
        """Test that we can read yt-dlp version from jauderho/yt-dlp."""
        if get_crane_path() is None:
            pytest.skip("crane not available - install with: brew install crane")

        version = get_image_label(
            "jauderho/yt-dlp:latest", "org.opencontainers.image.version"
        )

        if version is None:
            pytest.skip("Could not fetch upstream version (network or crane issue)")

        # Validate format
        parts = version.split(".")
        assert len(parts) == 3, f"Invalid version format: {version}"

        year, month, day = [int(p) for p in parts]
        assert 2020 <= year <= 2030, f"Year out of range: {year}"
        assert 1 <= month <= 12, f"Month out of range: {month}"
        assert 1 <= day <= 31, f"Day out of range: {day}"

        print(f"\n✅ Upstream yt-dlp: {version}")

    def test_hometube_version_coherence(self):
        """
        Test coherence between upstream yt-dlp and HomeTube versions.

        This is the main test - verifies that both versions can be read
        and that they are coherent (HomeTube <= upstream).
        """
        if get_crane_path() is None:
            pytest.skip("crane not available - install with: brew install crane")

        # Get upstream version
        upstream = get_image_label(
            "jauderho/yt-dlp:latest", "org.opencontainers.image.version"
        )

        if upstream is None:
            pytest.skip("Could not fetch upstream version (network or crane issue)")

        # Get HomeTube version
        hometube = get_image_label(
            "ghcr.io/egalitarianmonkey/hometube:latest", "io.hometube.ytdlp.version"
        )

        if hometube is None:
            pytest.skip(
                "Label io.hometube.ytdlp.version not found. "
                "Expected before next release (after 2025-10-16)."
            )

        print("\n📊 Version comparison:")
        print(f"   Upstream yt-dlp:  {upstream}")
        print(f"   HomeTube:         {hometube}")

        # Compare versions
        comparison = compare_versions(upstream, hometube)

        if comparison > 0:
            # Upstream is newer - this is acceptable
            days_behind = 0
            try:
                from datetime import date

                up_parts = [int(p) for p in upstream.split(".")]
                ht_parts = [int(p) for p in hometube.split(".")]

                up_date = date(up_parts[0], up_parts[1], up_parts[2])
                ht_date = date(ht_parts[0], ht_parts[1], ht_parts[2])

                days_behind = (up_date - ht_date).days
            except Exception:
                pass

            print(f"   Status:           HomeTube is behind ({days_behind} days)")
            print("   This is normal - will catch up on next automatic update")

            # Warn if too far behind (> 30 days)
            if days_behind > 30:
                print(
                    f"   ⚠️  WARNING: {days_behind} days behind - check if automatic updates are working"
                )

        elif comparison == 0:
            # Same version - perfect!
            print("   Status:           ✅ Up to date")
        else:
            # HomeTube is newer - this should not happen
            pytest.fail(
                f"HomeTube version ({hometube}) is newer than upstream ({upstream}). "
                "This indicates a configuration error."
            )

    def test_local_build_has_version_label(self):
        """Test that locally built image has the version label."""
        # Try common image names
        for image in ["hometube-hometube:latest", "hometube:latest"]:
            version = get_image_label(
                image, "io.hometube.ytdlp.version", use_docker=True
            )
            if version:
                # Validate format
                parts = version.split(".")
                assert len(parts) == 3, f"Invalid version format: {version}"

                print(f"\n✅ Local build has version: {version}")
                return

        pytest.skip("No local HomeTube image found. Run 'make docker-build' first.")

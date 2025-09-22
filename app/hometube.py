#!/usr/bin/env python3
"""
Main module for the hometube application
Can be imported as a Python module for programmatic usage
"""

import os
import subprocess
from pathlib import Path


def setup_environment():
    """Configure the environment for the application"""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent

    # Load .env file
    env_file = script_dir / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")
                    if key not in os.environ:
                        os.environ[key] = value


def run_app(port=8502, debug=False):
    """
    Lance l'application Streamlit

    Args:
        port (int): Port sur lequel lancer l'application
        debug (bool): Mode debug
    """
    import sys

    setup_environment()

    app_file = Path(__file__).parent / "app" / "main.py"

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.port",
        str(port),
        "--server.headless",
        "true" if not debug else "false",
        "--browser.gatherUsageStats",
        "false",
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Application stopped")


def download_video(url, filename, **options):
    """
    Function to download a video directly (programmatic usage)

    Args:
        url (str): Video URL
        filename (str): Output filename
        **options: Additional options

    Returns:
        bool: True if success, False otherwise
    """
    setup_environment()

    # Import necessary modules
    from app.main import sanitize_url, ensure_dir
    import subprocess

    try:
        # Basic configuration
        videos_folder = Path(os.getenv("VIDEOS_FOLDER", str(Path.home() / "Downloads")))
        ensure_dir(videos_folder)

        clean_url = sanitize_url(url)

        # Basic yt-dlp command
        cmd = [
            "yt-dlp",
            "-o",
            str(videos_folder / f"{filename}.%(ext)s"),
            "--merge-output-format",
            "mp4",
            clean_url,
        ]

        print(f"📥 Downloading: {url}")
        print(f"📁 Destination: {videos_folder / filename}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Download successful!")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    # If the script is run directly, launch the Streamlit interface
    run_app()

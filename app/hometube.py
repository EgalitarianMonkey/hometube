#!/usr/bin/env python3
"""
Main module for the hometube application
Can be imported as a Python module for programmatic usage
"""

import os
import subprocess
from pathlib import Path

# The port docker-compose.yml.sample publishes by default, kept in step with it
# deliberately: "${PORT:-8501}:8501".
DEFAULT_PORT = "8501"


def setup_environment():
    """Configure the environment for the application"""
    # This module lives in app/, so the project root — where .env sits — is one
    # level up. Same expression as app/config.py's early .env loading.
    project_root = Path(__file__).resolve().parent.parent

    # Load .env file
    env_file = project_root / ".env"
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


def run_app(port=None, debug=False):
    """
    Lance l'application Streamlit

    Args:
        port (int): Port sur lequel lancer l'application. Par défaut, PORT puis
            le 8501 que docker-compose.yml.sample publie.
        debug (bool): Mode debug

    Returns:
        int: le code de retour de Streamlit, 0 si le lancement a réussi
    """
    import sys

    setup_environment()

    # setup_environment() has just loaded .env, so PORT is readable here.
    if port is None:
        port = os.environ.get("PORT", "").strip() or DEFAULT_PORT

    # main.py sits next to this module, both inside app/.
    app_file = Path(__file__).resolve().parent / "main.py"

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

    # The return code is propagated rather than discarded: Streamlit exits
    # non-zero when it cannot start at all (a missing target, a taken port), and
    # a launcher that swallows that reports success having launched nothing.
    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
        return 0


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
    from app.medias_utils import sanitize_url
    from app.file_system_utils import ensure_dir
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
    # If the script is run directly, launch the Streamlit interface. Exit with
    # Streamlit's own code so a failed launch is a failed command.
    import sys

    sys.exit(run_app())

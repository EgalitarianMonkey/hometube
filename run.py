#!/usr/bin/env python3
"""
Simple launcher script for the hometube application
Usage: python run.py
"""

import os
import sys
import subprocess
from pathlib import Path

# The port docker-compose.yml.sample publishes by default, kept in step with it
# deliberately: "${PORT:-8501}:8501".
DEFAULT_PORT = "8501"


def read_port_from_env_file(env_file):
    """Return the PORT value set in a .env file, or None if it sets none.

    Deliberately a plain scan rather than a dotenv dependency: run.py has to
    work before anything is installed, so it may not import from the project.
    """
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("PORT="):
            continue
        value = line.split("=", 1)[1].split("#", 1)[0].strip().strip("\"'")
        if value:
            return value
    return None


def main():
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    app_file = script_dir / "app" / "main.py"

    if not app_file.exists():
        print("❌ Error: app/main.py file not found!")
        sys.exit(1)

    # Check if streamlit is installed
    try:
        import streamlit

        print("✅ Streamlit found!")
    except ImportError:
        print("❌ Streamlit is not installed!")
        print("   Install it with: pip install streamlit")
        sys.exit(1)

    # Check if yt-dlp is installed
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        print("✅ yt-dlp found!")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ yt-dlp is not installed or not in PATH!")
        print("   Install it with: pip install yt-dlp")
        sys.exit(1)

    # Resolve the port from PORT, the one port variable this project documents:
    # .env.sample ships it, docs/installation.md describes it, and
    # docker-compose.yml.sample publishes "${PORT:-8501}:8501" with it. The
    # default below is that same 8501, so a local run and a container answer on
    # the same port unless the user says otherwise.
    #
    # An explicit environment variable wins over the file, which is how
    # app/config.py behaves too (it calls load_dotenv with override=False).
    env_file = script_dir / ".env"
    port = DEFAULT_PORT

    if env_file.exists():
        print(f"✅ .env file found: {env_file}")
        port = read_port_from_env_file(env_file) or port
    else:
        print("⚠️  .env file not found, using default values")

    port = os.environ.get("PORT", "").strip() or port

    print(f"🚀 Starting application on port {port}")
    print(f"🌐 Open your browser at: http://localhost:{port}")
    print("   Press Ctrl+C to stop the application")

    # Launch streamlit. The return code is propagated rather than discarded:
    # Streamlit exits non-zero when it cannot start at all (a missing target, a
    # port already taken), and a launcher that swallows that reports success
    # having launched nothing.
    try:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(app_file),
                "--server.port",
                port,
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ]
        ).returncode
    except KeyboardInterrupt:
        print("\n👋 Application stopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())

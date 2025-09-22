#!/usr/bin/env python3
"""
Simple launcher script for the hometube application
Usage: python run.py
"""

import os
import sys
import subprocess
from pathlib import Path


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

    # Load port from .env if available
    env_file = script_dir / ".env"
    port = "8502"  # default port

    if env_file.exists():
        print(f"✅ .env file found: {env_file}")
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith("STREAMLIT_PORT="):
                    port = line.split("=")[1].strip()
                    break
    else:
        print("⚠️  .env file not found, using default values")

    print(f"🚀 Starting application on port {port}")
    print(f"🌐 Open your browser at: http://localhost:{port}")
    print("   Press Ctrl+C to stop the application")

    # Launch streamlit
    try:
        subprocess.run(
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
        )
    except KeyboardInterrupt:
        print("\n👋 Application stopped")


if __name__ == "__main__":
    main()

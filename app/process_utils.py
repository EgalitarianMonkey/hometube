"""
Process and Subprocess Utilities for HomeTube

Provides centralized subprocess execution with standardized error handling,
timeout management, and logging integration.
"""

import subprocess
from typing import List

# Import logging functions
try:
    from .logs_utils import safe_push_log
except ImportError:
    from logs_utils import safe_push_log


def run_subprocess_safe(
    cmd: List[str], timeout: int = 60, error_context: str = ""
) -> subprocess.CompletedProcess:
    """
    Run subprocess with standardized error handling and timeout.

    Args:
        cmd: Command to execute as list of strings
        timeout: Timeout in seconds (default: 60)
        error_context: Context string for error messages

    Returns:
        CompletedProcess object with result or mock object on error

    Example:
        result = run_subprocess_safe(
            ["ffprobe", "-v", "quiet", "video.mp4"],
            timeout=30,
            error_context="Video analysis"
        )
        if result.returncode == 0:
            print("Success:", result.stdout)
        else:
            print("Failed:", result.stderr)
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result
    except subprocess.TimeoutExpired:
        error_msg = f"Command timed out after {timeout} seconds"
        if error_context:
            error_msg = f"{error_context}: {error_msg}"
        safe_push_log(f"⚠️ {error_msg}")
        # Return a fake result object for consistency
        return subprocess.CompletedProcess(cmd, 1, "", error_msg)
    except Exception as e:
        error_msg = f"Command failed: {str(e)}"
        if error_context:
            error_msg = f"{error_context}: {error_msg}"
        safe_push_log(f"❌ {error_msg}")
        return subprocess.CompletedProcess(cmd, 1, "", error_msg)


def run_subprocess_with_progress(
    cmd: List[str],
    timeout: int = 300,
    error_context: str = "",
    progress_callback: callable = None,
) -> subprocess.CompletedProcess:
    """
    Run subprocess with optional progress monitoring.

    Args:
        cmd: Command to execute as list of strings
        timeout: Timeout in seconds (default: 300 for longer operations)
        error_context: Context string for error messages
        progress_callback: Optional function to call with progress updates

    Returns:
        CompletedProcess object with result or mock object on error
    """
    try:
        if progress_callback:
            # For commands that support progress monitoring
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
            )

            stdout_lines = []
            stderr_lines = []

            # Read output in real-time
            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    stdout_lines.append(output.strip())
                    if progress_callback:
                        progress_callback(output.strip())

            # Get remaining output
            remaining_stdout, remaining_stderr = process.communicate(timeout=timeout)
            if remaining_stdout:
                stdout_lines.extend(remaining_stdout.strip().split("\n"))
            if remaining_stderr:
                stderr_lines.extend(remaining_stderr.strip().split("\n"))

            return subprocess.CompletedProcess(
                cmd,
                process.returncode,
                "\n".join(stdout_lines),
                "\n".join(stderr_lines),
            )
        else:
            # Fallback to standard execution
            return run_subprocess_safe(cmd, timeout, error_context)

    except subprocess.TimeoutExpired:
        error_msg = (
            f"Command with progress monitoring timed out after {timeout} seconds"
        )
        if error_context:
            error_msg = f"{error_context}: {error_msg}"
        safe_push_log(f"⚠️ {error_msg}")
        return subprocess.CompletedProcess(cmd, 1, "", error_msg)
    except Exception as e:
        error_msg = f"Command with progress monitoring failed: {str(e)}"
        if error_context:
            error_msg = f"{error_context}: {error_msg}"
        safe_push_log(f"❌ {error_msg}")
        return subprocess.CompletedProcess(cmd, 1, "", error_msg)


def check_command_available(command: str) -> bool:
    """
    Check if a command is available in the system PATH.

    Args:
        command: Command name to check (e.g., 'ffmpeg', 'yt-dlp')

    Returns:
        True if command is available, False otherwise
    """
    try:
        result = run_subprocess_safe(
            (
                ["which", command]
                if not subprocess.sys.platform.startswith("win")
                else ["where", command]
            ),
            timeout=5,
            error_context=f"Checking {command} availability",
        )
        return result.returncode == 0
    except Exception:
        return False


def get_command_version(command: str, version_arg: str = "--version") -> str:
    """
    Get version information for a command.

    Args:
        command: Command name (e.g., 'ffmpeg', 'yt-dlp')
        version_arg: Argument to get version (default: '--version')

    Returns:
        Version string or empty string if failed
    """
    try:
        result = run_subprocess_safe(
            [command, version_arg],
            timeout=10,
            error_context=f"Getting {command} version",
        )
        if result.returncode == 0:
            # Return first line of output (usually contains version)
            return result.stdout.split("\n")[0] if result.stdout else ""
        return ""
    except Exception:
        return ""

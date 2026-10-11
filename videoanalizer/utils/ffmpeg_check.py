"""FFmpeg binary verification and capability diagnostics with auto-discovery."""

import os
import shutil
import subprocess
from pathlib import Path

from videoanalizer.exceptions import FFmpegNotFoundError


def find_and_inject_ffmpeg() -> str | None:
    """Find FFmpeg binary and inject its directory into os.environ['PATH'] if found."""
    found = shutil.which("ffmpeg")
    if found:
        return found

    # Check common Windows WinGet installation directory
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        winget_dir = Path(localappdata) / "Microsoft" / "WinGet" / "Packages"
        if winget_dir.exists():
            for candidate in winget_dir.glob("**/ffmpeg.exe"):
                bin_dir = str(candidate.parent)
                current_path = os.environ.get("PATH", "")
                if bin_dir not in current_path:
                    os.environ["PATH"] = bin_dir + os.pathsep + current_path
                return str(candidate)

    return None


def ensure_ffmpeg() -> str:
    """Verify that FFmpeg executable is installed and reachable on the system PATH.

    Returns:
        First line of ffmpeg -version output containing version details.

    Raises:
        FFmpegNotFoundError: If ffmpeg is not found on PATH or fails to run.
    """
    ffmpeg_binary = find_and_inject_ffmpeg()
    if not ffmpeg_binary:
        raise FFmpegNotFoundError(
            "FFmpeg executable not found on system PATH. "
            "Please install FFmpeg (e.g. via 'winget install Gyan.FFmpeg' on Windows) "
            "and ensure it is added to your PATH environment variable."
        )

    try:
        proc = subprocess.run(
            [ffmpeg_binary, "-version"],
            capture_output=True,
            text=True,
            check=True,
        )
        first_line = proc.stdout.splitlines()[0] if proc.stdout else "ffmpeg version (unknown)"
        return first_line
    except (subprocess.SubprocessError, OSError) as exc:
        raise FFmpegNotFoundError(
            f"Failed to execute FFmpeg at {ffmpeg_binary}: {exc}"
        ) from exc


def check_libass_support() -> bool:
    """Check if the installed FFmpeg supports the 'ass' video filter."""
    ffmpeg_binary = find_and_inject_ffmpeg()
    if not ffmpeg_binary:
        return False

    try:
        proc = subprocess.run(
            [ffmpeg_binary, "-filters"],
            capture_output=True,
            text=True,
            check=True,
        )
        return " ass " in proc.stdout or "--enable-libass" in proc.stdout
    except (subprocess.SubprocessError, OSError):
        return False

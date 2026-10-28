"""VideoAnalyzer - Automated Funny Moments TikTok/Shorts Generator."""

from videoanalizer.logging_setup import setup_console_logging
from videoanalizer.utils.ffmpeg_check import find_and_inject_ffmpeg

# Proactively locate and inject FFmpeg into PATH if installed via WinGet or custom location
find_and_inject_ffmpeg()

# Initialize console logging for all videoanalizer services
setup_console_logging()

__version__ = "0.1.0"

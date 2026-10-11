"""VideoAnalyzer - Automated Funny Moments TikTok/Shorts Generator."""

from videoanalizer.utils.ffmpeg_check import find_and_inject_ffmpeg

# Proactively locate and inject FFmpeg into PATH if installed via WinGet or custom location
find_and_inject_ffmpeg()

__version__ = "0.1.0"

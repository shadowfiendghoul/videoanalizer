"""FFmpeg probing utilities for extracting video and audio stream metadata."""

from pathlib import Path
from typing import Any
import ffmpeg

from videoanalizer.exceptions import MediaProcessingError


def probe_video(path: Path) -> dict[str, Any]:
    """Probe a media file using FFmpeg and extract essential stream properties.

    Args:
        path: Filesystem path to the target media file.

    Returns:
        Dictionary containing:
            - duration_sec (float)
            - width (int)
            - height (int)
            - fps (float)
            - codec (str)
            - audio_codec (str | None)
            - file_size_bytes (int)

    Raises:
        MediaProcessingError: If probing fails, file is corrupted, or no valid video stream exists.
    """
    if not path.exists():
        raise MediaProcessingError(f"Target video file not found at {path}")

    try:
        probe_data = ffmpeg.probe(str(path))
    except ffmpeg.Error as exc:
        stderr_output = exc.stderr.decode("utf-8", errors="replace") if exc.stderr else str(exc)
        raise MediaProcessingError(
            f"FFmpeg failed to probe media file {path.name}",
            details=stderr_output,
        ) from exc
    except Exception as exc:
        raise MediaProcessingError(
            f"Unexpected error while probing media file {path.name}: {exc}"
        ) from exc

    streams = probe_data.get("streams", [])
    format_info = probe_data.get("format", {})

    video_stream: dict[str, Any] | None = None
    audio_stream: dict[str, Any] | None = None

    for stream in streams:
        codec_type = stream.get("codec_type")
        if codec_type == "video" and video_stream is None:
            # Skip attached pictures (cover art) if present
            if stream.get("disposition", {}).get("attached_pic") != 1:
                video_stream = stream
        elif codec_type == "audio" and audio_stream is None:
            audio_stream = stream

    if not video_stream:
        raise MediaProcessingError(f"No valid video stream detected in media file {path.name}")

    # Extract resolution
    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    if width <= 0 or height <= 0:
        raise MediaProcessingError(
            f"Invalid video dimensions ({width}x{height}) in {path.name}"
        )

    # Extract FPS
    fps = 30.0
    r_frame_rate = video_stream.get("r_frame_rate", "")
    if "/" in r_frame_rate:
        num, denom = r_frame_rate.split("/", 1)
        try:
            d = float(denom)
            if d > 0:
                fps = round(float(num) / d, 2)
        except ValueError:
            pass

    # Extract duration
    duration = 0.0
    duration_str = format_info.get("duration") or video_stream.get("duration")
    if duration_str:
        try:
            duration = float(duration_str)
        except ValueError:
            pass

    if duration <= 0:
        raise MediaProcessingError(f"Could not determine valid duration for video {path.name}")

    # Codecs
    codec = video_stream.get("codec_name", "unknown")
    audio_codec = audio_stream.get("codec_name") if audio_stream else None

    # File size
    file_size_bytes = path.stat().st_size

    return {
        "duration_sec": round(duration, 3),
        "width": width,
        "height": height,
        "fps": fps,
        "codec": codec,
        "audio_codec": audio_codec,
        "file_size_bytes": file_size_bytes,
    }

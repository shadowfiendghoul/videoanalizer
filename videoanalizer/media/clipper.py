"""Media clipping and single-frame extraction utilities using FFmpeg."""

import subprocess
from pathlib import Path

from videoanalizer.exceptions import MediaProcessingError


def extract_clip(source_path: Path, start_sec: float, end_sec: float, output_path: Path) -> Path:
    """Extract a sub-clip segment from a source video file with accurate seeking and re-encoding.

    Args:
        source_path: Path to the input video.
        start_sec: Start time in seconds.
        end_sec: End time in seconds.
        output_path: Target path for the extracted sub-clip.

    Returns:
        Path to the output clip.

    Raises:
        MediaProcessingError: If FFmpeg fails to extract the segment.
    """
    if not source_path.exists():
        raise MediaProcessingError(f"Input video not found at {source_path}")

    duration = max(0.1, end_sec - start_sec)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_sec:.3f}",
        "-i",
        str(source_path),
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-avoid_negative_ts",
        "make_zero",
        str(output_path),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise MediaProcessingError(
                f"Failed to extract clip [{start_sec}s - {end_sec}s] from {source_path.name}",
                details=proc.stderr,
            )
        return output_path
    except Exception as exc:
        raise MediaProcessingError(f"Error extracting clip: {exc}") from exc


def extract_frame(source_path: Path, timestamp_sec: float, output_path: Path) -> Path:
    """Extract a single frame as a JPEG image at the given timestamp.

    Args:
        source_path: Path to the source video.
        timestamp_sec: Exact timestamp in seconds to sample.
        output_path: Path to write the output JPEG.

    Returns:
        Path to the output JPEG image.

    Raises:
        MediaProcessingError: If frame capture fails.
    """
    if not source_path.exists():
        raise MediaProcessingError(f"Input video not found at {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{timestamp_sec:.3f}",
        "-i",
        str(source_path),
        "-vframes",
        "1",
        "-q:v",
        "2",
        str(output_path),
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise MediaProcessingError(
                f"Failed to extract frame at {timestamp_sec}s from {source_path.name}",
                details=proc.stderr,
            )
        return output_path
    except Exception as exc:
        raise MediaProcessingError(f"Error extracting frame: {exc}") from exc

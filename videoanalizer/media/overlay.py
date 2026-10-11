"""Top banner and hook headline overlay generator using FFmpeg drawtext."""

import shutil
import subprocess
from pathlib import Path

from videoanalizer.exceptions import MediaProcessingError
from videoanalizer.models.render_job import BannerConfig


def add_banner(
    video_path: Path,
    banner: BannerConfig,
    output_path: Path,
    frame_width: int = 1080,
) -> Path:
    """Burn a top hook headline text banner over the video.

    Args:
        video_path: Input video file.
        banner: BannerConfig with text, font size, colors, and position.
        output_path: Target video file path.
        frame_width: Video canvas width.

    Returns:
        Path to output video with banner overlay.

    Raises:
        MediaProcessingError: If overlay generation fails.
    """
    if not video_path.exists():
        raise MediaProcessingError(f"Input video not found at {video_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not banner.enabled or not banner.text.strip():
        shutil.copy2(video_path, output_path)
        return output_path

    # Sanitize text for FFmpeg drawtext filter
    safe_text = (
        banner.text.replace("'", "'\\''")
        .replace(":", "\\:")
        .replace("%", "\\%")
        .replace("\n", " ")
    )

    banner_h = int(banner.font_size * 2.2)
    y_box = 80 if banner.position == "top" else "(h-180)"
    y_text = f"{y_box}+({banner_h}-text_h)/2"

    # Hex color to FFmpeg color
    font_color = banner.font_color.lstrip("#")
    # drawbox + drawtext filters
    box_filter = f"drawbox=x=0:y={y_box}:w=iw:h={banner_h}:color=black@0.65:t=fill"
    text_filter = (
        f"drawtext=text='{safe_text}':font='Arial':fontsize={banner.font_size}:"
        f"fontcolor=0x{font_color}:x=(w-text_w)/2:y={y_text}:shadowcolor=black:shadowx=2:shadowy=2"
    )

    vf = f"{box_filter},{text_filter}"

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-c:a",
        "copy",
        str(output_path),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not output_path.exists():
        raise MediaProcessingError(
            f"Failed to overlay banner onto {video_path.name}",
            details=proc.stderr,
        )

    return output_path

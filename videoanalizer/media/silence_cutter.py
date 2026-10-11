"""Silence cutting and segment concatenation engine with audio crossfades."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from videoanalizer.exceptions import MediaProcessingError


def cut_silences(
    input_path: Path,
    keep_segments: list[tuple[float, float]],
    output_path: Path,
    crossfade_ms: int = 25,
) -> Path:
    """Trim silence intervals from video using FFmpeg select filters or segment concatenation.

    Args:
        input_path: Input video file.
        keep_segments: List of (start_sec, end_sec) intervals to retain.
        output_path: Target output path.
        crossfade_ms: Crossfade smoothing in ms between segments.

    Returns:
        Path to output video with silences trimmed.

    Raises:
        MediaProcessingError: If trimming or concatenation fails.
    """
    if not input_path.exists():
        raise MediaProcessingError(f"Input file not found at {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not keep_segments:
        # Nothing to cut, copy directly
        shutil.copy2(input_path, output_path)
        return output_path

    # If only 1 segment covering the whole clip, copy directly
    if len(keep_segments) == 1 and keep_segments[0][0] <= 0.05:
        shutil.copy2(input_path, output_path)
        return output_path

    with tempfile.TemporaryDirectory(prefix="va_silence_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        concat_file = tmp_dir_path / "concat.txt"
        segment_files: list[Path] = []

        for idx, (start_sec, end_sec) in enumerate(keep_segments):
            dur = max(0.1, end_sec - start_sec)
            seg_out = tmp_dir_path / f"seg_{idx:03d}.mp4"

            # Apply afade for crossfade smoothing at splice points
            fade_sec = max(0.01, crossfade_ms / 1000.0)
            afade_filter = f"afade=t=in:ss=0:d={fade_sec},afade=t=out:st={dur - fade_sec:.3f}:d={fade_sec}"

            cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                f"{start_sec:.3f}",
                "-i",
                str(input_path),
                "-t",
                f"{dur:.3f}",
                "-af",
                afade_filter,
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
                str(seg_out),
            ]

            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0 or not seg_out.exists():
                raise MediaProcessingError(
                    f"Failed to cut segment [{start_sec}s - {end_sec}s]",
                    details=proc.stderr,
                )
            segment_files.append(seg_out)

        # Write concat demuxer manifest
        with open(concat_file, "w", encoding="utf-8") as f:
            for seg in segment_files:
                # Use forward slashes for FFmpeg concat file
                f.write(f"file '{seg.as_posix()}'\n")

        # Concat segments
        concat_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(output_path),
        ]

        proc = subprocess.run(concat_cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not output_path.exists():
            raise MediaProcessingError(
                "Failed to concatenate speech segments after silence removal",
                details=proc.stderr,
            )

        return output_path

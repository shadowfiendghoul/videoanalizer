"""Silence detection and speech segment computation service using FFmpeg silencedetect."""

import re
import subprocess
from pathlib import Path

from videoanalizer.exceptions import MediaProcessingError
from videoanalizer.models.render_job import SilenceConfig


class SilenceDetector:
    """Detects audio dead air and computes padded speech segments."""

    def detect_silences(
        self,
        audio_path: Path,
        config: SilenceConfig,
    ) -> list[tuple[float, float]]:
        """Run FFmpeg silencedetect on the media file to find silent intervals.

        Args:
            audio_path: Path to video or extracted audio file.
            config: SilenceConfig with threshold_sec and noise_db.

        Returns:
            List of (silence_start_sec, silence_end_sec) tuples.
        """
        if not audio_path.exists():
            raise MediaProcessingError(f"Audio file not found at {audio_path}")

        filter_arg = f"silencedetect=noise={config.noise_db}dB:d={config.threshold_sec}"
        cmd = [
            "ffmpeg",
            "-i",
            str(audio_path),
            "-af",
            filter_arg,
            "-f",
            "null",
            "-",
        ]

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        stderr_text = proc.stderr or ""

        silences: list[tuple[float, float]] = []
        current_start: float | None = None

        start_pattern = re.compile(r"silence_start:\s*([0-9.]+)")
        end_pattern = re.compile(r"silence_end:\s*([0-9.]+)")

        for line in stderr_text.splitlines():
            s_match = start_pattern.search(line)
            if s_match:
                try:
                    current_start = float(s_match.group(1))
                except ValueError:
                    pass

            e_match = end_pattern.search(line)
            if e_match:
                try:
                    end_val = float(e_match.group(1))
                    start_val = current_start if current_start is not None else 0.0
                    silences.append((round(start_val, 3), round(end_val, 3)))
                    current_start = None
                except ValueError:
                    pass

        return silences

    def compute_keep_segments(
        self,
        duration: float,
        silences: list[tuple[float, float]],
        padding_ms: int = 100,
    ) -> list[tuple[float, float]]:
        """Compute the inverse speech segments to keep, applying safety padding around speech.

        Args:
            duration: Total duration of the audio clip in seconds.
            silences: List of (silence_start, silence_end) in seconds.
            padding_ms: Safety padding in milliseconds added to speech boundaries.

        Returns:
            List of (keep_start, keep_end) segments covering all non-silent parts.
        """
        if not silences:
            return [(0.0, round(duration, 3))]

        pad_sec = padding_ms / 1000.0

        # Adjust silences by shrinking them by pad_sec on each side (effectively extending speech)
        adjusted_silences: list[tuple[float, float]] = []
        for s_start, s_end in silences:
            adj_start = s_start + pad_sec
            adj_end = s_end - pad_sec
            if adj_end > adj_start:
                adjusted_silences.append((adj_start, adj_end))

        if not adjusted_silences:
            return [(0.0, round(duration, 3))]

        # Invert silences into keep segments
        keep_segments: list[tuple[float, float]] = []
        cursor = 0.0

        for s_start, s_end in adjusted_silences:
            if s_start > cursor + 0.05:
                keep_segments.append((round(cursor, 3), round(s_start, 3)))
            cursor = max(cursor, s_end)

        if cursor < duration - 0.05:
            keep_segments.append((round(cursor, 3), round(duration, 3)))

        return keep_segments or [(0.0, round(duration, 3))]

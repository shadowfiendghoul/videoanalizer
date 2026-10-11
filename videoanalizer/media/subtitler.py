"""ASS subtitle generator and burner for dynamic TikTok karaoke style captions."""

import subprocess
import tempfile
from pathlib import Path

from videoanalizer.exceptions import MediaProcessingError
from videoanalizer.models.highlight import WordTiming
from videoanalizer.models.render_job import SubtitleStyle


def _hex_to_ass_color(hex_color: str) -> str:
    """Convert a standard #RRGGBB hex color to ASS &H00BBGGRR& format."""
    clean = hex_color.strip().lstrip("#")
    if len(clean) == 6:
        r, g, b = clean[0:2], clean[2:4], clean[4:6]
        return f"&H00{b}{g}{r}&"
    if len(clean) == 8:
        r, g, b, a = clean[0:2], clean[2:4], clean[4:6], clean[6:8]
        return f"&H{a}{b}{g}{r}&"
    return "&H00FFFFFF&"


def _format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp H:MM:SS.cc."""
    total_sec = max(0.0, seconds)
    hours = int(total_sec // 3600)
    minutes = int((total_sec % 3600) // 60)
    secs = int(total_sec % 60)
    centis = int(round((total_sec - int(total_sec)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def generate_ass_subtitles(
    word_timings: list[WordTiming],
    style: SubtitleStyle,
    frame_width: int = 1080,
    frame_height: int = 1920,
) -> str:
    """Generate Advanced SubStation Alpha (.ass) subtitle file content with karaoke tags.

    Args:
        word_timings: Ordered list of WordTiming objects.
        style: SubtitleStyle configuration.
        frame_width: Video canvas width.
        frame_height: Video canvas height.

    Returns:
        Full text string containing formatted ASS subtitle file content.
    """
    primary_color = _hex_to_ass_color(style.inactive_color)
    highlight_color = _hex_to_ass_color(style.active_color)
    outline_color = _hex_to_ass_color(style.outline_color)
    margin_v = int(frame_height * (1.0 - style.position_vertical_pct))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {frame_width}
PlayResY: {frame_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font_name},{style.font_size},{primary_color},{highlight_color},{outline_color},&H00000000&,1,0,0,0,100,100,0,0,1,{style.outline_width},0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    if not word_timings:
        return header

    # Chunk words into short readable phrases (4-6 words each)
    chunk_size = 5
    chunks: list[list[WordTiming]] = [
        word_timings[i : i + chunk_size] for i in range(0, len(word_timings), chunk_size)
    ]

    events: list[str] = []
    for chunk in chunks:
        if not chunk:
            continue
        phrase_start = chunk[0].start_sec
        phrase_end = max(chunk[-1].end_sec, phrase_start + 0.5)

        start_str = _format_ass_time(phrase_start)
        end_str = _format_ass_time(phrase_end)

        # Build karaoke line
        karaoke_text_parts: list[str] = []
        for wt in chunk:
            dur_centis = int(round(max(0.05, wt.end_sec - wt.start_sec) * 100))
            karaoke_text_parts.append(f"{{\\kf{dur_centis}}}{wt.word} ")

        line_text = "".join(karaoke_text_parts).strip()
        events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_text}")

    return header + "\n".join(events) + "\n"


def burn_subtitles(video_path: Path, ass_content: str, output_path: Path) -> Path:
    """Burn ASS subtitles into the video stream using FFmpeg ass filter.

    Args:
        video_path: Input video file.
        ass_content: Text of the ASS subtitle file.
        output_path: Target video file path.

    Returns:
        Path to output video with subtitles burned in.
    """
    if not video_path.exists():
        raise MediaProcessingError(f"Input video not found at {video_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="va_sub_") as tmp_dir:
        ass_file = Path(tmp_dir) / "subtitles.ass"
        ass_file.write_text(ass_content, encoding="utf-8")

        # In FFmpeg, escape colon and backslash in filter path
        escaped_ass_path = str(ass_file).replace("\\", "/").replace(":", "\\:")
        vf = f"ass='{escaped_ass_path}'"

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
                f"Failed to burn subtitles into {video_path.name}",
                details=proc.stderr,
            )

        return output_path

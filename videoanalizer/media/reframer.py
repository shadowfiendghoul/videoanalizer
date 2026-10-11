"""Reframing engine converting landscape 16:9 video to vertical 9:16 format."""

import subprocess
import tempfile
from pathlib import Path

from videoanalizer.exceptions import MediaProcessingError
from videoanalizer.media.clipper import extract_frame
from videoanalizer.models.layout import CropBox, LayoutPreset


class Reframer:
    """Engine orchestrating vertical 9:16 reframing via FFmpeg filter chains."""

    def center_crop(
        self,
        input_path: Path,
        output_path: Path,
        target_w: int = 1080,
        target_h: int = 1920,
    ) -> Path:
        """Apply a centered 9:16 crop to a landscape video and scale to target dimensions."""
        if not input_path.exists():
            raise MediaProcessingError(f"Input video not found at {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Centered 9:16 crop filter: ih*(9/16) width, full height, centered horizontally
        vf = f"crop=ih*9/16:ih:(iw-ow)/2:0,scale={target_w}:{target_h}"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
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
        if proc.returncode != 0:
            raise MediaProcessingError(
                f"Failed to center-crop video {input_path.name}",
                details=proc.stderr,
            )
        return output_path

    def split_screen(
        self,
        input_path: Path,
        output_path: Path,
        webcam_box: CropBox,
        gameplay_box: CropBox,
        webcam_position: str = "top",
        target_w: int = 1080,
        target_h: int = 1920,
    ) -> Path:
        """Compose a streamer split-screen vertical video stacking webcam and gameplay.

        Upper and lower halves are each target_h // 2 (e.g. 960px).
        """
        if not input_path.exists():
            raise MediaProcessingError(f"Input video not found at {input_path}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        half_h = target_h // 2

        # Filter chain:
        # [0:v] split [in1][in2];
        # [in1] crop=w:h:x:y, scale=target_w:half_h [cam];
        # [in2] crop=w:h:x:y, scale=target_w:half_h [game];
        # [cam][game] vstack [out]
        cam_crop = f"crop={webcam_box.width}:{webcam_box.height}:{webcam_box.x}:{webcam_box.y},scale={target_w}:{half_h}"
        game_crop = f"crop={gameplay_box.width}:{gameplay_box.height}:{gameplay_box.x}:{gameplay_box.y},scale={target_w}:{half_h}"

        if webcam_position == "top":
            filter_complex = (
                f"[0:v]split=2[vcam][vgame];"
                f"[vcam]{cam_crop}[top];"
                f"[vgame]{game_crop}[bottom];"
                f"[top][bottom]vstack=inputs=2[v]"
            )
        else:
            filter_complex = (
                f"[0:v]split=2[vcam][vgame];"
                f"[vgame]{game_crop}[top];"
                f"[vcam]{cam_crop}[bottom];"
                f"[top][bottom]vstack=inputs=2[v]"
            )

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "0:a?",
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
        if proc.returncode != 0:
            raise MediaProcessingError(
                f"Failed to generate split-screen video from {input_path.name}",
                details=proc.stderr,
            )
        return output_path

    def preview_frame(
        self,
        source_path: Path,
        timestamp_sec: float,
        layout: LayoutPreset,
        target_w: int = 1080,
        target_h: int = 1920,
    ) -> bytes:
        """Extract a single frame and reframe it according to layout preset, returning JPEG bytes."""
        with tempfile.TemporaryDirectory(prefix="va_preview_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            raw_frame = tmp_path / "raw.jpg"
            reframed_frame = tmp_path / "reframed.jpg"

            # 1. Extract raw JPEG frame
            extract_frame(source_path, timestamp_sec, raw_frame)

            # 2. Apply reframing layout to still image
            half_h = target_h // 2
            if layout.mode == "split_screen" and layout.webcam_box and layout.gameplay_box:
                wbox = layout.webcam_box
                gbox = layout.gameplay_box
                cam_f = f"crop={wbox.width}:{wbox.height}:{wbox.x}:{wbox.y},scale={target_w}:{half_h}"
                game_f = f"crop={gbox.width}:{gbox.height}:{gbox.x}:{gbox.y},scale={target_w}:{half_h}"

                if layout.webcam_position == "top":
                    fc = (
                        f"[0:v]split=2[c1][c2];"
                        f"[c1]{cam_f}[top];"
                        f"[c2]{game_f}[bot];"
                        f"[top][bot]vstack=inputs=2[v]"
                    )
                else:
                    fc = (
                        f"[0:v]split=2[c1][c2];"
                        f"[c2]{game_f}[top];"
                        f"[c1]{cam_f}[bot];"
                        f"[top][bot]vstack=inputs=2[v]"
                    )

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(raw_frame),
                    "-filter_complex",
                    fc,
                    "-map",
                    "[v]",
                    "-q:v",
                    "2",
                    str(reframed_frame),
                ]
            else:
                vf = f"crop=ih*9/16:ih:(iw-ow)/2:0,scale={target_w}:{target_h}"
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(raw_frame),
                    "-vf",
                    vf,
                    "-q:v",
                    "2",
                    str(reframed_frame),
                ]

            proc = subprocess.run(cmd, capture_output=True, check=False)
            if proc.returncode != 0 or not reframed_frame.exists():
                raise MediaProcessingError("Failed to render preview frame", details=proc.stderr.decode("utf-8", errors="replace"))

            return reframed_frame.read_bytes()

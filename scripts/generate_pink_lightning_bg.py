"""Script to generate the viral TikTok Preppy Pink Lightning Bolt 1080x1920 60fps looping background video.

Reconstructs the exact vector bolt geometry and pastel pink aesthetic:
- Background: #DE80BA (vibrant pastel bubblegum pink)
- Bolt: #EBA4E5 (light lavender-pink)
- Motion: Smooth diagonal drift with 100% mathematically seamless wrap-around loop.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np


def generate_bolt_sprite(target_w: int = 212, target_h: int = 312) -> Image.Image:
    """Generate supersampled antialiased bolt sprite from extracted vector points."""
    # Normalized key vertices of the isolated TikTok bolt:
    # (23, 0), (72, 0), (65, 26), (110, 28), (1, 162), (29, 71), (0, 68)
    scale_x = target_w / 111.0
    scale_y = target_h / 163.0

    pts = [
        (23 * scale_x, 0 * scale_y),
        (72 * scale_x, 0 * scale_y),
        (65 * scale_x, 26 * scale_y),
        (110 * scale_x, 28 * scale_y),
        (1 * scale_x, 162 * scale_y),
        (29 * scale_x, 71 * scale_y),
        (0 * scale_x, 68 * scale_y),
    ]

    ss = 4
    ss_w = int((target_w + 16) * ss)
    ss_h = int((target_h + 16) * ss)
    canvas = Image.new("RGBA", (ss_w, ss_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    ss_pts = [((x + 8) * ss, (y + 8) * ss) for x, y in pts]
    draw.polygon(ss_pts, fill=(235, 164, 229, 255))

    return canvas.resize((target_w + 16, target_h + 16), Image.Resampling.LANCZOS)


def main():
    width = 1080
    height = 1920
    fps = 60
    duration_sec = 10
    total_frames = fps * duration_sec  # 600 frames

    bg_color = (222, 128, 186)
    step_x = 350
    step_y = 375
    grid_w = step_x * 2  # 700
    grid_h = step_y * 2  # 750

    output_dir = Path("assets/backgrounds")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "pink_lightning.mp4"

    print("Generating bolt sprite...")
    bolt = generate_bolt_sprite(target_w=212, target_h=312)

    # Render a large repeating canvas
    # Canvas size: viewport + 2 full grid periods in each direction for smooth window sliding
    big_w = width + grid_w * 2
    big_h = height + grid_h * 2
    print(f"Creating tiled canvas ({big_w}x{big_h})...")
    canvas = Image.new("RGB", (big_w, big_h), bg_color)

    for r in range(-2, int(big_h / step_y) + 3):
        y = r * step_y
        x_offset = (r % 2) * step_x
        for c in range(-2, int(big_w / grid_w) + 3):
            x = c * grid_w + x_offset
            canvas.paste(bolt, (int(x), int(y)), bolt)

    canvas_arr = np.array(canvas)
    print("Canvas prepared. Starting FFmpeg pipeline...")

    # We start at (x0, y0) = (grid_w, grid_h)
    # Over total_frames, we shift by (-step_x, +step_y)
    # At t=total_frames, shift is exactly (-step_x, +step_y) which is identical to (0,0)
    x0 = grid_w
    y0 = grid_h

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "18",
        "-movflags", "+faststart",
        str(output_path),
    ]

    process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        for t in range(total_frames):
            u = t / total_frames
            # Drifting diagonally:
            # Let x slide: x = x0 - u * step_x
            # Let y slide: y = y0 + u * step_y
            curr_x = int(round(x0 - u * step_x))
            curr_y = int(round(y0 + u * step_y))

            frame = canvas_arr[curr_y : curr_y + height, curr_x : curr_x + width]
            process.stdin.write(frame.tobytes())

            if t % 120 == 0:
                print(f"Rendered frame {t}/{total_frames} ({int(u*100)}%)...", flush=True)

        process.stdin.close()
        process.wait()
        print(f"Successfully generated {output_path} ({total_frames} frames, {duration_sec}s @ {fps}fps)", flush=True)
    except Exception as e:
        process.kill()
        raise e


if __name__ == "__main__":
    main()

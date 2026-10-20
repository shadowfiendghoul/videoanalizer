"""Generate 6 viral aesthetic preppy looping background videos in 16:9 widescreen (1920x1080 60fps).

Themes:
1. mint_stars_16x9.mp4: Pastel Sage Mint (#98D7C2) + Cream Star Sparkles (#F4FBF7)
2. lavender_hearts_16x9.mp4: Pastel Lavender (#C8B6FF) + Soft Cloud Pink Hearts (#F7E8FF)
3. peach_butterflies_16x9.mp4: Soft Pastel Peach (#FFC6B3) + Vanilla Cream Butterflies (#FFF3EC)
4. sky_clouds_16x9.mp4: Pastel Baby Sky Blue (#A0C4FF) + Fluffy Marshmallow Clouds (#F0F6FF)
5. buttercup_daisies_16x9.mp4: Soft Buttercup Honey (#FDDE81) + Pure White Daisies (#FFFDF5)
6. pink_lightning_16x9.mp4: Vibrant Pastel Pink (#DE80BA) + Light Lavender-Pink Bolts (#EBA4E5)

All videos are 10.0s (600 frames) @ 60fps, 1920x1080, with 100% mathematically seamless wrap-around loop.
"""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np


def create_star_sprite(w: int = 180, h: int = 180, color=(244, 251, 247, 255)) -> Image.Image:
    """Generate 4-pointed curved aesthetic sparkle star."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    r_outer = (w * ss) * 0.46
    r_inner = (w * ss) * 0.11

    pts = []
    for i in range(16):
        angle = i * (math.pi / 8.0) - (math.pi / 2.0)
        if i % 4 == 0:
            rad = r_outer
        elif i % 2 == 0:
            rad = r_inner
        else:
            rad = (r_outer + r_inner) * 0.28
        pts.append((cx + rad * math.cos(angle), cy + rad * math.sin(angle)))

    draw.polygon(pts, fill=color)
    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_heart_sprite(w: int = 200, h: int = 180, color=(247, 232, 255, 255)) -> Image.Image:
    """Generate smooth cute preppy cartoon heart."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx = (w * ss) / 2.0
    cy = (h * ss) * 0.45
    scale = (w * ss) * 0.026

    pts = []
    for step in range(120):
        t = step * (2.0 * math.pi / 120.0)
        x = 16.0 * (math.sin(t) ** 3)
        y = -(13.0 * math.cos(t) - 5.0 * math.cos(2 * t) - 2.0 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * scale, cy + y * scale))

    draw.polygon(pts, fill=color)
    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_butterfly_sprite(w: int = 210, h: int = 180, color=(255, 243, 236, 255)) -> Image.Image:
    """Generate aesthetic preppy butterfly vector."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    s = (w * ss) * 0.44

    draw.ellipse([cx - s * 0.95, cy - s * 0.85, cx - s * 0.05, cy + s * 0.15], fill=color)
    draw.ellipse([cx + s * 0.05, cy - s * 0.85, cx + s * 0.95, cy + s * 0.15], fill=color)
    draw.ellipse([cx - s * 0.75, cy - s * 0.05, cx - s * 0.1, cy + s * 0.75], fill=color)
    draw.ellipse([cx + s * 0.1, cy - s * 0.05, cx + s * 0.75, cy + s * 0.75], fill=color)
    draw.rounded_rectangle([cx - s * 0.08, cy - s * 0.7, cx + s * 0.08, cy + s * 0.7], radius=int(s * 0.08), fill=color)

    rotated = canvas.rotate(-15, resample=Image.Resampling.BICUBIC)
    return rotated.resize((w, h), Image.Resampling.LANCZOS)


def create_cloud_sprite(w: int = 240, h: int = 150, color=(240, 246, 255, 255)) -> Image.Image:
    """Generate cute fluffy marshmallow cloud."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cw, ch = w * ss, h * ss

    base_y = ch * 0.75
    draw.ellipse([cw * 0.12, ch * 0.35, cw * 0.52, ch * 0.82], fill=color)
    draw.ellipse([cw * 0.35, ch * 0.15, cw * 0.75, ch * 0.82], fill=color)
    draw.ellipse([cw * 0.60, ch * 0.40, cw * 0.90, ch * 0.82], fill=color)
    draw.rounded_rectangle([cw * 0.15, ch * 0.55, cw * 0.87, base_y], radius=int(ch * 0.1), fill=color)

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_daisy_sprite(w: int = 200, h: int = 200, petal_color=(255, 253, 245, 255), center_color=(255, 215, 100, 255)) -> Image.Image:
    """Generate cute 5-petal daisy flower."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    r_center = (w * ss) * 0.16
    r_petal = (w * ss) * 0.23
    dist_petal = (w * ss) * 0.25

    for i in range(5):
        angle = i * (2.0 * math.pi / 5.0) - (math.pi / 2.0)
        px = cx + dist_petal * math.cos(angle)
        py = cy + dist_petal * math.sin(angle)
        draw.ellipse([px - r_petal, py - r_petal, px + r_petal, py + r_petal], fill=petal_color)

    draw.ellipse([cx - r_center, cy - r_center, cx + r_center, cy + r_center], fill=center_color)
    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_bolt_sprite(w: int = 180, h: int = 260, color=(235, 164, 229, 255)) -> Image.Image:
    """Generate aesthetic pastel preppy lightning bolt."""
    scale_x = w / 111.0
    scale_y = h / 163.0
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
    canvas = Image.new("RGBA", (int((w + 16) * ss), int((h + 16) * ss)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    ss_pts = [((x + 8) * ss, (y + 8) * ss) for x, y in pts]
    draw.polygon(ss_pts, fill=color)
    return canvas.resize((w + 16, h + 16), Image.Resampling.LANCZOS)


def render_loop_video(
    output_path: Path,
    sprite: Image.Image,
    bg_color: tuple[int, int, int],
    step_x: int = 350,
    step_y: int = 375,
    width: int = 1920,
    height: int = 1080,
    fps: int = 60,
    duration_sec: int = 10,
) -> None:
    """Render a seamless 1920x1080 60fps MP4 loop using diagonal scrolling grid."""
    total_frames = fps * duration_sec
    grid_w = step_x * 2
    grid_h = step_y * 2

    big_w = width + grid_w * 2
    big_h = height + grid_h * 2
    canvas = Image.new("RGB", (big_w, big_h), bg_color)

    for r in range(-2, int(big_h / step_y) + 3):
        y = r * step_y
        x_offset = (r % 2) * step_x
        for c in range(-2, int(big_w / grid_w) + 3):
            x = c * grid_w + x_offset
            canvas.paste(sprite, (int(x), int(y)), sprite)

    canvas_arr = np.array(canvas)

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
        "-preset", "fast",
        "-crf", "18",
        "-movflags", "+faststart",
        str(output_path),
    ]

    process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        for t in range(total_frames):
            u = t / total_frames
            curr_x = int(round(x0 - u * step_x))
            curr_y = int(round(y0 + u * step_y))
            frame = canvas_arr[curr_y : curr_y + height, curr_x : curr_x + width]
            process.stdin.write(frame.tobytes())

        process.stdin.close()
        process.wait()
    except Exception as e:
        process.kill()
        raise e


def main():
    bg_dir = Path("assets/backgrounds/pastel_16x9")
    bg_dir.mkdir(parents=True, exist_ok=True)

    remotion_public_bg = Path("templates/quiz-remotion/public/backgrounds")
    remotion_public_bg.mkdir(parents=True, exist_ok=True)

    configs = [
        {
            "name": "mint_stars_16x9.mp4",
            "sprite": create_star_sprite(180, 180, (244, 251, 247, 255)),
            "bg": (152, 215, 194),  # Pastel Sage Mint
            "step_x": 350,
            "step_y": 375,
        },
        {
            "name": "lavender_hearts_16x9.mp4",
            "sprite": create_heart_sprite(200, 180, (247, 232, 255, 255)),
            "bg": (200, 182, 255),  # Pastel Lavender
            "step_x": 350,
            "step_y": 375,
        },
        {
            "name": "peach_butterflies_16x9.mp4",
            "sprite": create_butterfly_sprite(210, 180, (255, 243, 236, 255)),
            "bg": (255, 198, 179),  # Soft Pastel Peach
            "step_x": 350,
            "step_y": 375,
        },
        {
            "name": "sky_clouds_16x9.mp4",
            "sprite": create_cloud_sprite(240, 150, (240, 246, 255, 255)),
            "bg": (160, 196, 255),  # Pastel Baby Sky Blue
            "step_x": 360,
            "step_y": 380,
        },
        {
            "name": "buttercup_daisies_16x9.mp4",
            "sprite": create_daisy_sprite(200, 200, (255, 253, 245, 255), (255, 215, 100, 255)),
            "bg": (253, 222, 129),  # Soft Buttercup Honey
            "step_x": 350,
            "step_y": 375,
        },
        {
            "name": "pink_lightning_16x9.mp4",
            "sprite": create_bolt_sprite(180, 260, (235, 164, 229, 255)),
            "bg": (222, 128, 186),  # Vibrant Bubblegum Pink
            "step_x": 350,
            "step_y": 375,
        },
    ]

    for cfg in configs:
        target = bg_dir / cfg["name"]
        print(f"Rendering {cfg['name']} (1920x1080 60fps)...", flush=True)
        render_loop_video(
            output_path=target,
            sprite=cfg["sprite"],
            bg_color=cfg["bg"],
            step_x=cfg["step_x"],
            step_y=cfg["step_y"],
            width=1920,
            height=1080,
            fps=60,
            duration_sec=10,
        )
        print(f"Finished {cfg['name']} ({target.stat().st_size} bytes)", flush=True)

        # Copy to remotion public folder as well
        remotion_target = remotion_public_bg / cfg["name"]
        shutil.copy2(target, remotion_target)


if __name__ == "__main__":
    main()

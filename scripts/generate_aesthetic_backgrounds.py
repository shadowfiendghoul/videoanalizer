"""Generate 5 viral TikTok/Reels aesthetic preppy looping background videos (1080x1920 60fps).

Themes with calm/passive pastel palettes:
1. mint_stars.mp4: Pastel Sage Mint (#98D7C2) + Cream Star Sparkles (#F4FBF7)
2. lavender_hearts.mp4: Pastel Lavender (#C8B6FF) + Soft Cloud Pink Hearts (#F7E8FF)
3. peach_butterflies.mp4: Soft Pastel Peach (#FFC6B3) + Vanilla Cream Butterflies (#FFF3EC)
4. sky_clouds.mp4: Pastel Baby Sky Blue (#A0C4FF) + Fluffy Marshmallow Clouds (#F0F6FF)
5. buttercup_daisies.mp4: Soft Buttercup Honey (#FDDE81) + Pure White Daisies (#FFFDF5)

All videos are 10.0s (600 frames) @ 60fps, 1080x1920, with 100% mathematically seamless wrap-around loop.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np


def create_star_sprite(w: int = 190, h: int = 190, color=(244, 251, 247, 255)) -> Image.Image:
    """Generate 4-pointed curved aesthetic sparkle star."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    r_outer = (w * ss) * 0.46
    r_inner = (w * ss) * 0.11

    pts = []
    # 8 points: alternating 4 tips and 4 inner curves
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


def create_heart_sprite(w: int = 210, h: int = 190, color=(247, 232, 255, 255)) -> Image.Image:
    """Generate smooth cute preppy cartoon heart."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx = (w * ss) / 2.0
    cy = (h * ss) * 0.45
    scale = (w * ss) * 0.026

    # Parametric heart curve: x = 16 sin^3(t), y = -(13 cos(t) - 5 cos(2t) - 2 cos(3t) - cos(4t))
    pts = []
    for step in range(120):
        t = step * (2.0 * math.pi / 120.0)
        x = 16.0 * (math.sin(t) ** 3)
        y = -(13.0 * math.cos(t) - 5.0 * math.cos(2 * t) - 2.0 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * scale, cy + y * scale))

    draw.polygon(pts, fill=color)
    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_butterfly_sprite(w: int = 220, h: int = 190, color=(255, 243, 236, 255)) -> Image.Image:
    """Generate aesthetic preppy butterfly vector."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    s = (w * ss) * 0.44

    # Upper wings (ellipses tilted)
    draw.ellipse([cx - s * 0.95, cy - s * 0.85, cx - s * 0.05, cy + s * 0.15], fill=color)
    draw.ellipse([cx + s * 0.05, cy - s * 0.85, cx + s * 0.95, cy + s * 0.15], fill=color)
    # Lower wings
    draw.ellipse([cx - s * 0.75, cy - s * 0.05, cx - s * 0.1, cy + s * 0.75], fill=color)
    draw.ellipse([cx + s * 0.1, cy - s * 0.05, cx + s * 0.75, cy + s * 0.75], fill=color)
    # Body
    draw.rounded_rectangle([cx - s * 0.08, cy - s * 0.7, cx + s * 0.08, cy + s * 0.7], radius=int(s*0.08), fill=color)

    # Slight tilt of -15 deg for dynamic preppy look
    rotated = canvas.rotate(-15, resample=Image.Resampling.BICUBIC)
    return rotated.resize((w, h), Image.Resampling.LANCZOS)


def create_cloud_sprite(w: int = 250, h: int = 160, color=(240, 246, 255, 255)) -> Image.Image:
    """Generate cute fluffy marshmallow cloud."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cw, ch = w * ss, h * ss

    # Flat bottom + 3 rounded puff domes
    base_y = ch * 0.75
    draw.ellipse([cw * 0.12, ch * 0.35, cw * 0.52, ch * 0.82], fill=color)
    draw.ellipse([cw * 0.35, ch * 0.15, cw * 0.75, ch * 0.82], fill=color)
    draw.ellipse([cw * 0.60, ch * 0.40, cw * 0.90, ch * 0.82], fill=color)
    draw.rounded_rectangle([cw * 0.15, ch * 0.55, cw * 0.87, base_y], radius=int(ch * 0.1), fill=color)

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_daisy_sprite(w: int = 210, h: int = 210, petal_color=(255, 253, 245, 255), center_color=(255, 215, 100, 255)) -> Image.Image:
    """Generate cute 5-petal daisy flower."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    r_center = (w * ss) * 0.16
    r_petal = (w * ss) * 0.23
    dist_petal = (w * ss) * 0.25

    # 5 Petals
    for i in range(5):
        angle = i * (2.0 * math.pi / 5.0) - (math.pi / 2.0)
        px = cx + dist_petal * math.cos(angle)
        py = cy + dist_petal * math.sin(angle)
        draw.ellipse([px - r_petal, py - r_petal, px + r_petal, py + r_petal], fill=petal_color)

    # Flower Center
    draw.ellipse([cx - r_center, cy - r_center, cx + r_center, cy + r_center], fill=center_color)

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def render_loop_video(
    output_path: Path,
    sprite: Image.Image,
    bg_color: tuple[int, int, int],
    step_x: int = 350,
    step_y: int = 375,
    width: int = 1080,
    height: int = 1920,
    fps: int = 60,
    duration_sec: int = 10,
) -> None:
    """Render a seamless 1080x1920 60fps MP4 loop using diagonal scrolling grid."""
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
            # Drifting diagonally:
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
    bg_dir = Path("assets/backgrounds")
    bg_dir.mkdir(parents=True, exist_ok=True)

    configs = [
        {
            "name": "mint_stars.mp4",
            "sprite": create_star_sprite(190, 190, (244, 251, 247, 255)),
            "bg": (152, 215, 194),  # #98D7C2 Pastel Sage Mint
            "step_x": 350,
            "step_y": 375,
        },
        {
            "name": "lavender_hearts.mp4",
            "sprite": create_heart_sprite(210, 190, (247, 232, 255, 255)),
            "bg": (200, 182, 255),  # #C8B6FF Pastel Lavender
            "step_x": 350,
            "step_y": 375,
        },
        {
            "name": "peach_butterflies.mp4",
            "sprite": create_butterfly_sprite(220, 190, (255, 243, 236, 255)),
            "bg": (255, 198, 179),  # #FFC6B3 Soft Pastel Peach
            "step_x": 350,
            "step_y": 375,
        },
        {
            "name": "sky_clouds.mp4",
            "sprite": create_cloud_sprite(250, 160, (240, 246, 255, 255)),
            "bg": (160, 196, 255),  # #A0C4FF Pastel Baby Sky Blue
            "step_x": 360,
            "step_y": 380,
        },
        {
            "name": "buttercup_daisies.mp4",
            "sprite": create_daisy_sprite(210, 210, (255, 253, 245, 255), (255, 215, 100, 255)),
            "bg": (253, 222, 129),  # #FDDE81 Soft Honey Buttercup
            "step_x": 350,
            "step_y": 375,
        },
    ]

    for cfg in configs:
        target = bg_dir / cfg["name"]
        print(f"Rendering {cfg['name']}...", flush=True)
        render_loop_video(
            output_path=target,
            sprite=cfg["sprite"],
            bg_color=cfg["bg"],
            step_x=cfg["step_x"],
            step_y=cfg["step_y"],
        )
        print(f"Finished {cfg['name']} ({target.stat().st_size} bytes)", flush=True)


if __name__ == "__main__":
    main()

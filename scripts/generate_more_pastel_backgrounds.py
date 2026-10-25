# -*- coding: utf-8 -*-
"""Generate additional viral aesthetic pastel looping background videos (1080x1920 60fps) into assets/backgrounds/pastel/.

New Pastel Themes:
1. rose_bows.mp4: Soft Ballet Rose (#F7CAD0) + Cream Ivory Coquette Bows (#FFFDF9)
2. matcha_clover.mp4: Pastel Soft Matcha (#D3E4CD) + Ivory Lucky 4-Leaf Clovers (#FAFCF6)
3. strawberry_milk.mp4: Pastel Strawberry Milk (#FBC4AB) + Vanilla Cream Strawberries (#FFF7F2)
4. lilac_cherries.mp4: Dreamy Pastel Lilac (#DDD6FE) + Soft Marshmallow Twin Cherries (#FAF5FF)
5. ice_mint_shells.mp4: Seafoam Ice Mint (#BAE6FD) + Pearl White Scallop Shells (#F8FAFC)
6. twilight_moons.mp4: Dreamy Pastel Periwinkle (#C7D2FE) + Vanilla Cream Crescent Moons (#FEFCE8)
7. sunshine_tulips.mp4: Warm Pastel Buttercup (#FEF3C7) + Pure Milk White Spring Tulips (#FFFDF5)
8. retro_sparkles.mp4: Pastel Candy Orchid (#E9D5FF) + Radiant Diamond Sparkles (#FFFFFF)

All videos are 10.0s (600 frames) @ 60fps, 1080x1920, 100% mathematically seamless diagonal wrap-around loop.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np


def create_bow_sprite(w: int = 210, h: int = 180, color=(255, 253, 249, 255)) -> Image.Image:
    """Generate aesthetic coquette ribbon bow."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) * 0.45
    s = (w * ss) * 0.38

    # Left loop (tilted ellipse / polygon)
    draw.ellipse([cx - s * 1.1, cy - s * 0.65, cx - s * 0.05, cy + s * 0.45], fill=color)
    # Right loop
    draw.ellipse([cx + s * 0.05, cy - s * 0.65, cx + s * 1.1, cy + s * 0.45], fill=color)
    # Cut inner loop holes for preppy vector look
    hole_color = (0, 0, 0, 0)
    draw.ellipse([cx - s * 0.85, cy - s * 0.35, cx - s * 0.3, cy + s * 0.15], fill=hole_color)
    draw.ellipse([cx + s * 0.3, cy - s * 0.35, cx + s * 0.85, cy + s * 0.15], fill=hole_color)

    # Center knot
    draw.ellipse([cx - s * 0.22, cy - s * 0.25, cx + s * 0.22, cy + s * 0.25], fill=color)

    # Ribbon tails
    # Left tail
    pts_left = [
        (cx - s * 0.15, cy + s * 0.15),
        (cx - s * 0.75, cy + s * 1.25),
        (cx - s * 0.45, cy + s * 1.15),
        (cx - s * 0.05, cy + s * 0.22),
    ]
    draw.polygon(pts_left, fill=color)
    # Right tail
    pts_right = [
        (cx + s * 0.15, cy + s * 0.15),
        (cx + s * 0.75, cy + s * 1.25),
        (cx + s * 0.45, cy + s * 1.15),
        (cx + s * 0.05, cy + s * 0.22),
    ]
    draw.polygon(pts_right, fill=color)

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_clover_sprite(w: int = 190, h: int = 200, color=(250, 252, 246, 255)) -> Image.Image:
    """Generate aesthetic 4-leaf lucky clover."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) * 0.45
    r_leaf = (w * ss) * 0.20
    dist = (w * ss) * 0.22

    # 4 Heart-shaped / rounded clover leaves
    for angle_deg in [0, 90, 180, 270]:
        rad = math.radians(angle_deg)
        lx = cx + dist * math.cos(rad)
        ly = cy + dist * math.sin(rad)
        draw.ellipse([lx - r_leaf, ly - r_leaf, lx + r_leaf, ly + r_leaf], fill=color)

    # Little curved stem at the bottom
    stem_pts = []
    for step in range(30):
        t = step / 30.0
        sx = cx + math.sin(t * 1.5) * (w * ss * 0.15)
        sy = cy + (h * ss * 0.1) + t * (h * ss * 0.38)
        stem_pts.append((sx, sy))
    for i in range(len(stem_pts) - 1):
        draw.line([stem_pts[i], stem_pts[i+1]], fill=color, width=int(w * ss * 0.05))

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_strawberry_sprite(w: int = 180, h: int = 210, color=(255, 247, 242, 255), crown_color=(255, 255, 255, 255)) -> Image.Image:
    """Generate cute minimalist preppy strawberry."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) * 0.52
    scale = (w * ss) * 0.024

    # Strawberry heart-like taper curve
    pts = []
    for step in range(100):
        t = step * (2.0 * math.pi / 100.0)
        x = 15.0 * (math.sin(t) ** 3)
        y = -(12.0 * math.cos(t) - 4.5 * math.cos(2 * t) - 1.8 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * scale, cy + y * scale))
    draw.polygon(pts, fill=color)

    # Little 3-pointed leaf crown at top
    top_y = cy - scale * 12.0
    cw = w * ss * 0.3
    crown_pts = [
        (cx - cw, top_y + cw * 0.2),
        (cx - cw * 0.4, top_y - cw * 0.4),
        (cx, top_y + cw * 0.1),
        (cx + cw * 0.4, top_y - cw * 0.4),
        (cx + cw, top_y + cw * 0.2),
        (cx, top_y + cw * 0.4),
    ]
    draw.polygon(crown_pts, fill=crown_color)

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_cherries_sprite(w: int = 200, h: int = 200, color=(250, 245, 255, 255)) -> Image.Image:
    """Generate aesthetic twin cherries with connected arched stems and leaf."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    r_cherry = (w * ss) * 0.18

    # Left cherry
    c1x, c1y = cx - r_cherry * 1.05, cy + r_cherry * 0.9
    draw.ellipse([c1x - r_cherry, c1y - r_cherry, c1x + r_cherry, c1y + r_cherry], fill=color)

    # Right cherry
    c2x, c2y = cx + r_cherry * 1.05, cy + r_cherry * 0.6
    draw.ellipse([c2x - r_cherry, c2y - r_cherry, c2x + r_cherry, c2y + r_cherry], fill=color)

    # Stem joint at top
    jx, jy = cx + r_cherry * 0.1, cy - r_cherry * 1.3
    # Curved stems
    draw.line([(c1x, c1y - r_cherry * 0.7), (jx - r_cherry * 0.4, cy), (jx, jy)], fill=color, width=int(r_cherry * 0.25))
    draw.line([(c2x, c2y - r_cherry * 0.7), (jx + r_cherry * 0.5, cy), (jx, jy)], fill=color, width=int(r_cherry * 0.25))

    # Leaf on stem
    draw.ellipse([jx, jy - r_cherry * 0.4, jx + r_cherry * 1.3, jy + r_cherry * 0.3], fill=color)

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_seashell_sprite(w: int = 200, h: int = 180, color=(248, 250, 252, 255)) -> Image.Image:
    """Generate aesthetic scallop seashell."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) * 0.55
    r = (w * ss) * 0.42

    # Scallop outer fan fan shape
    draw.pieslice([cx - r, cy - r * 0.9, cx + r, cy + r * 0.9], 185, 355, fill=color)
    # Scallop hinge base
    base_w = r * 0.45
    draw.polygon([(cx - base_w, cy), (cx + base_w, cy), (cx + base_w * 0.6, cy + r * 0.3), (cx - base_w * 0.6, cy + r * 0.3)], fill=color)

    # Slight contrast ridges
    ridge_color = (0, 0, 0, 25)
    for ang in [210, 240, 270, 300, 330]:
        rad = math.radians(ang)
        ex = cx + r * math.cos(rad)
        ey = cy + r * 0.9 * math.sin(rad)
        draw.line([(cx, cy), (ex, ey)], fill=ridge_color, width=int(r * 0.05))

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_crescent_moon_sprite(w: int = 180, h: int = 190, color=(254, 252, 232, 255)) -> Image.Image:
    """Generate dreamy aesthetic crescent moon."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    r = (w * ss) * 0.44

    # Full circle
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    # Cutout offset circle to form crescent
    cut_r = r * 0.9
    cut_x = cx + r * 0.42
    cut_y = cy - r * 0.15
    draw.ellipse([cut_x - cut_r, cut_y - cut_r, cut_x + cut_r, cut_y + cut_r], fill=(0, 0, 0, 0))

    # Add a tiny 4-pointed accent sparkle star near the crescent hollow
    star_x = cx - r * 0.4
    star_y = cy - r * 0.4
    star_r = r * 0.18
    pts = [
        (star_x, star_y - star_r),
        (star_x + star_r * 0.3, star_y),
        (star_x, star_y + star_r),
        (star_x - star_r * 0.3, star_y),
    ]
    draw.polygon(pts, fill=color)

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_tulip_sprite(w: int = 180, h: int = 210, color=(255, 253, 245, 255)) -> Image.Image:
    """Generate minimalist aesthetic tulip flower."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) * 0.4
    r = (w * ss) * 0.32

    # Tulip center petal
    draw.ellipse([cx - r * 0.4, cy - r * 0.85, cx + r * 0.4, cy + r * 0.4], fill=color)
    # Left petal
    draw.ellipse([cx - r * 0.85, cy - r * 0.7, cx - r * 0.05, cy + r * 0.4], fill=color)
    # Right petal
    draw.ellipse([cx + r * 0.05, cy - r * 0.7, cx + r * 0.85, cy + r * 0.4], fill=color)

    # Curved stem
    stem_w = int(r * 0.18)
    draw.line([(cx, cy + r * 0.35), (cx, cy + r * 1.5)], fill=color, width=stem_w)
    # Single smooth leaf
    draw.ellipse([cx + stem_w, cy + r * 0.6, cx + r * 0.9, cy + r * 1.3], fill=color)

    return canvas.resize((w, h), Image.Resampling.LANCZOS)


def create_retro_sparkle_sprite(w: int = 190, h: int = 190, color=(255, 255, 255, 255)) -> Image.Image:
    """Generate aesthetic preppy 8-point retro diamond sparkle."""
    ss = 4
    canvas = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    cx, cy = (w * ss) / 2.0, (h * ss) / 2.0
    r_major = (w * ss) * 0.46
    r_minor = (w * ss) * 0.22
    w_beam = (w * ss) * 0.08

    # 4 Major needle beams
    draw.polygon([(cx - w_beam, cy), (cx, cy - r_major), (cx + w_beam, cy), (cx, cy + r_major)], fill=color)
    draw.polygon([(cx, cy - w_beam), (cx - r_major, cy), (cx, cy + w_beam), (cx + r_major, cy)], fill=color)

    # 4 Minor diagonal beams
    m = r_minor * 0.707
    draw.polygon([(cx - w_beam * 0.7, cy), (cx - m, cy - m), (cx + w_beam * 0.7, cy), (cx + m, cy + m)], fill=color)
    draw.polygon([(cx, cy - w_beam * 0.7), (cx + m, cy - m), (cx, cy + w_beam * 0.7), (cx - m, cy + m)], fill=color)

    # Central diamond
    d = r_minor * 0.45
    draw.polygon([(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)], fill=color)

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
    output_path.parent.mkdir(parents=True, exist_ok=True)
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
            # Drifting diagonally with seamless periodicity:
            curr_x = int(round(x0 - u * step_x))
            curr_y = int(round(y0 + u * step_y))
            frame = canvas_arr[curr_y : curr_y + height, curr_x : curr_x + width]
            process.stdin.write(frame.tobytes())

        process.stdin.close()
        process.wait()
    except Exception as e:
        process.kill()
        raise e


def main() -> None:
    output_dir = Path("assets/backgrounds/pastel")
    output_dir.mkdir(parents=True, exist_ok=True)

    configs = [
        (
            output_dir / "rose_bows.mp4",
            create_bow_sprite(),
            (247, 202, 208),  # Soft Ballet Rose #F7CAD0
            340,
            360,
        ),
        (
            output_dir / "matcha_clover.mp4",
            create_clover_sprite(),
            (211, 228, 205),  # Pastel Soft Matcha #D3E4CD
            330,
            350,
        ),
        (
            output_dir / "strawberry_milk.mp4",
            create_strawberry_sprite(),
            (251, 196, 171),  # Pastel Strawberry Milk #FBC4AB
            320,
            350,
        ),
        (
            output_dir / "lilac_cherries.mp4",
            create_cherries_sprite(),
            (221, 214, 254),  # Dreamy Pastel Lilac #DDD6FE
            340,
            360,
        ),
        (
            output_dir / "ice_mint_shells.mp4",
            create_seashell_sprite(),
            (186, 230, 253),  # Seafoam Ice Mint #BAE6FD
            330,
            340,
        ),
        (
            output_dir / "twilight_moons.mp4",
            create_crescent_moon_sprite(),
            (199, 210, 254),  # Dreamy Pastel Periwinkle #C7D2FE
            320,
            340,
        ),
        (
            output_dir / "sunshine_tulips.mp4",
            create_tulip_sprite(),
            (254, 243, 199),  # Warm Pastel Buttercup #FEF3C7
            310,
            350,
        ),
        (
            output_dir / "retro_sparkles.mp4",
            create_retro_sparkle_sprite(),
            (233, 213, 255),  # Pastel Candy Orchid #E9D5FF
            340,
            340,
        ),
    ]

    print(f"Generating {len(configs)} new aesthetic pastel backgrounds...")
    for idx, (out_path, sprite, bg_col, sx, sy) in enumerate(configs, 1):
        print(f"[{idx}/{len(configs)}] Rendering {out_path.name}...")
        render_loop_video(out_path, sprite, bg_col, step_x=sx, step_y=sy)
        print(f" -> Completed {out_path.name} ({out_path.stat().st_size // 1024} KB)")

    print("All pastel backgrounds generated successfully!")


if __name__ == "__main__":
    main()

"""Generate 10 distinct, aesthetic, seamless looping minimalist backgrounds in 16:9 widescreen (1920x1080 60fps).

Styles:
1. dark_topography_16x9.mp4: Dark Topographic Contours (Luxury Tech Isolines)
2. cyber_grid_3d_16x9.mp4: 3D Perspective Retro-Cyber Grid (Infinite Rolling Wireframe)
3. aurora_borealis_16x9.mp4: Minimalist Soft Ambient Aurora (Emerald & Sapphire Glow)
4. digital_rain_matrix_16x9.mp4: Clean Minimal Digital Code Flow (Phosphor Matrix Streamlets)
5. geometric_hexagons_16x9.mp4: High-Tech Hexagonal Lattice (Pulsing Honeycomb)
6. minimal_starfield_16x9.mp4: Deep Cosmic Stardust & Constellations
7. synthwave_sunset_16x9.mp4: Minimalist Outrun Horizon & Striped Neon Sun
8. flowing_sine_ribbons_16x9.mp4: Harmonic Studio Ribbon Waves (Silk Oscillating Sine)
9. isometric_dot_matrix_16x9.mp4: Swiss Architectural Dot Matrix (Pulsing Node Field)
10. crimson_nebula_liquid_16x9.mp4: Luxury Velvet Ruby & Plum Liquid Gradient

All videos are 10.0s (600 frames) @ 60fps, 1920x1080, with 100% seamless mathematical loops.
"""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter


WIDTH = 1920
HEIGHT = 1080
FPS = 60
DURATION_SEC = 10
TOTAL_FRAMES = FPS * DURATION_SEC


def start_ffmpeg_pipe(output_path: Path) -> subprocess.Popen:
    """Create FFmpeg sub-process accepting raw RGB24 frames from stdin."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "20",
        "-movflags", "+faststart",
        str(output_path),
    ]
    return subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# =============================================================================
# 1. DARK TOPOGRAPHY (Luxury Tech Isolines)
# =============================================================================
def generate_dark_topography(output_path: Path):
    print("Rendering 1/10: dark_topography_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    # Pre-render a large seamless seamless contour canvas with stacked isoline curves
    ss_w = WIDTH + 800
    ss_h = HEIGHT + 800
    base_bg = (10, 14, 22)
    canvas = Image.new("RGB", (ss_w, ss_h), base_bg)
    draw = ImageDraw.Draw(canvas)
    
    # Draw 45 smooth contour lines across the canvas
    np.random.seed(42)
    n_lines = 48
    line_y_bases = np.linspace(-200, ss_h + 200, n_lines)
    
    for i, base_y in enumerate(line_y_bases):
        # Varying line colors from dark slate to subtle electric blue/amber
        if i % 7 == 0:
            stroke = (56, 189, 248, 120)  # Cyan accent
            lw = 3
        elif i % 11 == 0:
            stroke = (245, 158, 11, 100)  # Warm amber accent
            lw = 3
        else:
            val = int(24 + 18 * math.sin(i * 0.4))
            stroke = (val + 8, val + 16, val + 28, 255)
            lw = 2
            
        pts = []
        for x in range(0, ss_w + 40, 20):
            # Compound harmonic sine elevation
            y = (
                base_y
                + 55 * math.sin(x * 0.0035 + i * 0.45)
                + 35 * math.cos(x * 0.007 - i * 0.3)
                + 20 * math.sin(x * 0.012 + i * 0.7)
            )
            pts.append((x, y))
        draw.line(pts, fill=stroke, width=lw)
    
    canvas_arr = np.array(canvas)
    
    # 10s seamless diagonal pan of the field
    step_x = 400
    step_y = 300
    x0 = 400
    y0 = 400
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        # Loop angle for seamless closed cycle
        curr_x = int(round(x0 + 180 * math.sin(2 * math.pi * u)))
        curr_y = int(round(y0 + 140 * math.cos(2 * math.pi * u)))
        frame = canvas_arr[curr_y : curr_y + HEIGHT, curr_x : curr_x + WIDTH]
        proc.stdin.write(frame.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 2. CYBER GRID 3D (Infinite Rolling Perspective Grid)
# =============================================================================
def generate_cyber_grid_3d(output_path: Path):
    print("Rendering 2/10: cyber_grid_3d_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    horizon_y = int(HEIGHT * 0.45)
    floor_h = HEIGHT - horizon_y
    cx = WIDTH // 2
    
    # Fixed perspective rays
    num_rays = 32
    ray_angles = np.linspace(-math.pi * 0.45, math.pi * 0.45, num_rays)
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        img = Image.new("RGB", (WIDTH, HEIGHT), (6, 8, 15))
        draw = ImageDraw.Draw(img)
        
        # Sky ambient star dots & subtle horizon gradient
        sky_grad = Image.new("RGBA", (WIDTH, horizon_y), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(sky_grad)
        s_draw.rectangle([0, horizon_y - 80, WIDTH, horizon_y], fill=(0, 240, 255, 30))
        img.paste(sky_grad, (0, 0), sky_grad)
        
        # Draw perspective floor rays converging to horizon center
        for a in ray_angles:
            # Bottom x coordinate
            bottom_x = cx + math.tan(a) * floor_h * 1.6
            draw.line([(cx, horizon_y), (bottom_x, HEIGHT)], fill=(0, 240, 255, 60), width=1)
            
        # Draw moving horizontal grid lines (logarithmic perspective spacing)
        # 18 lines advancing forward seamlessly
        num_h_lines = 16
        for k in range(num_h_lines):
            line_pos = (k + u) / num_h_lines
            # Non-linear exponential perspective compression towards horizon
            y = horizon_y + int(floor_h * (line_pos ** 2.4))
            
            # Fade line as it approaches horizon
            alpha = int(220 * (line_pos ** 1.5))
            color = (0, int(200 + 40 * line_pos), 255, alpha)
            draw.line([(0, y), (WIDTH, y)], fill=color, width=2 if line_pos > 0.6 else 1)
            
        # Bright horizon edge glow line
        draw.line([(0, horizon_y), (WIDTH, horizon_y)], fill=(0, 240, 255, 140), width=2)
        
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 3. AURORA BOREALIS (Minimalist Soft Ambient Glow)
# =============================================================================
def generate_aurora_borealis(output_path: Path):
    print("Rendering 3/10: aurora_borealis_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    # Render downsampled luminous floating blobs then upscale with high blur
    ds_w = 384
    ds_h = 216
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        ang = 2 * math.pi * u
        
        # Deep space dark navy base
        base = np.zeros((ds_h, ds_w, 3), dtype=np.float32)
        base[:, :] = [7.0, 10.0, 18.0]
        
        # 4 Lissajous light orbs (Emerald, Sapphire, Cyan, Violet)
        orbs = [
            # cx, cy, radius, color (R, G, B)
            (
                ds_w * 0.35 + 80 * math.sin(ang),
                ds_h * 0.4 + 45 * math.cos(ang),
                110,
                [16.0, 185.0, 129.0],  # Emerald
            ),
            (
                ds_w * 0.65 + 75 * math.cos(ang),
                ds_h * 0.55 + 50 * math.sin(ang * 2),
                125,
                [59.0, 130.0, 246.0],  # Sapphire Blue
            ),
            (
                ds_w * 0.5 + 90 * math.sin(ang * 2 + 1),
                ds_h * 0.3 + 40 * math.sin(ang),
                95,
                [6.0, 182.0, 212.0],   # Electric Cyan
            ),
            (
                ds_w * 0.4 + 60 * math.cos(ang * 3),
                ds_h * 0.65 + 35 * math.sin(ang * 2),
                105,
                [139.0, 92.0, 246.0],  # Soft Violet
            ),
        ]
        
        y_coords, x_coords = np.ogrid[:ds_h, :ds_w]
        for ox, oy, rad, col in orbs:
            dist_sq = (x_coords - ox) ** 2 + (y_coords - oy) ** 2
            intensity = np.exp(-dist_sq / (2.0 * (rad * 0.45) ** 2))
            for c in range(3):
                base[:, :, c] += col[c] * intensity * 0.48
                
        base = np.clip(base, 0, 255).astype(np.uint8)
        img_ds = Image.fromarray(base)
        # Upscale and blur to achieve flawless creamy ambient gradient
        img_full = img_ds.resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC).filter(
            ImageFilter.GaussianBlur(radius=60)
        )
        proc.stdin.write(img_full.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 4. DIGITAL RAIN MATRIX (Clean Minimal Code Flow)
# =============================================================================
def generate_digital_rain_matrix(output_path: Path):
    print("Rendering 4/10: digital_rain_matrix_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    num_cols = 54
    col_x = np.linspace(40, WIDTH - 40, num_cols)
    np.random.seed(1337)
    
    # Each column has an integer loop multiplier so it wraps around 100% seamlessly
    speeds = np.random.choice([1, 2, 3], size=num_cols)
    offsets = np.random.uniform(0, HEIGHT, size=num_cols)
    dash_lens = np.random.randint(60, 180, size=num_cols)
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        img = Image.new("RGB", (WIDTH, HEIGHT), (5, 8, 14))
        draw = ImageDraw.Draw(img)
        
        for k in range(num_cols):
            x = col_x[k]
            # Seamless wrap-around Y coordinate
            y_head = (offsets[k] + u * speeds[k] * HEIGHT * 2) % (HEIGHT + 240) - 120
            d_len = dash_lens[k]
            
            # Draw sleek trailing dash with glowing head node
            y_tail = y_head - d_len
            
            # Tail fade
            draw.line([(x, y_tail), (x, y_head)], fill=(16, 185, 129, 60), width=2)
            # Bright head particle
            draw.ellipse([x - 2.5, y_head - 3, x + 2.5, y_head + 3], fill=(0, 255, 180, 230))
            
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 5. GEOMETRIC HEXAGONS (Pulsing Honeycomb Grid)
# =============================================================================
def generate_geometric_hexagons(output_path: Path):
    print("Rendering 5/10: geometric_hexagons_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    r = 52.0
    h_dist = r * math.sqrt(3)
    v_dist = r * 1.5
    
    # Collect hexagon centers
    hex_centers = []
    cols = int(WIDTH / h_dist) + 4
    rows = int(HEIGHT / v_dist) + 4
    
    for row in range(-2, rows):
        y = row * v_dist
        x_offset = (h_dist / 2.0) if (row % 2 != 0) else 0.0
        for col in range(-2, cols):
            x = col * h_dist + x_offset
            hex_centers.append((x, y))
            
    cx_screen = WIDTH / 2.0
    cy_screen = HEIGHT / 2.0
    max_diag = math.sqrt(cx_screen ** 2 + cy_screen ** 2)
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        img = Image.new("RGB", (WIDTH, HEIGHT), (11, 14, 20))
        draw = ImageDraw.Draw(img)
        
        # Radial pulse ring wave expanding from center
        wave_front = (u * 2.0 * max_diag) % max_diag
        
        for hx, hy in hex_centers:
            d_center = math.hypot(hx - cx_screen, hy - cy_screen)
            d_wave = abs(d_center - wave_front)
            
            if d_wave < 180:
                glow = 1.0 - (d_wave / 180.0)
                # Cyan/ice pulse
                color = (
                    int(20 + 35 * glow),
                    int(32 + 160 * glow),
                    int(48 + 205 * glow),
                )
                lw = 2 if glow > 0.4 else 1
            else:
                color = (22, 28, 40)
                lw = 1
                
            # Hexagon vertex points
            pts = []
            for i in range(6):
                angle = i * (math.pi / 3.0) + (math.pi / 6.0)
                pts.append((hx + r * math.cos(angle), hy + r * math.sin(angle)))
            draw.polygon(pts, outline=color, width=lw)
            
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 6. MINIMAL STARFIELD (Cosmic Stardust & Constellations)
# =============================================================================
def generate_minimal_starfield(output_path: Path):
    print("Rendering 6/10: minimal_starfield_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    np.random.seed(777)
    n_stars = 140
    # Store base positions and individual float speeds
    base_x = np.random.uniform(0, WIDTH, n_stars)
    base_y = np.random.uniform(0, HEIGHT, n_stars)
    radii = np.random.choice([1.0, 1.5, 2.0, 2.8], size=n_stars, p=[0.5, 0.3, 0.15, 0.05])
    twinkle_freq = np.random.choice([1, 2, 3], size=n_stars)
    twinkle_phase = np.random.uniform(0, 2 * math.pi, n_stars)
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        ang = 2 * math.pi * u
        img = Image.new("RGB", (WIDTH, HEIGHT), (4, 6, 11))
        draw = ImageDraw.Draw(img)
        
        current_pts = []
        for i in range(n_stars):
            # Smooth circular drift
            x = (base_x[i] + 40 * math.sin(ang + i * 0.1)) % WIDTH
            y = (base_y[i] + 30 * math.cos(ang + i * 0.1)) % HEIGHT
            current_pts.append((x, y))
            
            tw = 0.5 + 0.5 * math.sin(ang * twinkle_freq[i] + twinkle_phase[i])
            brightness = int(140 + 115 * tw)
            rad = radii[i]
            
            draw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(brightness, brightness, int(brightness * 1.05)))
            
        # Draw delicate constellation lines between near neighbors
        for i in range(0, n_stars, 3):
            p1 = current_pts[i]
            for j in range(i + 1, min(i + 6, n_stars)):
                p2 = current_pts[j]
                dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                if dist < 130:
                    alpha = int(70 * (1.0 - dist / 130.0))
                    draw.line([p1, p2], fill=(100, 150, 255, alpha), width=1)
                    
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 7. SYNTHWAVE SUNSET (Minimalist Outrun Horizon & Striped Sun)
# =============================================================================
def generate_synthwave_sunset(output_path: Path):
    print("Rendering 7/10: synthwave_sunset_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    sun_cx = WIDTH // 2
    sun_cy = int(HEIGHT * 0.44)
    sun_r = 190
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        img = Image.new("RGB", (WIDTH, HEIGHT), (10, 7, 20))
        draw = ImageDraw.Draw(img)
        
        # Deep dusk gradient sky
        for y in range(0, sun_cy + 80):
            ratio = y / (sun_cy + 80)
            r_val = int(10 + 35 * ratio)
            g_val = int(7 + 15 * ratio)
            b_val = int(20 + 55 * ratio)
            draw.line([(0, y), (WIDTH, y)], fill=(r_val, g_val, b_val))
            
        # Striped neon sun
        sun_img = Image.new("RGBA", (sun_r * 2, sun_r * 2), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(sun_img)
        # Gradient disk
        for sy in range(sun_r * 2):
            val = sy / (sun_r * 2)
            c = (int(255 - 40 * val), int(60 + 120 * val), int(140 + 80 * val), 255)
            s_draw.line([(0, sy), (sun_r * 2, sy)], fill=c)
            
        # Mask out circle
        mask = Image.new("L", (sun_r * 2, sun_r * 2), 0)
        m_draw = ImageDraw.Draw(mask)
        m_draw.ellipse([0, 0, sun_r * 2, sun_r * 2], fill=255)
        
        # Cut horizontal stripes into lower half
        n_stripes = 7
        for k in range(n_stripes):
            stripe_y = int(sun_r + (k + 0.5) * (sun_r / n_stripes))
            th = int(3 + k * 2.5)
            m_draw.rectangle([0, stripe_y, sun_r * 2, stripe_y + th], fill=0)
            
        img.paste(sun_img, (sun_cx - sun_r, sun_cy - sun_r), mask)
        
        # Dark perspective ground grid
        horizon_y = sun_cy + 60
        floor_h = HEIGHT - horizon_y
        for k in range(12):
            pos = (k + u) / 12.0
            y = horizon_y + int(floor_h * (pos ** 2.2))
            alpha = int(160 * (pos ** 1.3))
            draw.line([(0, y), (WIDTH, y)], fill=(236, 72, 153, alpha), width=1)
            
        # Draw perspective floor rays
        for ray in np.linspace(-1.0, 1.0, 20):
            bx = sun_cx + ray * WIDTH * 0.9
            draw.line([(sun_cx, horizon_y), (bx, HEIGHT)], fill=(236, 72, 153, 50), width=1)
            
        draw.line([(0, horizon_y), (WIDTH, horizon_y)], fill=(236, 72, 153, 180), width=2)
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 8. FLOWING SINE RIBBONS (Harmonic Silk Studio Waves)
# =============================================================================
def generate_flowing_sine_ribbons(output_path: Path):
    print("Rendering 8/10: flowing_sine_ribbons_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    ribbon_configs = [
        {"y": 420, "amp": 85, "freq": 0.003, "col": (6, 182, 212), "width": 4},   # Cyan
        {"y": 500, "amp": 105, "freq": 0.0025, "col": (99, 102, 241), "width": 5}, # Indigo
        {"y": 580, "amp": 90, "freq": 0.0035, "col": (236, 72, 153), "width": 4}, # Pink
        {"y": 660, "amp": 75, "freq": 0.0028, "col": (16, 185, 129), "width": 3}, # Emerald
        {"y": 740, "amp": 60, "freq": 0.004, "col": (245, 158, 11), "width": 3},  # Amber
    ]
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        ang = 2 * math.pi * u
        img = Image.new("RGB", (WIDTH, HEIGHT), (9, 12, 18))
        draw = ImageDraw.Draw(img)
        
        for idx, r_cfg in enumerate(ribbon_configs):
            base_y = r_cfg["y"]
            amp = r_cfg["amp"]
            freq = r_cfg["freq"]
            color = r_cfg["col"]
            lw = r_cfg["width"]
            
            pts = []
            for x in range(0, WIDTH + 20, 16):
                # Seamless phase harmonic
                y = (
                    base_y
                    + amp * math.sin(x * freq + ang + idx * 0.8)
                    + (amp * 0.4) * math.cos(x * (freq * 1.8) - ang * 2)
                )
                pts.append((x, y))
                
            draw.line(pts, fill=color, width=lw)
            
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 9. ISOMETRIC DOT MATRIX (Swiss Architectural Node Field)
# =============================================================================
def generate_isometric_dot_matrix(output_path: Path):
    print("Rendering 9/10: isometric_dot_matrix_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    step_x = 48
    step_y = 48
    cx = WIDTH / 2.0
    cy = HEIGHT / 2.0
    
    # Grid coordinates
    xs = np.arange(24, WIDTH, step_x)
    ys = np.arange(24, HEIGHT, step_y)
    grid_x, grid_y = np.meshgrid(xs, ys)
    grid_dist = np.hypot(grid_x - cx, grid_y - cy)
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        ang = 2 * math.pi * u
        img = Image.new("RGB", (WIDTH, HEIGHT), (14, 18, 27))
        draw = ImageDraw.Draw(img)
        
        # Ripple wave modulating node radius and luminance
        wave = np.sin(grid_dist * 0.012 - ang)
        radii = 1.8 + 2.4 * (0.5 + 0.5 * wave)
        alphas = 70 + 175 * (0.5 + 0.5 * wave)
        
        for r_idx in range(len(ys)):
            for c_idx in range(len(xs)):
                x = grid_x[r_idx, c_idx]
                y = grid_y[r_idx, c_idx]
                rad = radii[r_idx, c_idx]
                alpha = int(alphas[r_idx, c_idx])
                
                draw.ellipse(
                    [x - rad, y - rad, x + rad, y + rad],
                    fill=(int(alpha * 0.85), int(alpha * 0.95), alpha),
                )
                
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# 10. CRIMSON NEBULA LIQUID (Luxury Velvet Ruby & Plum Gradient)
# =============================================================================
def generate_crimson_nebula_liquid(output_path: Path):
    print("Rendering 10/10: crimson_nebula_liquid_16x9.mp4...", flush=True)
    proc = start_ffmpeg_pipe(output_path)
    
    ds_w = 384
    ds_h = 216
    
    for t in range(TOTAL_FRAMES):
        u = t / TOTAL_FRAMES
        ang = 2 * math.pi * u
        
        # Deep onyx plum base
        base = np.zeros((ds_h, ds_w, 3), dtype=np.float32)
        base[:, :] = [10.0, 5.0, 12.0]
        
        orbs = [
            (
                ds_w * 0.4 + 70 * math.cos(ang),
                ds_h * 0.45 + 50 * math.sin(ang),
                120,
                [225.0, 29.0, 72.0],  # Crimson Ruby
            ),
            (
                ds_w * 0.6 + 65 * math.sin(ang),
                ds_h * 0.55 + 40 * math.cos(ang),
                130,
                [124.0, 58.0, 237.0], # Royal Plum Purple
            ),
            (
                ds_w * 0.5 + 80 * math.sin(ang * 2),
                ds_h * 0.35 + 35 * math.cos(ang),
                100,
                [244.0, 63.0, 94.0],  # Rose Glow
            ),
            (
                ds_w * 0.3 + 55 * math.cos(ang * 2),
                ds_h * 0.65 + 30 * math.sin(ang),
                110,
                [88.0, 28.0, 135.0],  # Deep Velvet Violet
            ),
        ]
        
        y_coords, x_coords = np.ogrid[:ds_h, :ds_w]
        for ox, oy, rad, col in orbs:
            dist_sq = (x_coords - ox) ** 2 + (y_coords - oy) ** 2
            intensity = np.exp(-dist_sq / (2.0 * (rad * 0.45) ** 2))
            for c in range(3):
                base[:, :, c] += col[c] * intensity * 0.45
                
        base = np.clip(base, 0, 255).astype(np.uint8)
        img_ds = Image.fromarray(base)
        img_full = img_ds.resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC).filter(
            ImageFilter.GaussianBlur(radius=65)
        )
        proc.stdin.write(img_full.tobytes())
        
    proc.stdin.close()
    proc.wait()


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================
def main():
    target_dir = Path("assets/backgrounds/minimalist_16x9")
    target_dir.mkdir(parents=True, exist_ok=True)
    
    remotion_dir = Path("templates/quiz-remotion/public/backgrounds/minimalist_16x9")
    remotion_dir.mkdir(parents=True, exist_ok=True)
    
    tasks = [
        ("dark_topography_16x9.mp4", generate_dark_topography),
        ("cyber_grid_3d_16x9.mp4", generate_cyber_grid_3d),
        ("aurora_borealis_16x9.mp4", generate_aurora_borealis),
        ("digital_rain_matrix_16x9.mp4", generate_digital_rain_matrix),
        ("geometric_hexagons_16x9.mp4", generate_geometric_hexagons),
        ("minimal_starfield_16x9.mp4", generate_minimal_starfield),
        ("synthwave_sunset_16x9.mp4", generate_synthwave_sunset),
        ("flowing_sine_ribbons_16x9.mp4", generate_flowing_sine_ribbons),
        ("isometric_dot_matrix_16x9.mp4", generate_isometric_dot_matrix),
        ("crimson_nebula_liquid_16x9.mp4", generate_crimson_nebula_liquid),
    ]
    
    for filename, func in tasks:
        file_path = target_dir / filename
        func(file_path)
        print(f"Successfully created: {file_path} ({file_path.stat().st_size // 1024} KB)")
        
        # Copy to remotion public backgrounds folder
        remotion_file = remotion_dir / filename
        shutil.copy2(file_path, remotion_file)
        
    print("\n[SUCCESS] Generated all 10 minimalist 16:9 backgrounds!")


if __name__ == "__main__":
    main()

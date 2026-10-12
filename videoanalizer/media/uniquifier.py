"""Video uniquifier and anti-fingerprint engine for TikTok, YouTube Shorts, and Reels."""

import logging
import secrets
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from videoanalizer.exceptions import MediaProcessingError
from videoanalizer.quiz.models import RenderProfile
from videoanalizer.utils.hardware import get_active_encoder_args, get_hardware_capabilities

logger = logging.getLogger(__name__)

_sys_random = secrets.SystemRandom()


class VideoUniquifierConfig(BaseModel):
    """Configuration for final video anti-fingerprint and uniqueness processor."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=False,
        description="Master toggle for video uniquifier post-processing.",
    )
    mode: Literal["smart_random", "custom"] = Field(
        default="smart_random",
        description=(
            "Mode: 'smart_random' for automatic subtle variations, 'custom' for manual parameters."
        ),
    )
    # Visual Tweaks
    brightness: float = Field(
        default=0.02,
        ge=-0.15,
        le=0.15,
        description="Brightness shift (-0.15 to +0.15).",
    )
    contrast: float = Field(
        default=1.04,
        ge=0.85,
        le=1.25,
        description="Contrast multiplier (0.85 to 1.25).",
    )
    saturation: float = Field(
        default=1.08,
        ge=0.80,
        le=1.35,
        description="Saturation multiplier (0.80 to 1.35).",
    )
    gamma: float = Field(
        default=1.01,
        ge=0.85,
        le=1.20,
        description="Gamma correction (0.85 to 1.20).",
    )
    zoom_percent: float = Field(
        default=1.02,
        ge=1.00,
        le=1.05,
        description="Micro-crop zoom factor (1.00 to 1.05 = 0% to 5% zoom).",
    )
    noise_intensity: float = Field(
        default=1.5,
        ge=0.0,
        le=5.0,
        description="Subtle film grain/noise strength (0 to 5.0).",
    )
    flip_horizontal: bool = Field(
        default=False,
        description="Mirror/flip video horizontally.",
    )

    # Audio Tweaks (Acoustic Fingerprint Disruption)
    audio_tempo_drift: float = Field(
        default=1.005,
        ge=0.98,
        le=1.03,
        description="Audio micro-tempo shift (0.98 to 1.03).",
    )

    # Metadata & Container
    strip_metadata: bool = Field(
        default=True,
        description="Strip original metadata and container tags.",
    )
    render_profile: RenderProfile = Field(
        default=RenderProfile.GPU_FAST,
        description="Encoder profile used during re-encoding ('gpu_fast' or 'cpu_safe').",
    )


def generate_uniquifier_parameters(
    config: VideoUniquifierConfig,
) -> dict[str, float | bool]:
    """Generate resolved parameters, computing random variations in smart_random mode."""
    if config.mode == "smart_random":
        # Subtle, visually pleasing random offsets that change every video's digital hash
        b = round(_sys_random.uniform(0.012, 0.035) * _sys_random.choice([1, -1]), 4)
        c = round(_sys_random.uniform(1.02, 1.055), 4)
        s = round(_sys_random.uniform(1.04, 1.095), 4)
        g = round(_sys_random.uniform(0.985, 1.02), 4)
        z = round(_sys_random.uniform(1.012, 1.026), 4)
        n = round(_sys_random.uniform(1.0, 2.0), 1)
        t = round(_sys_random.uniform(1.003, 1.008), 4)
        flip = config.flip_horizontal
    else:
        b = round(config.brightness, 4)
        c = round(config.contrast, 4)
        s = round(config.saturation, 4)
        g = round(config.gamma, 4)
        z = round(config.zoom_percent, 4)
        n = round(config.noise_intensity, 1)
        t = round(config.audio_tempo_drift, 4)
        flip = config.flip_horizontal

    return {
        "brightness": b,
        "contrast": c,
        "saturation": s,
        "gamma": g,
        "zoom": z,
        "noise": n,
        "tempo": t,
        "flip": flip,
    }


def build_uniquifier_filterchains(
    params: dict[str, float | bool],
    width: int = 1080,
    height: int = 1920,
) -> tuple[str, str, list[str]]:
    """Build FFmpeg video filter, audio filter, and metadata flags."""
    b = float(params["brightness"])
    c = float(params["contrast"])
    s = float(params["saturation"])
    g = float(params["gamma"])
    z = float(params["zoom"])
    n = float(params["noise"])
    t = float(params["tempo"])
    flip = bool(params["flip"])

    vf_parts: list[str] = [
        f"eq=brightness={b:.4f}:contrast={c:.4f}:saturation={s:.4f}:gamma={g:.4f}",
    ]

    # Micro-zoom to alter edge coordinates and pixel alignments
    if z > 1.0:
        vf_parts.append(
            f"crop=w=iw/{z:.4f}:h=ih/{z:.4f},scale={width}:{height}:flags=bicubic"
        )

    # Subtle film grain / noise to randomize per-frame pixel hash
    if n > 0.0:
        vf_parts.append(f"noise=c0s={n:.1f}:c0f=t+u")

    if flip:
        vf_parts.append("hflip")

    video_filter = ",".join(vf_parts)

    # Audio micro-tempo shift to disrupt acoustic fingerprinting
    audio_filter = f"atempo={t:.4f}" if t != 1.0 else "anull"

    # Metadata spoofing
    rand_uuid = uuid.uuid4().hex
    metadata_args = [
        "-map_metadata",
        "-1",
        "-metadata",
        f"title=Short_{rand_uuid[:10]}",
        "-metadata",
        "artist=VideoAnalyzer Studio",
        "-metadata",
        f"comment=Render_{rand_uuid[:8]}",
        "-metadata:s:v:0",
        f"handler_name=VideoHandler_{rand_uuid[:6]}",
        "-metadata:s:a:0",
        f"handler_name=AudioHandler_{rand_uuid[:6]}",
    ]

    return video_filter, audio_filter, metadata_args


def apply_video_uniquifier(
    input_path: Path,
    output_path: Path,
    config: VideoUniquifierConfig | None = None,
    width: int = 1080,
    height: int = 1920,
    render_profile: RenderProfile | None = None,
) -> Path:
    """Process a rendered video through the anti-fingerprint uniquifier filterchain.

    Args:
        input_path: Source input video file.
        output_path: Target output path.
        config: VideoUniquifierConfig or None.
        width: Canvas width (default 1080).
        height: Canvas height (default 1920).
        render_profile: Rendering execution profile ('gpu_fast' or 'cpu_safe').

    Returns:
        Path to processed unique video.
    """
    if not input_path.exists():
        raise MediaProcessingError(f"Input video for uniquifier not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not config or not config.enabled:
        if input_path.resolve() != output_path.resolve():
            shutil.copy2(input_path, output_path)
        return output_path

    effective_profile = (
        render_profile or (config.render_profile if config else RenderProfile.GPU_FAST)
    )
    caps = get_hardware_capabilities()
    active_encoder = (
        caps.active_hw_encoder if effective_profile == RenderProfile.GPU_FAST else None
    )
    encoder_args = get_active_encoder_args(active_encoder, effective_profile)

    params = generate_uniquifier_parameters(config)
    vf, af, meta_args = build_uniquifier_filterchains(params, width=width, height=height)

    # If input and output are the same, render to an intermediate temporary file
    temp_target = (
        output_path.with_name(f"uniquify_tmp_{uuid.uuid4().hex[:8]}.mp4")
        if input_path.resolve() == output_path.resolve()
        else output_path
    )

    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(input_path),
        "-vf",
        vf,
        "-af",
        af,
        *meta_args,
        *encoder_args,
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(temp_target),
    ]

    logger.info(
        "Applying Video Uniquifier (profile=%s, encoder=%s): %s -> %s",
        effective_profile,
        active_encoder or "libx264",
        input_path.name,
        output_path.name,
    )
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603

    if proc.returncode != 0 or not temp_target.exists() or temp_target.stat().st_size == 0:
        # Automatic fallback to CPU Safe if GPU encoding failed
        if effective_profile == RenderProfile.GPU_FAST:
            logger.warning(
                "Uniquifier hardware encoding failed (%s). Falling back to CPU Safe...",
                proc.returncode,
            )
            if temp_target.exists() and temp_target != output_path:
                temp_target.unlink(missing_ok=True)
            return apply_video_uniquifier(
                input_path=input_path,
                output_path=output_path,
                config=config,
                width=width,
                height=height,
                render_profile=RenderProfile.CPU_SAFE,
            )

        if temp_target.exists() and temp_target != output_path:
            temp_target.unlink(missing_ok=True)
        raise MediaProcessingError(
            f"Video Uniquifier failed on {input_path.name}",
            details=proc.stderr,
        )

    if temp_target != output_path:
        shutil.move(temp_target, output_path)

    logger.info(
        "Video Uniquifier completed successfully: %s (params: %s)",
        output_path.name,
        params,
    )
    return output_path

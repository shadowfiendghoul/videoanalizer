"""Render job and effect styling models for final video composition."""

from pathlib import Path
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field

from videoanalizer.media.uniquifier import VideoUniquifierConfig
from videoanalizer.models.highlight import HighlightSegment
from videoanalizer.models.layout import LayoutPreset


class SubtitleStyle(BaseModel):
    """TikTok karaoke subtitle styling configuration."""

    font_name: str = Field(
        default="Arial Bold",
        description="Font family name for burned ASS subtitles.",
    )
    font_size: int = Field(
        default=42,
        ge=16,
        le=72,
        description="Font size in points/pixels.",
    )
    active_color: str = Field(
        default="#FFFF00",
        description="Hex color code for highlighted active spoken word (e.g. bright yellow).",
    )
    inactive_color: str = Field(
        default="#FFFFFF",
        description="Hex color code for inactive spoken words (white).",
    )
    outline_color: str = Field(
        default="#000000",
        description="Hex color code for text stroke outline.",
    )
    outline_width: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Width of text outline stroke in pixels.",
    )
    position_vertical_pct: float = Field(
        default=0.78,
        ge=0.5,
        le=0.95,
        description="Vertical placement as fraction of canvas height (lower third).",
    )


class SilenceConfig(BaseModel):
    """Silence removal and audio crossfade parameters."""

    enabled: bool = Field(
        default=True,
        description="Whether to detect and cut dead pauses.",
    )
    threshold_sec: float = Field(
        default=1.0,
        ge=0.3,
        description="Silence duration threshold in seconds.",
    )
    noise_db: float = Field(
        default=-30.0,
        description="Noise floor in dB below which audio is treated as silence.",
    )
    padding_ms: int = Field(
        default=100,
        ge=0,
        description="Speech boundary safety padding in milliseconds.",
    )
    crossfade_ms: int = Field(
        default=25,
        ge=0,
        description="Audio micro-crossfade duration in milliseconds.",
    )


class BannerConfig(BaseModel):
    """Top text banner / hook headline overlay configuration."""

    enabled: bool = Field(
        default=True,
        description="Whether to overlay a top hook banner.",
    )
    text: str = Field(
        default="",
        max_length=120,
        description="Banner text content (AI-suggested or user-edited).",
    )
    font_size: int = Field(
        default=36,
        ge=20,
        le=60,
        description="Banner font size.",
    )
    font_color: str = Field(
        default="#FFFFFF",
        description="Banner text font hex color.",
    )
    bg_color: str = Field(
        default="#000000AA",
        description="Banner background color with alpha hex.",
    )
    position: Literal["top", "bottom"] = Field(
        default="top",
        description="Placement of banner overlay ('top' or 'bottom').",
    )


class ClipRenderJob(BaseModel):
    """Specification and execution state for a rendered vertical short."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the rendering task.",
    )
    highlight: HighlightSegment = Field(
        ...,
        description="Source highlight segment to render.",
    )
    layout: LayoutPreset = Field(
        ...,
        description="Vertical reframing layout configuration.",
    )
    silence: SilenceConfig = Field(
        default_factory=SilenceConfig,
        description="Silence removal configuration.",
    )
    subtitles: SubtitleStyle = Field(
        default_factory=SubtitleStyle,
        description="Subtitle styling configuration.",
    )
    subtitles_enabled: bool = Field(
        default=True,
        description="Whether karaoke subtitles should be burned into video.",
    )
    banner: BannerConfig = Field(
        default_factory=BannerConfig,
        description="Top hook headline banner configuration.",
    )
    uniquifier: VideoUniquifierConfig = Field(
        default_factory=VideoUniquifierConfig,
        description="Video uniquifier anti-fingerprint configuration.",
    )
    output_width: int = Field(
        default=1080,
        description="Output canvas width in pixels (standard vertical 1080).",
    )
    output_height: int = Field(
        default=1920,
        description="Output canvas height in pixels (standard vertical 1920).",
    )
    output_fps: int = Field(
        default=30,
        description="Output video framerate (30 or 60 fps).",
    )
    output_path: Path | None = Field(
        default=None,
        description="Absolute filesystem path to the rendered output MP4 upon completion.",
    )
    status: Literal["pending", "rendering", "complete", "failed"] = Field(
        default="pending",
        description="Lifecycle status of the render task.",
    )
    error_message: str | None = Field(
        default=None,
        description="Error details if render failed.",
    )

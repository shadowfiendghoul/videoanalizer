"""Source video model representing ingested raw media."""

from pathlib import Path
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field, model_validator


class SourceVideo(BaseModel):
    """Represents an ingested video file from YouTube or local upload."""

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the video ingestion session.",
    )
    origin: Literal["youtube", "local"] = Field(
        ...,
        description="Source type: either 'youtube' or 'local'.",
    )
    original_url: str | None = Field(
        default=None,
        description="Original YouTube URL if ingested from web, otherwise None.",
    )
    local_path: Path = Field(
        ...,
        description="Local absolute filesystem path to the downloaded or uploaded video.",
    )
    filename: str = Field(
        ...,
        description="Original or target filename for display and output naming.",
    )
    duration_sec: float = Field(
        ...,
        gt=0,
        description="Total duration in seconds reported by FFmpeg probe.",
    )
    width: int = Field(
        ...,
        gt=0,
        description="Video frame width in pixels.",
    )
    height: int = Field(
        ...,
        gt=0,
        description="Video frame height in pixels.",
    )
    fps: float = Field(
        ...,
        gt=0,
        description="Frames per second rate.",
    )
    codec: str = Field(
        ...,
        description="Video stream codec identifier (e.g. 'h264', 'vp9').",
    )
    audio_codec: str | None = Field(
        default=None,
        description="Audio stream codec identifier (e.g. 'aac', 'opus') or None if mute.",
    )
    file_size_bytes: int = Field(
        default=0,
        ge=0,
        description="File size on disk in bytes.",
    )

    @model_validator(mode="after")
    def validate_youtube_url(self) -> "SourceVideo":
        """Ensure original_url is supplied when origin is youtube."""
        if self.origin == "youtube" and not self.original_url:
            raise ValueError("original_url must be provided when origin is 'youtube'")
        return self

"""Configuration settings for VideoAnalyzer using Pydantic Settings."""

from pathlib import Path
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application-wide configuration loaded from environment and defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    google_api_key: SecretStr = Field(
        ...,
        alias="GOOGLE_API_KEY",
        description="Google Gemini GenAI API key. Loaded from environment, never logged.",
    )
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite",
        alias="GEMINI_MODEL",
        description="Gemini model identifier.",
    )
    output_dir: Path = Field(
        default=Path("./output"),
        alias="OUTPUT_DIR",
        description="Directory for rendered MP4 output clips.",
    )
    temp_dir: Path | None = Field(
        default=None,
        alias="TEMP_DIR",
        description="Optional override for temporary file directory.",
    )
    default_clip_count: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Default number of funny highlight clips to generate (1-10).",
    )
    default_min_duration: float = Field(
        default=30.0,
        ge=15.0,
        le=90.0,
        description="Default minimum highlight duration in seconds (15-90s).",
    )
    default_max_duration: float = Field(
        default=60.0,
        ge=15.0,
        le=90.0,
        description="Default maximum highlight duration in seconds (15-90s).",
    )
    silence_threshold_sec: float = Field(
        default=1.0,
        ge=0.3,
        description="Silence duration threshold in seconds above which pauses are trimmed.",
    )
    silence_db: float = Field(
        default=-30.0,
        description="Decibel threshold below which audio is treated as silence.",
    )
    crossfade_ms: int = Field(
        default=25,
        ge=0,
        description="Audio crossfade duration in milliseconds for smooth silence cut splices.",
    )
    padding_ms: int = Field(
        default=100,
        ge=0,
        description="Safety padding in milliseconds around speech boundaries before silence cuts.",
    )

    @model_validator(mode="after")
    def validate_duration_range(self) -> "AppConfig":
        """Validate that min duration does not exceed max duration."""
        if self.default_min_duration > self.default_max_duration:
            raise ValueError(
                f"default_min_duration ({self.default_min_duration}) cannot be greater than "
                f"default_max_duration ({self.default_max_duration})"
            )
        return self


def get_config() -> AppConfig:
    """Load and return application settings instance."""
    return AppConfig()

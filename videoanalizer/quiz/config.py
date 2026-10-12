"""Configuration settings for Quiz Shorts Generator using Pydantic Settings."""

import os
import shutil
import sys
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def ensure_system_paths() -> None:
    """Ensure system paths for FFmpeg and Node.js are available in os.environ['PATH']."""
    if sys.platform != "win32":
        return

    # Check if node and ffmpeg are already in PATH
    if shutil.which("node") and shutil.which("ffmpeg"):
        return

    try:
        import winreg

        user_path = ""
        machine_path = ""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                user_path, _ = winreg.QueryValueEx(key, "Path")
        except OSError:
            pass

        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            ) as key:
                machine_path, _ = winreg.QueryValueEx(key, "Path")
        except OSError:
            pass

        current = os.environ.get("PATH", "")
        combined = f"{user_path};{machine_path};{current}"
        os.environ["PATH"] = combined
    except (OSError, ImportError):
        pass


class QuizConfig(BaseSettings):
    """Configuration for quiz shorts generation pipeline."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="GEMINI_API_KEY",
        description="Gemini API Key.",
    )
    google_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="GOOGLE_API_KEY",
        description="Google API Key.",
    )
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite",
        validation_alias="QUIZ_GEMINI_MODEL",
        description="Gemini model for quiz generation.",
    )
    creative_temperature: float = Field(
        default=0.95,
        ge=0.0,
        le=2.0,
        validation_alias="QUIZ_CREATIVE_TEMPERATURE",
        description="Sampling temperature for creative initial quiz generation (0.7-1.1).",
    )
    verifier_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        validation_alias="QUIZ_VERIFIER_TEMPERATURE",
        description="Strict sampling temperature for fact-checking verifier pass (0.0-0.2).",
    )
    fact_check_enabled: bool = Field(
        default=True,
        validation_alias="QUIZ_FACT_CHECK_ENABLED",
        description="Whether to run the strict secondary fact-checking verifier pass.",
    )

    default_voices: dict[str, str] = Field(
        default={
            "ru": "ru-RU-SvetlanaNeural",
            "en": "en-US-GuyNeural",
        },
        description="Default Edge-TTS neural voices per language.",
    )

    backgrounds_dir: Path = Field(
        default=Path("assets/backgrounds"),
        description="Directory containing neutral vertical background video loops.",
    )
    banners_dir: Path = Field(
        default=Path("assets/banners"),
        description="Directory containing uploaded promo banner videos.",
    )
    music_dir: Path = Field(
        default=Path("assets/music"),
        description="Directory containing uploaded background music audio files.",
    )
    sfx_dir: Path = Field(
        default=Path("assets/sfx"),
        description="Directory containing sound effects.",
    )
    output_dir: Path = Field(
        default=Path("outputs"),
        description="Directory for rendered MP4 output videos.",
    )
    remotion_dir: Path = Field(
        default=Path("templates/quiz-remotion"),
        description="Path to Remotion template root directory.",
    )
    temp_dir: Path = Field(
        default=Path("temp"),
        description="Root temporary workspace directory.",
    )

    think_duration_sec: float = Field(
        default=3.0,
        description="Think phase duration in seconds per question.",
    )
    fps: int = Field(
        default=60,
        description="Rendering frames per second.",
    )
    width: int = Field(
        default=1080,
        description="Render width in pixels.",
    )
    height: int = Field(
        default=1920,
        description="Render height in pixels.",
    )
    render_timeout_sec: int | None = Field(
        default=None,
        description=(
            "Maximum seconds before timing out Remotion rendering subprocess. "
            "Set None or 0 to disable."
        ),
    )
    remotion_delay_render_timeout_ms: int = Field(
        default=3600000,
        description="Puppeteer delayRender timeout in ms for Remotion CLI (>=7000ms).",
    )
    crf: int = Field(
        default=18,
        ge=0,
        le=51,
        description="x264 Constant Rate Factor (18 is visually lossless).",
    )
    remotion_x264_preset: str = Field(
        default="fast",
        description="x264 preset for Remotion CLI ('fast', 'medium', 'faster').",
    )
    remotion_jpeg_quality: int = Field(
        default=95,
        ge=50,
        le=100,
        description="Puppeteer frame screenshot JPEG quality (default 95).",
    )

    @property
    def effective_api_key(self) -> SecretStr:
        """Resolve effective API key from GEMINI_API_KEY or GOOGLE_API_KEY."""
        if self.gemini_api_key and self.gemini_api_key.get_secret_value():
            return self.gemini_api_key
        if self.google_api_key and self.google_api_key.get_secret_value():
            return self.google_api_key
        return SecretStr("")


def get_quiz_config() -> QuizConfig:
    """Load and return QuizConfig instance after refreshing system paths."""
    ensure_system_paths()
    return QuizConfig()

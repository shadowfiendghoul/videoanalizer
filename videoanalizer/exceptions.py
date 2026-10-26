"""Custom domain exception hierarchy for VideoAnalyzer."""


class VideoAnalyzerError(Exception):
    """Base exception for all domain errors in VideoAnalyzer."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigurationError(VideoAnalyzerError):
    """Raised when application configuration or credentials are missing or invalid."""


# Ingestion exceptions
class IngestionError(VideoAnalyzerError):
    """Base exception for media ingestion failures."""


class DownloadError(IngestionError):
    """Raised when external video download (e.g. via yt-dlp) fails."""


class UnsupportedFormatError(IngestionError):
    """Raised when input video format, codec, or file stream is unsupported or corrupted."""


# Analysis exceptions
class AnalysisError(VideoAnalyzerError):
    """Base exception for multimodal AI analysis failures."""


class AnalysisTimeoutError(AnalysisError):
    """Raised when Gemini analysis exceeds the configured network timeout."""


class RateLimitError(AnalysisError):
    """Raised when Gemini API quota or rate limits are exceeded after retries."""


class SchemaValidationError(AnalysisError):
    """Raised when AI model response fails structured JSON validation."""


class ContentFilteredError(AnalysisError):
    """Raised when video content or prompt is blocked by AI safety filters."""


# Media processing exceptions
class MediaProcessingError(VideoAnalyzerError):
    """Base exception for FFmpeg media processing failures."""


class RenderError(MediaProcessingError):
    """Raised when video clipping, filtering, subtitle burning, or encoding fails."""


class FFmpegNotFoundError(MediaProcessingError):
    """Raised when FFmpeg binary is not found on system PATH."""


# YouTube exceptions
class YouTubeError(VideoAnalyzerError):
    """Base exception for YouTube API interactions and uploads."""


class YouTubeAuthError(YouTubeError):
    """Raised when YouTube OAuth authentication is missing, invalid, or expired."""


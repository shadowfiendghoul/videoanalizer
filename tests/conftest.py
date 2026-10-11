"""Shared pytest fixtures for VideoAnalyzer test suite."""

from collections.abc import Generator
from pathlib import Path
import pytest

from videoanalizer.config import AppConfig
from videoanalizer.models import (
    HighlightSegment,
    SourceVideo,
    WordTiming,
)
from videoanalizer.utils.tempfiles import SessionTempDir


@pytest.fixture
def sample_config() -> AppConfig:
    """Provide an AppConfig instance with test credentials and defaults."""
    return AppConfig(
        GOOGLE_API_KEY="test_gemini_api_key_mock_12345",
        GEMINI_MODEL="gemini-2.5-flash",
        OUTPUT_DIR=Path("./test_output"),
        default_clip_count=3,
        default_min_duration=30.0,
        default_max_duration=60.0,
    )


@pytest.fixture
def tmp_session_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a managed temporary directory using SessionTempDir."""
    with SessionTempDir(base_dir=tmp_path) as session:
        yield session.path


@pytest.fixture
def mock_source_video(tmp_path: Path) -> SourceVideo:
    """Provide a valid SourceVideo instance with dummy local file on disk."""
    dummy_video_file = tmp_path / "mock_stream.mp4"
    dummy_video_file.write_bytes(b"dummy_mp4_bytes")

    return SourceVideo(
        id="test-source-video-uuid-1",
        origin="local",
        local_path=dummy_video_file,
        filename="mock_stream.mp4",
        duration_sec=300.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec="h264",
        audio_codec="aac",
        file_size_bytes=1024,
    )


@pytest.fixture
def mock_highlight_segment() -> HighlightSegment:
    """Provide a valid HighlightSegment instance with word timings."""
    return HighlightSegment(
        id="test-highlight-uuid-1",
        source_video_id="test-source-video-uuid-1",
        start_sec=45.0,
        end_sec=75.0,
        humor_score=8.5,
        summary="Player walks into laser trap after explaining how easy the puzzle is",
        transcript="This puzzle is super easy just don't touch the laser oops",
        word_timings=[
            WordTiming(word="This", start_sec=0.0, end_sec=0.3),
            WordTiming(word="puzzle", start_sec=0.3, end_sec=0.7),
            WordTiming(word="is", start_sec=0.7, end_sec=0.9),
            WordTiming(word="super", start_sec=0.9, end_sec=1.3),
            WordTiming(word="easy", start_sec=1.3, end_sec=1.8),
        ],
        suggested_headline="He said it was super easy 💀🤣",
        is_selected=True,
    )

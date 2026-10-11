"""Unit tests for Pydantic domain models and validation rules."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from videoanalizer.models import (
    BannerConfig,
    ClipRenderJob,
    CropBox,
    HighlightSegment,
    LayoutPreset,
    SilenceConfig,
    SourceVideo,
    SubtitleStyle,
    WordTiming,
)


def test_source_video_validation() -> None:
    """Test SourceVideo validation rules."""
    # Valid local video
    video = SourceVideo(
        origin="local",
        local_path=Path("sample.mp4"),
        filename="sample.mp4",
        duration_sec=60.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec="h264",
    )
    assert video.origin == "local"
    assert video.duration_sec == 60.0

    # YouTube origin requires original_url
    with pytest.raises(ValidationError):
        SourceVideo(
            origin="youtube",
            original_url=None,
            local_path=Path("sample.mp4"),
            filename="sample.mp4",
            duration_sec=60.0,
            width=1920,
            height=1080,
            fps=30.0,
            codec="h264",
        )


def test_highlight_segment_duration_and_bounds() -> None:
    """Test HighlightSegment computed duration and boundary ordering."""
    highlight = HighlightSegment(
        source_video_id="video-1",
        start_sec=10.0,
        end_sec=25.5,
        humor_score=8.5,
        summary="Funny punchline",
        transcript="Hello world",
        suggested_headline="Best joke",
    )
    assert highlight.duration_sec == 15.5

    # Invalid bounds (end <= start)
    with pytest.raises(ValidationError):
        HighlightSegment(
            source_video_id="video-1",
            start_sec=25.0,
            end_sec=20.0,
            humor_score=5.0,
            summary="Invalid",
            transcript="",
            suggested_headline="",
        )


def test_word_timing_validation() -> None:
    """Test WordTiming field ordering."""
    wt = WordTiming(word="test", start_sec=1.0, end_sec=1.5)
    assert wt.word == "test"

    with pytest.raises(ValidationError):
        WordTiming(word="test", start_sec=2.0, end_sec=1.0)


def test_layout_preset_split_screen_requires_boxes() -> None:
    """Test that split_screen requires both webcam_box and gameplay_box."""
    with pytest.raises(ValidationError):
        LayoutPreset(mode="split_screen", webcam_box=None, gameplay_box=None)

    valid_split = LayoutPreset(
        mode="split_screen",
        webcam_box=CropBox(x=0, y=0, width=300, height=300),
        gameplay_box=CropBox(x=0, y=0, width=1920, height=1080),
    )
    assert valid_split.mode == "split_screen"


def test_clip_render_job_defaults() -> None:
    """Test ClipRenderJob default factories and status lifecycle."""
    highlight = HighlightSegment(
        source_video_id="video-1",
        start_sec=5.0,
        end_sec=20.0,
        humor_score=7.0,
        summary="Short laugh",
        transcript="Haha",
        suggested_headline="Lol",
    )
    layout = LayoutPreset(mode="center_crop")

    job = ClipRenderJob(highlight=highlight, layout=layout)
    assert job.status == "pending"
    assert job.output_width == 1080
    assert job.output_height == 1920
    assert job.output_fps == 30
    assert job.silence.enabled is True
    assert job.subtitles.font_size == 42

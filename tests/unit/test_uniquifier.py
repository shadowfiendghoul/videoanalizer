"""Unit tests for Video Uniquifier anti-fingerprint engine."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from videoanalizer.exceptions import MediaProcessingError
from videoanalizer.media.uniquifier import (
    VideoUniquifierConfig,
    apply_video_uniquifier,
    build_uniquifier_filterchains,
    generate_uniquifier_parameters,
)


def test_uniquifier_config_defaults() -> None:
    """Test default VideoUniquifierConfig settings."""
    cfg = VideoUniquifierConfig()
    assert cfg.enabled is False
    assert cfg.mode == "smart_random"
    assert cfg.brightness == 0.02
    assert cfg.contrast == 1.04
    assert cfg.saturation == 1.08
    assert cfg.zoom_percent == 1.02
    assert cfg.noise_intensity == 1.5
    assert cfg.flip_horizontal is False


def test_generate_uniquifier_parameters_custom() -> None:
    """Test parameter extraction in custom mode."""
    cfg = VideoUniquifierConfig(
        enabled=True,
        mode="custom",
        brightness=0.05,
        contrast=1.10,
        saturation=1.15,
        gamma=1.02,
        zoom_percent=1.03,
        noise_intensity=2.0,
        audio_tempo_drift=1.01,
        flip_horizontal=True,
    )
    params = generate_uniquifier_parameters(cfg)
    assert params["brightness"] == 0.05
    assert params["contrast"] == 1.10
    assert params["saturation"] == 1.15
    assert params["gamma"] == 1.02
    assert params["zoom"] == 1.03
    assert params["noise"] == 2.0
    assert params["tempo"] == 1.01
    assert params["flip"] is True


def test_generate_uniquifier_parameters_smart_random() -> None:
    """Test smart random generates bounded unique variations."""
    cfg = VideoUniquifierConfig(enabled=True, mode="smart_random")
    p1 = generate_uniquifier_parameters(cfg)
    p2 = generate_uniquifier_parameters(cfg)

    # Random parameters should stay within safe bounds and produce variation
    assert -0.15 <= p2["brightness"] <= 0.15
    assert -0.15 <= p1["brightness"] <= 0.15
    assert 1.0 <= p1["contrast"] <= 1.15
    assert 1.0 <= p1["saturation"] <= 1.20
    assert 1.0 <= p1["zoom"] <= 1.05
    assert 0.0 <= p1["noise"] <= 5.0
    assert 0.99 <= p1["tempo"] <= 1.02


def test_build_uniquifier_filterchains() -> None:
    """Test filter chain formatting for FFmpeg."""
    params = {
        "brightness": 0.03,
        "contrast": 1.05,
        "saturation": 1.09,
        "gamma": 1.01,
        "zoom": 1.02,
        "noise": 1.5,
        "tempo": 1.006,
        "flip": True,
    }
    vf, af, meta = build_uniquifier_filterchains(params, width=1080, height=1920)

    assert "eq=brightness=0.0300:contrast=1.0500:saturation=1.0900:gamma=1.0100" in vf
    assert "crop=w=iw/1.0200:h=ih/1.0200,scale=1080:1920" in vf
    assert "noise=c0s=1.5:c0f=t+u" in vf
    assert "hflip" in vf

    assert "atempo=1.0060" in af

    assert "-map_metadata" in meta
    assert "-1" in meta
    assert "-metadata" in meta


def test_apply_video_uniquifier_disabled_passthrough(tmp_path: Path) -> None:
    """Disabled uniquifier copies input to output without re-encoding."""
    in_file = tmp_path / "in.mp4"
    in_file.write_bytes(b"sample_data")
    out_file = tmp_path / "out.mp4"

    cfg = VideoUniquifierConfig(enabled=False)
    result = apply_video_uniquifier(in_file, out_file, cfg)

    assert result == out_file
    assert out_file.exists()
    assert out_file.read_bytes() == b"sample_data"


def test_apply_video_uniquifier_missing_input(tmp_path: Path) -> None:
    """Missing input file raises MediaProcessingError."""
    in_file = tmp_path / "missing.mp4"
    out_file = tmp_path / "out.mp4"

    with pytest.raises(MediaProcessingError, match="Input video for uniquifier not found"):
        apply_video_uniquifier(in_file, out_file, VideoUniquifierConfig(enabled=True))


@patch("subprocess.run")
def test_apply_video_uniquifier_success_invocation(
    mock_subproc: MagicMock,
    tmp_path: Path,
) -> None:
    """Enabled uniquifier executes FFmpeg subprocess with expected flags."""
    in_file = tmp_path / "in.mp4"
    in_file.write_bytes(b"valid_bytes")
    out_file = tmp_path / "out.mp4"

    # Simulate FFmpeg creating the file
    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        out_target = Path(cmd[-1])
        out_target.write_bytes(b"uniquified_bytes")
        mock_res = MagicMock()
        mock_res.returncode = 0
        return mock_res

    mock_subproc.side_effect = fake_run

    cfg = VideoUniquifierConfig(enabled=True, mode="custom", brightness=0.03)
    result = apply_video_uniquifier(in_file, out_file, cfg)

    assert result == out_file
    assert out_file.exists()
    assert mock_subproc.called
    cmd = mock_subproc.call_args[0][0]
    assert "-vf" in cmd
    assert "-af" in cmd
    assert "-map_metadata" in cmd
    assert "-pix_fmt" in cmd
    assert "yuv420p" in cmd


@patch("subprocess.run")
def test_apply_video_uniquifier_gpu_fallback_on_failure(
    mock_subproc: MagicMock,
    tmp_path: Path,
) -> None:
    """When GPU Fast hardware encoding fails, automatically fallback to CPU libx264."""
    from videoanalizer.quiz.models import RenderProfile

    in_file = tmp_path / "in_gpu.mp4"
    in_file.write_bytes(b"gpu_input_bytes")
    out_file = tmp_path / "out_gpu.mp4"

    call_count = 0

    def fake_run(cmd: list[str], **kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        mock_res = MagicMock()
        if call_count == 1:
            # First attempt (GPU Fast) fails
            mock_res.returncode = 1
            mock_res.stderr = "CUDA/AMF driver hardware failure"
            return mock_res
        # Second attempt (CPU Safe fallback) succeeds
        out_target = Path(cmd[-1])
        out_target.write_bytes(b"fallback_bytes")
        mock_res.returncode = 0
        return mock_res

    mock_subproc.side_effect = fake_run

    cfg = VideoUniquifierConfig(enabled=True, render_profile=RenderProfile.GPU_FAST)
    result = apply_video_uniquifier(in_file, out_file, cfg)

    assert result == out_file
    assert out_file.exists()
    assert call_count == 2


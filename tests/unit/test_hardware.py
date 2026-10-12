"""Unit tests for hardware capabilities probing, GPU detection, and encoder selection."""

from unittest.mock import patch

from videoanalizer.quiz.models import GpuVendor, HardwareCapabilities, RenderProfile
from videoanalizer.utils.hardware import (
    detect_gpu_device_name,
    get_active_encoder_args,
    get_available_ffmpeg_encoders,
    get_hardware_capabilities,
    validate_encoder,
)


def test_real_hardware_capabilities_probe() -> None:
    """Test hardware probing on host system."""
    caps = get_hardware_capabilities()
    assert isinstance(caps, HardwareCapabilities)
    assert isinstance(caps.gpu_name, str)
    assert isinstance(caps.gpu_vendor, GpuVendor)
    assert caps.recommended_profile in [RenderProfile.GPU_FAST, RenderProfile.CPU_SAFE]
    assert len(caps.supported_encoders) > 0


def test_detect_gpu_device_name() -> None:
    """Test detect_gpu_device_name returns a non-empty string and valid vendor."""
    gpu_name, vendor = detect_gpu_device_name()
    assert isinstance(gpu_name, str)
    assert len(gpu_name) > 0
    assert isinstance(vendor, GpuVendor)


def test_get_available_ffmpeg_encoders() -> None:
    """Test that FFmpeg encoders are discovered."""
    encoders = get_available_ffmpeg_encoders()
    assert isinstance(encoders, list)
    assert len(encoders) > 0


def test_validate_encoder_live() -> None:
    """Test validate_encoder with a known invalid encoder and valid software encoder."""
    assert validate_encoder("libx264") is True
    assert validate_encoder("nonexistent_codec_999") is False


def test_get_active_encoder_args() -> None:
    """Test generated FFmpeg arguments for each profile and encoder."""
    # CPU Safe
    cpu_args = get_active_encoder_args("h264_amf", RenderProfile.CPU_SAFE)
    assert cpu_args == ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

    # GPU Fast - AMF
    amf_args = get_active_encoder_args("h264_amf", RenderProfile.GPU_FAST)
    assert "-c:v" in amf_args and "h264_amf" in amf_args
    assert "-quality" in amf_args

    # GPU Fast - NVENC
    nvenc_args = get_active_encoder_args("h264_nvenc", RenderProfile.GPU_FAST)
    assert "-c:v" in nvenc_args and "h264_nvenc" in nvenc_args
    assert "-cq" in nvenc_args

    # GPU Fast - MediaFoundation
    mf_args = get_active_encoder_args("h264_mf", RenderProfile.GPU_FAST)
    assert "-c:v" in mf_args and "h264_mf" in mf_args

    # GPU Fast - QSV
    qsv_args = get_active_encoder_args("h264_qsv", RenderProfile.GPU_FAST)
    assert "-c:v" in qsv_args and "h264_qsv" in qsv_args


def test_hardware_probe_fallback_mocked() -> None:
    """Test that if all hardware encoders fail, fallback to CPU_SAFE occurs."""
    get_hardware_capabilities.cache_clear()
    with (
        patch(
            "videoanalizer.utils.hardware.get_available_ffmpeg_encoders",
            return_value=["libx264"],
        ),
        patch("videoanalizer.utils.hardware.validate_encoder", return_value=False),
    ):
        caps = get_hardware_capabilities()
        assert caps.gpu_available is False
        assert caps.active_hw_encoder is None
        assert caps.recommended_profile == RenderProfile.CPU_SAFE
    get_hardware_capabilities.cache_clear()

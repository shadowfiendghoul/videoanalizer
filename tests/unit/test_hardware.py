"""Unit tests for hardware capabilities probing, GPU detection, and encoder selection."""

from unittest.mock import patch

from videoanalizer.quiz.models import GpuVendor, HardwareCapabilities, RenderProfile
from videoanalizer.utils.hardware import (
    calculate_optimal_concurrency,
    detect_gpu_device_name,
    get_active_encoder_args,
    get_available_ffmpeg_encoders,
    get_hardware_capabilities,
    get_system_memory_mb,
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
    assert caps.cpu_logical_cores >= 1
    assert caps.ram_total_gb > 0
    assert caps.ram_available_gb > 0
    assert caps.optimal_concurrency >= 2
    assert caps.build_reuse_enabled is True


def test_get_system_memory_mb() -> None:
    """Test get_system_memory_mb returns reasonable values."""
    total_mb, avail_mb = get_system_memory_mb()
    assert total_mb > 0
    assert avail_mb > 0
    assert avail_mb <= total_mb * 1.5  # reasonable sanity bound


def test_calculate_optimal_concurrency_scaling() -> None:
    """Test concurrency scaling across different core counts and profiles."""
    with patch("videoanalizer.utils.hardware.get_system_memory_mb", return_value=(32768, 16384)):
        # 4 cores -> 75% = 3
        with patch("os.cpu_count", return_value=4):
            assert calculate_optimal_concurrency(RenderProfile.GPU_FAST) == 3
            assert calculate_optimal_concurrency(RenderProfile.CPU_SAFE) == 2

        # 8 cores -> 75% = 6
        with patch("os.cpu_count", return_value=8):
            assert calculate_optimal_concurrency(RenderProfile.GPU_FAST) == 6
            assert calculate_optimal_concurrency(RenderProfile.CPU_SAFE) == 4

        # 16 cores -> 75% = 12
        with patch("os.cpu_count", return_value=16):
            assert calculate_optimal_concurrency(RenderProfile.GPU_FAST) == 12
            assert calculate_optimal_concurrency(RenderProfile.CPU_SAFE) == 9

        # 32 cores -> 75% = 24
        with patch("os.cpu_count", return_value=32):
            assert calculate_optimal_concurrency(RenderProfile.GPU_FAST) == 24
            assert calculate_optimal_concurrency(RenderProfile.CPU_SAFE) == 19


def test_calculate_optimal_concurrency_oom_guard() -> None:
    """Test that low available RAM constrains concurrency to prevent OOM."""
    # Only 1000 MB available: (1000 * 0.85) // 450 = 1, min floor is 2
    with (
        patch("videoanalizer.utils.hardware.get_system_memory_mb", return_value=(8192, 1000)),
        patch("os.cpu_count", return_value=16),
    ):
        concurrency = calculate_optimal_concurrency(RenderProfile.GPU_FAST)
        assert concurrency == 2


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
    """Test generated FFmpeg arguments with ultra-fast presets for each profile and encoder."""
    # CPU Safe: ultrafast preset, fastdecode tune, threads 0
    cpu_args = get_active_encoder_args("h264_amf", RenderProfile.CPU_SAFE)
    assert cpu_args == [
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-tune",
        "fastdecode",
        "-threads",
        "0",
        "-crf",
        "20",
    ]

    # CPU Safe fallback with None or libx264
    fallback_args = get_active_encoder_args(None, RenderProfile.GPU_FAST)
    assert fallback_args[1] == "libx264"
    assert "ultrafast" in fallback_args

    # GPU Fast - AMF: quality speed, cbr
    amf_args = get_active_encoder_args("h264_amf", RenderProfile.GPU_FAST)
    assert "-c:v" in amf_args and "h264_amf" in amf_args
    assert "speed" in amf_args

    # GPU Fast - NVENC: preset p1, tune ull, cbr
    nvenc_args = get_active_encoder_args("h264_nvenc", RenderProfile.GPU_FAST)
    assert "-c:v" in nvenc_args and "h264_nvenc" in nvenc_args
    assert "p1" in nvenc_args
    assert "ull" in nvenc_args

    # GPU Fast - QSV: veryfast
    qsv_args = get_active_encoder_args("h264_qsv", RenderProfile.GPU_FAST)
    assert "-c:v" in qsv_args and "h264_qsv" in qsv_args
    assert "veryfast" in qsv_args

    # GPU Fast - VideoToolbox: realtime 1
    vt_args = get_active_encoder_args("h264_videotoolbox", RenderProfile.GPU_FAST)
    assert "-c:v" in vt_args and "h264_videotoolbox" in vt_args
    assert "-realtime" in vt_args

    # GPU Fast - MediaFoundation: cbr
    mf_args = get_active_encoder_args("h264_mf", RenderProfile.GPU_FAST)
    assert "-c:v" in mf_args and "h264_mf" in mf_args


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

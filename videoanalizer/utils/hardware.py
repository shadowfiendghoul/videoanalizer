"""Hardware acceleration and GPU detection utilities for VideoAnalyzer."""

import logging
import platform
import shutil
import subprocess
from functools import lru_cache

from videoanalizer.quiz.models import GpuVendor, HardwareCapabilities, RenderProfile

logger = logging.getLogger(__name__)

# Preferred cascade order per specification
CANDIDATE_HARDWARE_ENCODERS = [
    ("h264_nvenc", GpuVendor.NVIDIA),
    ("h264_amf", GpuVendor.AMD),
    ("h264_qsv", GpuVendor.INTEL),
    ("h264_mf", GpuVendor.GENERIC_WINDOWS),
]


def detect_gpu_device_name() -> tuple[str, GpuVendor]:
    """Detect primary host GPU name and vendor classification."""
    sys_name = platform.system()

    if sys_name == "Windows":
        try:
            # Query WMI VideoController via powershell
            cmd = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ]
            proc = subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, timeout=3, check=False
            )
            if proc.returncode == 0 and proc.stdout.strip():
                lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
                # Filter out remote desktop / virtual displays if possible
                physical_gpus = [
                    line
                    for line in lines
                    if not any(
                        v in line.lower()
                        for v in ["virtual", "idd", "remote", "citrix", "basic display"]
                    )
                ]
                chosen = physical_gpus[0] if physical_gpus else lines[0]
                lowered = chosen.lower()
                if "nvidia" in lowered or "geforce" in lowered:
                    return chosen, GpuVendor.NVIDIA
                if "amd" in lowered or "radeon" in lowered:
                    return chosen, GpuVendor.AMD
                if "intel" in lowered or "arc" in lowered or "iris" in lowered:
                    return chosen, GpuVendor.INTEL
                return chosen, GpuVendor.GENERIC_WINDOWS
        except Exception as e:
            logger.debug("Windows GPU detection query failed: %s", e)

    elif sys_name == "Darwin":
        try:
            cmd = ["system_profiler", "SPDisplaysDataType"]
            proc = subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, timeout=3, check=False
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if "Chipset Model:" in line:
                        name = line.split(":", 1)[1].strip()
                        return name, GpuVendor.APPLE
        except Exception as e:
            logger.debug("macOS GPU detection query failed: %s", e)

    elif sys_name == "Linux":
        try:
            cmd = ["lspci"]
            proc = subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, timeout=3, check=False
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if any(w in line.lower() for w in ["vga", "3d", "display"]):
                        low = line.lower()
                        vendor = (
                            GpuVendor.NVIDIA
                            if "nvidia" in low
                            else GpuVendor.AMD
                            if "amd" in low or "ati" in low
                            else GpuVendor.INTEL
                            if "intel" in low
                            else GpuVendor.UNKNOWN
                        )
                        return line.split(":", 2)[-1].strip(), vendor
        except Exception as e:
            logger.debug("Linux lspci query failed: %s", e)

    return "Standard Graphics Adapter", GpuVendor.UNKNOWN


def get_available_ffmpeg_encoders(ffmpeg_bin: str = "ffmpeg") -> list[str]:
    """Retrieve list of video encoders compiled into the local FFmpeg binary."""
    bin_path = shutil.which(ffmpeg_bin) or ffmpeg_bin
    try:
        proc = subprocess.run(  # noqa: S603
            [bin_path, "-encoders"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if proc.returncode != 0:
            return ["libx264"]

        encoders: list[str] = []
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith("V"):
                encoders.append(parts[1])
        return encoders
    except Exception as e:
        logger.debug("Failed to list FFmpeg encoders: %s", e)
        return ["libx264"]


def validate_encoder(encoder_name: str, ffmpeg_bin: str = "ffmpeg") -> bool:
    """Perform a fast 1-frame micro-probe to verify hardware encoder driver stability."""
    bin_path = shutil.which(ffmpeg_bin) or ffmpeg_bin
    cmd = [
        bin_path,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=0.04:size=320x240:rate=25",
        "-c:v",
        encoder_name,
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        return proc.returncode == 0
    except Exception as e:
        logger.debug("Encoder validation failed for %s: %s", encoder_name, e)
        return False


@lru_cache(maxsize=1)
def get_hardware_capabilities() -> HardwareCapabilities:
    """Probe and return cached host hardware capabilities and optimal video encoder."""
    gpu_name, gpu_vendor = detect_gpu_device_name()
    discovered_encoders = get_available_ffmpeg_encoders()

    # Determine highest-priority working hardware encoder
    active_encoder: str | None = None
    working_encoders: list[str] = []

    for enc_name, _vendor in CANDIDATE_HARDWARE_ENCODERS:
        if enc_name in discovered_encoders and validate_encoder(enc_name):
            working_encoders.append(enc_name)
            if active_encoder is None:
                active_encoder = enc_name

    # Check fallback software libx264
    if "libx264" in discovered_encoders or not working_encoders:
        working_encoders.append("libx264")

    gpu_available = active_encoder is not None
    recommended_profile = RenderProfile.GPU_FAST if gpu_available else RenderProfile.CPU_SAFE

    caps = HardwareCapabilities(
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        gpu_vendor=gpu_vendor,
        active_hw_encoder=active_encoder,
        supported_encoders=working_encoders,
        gl_backend="angle" if platform.system() == "Windows" else "egl",
        recommended_profile=recommended_profile,
    )

    logger.info(
        "Hardware capability probe: GPU='%s' (%s), Active Encoder=%s, Profile=%s",
        caps.gpu_name,
        caps.gpu_vendor,
        caps.active_hw_encoder or "libx264",
        caps.recommended_profile,
    )
    return caps


def get_active_encoder_args(
    encoder_name: str | None,
    profile: RenderProfile,
) -> list[str]:
    """Generate vendor-tailored FFmpeg encoding quality and bitrate arguments."""
    if profile == RenderProfile.CPU_SAFE or not encoder_name or encoder_name == "libx264":
        return ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

    if encoder_name == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "speed", "-rc", "cbr", "-b:v", "10M"]
    if encoder_name == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "19", "-b:v", "10M"]
    if encoder_name == "h264_qsv":
        return ["-c:v", "h264_qsv", "-global_quality", "20", "-b:v", "10M"]
    if encoder_name == "h264_mf":
        return ["-c:v", "h264_mf", "-b:v", "10M"]

    return ["-c:v", encoder_name, "-b:v", "10M"]

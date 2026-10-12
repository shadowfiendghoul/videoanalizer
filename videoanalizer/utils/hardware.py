"""Hardware acceleration and GPU detection utilities for VideoAnalyzer."""

import logging
import os
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
    ("h264_videotoolbox", GpuVendor.APPLE),
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


def get_system_memory_mb() -> tuple[int, int]:
    """Retrieve system physical memory (total_mb, available_mb) cross-platform."""
    sys_name = platform.system()

    if sys_name == "Windows":
        try:
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MemoryStatusEx()
            stat.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return (
                    int(stat.ullTotalPhys // (1024 * 1024)),
                    int(stat.ullAvailPhys // (1024 * 1024)),
                )
        except Exception as e:
            logger.debug("Win32 memory query failed: %s", e)

    elif sys_name == "Linux":
        try:
            mem_total = 0
            mem_avail = 0
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1]) // 1024
                    elif line.startswith("MemAvailable:"):
                        mem_avail = int(line.split()[1]) // 1024
            if mem_total > 0:
                return (mem_total, mem_avail or (mem_total // 2))
        except Exception as e:
            logger.debug("Linux /proc/meminfo query failed: %s", e)

    elif sys_name == "Darwin":
        try:
            cmd = ["sysctl", "-n", "hw.memsize"]
            proc = subprocess.run(  # noqa: S603
                cmd, capture_output=True, text=True, timeout=2, check=False
            )
            if proc.returncode == 0 and proc.stdout.strip():
                total_mb = int(proc.stdout.strip()) // (1024 * 1024)
                return (total_mb, total_mb // 2)
        except Exception as e:
            logger.debug("macOS memory query failed: %s", e)

    return (8192, 4096)


def calculate_optimal_concurrency(
    profile: RenderProfile = RenderProfile.GPU_FAST,
    safety_margin: float = 0.75,
) -> int:
    """Dynamically calculate Remotion rendering concurrency based on CPU cores and RAM quota.

    Scales to 75-80% of logical CPU cores with strict memory guarding (~450MB per Chromium tab)
    to eliminate Out-Of-Memory (OOM) risks.
    """
    cores = os.cpu_count() or 4
    _total_mb, avail_mb = get_system_memory_mb()

    # Memory constraint: ~450MB per headless Chromium tab, reserve 15% headroom
    max_workers_by_ram = max(2, int((avail_mb * 0.85) // 450))

    if profile == RenderProfile.GPU_FAST:
        target_cores = max(2, int(cores * safety_margin))
    else:
        # In CPU_SAFE mode reserve extra cycles for x264 software encoder
        target_cores = max(2, int(cores * 0.60))

    return max(2, min(target_cores, max_workers_by_ram))


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

    cpu_cores = os.cpu_count() or 4
    total_mem_mb, avail_mem_mb = get_system_memory_mb()
    concurrency = calculate_optimal_concurrency(recommended_profile)

    caps = HardwareCapabilities(
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        gpu_vendor=gpu_vendor,
        active_hw_encoder=active_encoder,
        supported_encoders=working_encoders,
        gl_backend="angle" if platform.system() == "Windows" else "egl",
        recommended_profile=recommended_profile,
        bundle_cache_enabled=True,
        cpu_logical_cores=cpu_cores,
        ram_total_gb=round(total_mem_mb / 1024.0, 2),
        ram_available_gb=round(avail_mem_mb / 1024.0, 2),
        optimal_concurrency=concurrency,
        build_reuse_enabled=True,
    )

    logger.info(
        "Hardware capability probe: GPU='%s' (%s), Active Encoder=%s, CPU=%d cores, "
        "RAM=%.1f/%.1f GB, Optimal Concurrency=%d",
        caps.gpu_name,
        caps.gpu_vendor,
        caps.active_hw_encoder or "libx264",
        caps.cpu_logical_cores,
        caps.ram_available_gb,
        caps.ram_total_gb,
        caps.optimal_concurrency,
    )
    return caps


def get_active_encoder_args(
    encoder_name: str | None,
    profile: RenderProfile,
) -> list[str]:
    """Generate vendor-tailored FFmpeg encoding quality and ultra-fast bitrate arguments."""
    if profile == RenderProfile.CPU_SAFE or not encoder_name or encoder_name == "libx264":
        return [
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

    if encoder_name == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "speed", "-rc", "cbr", "-b:v", "12M"]
    if encoder_name == "h264_nvenc":
        return [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p1",
            "-tune",
            "ull",
            "-rc",
            "cbr",
            "-b:v",
            "12M",
        ]
    if encoder_name == "h264_qsv":
        return ["-c:v", "h264_qsv", "-preset", "veryfast", "-b:v", "12M"]
    if encoder_name == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-realtime", "1", "-b:v", "12M"]
    if encoder_name == "h264_mf":
        return ["-c:v", "h264_mf", "-rate_control", "cbr", "-b:v", "12M"]

    return ["-c:v", encoder_name, "-b:v", "12M"]

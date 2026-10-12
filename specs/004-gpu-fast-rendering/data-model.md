# Phase 1 Data Model: Схемы Pydantic v2 для аппаратного профиля 'gpu_fast'

**Feature**: `004-gpu-fast-rendering`  
**Date**: 2026-10-12  

Все контракты строго соответствуют **Принципу I (Strict Type Safety & Pydantic Data Contracts)** Конституции проекта.

---

## 📐 1. Перечисления (Enums)

### `RenderProfile`
```python
from enum import StrEnum

class RenderProfile(StrEnum):
    """Rendering execution profile."""
    GPU_FAST = "gpu_fast"  # Hardware GPU encoding (AMF/NVENC/QSV/MF) + ANGLE + Webpack Cache
    CPU_SAFE = "cpu_safe"  # Software CPU encoding (libx264) + Standard rasterization
```

### `GpuVendor`
```python
class GpuVendor(StrEnum):
    """Detected graphics processor vendor."""
    AMD = "amd"
    NVIDIA = "nvidia"
    INTEL = "intel"
    APPLE = "apple"
    GENERIC_WINDOWS = "windows_mf"
    UNKNOWN = "unknown"
```

---

## 🧩 2. Модели оборудования и статуса

### `HardwareCapabilities`
```python
from pydantic import BaseModel, Field

class HardwareCapabilities(BaseModel):
    """Detected hardware capabilities and hardware encoder status."""

    gpu_available: bool = Field(
        ...,
        description="Whether a compatible GPU was detected on the host system."
    )
    gpu_name: str = Field(
        default="Unknown GPU",
        description="Full human-readable graphics card name (e.g., 'AMD Radeon 780M Graphics')."
    )
    gpu_vendor: GpuVendor = Field(
        default=GpuVendor.UNKNOWN,
        description="Detected GPU vendor category."
    )
    active_hw_encoder: str | None = Field(
        default=None,
        description="Top-priority validated FFmpeg hardware encoder (e.g., 'h264_amf', 'h264_nvenc', 'h264_mf')."
    )
    supported_encoders: list[str] = Field(
        default_factory=list,
        description="List of all operational FFmpeg video encoders discovered on the machine."
    )
    gl_backend: str = Field(
        default="angle",
        description="Optimal Chromium OpenGL/DirectX rasterization backend ('angle', 'egl', etc.)."
    )
    recommended_profile: RenderProfile = Field(
        default=RenderProfile.GPU_FAST,
        description="Recommended profile based on verified hardware capabilities."
    )
```

---

## 🔄 3. Обновления в существующих контрактах

### `QuizGenerateRequest` (`videoanalizer/api/routes_quiz.py`)
```python
class QuizGenerateRequest(BaseModel):
    # Существующие поля (topic, language, retention_enabled, etc.)...
    
    render_profile: RenderProfile = Field(
        default=RenderProfile.GPU_FAST,
        description="Rendering acceleration profile ('gpu_fast' or 'cpu_safe').",
    )
```

### `QuizOrchestratorConfig` (`videoanalizer/quiz/config.py`)
```python
class QuizOrchestratorConfig(BaseSettings):
    # Существующие параметры (fps, width, height, crf, etc.)...
    
    render_profile: RenderProfile = Field(
        default=RenderProfile.GPU_FAST,
        description="Active rendering execution profile.",
    )
    enable_bundle_cache: bool = Field(
        default=True,
        description="Enable Webpack compilation bundle caching across renders.",
    )
    gl_backend: str = Field(
        default="angle",
        description="Chromium GPU rendering backend for Remotion CLI.",
    )
```

### `VideoUniquifierConfig` (`videoanalizer/media/uniquifier.py`)
```python
class VideoUniquifierConfig(BaseModel):
    # Существующие параметры (mode, brightness, contrast, etc.)...

    render_profile: RenderProfile = Field(
        default=RenderProfile.GPU_FAST,
        description="Encoder profile used during final re-encoding.",
    )
```

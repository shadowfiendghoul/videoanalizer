"""FastAPI REST routes for Quiz Shorts Generator background jobs and video download."""

import logging
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from videoanalizer.media.uniquifier import VideoUniquifierConfig
from videoanalizer.quiz.audio_service import probe_audio_duration_ms
from videoanalizer.quiz.batch_queue import get_batch_queue_manager
from videoanalizer.quiz.models import (
    BatchQueueItem,
    BatchQueueItemStatus,
    BatchQueueState,
    BatchRenderStartRequest,
    BatchTopicList,
    BatchTopicSuggestRequest,
    ComboStreakConfig,
    CommentTrapConfig,
    GenerationHistoryItem,
    HardwareCapabilities,
    QuizChallenge,
    QuizRetentionConfig,
    RenderProfile,
    RvcModelListResponse,
    SingleTopicSuggestRequest,
    TopicSuggestion,
    VisualQuizDataset,
    VisualTopicSuggestion,
    VoiceConfig,
    VoicePreviewRequest,
    VoicePreviewResponse,
    WidescreenQuizDataset,
)
from videoanalizer.quiz.exclusions_service import QuizExclusionsManager
from videoanalizer.quiz.image_service import ImageService
from videoanalizer.quiz.orchestrator import QuizOrchestrator
from videoanalizer.quiz.sound_service import SoundService
from videoanalizer.quiz.voice_service import RvcModelRegistry, VoiceService
from videoanalizer.utils.hardware import get_hardware_capabilities

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz Shorts Generator"])
hardware_router = APIRouter(prefix="/api/v1/hardware", tags=["Hardware Acceleration"])
voice_router = APIRouter(prefix="/api/v1/voice", tags=["Voice Pipeline & Cloning"])


@hardware_router.get("/status", response_model=HardwareCapabilities)
@router.get("/hardware/status", response_model=HardwareCapabilities)
async def get_hardware_status() -> HardwareCapabilities:
    """Detect and return GPU hardware acceleration capabilities and encoders."""
    return get_hardware_capabilities()


class QuizQuestionsPreviewRequest(BaseModel):
    """Payload to generate question preview before video rendering."""

    topic: str = Field(..., description="Topic prompt for the 9-question quiz challenge.")
    language: Literal["ru", "en"] = Field(default="ru", description="Narration and text language.")
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description=(
            "Sampling temperature for creative generation (0.2-2.0, default 0.95)."
        ),
    )
    fact_check: bool | None = Field(
        default=None,
        description="Enable strict secondary fact-checking pass to correct inaccuracies and myths.",
    )


class QuizRegenerateSelectedRequest(BaseModel):
    """Payload to selectively regenerate specified questions in an existing challenge."""

    challenge: QuizChallenge = Field(
        ..., description="Current 9-question challenge structure with any user edits."
    )
    question_numbers: list[int] = Field(
        ...,
        min_length=1,
        max_length=9,
        description="List of question numbers (1 to 9) to regenerate.",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description=(
            "Sampling temperature for creative generation (0.2-2.0, default 0.95)."
        ),
    )
    fact_check: bool | None = Field(
        default=None,
        description="Enable strict secondary fact-checking pass.",
    )


class QuizGenerateRequest(BaseModel):
    """Payload to trigger asynchronous quiz video generation."""

    topic: str = Field(..., description="Topic prompt for the 9-question quiz challenge.")
    language: Literal["ru", "en"] = Field(default="ru", description="Narration and text language.")
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description=(
            "Sampling temperature for creative generation (0.2-2.0, default 0.95)."
        ),
    )
    fact_check: bool | None = Field(
        default=None,
        description="Enable strict secondary fact-checking pass to correct inaccuracies and myths.",
    )
    background_video: str | None = Field(
        default=None, description="Optional custom background video filename or path, or 'random'."
    )
    background_mode: Literal["loop", "random_switch"] = Field(
        default="loop",
        description="Background video playback mode: 'loop' (single seamless loop) or 'random_switch' (random change upon ending).",
    )
    voice: str | None = Field(default=None, description="Optional edge-tts voice override.")
    voice_config: VoiceConfig | None = Field(
        default=None, description="Optional voice pipeline and cloning configuration."
    )
    banner_video: str | None = Field(
        default=None, description="Optional custom promo banner video filename or path."
    )
    challenge: QuizChallenge | None = Field(
        default=None, description="Optional pre-approved 9-question challenge structure."
    )
    retention_enabled: bool = Field(
        default=True, description="Master switch for viral retention mechanics."
    )
    rank_bar_enabled: bool = Field(
        default=True, description="Enable psychological IQ/Rank status bar."
    )
    stress_timer_enabled: bool = Field(
        default=True, description="Enable blitz progressive stress timer."
    )
    streak_fire_enabled: bool = Field(
        default=True, description="Enable combo streak flame counter."
    )
    comment_trap_enabled: bool = Field(
        default=True, description="Enable controversy outro comment callout."
    )
    intro_hook: str | None = Field(
        default=None,
        description=(
            "Optional custom greeting/hook phrase spoken at start. "
            "If omitted or None, video starts directly with Question 1."
        ),
    )
    background_music: str | None = Field(
        default=None,
        description="Optional custom background music filename or path.",
    )
    background_music_volume: float = Field(
        default=0.18,
        ge=0.0,
        le=1.0,
        description="Background music volume (0.0 to 1.0, default 0.18).",
    )
    uniquifier: VideoUniquifierConfig | None = Field(
        default=None,
        description="Optional video uniquifier and anti-fingerprint configuration.",
    )
    render_profile: RenderProfile = Field(
        default=RenderProfile.GPU_FAST,
        description="Rendering acceleration profile ('gpu_fast' or 'cpu_safe').",
    )


class ImageSearchRequest(BaseModel):
    """Payload to search candidate images for visual trivia."""

    query: str = Field(..., description="Image search query string.")
    max_results: int = Field(default=5, description="Maximum candidate images to fetch.")


class ImageSearchResultItem(BaseModel):
    """Candidate image result."""

    image: str
    thumbnail: str | None = None


class ImageSearchResponse(BaseModel):
    """List of image search candidates."""

    images: list[ImageSearchResultItem]


class BannerUploadResponse(BaseModel):
    """Metadata response when a promo banner video is uploaded."""

    banner_path: str
    filename: str
    saved_filename: str
    duration_seconds: float


class MusicUploadResponse(BaseModel):
    """Metadata response when a background music audio file is uploaded."""

    music_path: str
    filename: str
    saved_filename: str
    duration_seconds: float


class VisualQuizGenerateRequest(BaseModel):
    """Payload to generate Visual Image Quiz script and candidates."""

    theme: str | None = Field(default=None, description="Optional topic for visual quiz")
    language: Literal["ru", "en"] = Field(default="ru", description="Voice and UI language")
    auto_search_images: bool = Field(default=True, description="Automatically search candidate images on web")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0, description="Sampling temperature")


class VisualQuizRenderRequest(BaseModel):
    """Payload to render approved Visual Image Quiz into MP4."""

    dataset: VisualQuizDataset = Field(..., description="Approved visual quiz dataset")
    background_video: str | None = Field(default=None, description="Optional background video file or path")
    background_mode: Literal["loop", "random_switch"] = Field(
        default="loop",
        description="Background video playback mode: 'loop' or 'random_switch'",
    )
    background_music: str | None = Field(default=None, description="Optional background music file or path")
    background_music_volume: float = Field(default=0.18, ge=0.0, le=1.0, description="Music volume")
    voice: str | None = Field(default=None, description="Edge-TTS voice name")
    voice_config: VoiceConfig | None = Field(default=None, description="Voice pipeline config")
    banner_video: str | None = Field(default=None, description="Optional custom promo banner video filename or path")
    render_profile: RenderProfile | None = Field(default=None, description="Render profile (e.g. gpu_fast, cpu_safe)")

    @field_validator("render_profile", mode="before")
    @classmethod
    def normalize_render_profile(cls, v: Any) -> Any:
        if isinstance(v, str):
            clean = v.strip().lower()
            if clean in {"fast", "gpu", "gpu_fast"}:
                return RenderProfile.GPU_FAST
            if clean in {"cpu", "safe", "cpu_safe"}:
                return RenderProfile.CPU_SAFE
        return v


class VisualTopicSuggestRequest(BaseModel):
    """Payload to request an AI visual quiz topic suggestion with rapid-flip hook."""

    category_hint: str | None = Field(
        default=None, max_length=300, description="Optional theme or category guidance"
    )
    language: Literal["ru", "en"] = Field(
        default="ru", description="Output language (ru or en)"
    )
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Sampling temperature (0.0-2.0, default 1.05)"
    )


class VisualQuizRenderResponse(BaseModel):
    """Result of Visual Image Quiz video rendering."""

    video_path: str = Field(..., description="Local path to generated MP4 video")
    download_url: str = Field(..., description="API endpoint to download or stream MP4")
    duration_sec: float | None = Field(default=None, description="Video duration in seconds")
    status: str = Field(default="completed", description="Render status")


class QuizPlanItem(BaseModel):
    """Item specification in a JSON publication plan."""

    topic: str = Field(..., description="Quiz theme or topic prompt")
    title: str = Field(default="", description="YouTube video title")
    description: str = Field(default="", description="YouTube video description")
    date: str | None = Field(default=None, description="Scheduled publication date/time (RFC 3339 or ISO)")
    tags: list[str] = Field(default_factory=list, description="YouTube search tags")
    hook_tts: str | None = Field(default=None, description="Optional custom intro hook phrase")
    channel: str | None = Field(default=None, description="Optional target YouTube channel name or ID")



class LoadPlanRequest(BaseModel):
    """Payload to load publishing plan from local file or raw JSON content."""

    file_path: str | None = Field(default=None, description="Filesystem path to JSON file")
    raw_json: str | None = Field(default=None, description="Raw JSON string")


class LoadPlanResponse(BaseModel):
    """Parsed items from plan JSON."""

    status: str = "ok"
    items: list[QuizPlanItem]
    count: int



class BackgroundInfo(BaseModel):
    """Available background video or folder metadata."""

    id: str
    name: str
    filename: str
    folder: str | None = None
    is_folder: bool = False
    count: int = 1


class QuizGenerateResponse(BaseModel):
    """Immediate response confirming job acceptance."""

    job_id: str
    status: str = "pending"
    topic: str
    created_at: str
    status_url: str


class ChallengeSummary(BaseModel):
    """Summary metadata of the generated challenge."""

    topic: str
    total_questions: int = 9
    duration_seconds: float


class QuizJobStatusResponse(BaseModel):
    """Status tracking response for an asynchronous quiz rendering job."""

    job_id: str
    status: str
    progress_percent: int
    stage: str
    challenge_summary: ChallengeSummary | None = None
    video_path: str | None = None
    download_url: str | None = None
    error_message: str | None = None


# In-memory job state storage
quiz_jobs: dict[str, dict] = {}


async def _run_quiz_job(job_id: str, request: QuizGenerateRequest) -> None:
    """Worker task executing the orchestrator pipeline."""
    orchestrator = QuizOrchestrator()
    job = quiz_jobs[job_id]

    try:
        job["status"] = "rendering_video"
        job["stage"] = "Инициализация рендеринга..."
        job["progress_percent"] = 10

        def on_progress(percent: int, stage_detail: str) -> None:
            job["progress_percent"] = max(job.get("progress_percent", 0), percent)
            job["stage"] = stage_detail

        retention_config = QuizRetentionConfig(
            enabled=request.retention_enabled,
            rank_bar_enabled=request.rank_bar_enabled,
            stress_timer_enabled=request.stress_timer_enabled,
            streak_fire=ComboStreakConfig(enabled=request.streak_fire_enabled),
            comment_trap=CommentTrapConfig(enabled=request.comment_trap_enabled),
        )

        output_path = await orchestrator.generate(
            topic=request.topic,
            language=request.language,
            background_video=request.background_video,
            voice=request.voice,
            banner_video=request.banner_video,
            challenge=request.challenge,
            retention_config=retention_config,
            creative_temperature=request.temperature,
            fact_check=request.fact_check,
            intro_hook=request.intro_hook,
            background_music=request.background_music,
            background_music_volume=request.background_music_volume,
            uniquifier=request.uniquifier,
            render_profile=request.render_profile,
            progress_callback=on_progress,
            voice_config=request.voice_config,
            background_mode=request.background_mode,
        )

        job["status"] = "completed"
        job["stage"] = "finished"
        job["progress_percent"] = 100
        job["video_path"] = str(output_path)
        job["download_url"] = f"/api/v1/quiz/jobs/{job_id}/download"
        job["challenge_summary"] = {
            "topic": request.topic,
            "total_questions": 9,
            "duration_seconds": 60.0,
        }

        # Also record in persistent generation history
        try:
            manager = get_batch_queue_manager()
            manager.record_history(
                BatchQueueItem(
                    item_id=job_id,
                    topic=request.topic,
                    order_index=1,
                    status=BatchQueueItemStatus.COMPLETED,
                    video_path=str(output_path),
                    download_url=f"/api/v1/quiz/jobs/{job_id}/download",
                )
            )
        except Exception as exc:
            logger.warning("Failed to record single quiz to history: %s", exc)
    except Exception as exc:
        logger.error("Quiz job %s failed: %s", job_id, exc, exc_info=True)
        job["status"] = "failed"
        job["stage"] = "error"
        job["progress_percent"] = 0
        job["error_message"] = str(exc)


@router.post("/preview-questions", response_model=QuizChallenge)
async def preview_questions(request: QuizQuestionsPreviewRequest) -> QuizChallenge:
    """Generate 9 trivia questions for interactive user review before rendering."""
    orchestrator = QuizOrchestrator()
    try:
        challenge = await orchestrator.script_service.generate_quiz(
            topic=request.topic,
            language=request.language,
            creative_temperature=request.temperature,
            fact_check=request.fact_check,
        )
        return challenge
    except Exception as exc:
        logger.error("Failed to generate quiz preview questions: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка генерации вопросов нейросетью: {exc}",
        ) from exc


@router.post("/regenerate-questions", response_model=QuizChallenge)
async def regenerate_questions(request: QuizRegenerateSelectedRequest) -> QuizChallenge:
    """Regenerate specific questions within an existing challenge while preserving others."""
    orchestrator = QuizOrchestrator()
    try:
        updated = await orchestrator.script_service.regenerate_selected_questions(
            challenge=request.challenge,
            question_numbers=request.question_numbers,
            creative_temperature=request.temperature,
            fact_check=request.fact_check,
        )
        return updated
    except Exception as exc:
        logger.error(
            "Failed to regenerate questions %s: %s",
            request.question_numbers,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка перегенерации вопросов: {exc}",
        ) from exc


@router.post("/topics/suggest-single", response_model=TopicSuggestion)
async def suggest_single_topic(request: SingleTopicSuggestRequest) -> TopicSuggestion:
    """Suggest an individual viral quiz topic via Gemini REST API."""
    orchestrator = QuizOrchestrator()
    try:
        suggestion = await orchestrator.script_service.suggest_topic(
            category_hint=request.category_hint,
            language=request.language,
            temperature=request.temperature,
            previous_topic=request.previous_topic,
        )
        return suggestion
    except Exception as exc:
        logger.error("Failed to suggest single topic: %s", exc, exc_info=True)
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"Ошибка генерации темы: {exc}",
        ) from exc


@router.post("/topics/suggest-batch", response_model=BatchTopicList)
async def suggest_batch_topics(request: BatchTopicSuggestRequest) -> BatchTopicList:
    """Suggest N diverse viral quiz topics in a SINGLE request to conserve quota."""
    orchestrator = QuizOrchestrator()
    try:
        batch = await orchestrator.script_service.suggest_batch_topics(
            count=request.count,
            category_hint=request.category_hint,
            language=request.language,
            temperature=request.temperature,
        )
        return batch
    except Exception as exc:
        logger.error("Failed to suggest batch topics: %s", exc, exc_info=True)
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"Ошибка генерации списка тем: {exc}",
        ) from exc


@router.post("/search-image", response_model=ImageSearchResponse)
async def search_image(request: ImageSearchRequest) -> ImageSearchResponse:
    """Search candidates for visual trivia question preview, strictly transparent PNG prioritized."""
    orchestrator = QuizOrchestrator()
    sanitized_query = ImageService.format_transparent_query(request.query)
    items = await orchestrator.image_service._search_image_urls(
        sanitized_query, max_results=max(8, request.max_results)
    )
    sorted_items = ImageService.sort_transparent_candidates(items)
    results: list[ImageSearchResultItem] = []
    for it in sorted_items:
        img_url = it.get("image") or it.get("thumbnail")
        if img_url:
            results.append(
                ImageSearchResultItem(
                    image=img_url,
                    thumbnail=it.get("thumbnail") or img_url,
                )
            )
    return ImageSearchResponse(images=results[: request.max_results])


@router.post("/upload-banner", response_model=BannerUploadResponse)
async def upload_banner(file: UploadFile) -> BannerUploadResponse:
    """Upload a promotional video banner (MP4, WebM, MOV) to be displayed in the center."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )
    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp4", ".webm", ".mov", ".m4v"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format '{ext}'. Allowed: .mp4, .webm, .mov, .m4v",
        )

    orchestrator = QuizOrchestrator()
    banners_dir = orchestrator.config.banners_dir
    banners_dir.mkdir(parents=True, exist_ok=True)

    safe_stem = "".join(c if c.isalnum() else "_" for c in Path(file.filename).stem).strip("_")
    saved_name = f"banner_{uuid.uuid4().hex[:8]}_{safe_stem}{ext}"
    target_path = banners_dir / saved_name

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    dur_frames = orchestrator._probe_video_duration_frames(target_path, fps=orchestrator.config.fps)
    dur_sec = round(dur_frames / orchestrator.config.fps, 2)

    return BannerUploadResponse(
        banner_path=str(target_path),
        filename=file.filename,
        saved_filename=saved_name,
        duration_seconds=dur_sec,
    )


@router.post("/upload-music", response_model=MusicUploadResponse)
async def upload_music(file: UploadFile) -> MusicUploadResponse:
    """Upload background music audio file (MP3, WAV, M4A, OGG, AAC, FLAC)."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload.",
        )
    ext = Path(file.filename).suffix.lower()
    allowed_exts = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{ext}'. Allowed: {', '.join(sorted(allowed_exts))}",
        )

    orchestrator = QuizOrchestrator()
    music_dir = orchestrator.config.music_dir
    music_dir.mkdir(parents=True, exist_ok=True)

    safe_stem = "".join(c if c.isalnum() else "_" for c in Path(file.filename).stem).strip("_")
    saved_name = f"music_{uuid.uuid4().hex[:8]}_{safe_stem}{ext}"
    target_path = music_dir / saved_name

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    dur_ms = probe_audio_duration_ms(target_path)
    dur_sec = round(dur_ms / 1000.0, 2)

    return MusicUploadResponse(
        music_path=str(target_path),
        filename=file.filename,
        saved_filename=saved_name,
        duration_seconds=dur_sec,
    )


@router.get("/music")
async def list_available_music() -> list[dict[str, str | float]]:
    """List available saved background music audio files."""
    orchestrator = QuizOrchestrator()
    music_dir = orchestrator.config.music_dir
    results: list[dict[str, str | float]] = []
    allowed_exts = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
    if music_dir.exists():
        for p in sorted(music_dir.iterdir()):
            if p.is_file() and p.suffix.lower() in allowed_exts:
                dur_ms = probe_audio_duration_ms(p)
                results.append(
                    {
                        "filename": p.name,
                        "saved_filename": p.name,
                        "duration_seconds": round(dur_ms / 1000.0, 2),
                    }
                )
    return results


def _format_bg_friendly_name(stem: str) -> str:
    lower = stem.lower()
    if "minecraft" in lower:
        return "Minecraft Parkour"
    elif "forza" in lower:
        return "Forza Horizon — Ночное шоссе (Forza Night Highway)"
    elif "gta" in lower and ("night" in lower or "highway" in lower):
        return "GTA 5 — Ночное шоссе (GTA 5 Night Highway)"
    elif "gta" in lower:
        return "GTA 5 Mega Ramp"
    elif "subway" in lower:
        return "Subway Surfers"
    elif "earth" in lower or "space" in lower:
        return "Земля из космоса (Earth Night)"
    elif "topograph" in lower:
        return "Тёмная топография (Dark Topography 16:9)"
    elif "cyber_grid" in lower:
        return "Кибер-сетка 3D (Cyber Grid 3D 16:9)"
    elif "aurora" in lower:
        return "Северное сияние (Aurora Borealis 16:9)"
    elif "digital_rain" in lower or "rain" in lower:
        return "Цифровой дождь Матрицы (Digital Rain Matrix 16:9)"
    elif "hexagon" in lower:
        return "Неоновые гексагоны (Geometric Hexagons 16:9)"
    elif "starfield" in lower:
        return "Космическое звездное поле (Minimal Starfield 16:9)"
    elif "synthwave" in lower or "sunset" in lower:
        return "Ретровейв закат (Synthwave Sunset 16:9)"
    elif "ribbon" in lower or "sine" in lower:
        return "Шелковые синусоиды (Flowing Sine Ribbons 16:9)"
    elif "dot_matrix" in lower or "isometric" in lower:
        return "Изометрическая матрица точек (Isometric Dot Matrix 16:9)"
    elif "crimson" in lower or "nebula" in lower:
        return "Багровая туманность (Crimson Nebula Liquid 16:9)"
    elif "pink" in lower or "lightning" in lower:
        return "Розовые молнии (Pink Lightning)"
    elif "mint" in lower:
        return "Мятные звёздочки (Mint Stars)"
    elif "lavender" in lower or "heart" in lower:
        return "Лавандовые сердца (Lavender Hearts)"
    elif "peach" in lower or "butterfl" in lower:
        return "Персиковые бабочки (Peach Butterflies)"
    elif "cloud" in lower or "sky" in lower:
        return "Небесные облака (Sky Clouds)"
    elif "dais" in lower or "buttercup" in lower:
        return "Сливочные ромашки (Buttercup Daisies)"
    elif "default" in lower:
        return "Стандартный фон (Default)"
    elif lower.startswith("videoplayback"):
        num = "".join(ch for ch in stem if ch.isdigit())
        return f"Геймплей клип #{num}" if num else "Геймплей клип"
    else:
        return stem.replace("_", " ").title()


@router.get("/backgrounds", response_model=list[BackgroundInfo])
async def list_available_backgrounds() -> list[BackgroundInfo]:
    """List available background video files and subfolders."""
    orchestrator = QuizOrchestrator()
    bg_dir = orchestrator.config.backgrounds_dir
    results: list[BackgroundInfo] = []
    if not bg_dir.exists():
        return results

    # 1. Discover subfolders containing .mp4 files
    subdirs = [d for d in bg_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    for sub in sorted(subdirs, key=lambda d: d.name.lower()):
        mp4s = [p for p in sub.glob("*.mp4") if not p.name.startswith(".") and p.is_file()]
        if not mp4s:
            continue
        folder_friendly = sub.name.replace("_", " ").title()
        # Add folder item (for random switching strictly within folder)
        results.append(
            BackgroundInfo(
                id=f"folder:{sub.name}",
                name=f"Папка: {folder_friendly} ({len(mp4s)} видео)",
                filename=f"folder:{sub.name}",
                folder=sub.name,
                is_folder=True,
                count=len(mp4s),
            )
        )
        # Add individual files within subfolder
        for p in sorted(mp4s, key=lambda f: f.name.lower()):
            rel_name = f"{sub.name}/{p.name}"
            results.append(
                BackgroundInfo(
                    id=rel_name,
                    name=_format_bg_friendly_name(p.stem),
                    filename=rel_name,
                    folder=sub.name,
                    is_folder=False,
                    count=1,
                )
            )

    # 2. Discover root .mp4 files
    for p in sorted(bg_dir.glob("*.mp4"), key=lambda f: f.name.lower()):
        if p.name.startswith(".") or not p.is_file():
            continue
        results.append(
            BackgroundInfo(
                id=p.name,
                name=_format_bg_friendly_name(p.stem),
                filename=p.name,
                folder=None,
                is_folder=False,
                count=1,
            )
        )

    return results


@router.post("/backgrounds/open-folder")
async def open_backgrounds_folder() -> dict[str, str]:
    """Open backgrounds directory in local file manager (Explorer on Windows)."""
    orchestrator = QuizOrchestrator()
    bg_dir = orchestrator.config.backgrounds_dir
    bg_dir.mkdir(parents=True, exist_ok=True)
    try:
        resolved = str(bg_dir.resolve())
        if sys.platform == "win32":
            os.startfile(resolved)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", resolved], check=False)
        else:
            subprocess.run(["xdg-open", resolved], check=False)
        return {"status": "ok", "path": resolved}
    except Exception as exc:
        logger.warning("Failed to open backgrounds folder: %s", exc)
        return {"status": "error", "message": str(exc), "path": str(bg_dir.resolve())}


class ExclusionsAddRequest(BaseModel):
    """Payload to add custom topic and/or items to exclusions."""

    topic: str | None = Field(default=None, description="Topic to exclude")
    items: list[str] | None = Field(default=None, description="List of items/brands to exclude")


@router.get("/exclusions")
async def get_quiz_exclusions():
    """Retrieve currently stored topics and items to be excluded from quiz generation."""
    manager = QuizExclusionsManager()
    data = manager.load()
    return {
        "status": "ok",
        "file_path": str(manager.file_path.resolve()),
        "topics": data.get("topics", []),
        "items": data.get("items", []),
        "count_topics": len(data.get("topics", [])),
        "count_items": len(data.get("items", [])),
    }


@router.post("/exclusions/add")
async def add_quiz_exclusions(request: ExclusionsAddRequest):
    """Add a topic and/or list of items/brands to exclusions."""
    manager = QuizExclusionsManager()
    res = manager.add_exclusions(topic=request.topic, items=request.items)
    return {
        "status": "ok",
        "total_topics": res["total_topics"],
        "total_items": res["total_items"],
    }


@router.post("/exclusions/clear")
async def clear_quiz_exclusions():
    """Clear all stored exclusions."""
    manager = QuizExclusionsManager()
    manager.clear()
    return {"status": "ok", "message": "Исключения успешно очищены"}


@router.post("/exclusions/open-file")
async def open_quiz_exclusions_file() -> dict[str, str]:
    """Open exclusions JSON file in system default editor (e.g. Notepad on Windows)."""
    manager = QuizExclusionsManager()
    manager.ensure_file()
    try:
        resolved = str(manager.file_path.resolve())
        if sys.platform == "win32":
            os.startfile(resolved)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", resolved], check=False)
        else:
            subprocess.run(["xdg-open", resolved], check=False)
        return {"status": "ok", "path": resolved}
    except Exception as exc:
        logger.warning("Failed to open exclusions file: %s", exc)
        return {"status": "error", "message": str(exc), "path": str(manager.file_path.resolve())}


@router.post("/generate", response_model=QuizGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_quiz(
    request: QuizGenerateRequest,
    background_tasks: BackgroundTasks,
) -> QuizGenerateResponse:
    """Trigger asynchronous background quiz video generation."""
    job_id = f"qz_{uuid.uuid4().hex[:10]}"
    created_at = datetime.now(UTC).isoformat()
    status_url = f"/api/v1/quiz/jobs/{job_id}"

    quiz_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "stage": "queued",
        "progress_percent": 5,
        "topic": request.topic,
        "created_at": created_at,
        "video_path": None,
        "download_url": None,
        "error_message": None,
        "challenge_summary": None,
    }

    background_tasks.add_task(_run_quiz_job, job_id, request)

    return QuizGenerateResponse(
        job_id=job_id,
        status="pending",
        topic=request.topic,
        created_at=created_at,
        status_url=status_url,
    )


@router.get("/jobs/{job_id}", response_model=QuizJobStatusResponse)
async def get_quiz_job(job_id: str) -> QuizJobStatusResponse:
    """Retrieve execution status and progress for a quiz video generation job."""
    if job_id not in quiz_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz job '{job_id}' not found.",
        )

    data = quiz_jobs[job_id]
    summary_data = data.get("challenge_summary")
    summary = ChallengeSummary(**summary_data) if summary_data else None

    return QuizJobStatusResponse(
        job_id=data["job_id"],
        status=data["status"],
        progress_percent=data["progress_percent"],
        stage=data["stage"],
        challenge_summary=summary,
        video_path=data.get("video_path"),
        download_url=data.get("download_url"),
        error_message=data.get("error_message"),
    )


@router.get("/jobs/{job_id}/download")
async def download_quiz_video(job_id: str) -> FileResponse:
    """Download the completed 1080x1920 60fps MP4 video."""
    if job_id not in quiz_jobs:
        manager = get_batch_queue_manager()
        for it in manager.get_history():
            if (
                it.job_id == job_id
                or it.history_id == job_id
                or job_id in it.video_path
            ) and Path(it.video_path).exists():
                p = Path(it.video_path)
                return FileResponse(path=str(p), media_type="video/mp4", filename=p.name)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz job '{job_id}' not found.",
        )

    job = quiz_jobs[job_id]
    if job["status"] != "completed" or not job.get("video_path"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quiz job '{job_id}' has not finished rendering yet (status: {job['status']}).",
        )

    video_path = Path(job["video_path"])
    if not video_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rendered video file is missing on server.",
        )

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=video_path.name,
    )


# ==============================================================================
# Batch Queue & Multi-Video Approval Endpoints (005-batch-queue-topics)
# ==============================================================================


class BatchInitRequest(BaseModel):
    """Payload to initialize a batch session and start progressive script generation."""

    topics: list[str] = Field(..., min_length=1, max_length=20, description="List of topics")
    language: Literal["ru", "en"] = Field(default="ru")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    fact_check: bool | None = Field(default=None)


@router.post("/batch/init", response_model=BatchQueueState)
async def init_batch(request: BatchInitRequest) -> BatchQueueState:
    """Initialize a batch session and launch progressive paced background generation."""
    manager = get_batch_queue_manager()
    state = await manager.init_batch(
        topics=request.topics,
        language=request.language,
        temperature=request.temperature,
        fact_check=request.fact_check,
    )
    return state


@router.get("/batch/queue/status", response_model=BatchQueueState)
async def get_batch_queue_status() -> BatchQueueState:
    """Retrieve live status, progress percentages, and metrics of active batch queue."""
    manager = get_batch_queue_manager()
    if manager.current_state is None:
        return BatchQueueState(
            batch_id="empty",
            items=[],
            is_rendering=False,
            active_item_id=None,
            completed_count=0,
            total_count=0,
            rate_limit_waiting=False,
            rate_limit_delay_sec=0.0,
        )
    return manager.current_state


@router.post("/batch/queue/start", response_model=BatchQueueState)
async def start_batch_queue(request: BatchRenderStartRequest) -> BatchQueueState:
    """Enqueue approved batch items into sequential Remotion render queue."""
    logger.info(
        "🚀 [API] /batch/queue/start: batch_id='%s', %d approved items, voice=%s",
        request.batch_id,
        len(request.approved_item_ids),
        request.voice,
    )
    manager = get_batch_queue_manager()
    state = await manager.start_render_queue(request)
    return state


@router.post("/batch/queue/cancel/{item_id}")
async def cancel_batch_item(item_id: str) -> dict[str, str]:
    """Cancel a queued item before its rendering starts."""
    manager = get_batch_queue_manager()
    ok = manager.cancel_item(item_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Элемент очереди '{item_id}' не найден или уже рендерится.",
        )
    return {"status": "cancelled", "item_id": item_id}


@router.post("/batch/queue/clear")
async def clear_batch_queue() -> dict[str, str]:
    """Clear completed and failed jobs from queue list."""
    manager = get_batch_queue_manager()
    manager.clear_completed()
    return {"status": "cleared"}


@router.get("/batch/queue/download-all")
async def download_all_batch_videos() -> StreamingResponse:
    """Download ZIP archive containing all completed batch MP4 videos."""
    manager = get_batch_queue_manager()
    mem_zip = manager.create_batch_zip()
    if not mem_zip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Нет готовых видео для скачивания в архиве.",
        )
    return StreamingResponse(
        mem_zip,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=quiz_batch_videos.zip"},
    )


@router.get("/batch/download/{item_id}")
async def download_batch_item_video(item_id: str) -> FileResponse:
    """Download single completed batch MP4 video."""
    manager = get_batch_queue_manager()
    found_item = None
    if manager.current_state:
        for it in manager.current_state.items:
            if it.item_id == item_id:
                found_item = it
                break

    if not found_item:
        for it in manager.get_history():
            if (
                it.job_id == item_id
                or it.history_id == item_id
                or Path(it.video_path).stem == item_id
            ) and Path(it.video_path).exists():
                p = Path(it.video_path)
                return FileResponse(path=str(p), media_type="video/mp4", filename=p.name)

    if (
        not found_item
        or found_item.status != BatchQueueItemStatus.COMPLETED
        or not found_item.video_path
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Видео для задачи '{item_id}' ещё не готово или отсутствует.",
        )

    p = Path(found_item.video_path)
    if not p.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл готового видео не найден на сервере.",
        )
    return FileResponse(path=str(p), media_type="video/mp4", filename=p.name)


@router.get("/history", response_model=list[GenerationHistoryItem])
async def get_generation_history() -> list[GenerationHistoryItem]:
    """Retrieve persistent history of all completed quiz video generations."""
    manager = get_batch_queue_manager()
    return manager.get_history()


@router.get("/history/download/{item_id}")
async def download_history_video(item_id: str) -> FileResponse:
    """Download or stream completed video from generation history."""
    manager = get_batch_queue_manager()
    for it in manager.get_history():
        if (
            it.history_id == item_id
            or it.job_id == item_id
            or Path(it.video_path).stem == item_id
            or Path(it.video_path).name == item_id
        ) and Path(it.video_path).exists():
            p = Path(it.video_path)
            return FileResponse(path=str(p), media_type="video/mp4", filename=p.name)

    # Direct fallback on candidate folders
    for d in [manager.config.output_dir, Path("output"), Path("outputs")]:
        cand = d / item_id
        if cand.exists() and cand.is_file():
            return FileResponse(path=str(cand), media_type="video/mp4", filename=cand.name)
        cand_mp4 = d / f"{item_id}.mp4"
        if cand_mp4.exists() and cand_mp4.is_file():
            return FileResponse(path=str(cand_mp4), media_type="video/mp4", filename=cand_mp4.name)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Видео '{item_id}' не найдено в истории генераций.",
    )


# ==============================================================================
# Visual Image Quiz Endpoints (007-visual-image-quiz)
# ==============================================================================


@router.post("/visual/generate", response_model=VisualQuizDataset)
async def generate_visual_quiz(request: VisualQuizGenerateRequest) -> VisualQuizDataset:
    """Generate a complete Visual Image Quiz script and candidate images."""
    orchestrator = QuizOrchestrator()
    try:
        return await orchestrator.script_service.generate_visual_quiz_dataset(
            theme=request.theme,
            language=request.language,
            auto_search_images=request.auto_search_images,
            temperature=request.temperature,
        )
    except Exception as exc:
        logger.error("Failed to generate visual quiz: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось сгенерировать визуальную викторину: {exc}",
        ) from exc


@router.post("/visual/suggest-topic", response_model=VisualTopicSuggestion)
async def suggest_visual_topic(request: VisualTopicSuggestRequest) -> VisualTopicSuggestion:
    """Suggest a viral visual quiz topic with catchy rapid-flip hook via Gemini."""
    orchestrator = QuizOrchestrator()
    try:
        return await orchestrator.script_service.suggest_visual_topic(
            category_hint=request.category_hint,
            language=request.language,
            temperature=request.temperature,
        )
    except Exception as exc:
        logger.error("Failed to suggest visual topic: %s", exc, exc_info=True)
        status_code = (
            status.HTTP_429_TOO_MANY_REQUESTS
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(
            status_code=status_code,
            detail=f"Не удалось сгенерировать визуальную тему: {exc}",
        ) from exc


@router.post("/plan/load", response_model=LoadPlanResponse)
async def load_quiz_plan(request: LoadPlanRequest) -> LoadPlanResponse:
    """Load and parse publication plan JSON containing topic, date, title, description."""
    raw_data = None

    if request.file_path:
        p = Path(request.file_path.strip().strip('"\''))
        if not p.is_absolute():
            candidates = [p, Path("data") / p, Path(".") / p]
            for cand in candidates:
                if cand.exists() and cand.is_file():
                    p = cand
                    break
        if not p.exists() or not p.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Файл плана '{request.file_path}' не найден.",
            )
        try:
            with p.open("r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка чтения JSON из файла '{p.name}': {exc}",
            ) from exc

    elif request.raw_json:
        try:
            raw_data = json.loads(request.raw_json)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка парсинга JSON: {exc}",
            ) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Укажите 'file_path' к JSON файлу или передайте 'raw_json'.",
        )

    raw_list = raw_data if isinstance(raw_data, list) else [raw_data]
    parsed_items: list[QuizPlanItem] = []

    for entry in raw_list:
        if not isinstance(entry, dict):
            continue
        topic = (
            entry.get("topic")
            or entry.get("theme")
            or entry.get("subject")
            or entry.get("prompt")
            or ""
        ).strip()
        if not topic:
            continue

        title = (
            entry.get("title")
            or entry.get("name")
            or f"{topic} #shorts #викторина"
        ).strip()

        desc = (
            entry.get("description")
            or entry.get("desc")
            or "Сможешь ответить на все вопросы? Пиши в комментариях! 👇\n\n#shorts #викторина"
        ).strip()

        date_val = (
            entry.get("date")
            or entry.get("publish_at")
            or entry.get("publishAt")
            or entry.get("scheduled_at")
            or entry.get("time")
        )
        if date_val:
            date_val = str(date_val).strip()

        tags_val = entry.get("tags") or entry.get("keywords") or []
        if isinstance(tags_val, str):
            tags_list = [t.strip() for t in tags_val.split(",") if t.strip()]
        elif isinstance(tags_val, list):
            tags_list = [str(t).strip() for t in tags_val if str(t).strip()]
        else:
            tags_list = []

        hook_val = (entry.get("hook_tts") or entry.get("hook") or "").strip() or None
        channel_val = (entry.get("channel") or entry.get("channel_id") or "").strip() or None

        parsed_items.append(
            QuizPlanItem(
                topic=topic,
                title=title,
                description=desc,
                date=date_val,
                tags=tags_list,
                hook_tts=hook_val,
                channel=channel_val,
            )
        )

    if not parsed_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="В переданном JSON не найдено ни одного элемента с полем 'topic' или 'theme'.",
        )

    return LoadPlanResponse(status="ok", items=parsed_items, count=len(parsed_items))


@router.post("/visual/render", response_model=VisualQuizRenderResponse)
async def render_visual_quiz(request: VisualQuizRenderRequest) -> VisualQuizRenderResponse:
    """Render finalized Visual Image Quiz into MP4 via Remotion."""
    logger.info(
        "🚀 [API] /visual/render: theme='%s', items=%d, voice=%s, profile=%s",
        request.dataset.theme,
        len(request.dataset.items),
        request.voice,
        request.render_profile,
    )
    orchestrator = QuizOrchestrator()
    job_id = f"vis_{uuid.uuid4().hex[:10]}"
    try:
        out_path = await orchestrator.render_visual_quiz(
            dataset=request.dataset,
            background_video=request.background_video,
            background_music=request.background_music,
            background_music_volume=request.background_music_volume,
            voice=request.voice,
            voice_config=request.voice_config,
            render_profile=request.render_profile,
            background_mode=request.background_mode,
            banner_video=request.banner_video,
        )
        download_url = f"/api/v1/quiz/jobs/{job_id}/download"
        duration_sec = float(len(request.dataset.items) * 4.5 + 4.0)

        # Store in in-memory jobs cache
        quiz_jobs[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "stage": "finished",
            "progress_percent": 100,
            "topic": request.dataset.theme,
            "created_at": datetime.now(UTC).isoformat(),
            "video_path": str(out_path),
            "download_url": download_url,
            "challenge_summary": {
                "topic": request.dataset.theme,
                "total_questions": len(request.dataset.items),
                "duration_seconds": duration_sec,
            },
        }

        # Store in persistent history
        try:
            manager = get_batch_queue_manager()
            manager.record_history(
                BatchQueueItem(
                    item_id=job_id,
                    index=1,
                    topic=f"[Visual Quiz] {request.dataset.theme}",
                    status=BatchQueueItemStatus.COMPLETED,
                    video_path=str(out_path),
                    download_url=download_url,
                )
            )
        except Exception as err:
            logger.warning("Failed to record visual quiz to history: %s", err)

        return VisualQuizRenderResponse(
            video_path=str(out_path),
            download_url=download_url,
            duration_sec=duration_sec,
            status="completed",
        )
    except Exception as exc:
        logger.error("Failed to render visual quiz: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка рендеринга визуальной викторины: {exc}",
        ) from exc


# ==============================================================================
# Widescreen Gaming Quiz Endpoints (008-widescreen-gaming-quiz)
# ==============================================================================


class WidescreenQuizGenerateRequest(BaseModel):
    topic_prompt: str = Field(..., description="Prompt describing the 5 rounds topic or theme")
    rounds_count: int = Field(default=5, ge=1, le=10)
    questions_per_round: int = Field(default=10, ge=1, le=20)
    language: str = Field(default="ru", pattern=r"^(ru|en)$")
    auto_fetch_assets: bool = Field(default=True)


class WidescreenSearchAudioRequest(BaseModel):
    query: str
    max_duration_sec: float = Field(default=4.0, ge=0.5, le=10.0)


class WidescreenSearchAudioCandidate(BaseModel):
    source: str
    title: str
    preview_url: str
    duration_sec: float = 4.0


class WidescreenSearchAudioResponse(BaseModel):
    candidates: list[WidescreenSearchAudioCandidate] = Field(default_factory=list)


class WidescreenSearchImageRequest(BaseModel):
    query: str
    asset_mode: str = "screenshot"


class WidescreenSearchImageCandidate(BaseModel):
    thumbnail_url: str | None = None
    image_url: str | None = None
    title: str
    width: int | None = 1920
    height: int | None = 1080


class WidescreenSearchImageResponse(BaseModel):
    candidates: list[WidescreenSearchImageCandidate] = Field(default_factory=list)


class WidescreenQuizRenderRequest(BaseModel):
    dataset: WidescreenQuizDataset
    render_profile: RenderProfile = RenderProfile.GPU_FAST
    background_video: str | None = None
    background_music: str | None = None
    background_music_volume: float = 0.20
    voice: str = "ru-RU-SvetlanaNeural"
    voice_config: VoiceConfig | None = None


class WidescreenQuizRenderResponse(BaseModel):
    job_id: str
    video_path: str
    download_url: str
    total_frames: int
    duration_sec: float
    status: str = "completed"


@router.post("/widescreen/generate", response_model=WidescreenQuizDataset)
async def generate_widescreen_quiz(request: WidescreenQuizGenerateRequest) -> WidescreenQuizDataset:
    """Generate complete 5-round 16:9 gaming quiz show dataset."""
    orchestrator = QuizOrchestrator()
    try:
        return await orchestrator.script_service.generate_widescreen_quiz_dataset(
            topic_prompt=request.topic_prompt,
            language=request.language,
            num_rounds=request.rounds_count,
            questions_per_round=request.questions_per_round,
        )
    except Exception as exc:
        logger.error("Failed to generate widescreen quiz: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось сгенерировать 16:9 викторину: {exc}",
        ) from exc


@router.post("/widescreen/search-audio", response_model=WidescreenSearchAudioResponse)
async def search_widescreen_audio(request: WidescreenSearchAudioRequest) -> WidescreenSearchAudioResponse:
    """Search gaming weapon/item sound effect candidates."""
    orchestrator = QuizOrchestrator()
    candidates: list[WidescreenSearchAudioCandidate] = []

    # Check web sound search candidates
    try:
        import httpx
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            search_url = f"https://api.myinstants.com/api/v1/instants/?format=json&name={request.query}"
            resp = await client.get(search_url)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", [])[:5]:
                    if "sound" in item:
                        candidates.append(
                            WidescreenSearchAudioCandidate(
                                source="myinstants",
                                title=item.get("name", request.query),
                                preview_url=item["sound"],
                                duration_sec=request.max_duration_sec,
                            )
                        )
    except Exception as err:
        logger.debug("Failed web sound candidates query: %s", err)

    if not candidates:
        candidates.append(
            WidescreenSearchAudioCandidate(
                source="procedural",
                title=f"Procedural {request.query}",
                preview_url="",
                duration_sec=2.5,
            )
        )

    return WidescreenSearchAudioResponse(candidates=candidates)


@router.post("/widescreen/search-image", response_model=WidescreenSearchImageResponse)
async def search_widescreen_image(request: WidescreenSearchImageRequest) -> WidescreenSearchImageResponse:
    """Search candidate screenshot/game over/minimap/silhouette images."""
    orchestrator = QuizOrchestrator()
    formatted_query = orchestrator.image_service.format_gaming_query(request.query, request.asset_mode)
    results = await orchestrator.image_service._search_image_urls(formatted_query, max_results=8)
    candidates: list[WidescreenSearchImageCandidate] = []
    for item in results:
        img_url = item.get("image")
        if img_url:
            candidates.append(
                WidescreenSearchImageCandidate(
                    thumbnail_url=item.get("thumbnail"),
                    image_url=img_url,
                    title=item.get("title", request.query),
                    width=int(item.get("width", 1920) or 1920),
                    height=int(item.get("height", 1080) or 1080),
                )
            )
    return WidescreenSearchImageResponse(candidates=candidates)


@router.post("/widescreen/render", response_model=WidescreenQuizRenderResponse)
async def render_widescreen_quiz(request: WidescreenQuizRenderRequest) -> WidescreenQuizRenderResponse:
    """Render finalized 16:9 Widescreen Gaming Quiz into MP4 via Remotion."""
    orchestrator = QuizOrchestrator()
    job_id = f"wide_{uuid.uuid4().hex[:10]}"
    try:
        out_path = await orchestrator.render_widescreen_quiz(
            dataset=request.dataset,
            background_video=request.background_video,
            background_music=request.background_music,
            background_music_volume=request.background_music_volume,
            voice=request.voice,
            voice_config=request.voice_config,
            render_profile=request.render_profile,
        )
        download_url = f"/api/v1/quiz/jobs/{job_id}/download"
        total_questions = request.dataset.total_questions_count
        duration_sec = float(total_questions * 9.0 + 8.0 + 15.0 + len(request.dataset.rounds) * 4.0)

        # Store in in-memory jobs cache
        quiz_jobs[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "stage": "finished",
            "progress_percent": 100,
            "topic": request.dataset.title,
            "created_at": datetime.now(UTC).isoformat(),
            "video_path": str(out_path),
            "download_url": download_url,
            "challenge_summary": {
                "topic": request.dataset.title,
                "total_questions": total_questions,
                "duration_seconds": duration_sec,
            },
        }

        # Store in persistent history
        try:
            manager = get_batch_queue_manager()
            manager.record_history(
                BatchQueueItem(
                    item_id=job_id,
                    index=1,
                    topic=f"[16:9 Quiz] {request.dataset.title}",
                    status=BatchQueueItemStatus.COMPLETED,
                    video_path=str(out_path),
                    download_url=download_url,
                )
            )
        except Exception as err:
            logger.warning("Failed to record widescreen quiz to history: %s", err)

        return WidescreenQuizRenderResponse(
            job_id=job_id,
            video_path=str(out_path),
            download_url=download_url,
            total_frames=int(duration_sec * 60),
            duration_sec=duration_sec,
            status="completed",
        )
    except Exception as exc:
        logger.error("Failed to render widescreen quiz: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка рендеринга 16:9 викторины: {exc}",
        ) from exc


# ==============================================================================
# Voice Pipeline & RVC Voice Cloning Endpoints
# ==============================================================================


@voice_router.get("/models", response_model=RvcModelListResponse)
@router.get("/voice/models", response_model=RvcModelListResponse)
async def list_rvc_models() -> RvcModelListResponse:
    """Discover available local RVC voice models (*.pth) in assets/models/rvc/."""
    registry = RvcModelRegistry()
    models = registry.discover_models()
    return RvcModelListResponse(
        models=models,
        active_model_id=models[0].model_id if models else None,
        total_count=len(models),
    )


@voice_router.post("/preview", response_model=VoicePreviewResponse)
@router.post("/voice/preview", response_model=VoicePreviewResponse)
async def create_voice_preview(request: VoicePreviewRequest) -> VoicePreviewResponse:
    """Synthesize a short audio preview clip using the requested voice config."""
    preview_id = f"prev_{uuid.uuid4().hex[:12]}"
    preview_dir = Path("data/previews")
    preview_dir.mkdir(parents=True, exist_ok=True)
    out_audio = preview_dir / f"{preview_id}.wav"

    svc = VoiceService(config=request.config)
    try:
        result = await svc.synthesize(
            text=request.text, output_path=out_audio, config=request.config
        )
    except Exception as exc:
        logger.error("Failed to generate voice preview: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate voice preview: {exc}",
        ) from exc

    return VoicePreviewResponse(
        audio_url=f"/api/v1/voice/preview/audio/{preview_id}",
        duration_ms=result.duration_ms,
        voice_mode_used=result.voice_mode_used,
    )


@voice_router.get("/preview/audio/{preview_id}")
@router.get("/voice/preview/audio/{preview_id}")
async def get_preview_audio(preview_id: str) -> FileResponse:
    """Stream synthesized voice preview audio file."""
    preview_dir = Path("data/previews")
    candidate_wav = preview_dir / f"{preview_id}.wav"
    candidate_mp3 = preview_dir / f"{preview_id}.mp3"

    if candidate_wav.exists():
        target = candidate_wav
    elif candidate_mp3.exists():
        target = candidate_mp3
    else:
        target = None

    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview file not found")

    media_type = "audio/wav" if target.suffix.lower() == ".wav" else "audio/mpeg"
    return FileResponse(target, media_type=media_type)


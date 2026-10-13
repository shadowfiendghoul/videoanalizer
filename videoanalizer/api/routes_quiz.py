"""FastAPI REST routes for Quiz Shorts Generator background jobs and video download."""

import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

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
    SingleTopicSuggestRequest,
    TopicSuggestion,
)
from videoanalizer.quiz.orchestrator import QuizOrchestrator
from videoanalizer.utils.hardware import get_hardware_capabilities

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz Shorts Generator"])
hardware_router = APIRouter(prefix="/api/v1/hardware", tags=["Hardware Acceleration"])


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
        le=3.0,
        description=(
            "Sampling temperature for creative generation (0.2-3.0, default 0.95, clamped to 2.0)."
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
        le=3.0,
        description=(
            "Sampling temperature for creative generation (0.2-3.0, default 0.95, clamped to 2.0)."
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
        le=3.0,
        description=(
            "Sampling temperature for creative generation (0.2-3.0, default 0.95, clamped to 2.0)."
        ),
    )
    fact_check: bool | None = Field(
        default=None,
        description="Enable strict secondary fact-checking pass to correct inaccuracies and myths.",
    )
    background_video: str | None = Field(
        default=None, description="Optional custom background video filename or path, or 'random'."
    )
    voice: str | None = Field(default=None, description="Optional edge-tts voice override.")
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
        default="Ты гений, если ответишь на все вопросы!",
        description="Optional custom greeting/hook phrase spoken at start.",
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


class BackgroundInfo(BaseModel):
    """Available background video metadata."""

    id: str
    name: str
    filename: str


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
    """Search candidates for visual trivia question preview."""
    orchestrator = QuizOrchestrator()
    items = await orchestrator.image_service._search_image_urls(
        request.query, max_results=request.max_results
    )
    results: list[ImageSearchResultItem] = []
    for it in items:
        img_url = it.get("image") or it.get("thumbnail")
        if img_url:
            results.append(
                ImageSearchResultItem(
                    image=img_url,
                    thumbnail=it.get("thumbnail") or img_url,
                )
            )
    return ImageSearchResponse(images=results)


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


@router.get("/backgrounds", response_model=list[BackgroundInfo])
async def list_available_backgrounds() -> list[BackgroundInfo]:
    """List available background video loop files."""
    orchestrator = QuizOrchestrator()
    bg_dir = orchestrator.config.backgrounds_dir
    results: list[BackgroundInfo] = []
    if bg_dir.exists():
        for p in sorted(bg_dir.glob("*.mp4")):
            if p.name.startswith("."):
                continue
            lower = p.name.lower()
            if "minecraft" in lower:
                friendly_name = "Minecraft Parkour"
            elif "gta" in lower:
                friendly_name = "GTA 5 Mega Ramp"
            elif "subway" in lower:
                friendly_name = "Subway Surfers"
            elif "earth" in lower or "space" in lower:
                friendly_name = "Земля из космоса (Earth Night)"
            elif "default" in lower:
                friendly_name = "Стандартный фон (Default)"
            else:
                friendly_name = p.stem.replace("_", " ").title()

            results.append(
                BackgroundInfo(
                    id=p.name,
                    name=friendly_name,
                    filename=p.name,
                )
            )
    return results


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
    temperature: float | None = Field(default=None, ge=0.0, le=3.0)
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

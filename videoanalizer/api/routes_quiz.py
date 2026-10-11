"""FastAPI REST routes for Quiz Shorts Generator background jobs and video download."""

import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from videoanalizer.quiz.models import QuizChallenge
from videoanalizer.quiz.orchestrator import QuizOrchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz Shorts Generator"])


class QuizQuestionsPreviewRequest(BaseModel):
    """Payload to generate question preview before video rendering."""

    topic: str = Field(..., description="Topic prompt for the 9-question quiz challenge.")
    language: Literal["ru", "en"] = Field(default="ru", description="Narration and text language.")


class QuizGenerateRequest(BaseModel):
    """Payload to trigger asynchronous quiz video generation."""

    topic: str = Field(..., description="Topic prompt for the 9-question quiz challenge.")
    language: Literal["ru", "en"] = Field(default="ru", description="Narration and text language.")
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


class BannerUploadResponse(BaseModel):
    """Metadata response when a promo banner video is uploaded."""

    banner_path: str
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
        job["stage"] = "remotion_rendering"
        job["progress_percent"] = 40

        output_path = await orchestrator.generate(
            topic=request.topic,
            language=request.language,
            background_video=request.background_video,
            voice=request.voice,
            banner_video=request.banner_video,
            challenge=request.challenge,
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
        )
        return challenge
    except Exception as exc:
        logger.error("Failed to generate quiz preview questions: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка генерации вопросов нейросетью: {exc}",
        ) from exc


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

    dur_frames = orchestrator._probe_video_duration_frames(
        target_path, fps=orchestrator.config.fps
    )
    dur_sec = round(dur_frames / orchestrator.config.fps, 2)

    return BannerUploadResponse(
        banner_path=str(target_path),
        filename=file.filename,
        saved_filename=saved_name,
        duration_seconds=dur_sec,
    )


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

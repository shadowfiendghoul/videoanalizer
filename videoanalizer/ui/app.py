"""FastAPI application for VideoAnalyzer with modern Linear/Vercel UI and SSE streaming."""

import asyncio
import contextlib
import json
import logging
import shutil
import sys
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from videoanalizer.api.routes_quiz import hardware_router, voice_router
from videoanalizer.api.routes_quiz import router as quiz_router
from videoanalizer.api.routes_youtube import router as youtube_router
from videoanalizer.config import AppConfig, get_config
from videoanalizer.exceptions import VideoAnalyzerError
from videoanalizer.media.reframer import Reframer
from videoanalizer.media.renderer import Renderer
from videoanalizer.models.highlight import HighlightSegment
from videoanalizer.models.layout import CropBox, LayoutPreset
from videoanalizer.models.render_job import (
    BannerConfig,
    ClipRenderJob,
    SilenceConfig,
    SubtitleStyle,
)
from videoanalizer.models.source_video import SourceVideo
from videoanalizer.services.analyzer import AnalyzerService
from videoanalizer.services.headline import HeadlineService
from videoanalizer.services.ingestion import IngestionService
from videoanalizer.utils.ffmpeg_check import ensure_ffmpeg
from videoanalizer.utils.tempfiles import SessionTempDir

logger = logging.getLogger("videoanalizer.ui")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"


class ProgressManager:
    """Manages Server-Sent Events subscribers and stage progress broadcasting."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._last_event: dict = {
            "stage": "Готов к работе",
            "percent": 0,
            "details": "",
        }

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def broadcast(self, stage: str, percent: int, details: str = "") -> None:
        self._last_event = {"stage": stage, "percent": percent, "details": details}
        for q in list(self._subscribers):
            with contextlib.suppress(Exception):
                await q.put(self._last_event)

    def broadcast_from_thread(
        self,
        percent: int,
        stage: str,
        details: str = "",
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        if loop and loop.is_running():
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self.broadcast(stage, percent, details))
            )


class SessionState:
    """Shared in-memory state for the single-user local web dashboard."""

    def __init__(self) -> None:
        self.source_video: SourceVideo | None = None
        self.highlights: list[HighlightSegment] = []
        self.session_temp: SessionTempDir | None = None

    def get_temp_dir(self, config: AppConfig) -> Path:
        if self.session_temp is None:
            self.session_temp = SessionTempDir(base_dir=config.temp_dir)
            self.session_temp.__enter__()
        return self.session_temp.path

    def cleanup(self) -> None:
        if self.session_temp:
            with contextlib.suppress(Exception):
                self.session_temp.cleanup()
            self.session_temp = None


def _patch_win32_asyncio() -> None:
    """Silence harmless WinError 10054 on client disconnects in Windows asyncio."""
    if sys.platform != "win32":
        return

    import asyncio.proactor_events
    import socket

    def _call_connection_lost_patched(
        self: asyncio.proactor_events._ProactorBasePipeTransport,
        exc: BaseException | None,
    ) -> None:
        if self._called_connection_lost:
            return
        try:
            self._protocol.connection_lost(exc)
        finally:
            if hasattr(self._sock, "shutdown") and self._sock.fileno() != -1:
                with contextlib.suppress(OSError):
                    self._sock.shutdown(socket.SHUT_RDWR)
            with contextlib.suppress(OSError):
                self._sock.close()
            self._sock = None
            server = self._server
            if server is not None:
                server._detach(self)
                self._server = None
            self._called_connection_lost = True

    asyncio.proactor_events._ProactorBasePipeTransport._call_connection_lost = (
        _call_connection_lost_patched
    )


_patch_win32_asyncio()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Configure loop exception handler to silence premature socket drops on streaming."""
    with contextlib.suppress(Exception):
        loop = asyncio.get_running_loop()
        orig_handler = loop.get_exception_handler()

        def _custom_exception_handler(
            current_loop: asyncio.AbstractEventLoop,
            context: dict[str, Any],
        ) -> None:
            exc = context.get("exception")
            if isinstance(exc, (ConnectionResetError, BrokenPipeError, ConnectionAbortedError)):
                return
            if isinstance(exc, OSError) and getattr(exc, "winerror", None) in (10053, 10054, 10038):
                return
            if orig_handler:
                orig_handler(current_loop, context)
            else:
                current_loop.default_exception_handler(context)

        loop.set_exception_handler(_custom_exception_handler)

    yield


# Instantiate singletons
progress_mgr = ProgressManager()
state = SessionState()

app = FastAPI(
    title="VideoAnalyzer",
    description="AI-powered funny moments detector and TikTok/Shorts vertical video generator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount quiz generator API routes
app.include_router(quiz_router)
app.include_router(hardware_router)
app.include_router(voice_router)
app.include_router(youtube_router)


# --- Pydantic Request Models ---
class CropBoxInput(BaseModel):
    x: int = 0
    y: int = 0
    width: int = 400
    height: int = 400


class PreviewRequest(BaseModel):
    timestamp_sec: float = 0.0
    mode: str = "center_crop"
    webcam_position: str = "top"
    webcam_box: CropBoxInput = Field(default_factory=CropBoxInput)
    gameplay_box: CropBoxInput = Field(
        default_factory=lambda: CropBoxInput(width=1920, height=1080)
    )


class RenderSilenceInput(BaseModel):
    enabled: bool = True
    threshold_sec: float = 1.0


class RenderSubtitlesInput(BaseModel):
    enabled: bool = True
    font_size: int = 42
    active_color: str = "#FFFF00"
    inactive_color: str = "#FFFFFF"


class RenderBannerInput(BaseModel):
    enabled: bool = True
    text: str = ""
    position: str = "top"


class RenderShortRequest(BaseModel):
    highlight_id: str
    start_sec: float
    end_sec: float
    layout: PreviewRequest = Field(default_factory=PreviewRequest)
    silence: RenderSilenceInput = Field(default_factory=RenderSilenceInput)
    subtitles: RenderSubtitlesInput = Field(default_factory=RenderSubtitlesInput)
    banner: RenderBannerInput = Field(default_factory=RenderBannerInput)


class RegenHeadlineRequest(BaseModel):
    highlight_id: str


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def get_index() -> HTMLResponse:
    """Serve the single-page Linear/Vercel dashboard."""
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Шаблон index.html не найден")
    content = index_file.read_text(encoding="utf-8")
    return HTMLResponse(content=content)


@app.get("/quiz", response_class=HTMLResponse)
async def get_quiz_page() -> HTMLResponse:
    """Serve the TikTok Quiz Shorts Generator dashboard."""
    quiz_file = TEMPLATES_DIR / "quiz.html"
    if not quiz_file.exists():
        raise HTTPException(status_code=404, detail="Шаблон quiz.html не найден")
    content = quiz_file.read_text(encoding="utf-8")
    return HTMLResponse(content=content)


@app.get("/api/progress")
async def progress_stream() -> StreamingResponse:
    """Server-Sent Events (SSE) stream for real-time progress updates."""
    queue = progress_mgr.subscribe()

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Yield initial status immediately on connection
            yield f"data: {json.dumps(progress_mgr._last_event, ensure_ascii=False)}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except TimeoutError:
                    # Keep-alive heartbeat
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            progress_mgr.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/state")
async def get_state() -> dict:
    """Return current session state (video and highlights) if available."""
    if not state.source_video:
        return {"has_video": False, "highlights": []}
    return {
        "has_video": True,
        "video": {
            "id": state.source_video.id,
            "filename": state.source_video.filename,
            "duration_sec": state.source_video.duration_sec,
            "width": state.source_video.width,
            "height": state.source_video.height,
        },
        "highlights": [h.model_dump(mode="json") for h in state.highlights],
    }


@app.post("/api/analyze")
async def analyze_video(
    url: str | None = Form(None),
    file: UploadFile | None = File(None),  # noqa: B008
    clip_count: int = Form(3),
    min_duration: float = Form(30.0),
    max_duration: float = Form(60.0),
) -> dict:
    """Ingest source video and detect funny moments via Gemini AI."""
    cfg = get_config()
    temp_dir = state.get_temp_dir(cfg)

    if not url and not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Необходимо указать YouTube URL или загрузить видеофайл",
        )

    loop = asyncio.get_running_loop()
    ingestion = IngestionService()
    analyzer = AnalyzerService()

    try:
        # Stage 1: Ingestion
        await progress_mgr.broadcast(
            stage="Скачивание видео через yt-dlp...",
            percent=10,
            details="Загрузка и проверка медиафайла...",
        )

        if file and file.filename:
            safe_filename = "".join(
                c for c in file.filename if c.isalnum() or c in (".", "-", "_")
            )
            local_dest = temp_dir / safe_filename
            with open(local_dest, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            def run_local_ingest() -> SourceVideo:
                return ingestion.ingest(str(local_dest), temp_dir)

            source_video = await loop.run_in_executor(None, run_local_ingest)
        else:
            assert url is not None

            def run_yt_ingest() -> SourceVideo:
                return ingestion.ingest(url, temp_dir)

            source_video = await loop.run_in_executor(None, run_yt_ingest)

        state.source_video = source_video

        # Stage 2: Scene analysis with Gemini AI
        await progress_mgr.broadcast(
            stage="Анализ сцен через Gemini AI...",
            percent=35,
            details=f"Обработка аудиодиалогов ({source_video.duration_sec:.1f}с)...",
        )

        def run_analysis() -> list[HighlightSegment]:
            return analyzer.analyze(
                video=source_video,
                clip_count=clip_count,
                min_duration=min_duration,
                max_duration=max_duration,
                config=cfg,
            )

        highlights = await loop.run_in_executor(None, run_analysis)
        state.highlights = highlights

        # Analysis Complete
        await progress_mgr.broadcast(
            stage="Готово к скачиванию!",
            percent=100,
            details=f"Найдено моментов: {len(highlights)}",
        )

        return {
            "success": True,
            "video": {
                "id": source_video.id,
                "filename": source_video.filename,
                "duration_sec": source_video.duration_sec,
                "width": source_video.width,
                "height": source_video.height,
            },
            "highlights": [h.model_dump(mode="json") for h in highlights],
        }

    except VideoAnalyzerError as exc:
        logger.error(f"Analysis error: {exc}", exc_info=True)
        await progress_mgr.broadcast(stage="Ошибка анализа", percent=0, details=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        await progress_mgr.broadcast(stage="Непредвиденная ошибка", percent=0, details=str(exc))
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {exc}") from exc


@app.post("/api/preview-frame")
async def preview_frame(req: PreviewRequest) -> Response:
    """Generate a single reframed 9:16 JPEG preview frame at the specified timestamp."""
    if not state.source_video:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала загрузите и проанализируйте видео",
        )

    if req.mode == "split_screen":
        layout = LayoutPreset(
            mode="split_screen",
            webcam_box=CropBox(
                x=req.webcam_box.x,
                y=req.webcam_box.y,
                width=req.webcam_box.width,
                height=req.webcam_box.height,
            ),
            gameplay_box=CropBox(
                x=req.gameplay_box.x,
                y=req.gameplay_box.y,
                width=req.gameplay_box.width,
                height=req.gameplay_box.height,
            ),
            webcam_position=req.webcam_position,  # type: ignore[arg-type]
        )
    else:
        layout = LayoutPreset(mode="center_crop")

    reframer = Reframer()
    loop = asyncio.get_running_loop()

    try:
        def extract() -> bytes:
            assert state.source_video is not None
            return reframer.preview_frame(
                source_path=state.source_video.local_path,
                timestamp_sec=req.timestamp_sec,
                layout=layout,
            )

        jpeg_bytes = await loop.run_in_executor(None, extract)
        return Response(content=jpeg_bytes, media_type="image/jpeg")
    except Exception as exc:
        logger.error(f"Preview frame error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка генерации превью: {exc}") from exc


@app.post("/api/render")
async def render_short(req: RenderShortRequest) -> dict:
    """Render full vertical short via FFmpeg with real-time SSE progress updates."""
    if not state.source_video:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сначала загрузите и проанализируйте видео",
        )

    target_highlight = next((h for h in state.highlights if h.id == req.highlight_id), None)
    if not target_highlight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Указанный момент не найден",
        )

    cfg = get_config()
    temp_dir = state.get_temp_dir(cfg)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    # Clone and adjust boundaries
    suggested = req.banner.text if req.banner.enabled else target_highlight.suggested_headline
    adjusted_highlight = target_highlight.model_copy(
        update={
            "start_sec": req.start_sec,
            "end_sec": req.end_sec,
            "suggested_headline": suggested,
        }
    )

    if req.layout.mode == "split_screen":
        layout = LayoutPreset(
            mode="split_screen",
            webcam_box=CropBox(
                x=req.layout.webcam_box.x,
                y=req.layout.webcam_box.y,
                width=req.layout.webcam_box.width,
                height=req.layout.webcam_box.height,
            ),
            gameplay_box=CropBox(
                x=req.layout.gameplay_box.x,
                y=req.layout.gameplay_box.y,
                width=req.layout.gameplay_box.width,
                height=req.layout.gameplay_box.height,
            ),
            webcam_position=req.layout.webcam_position,  # type: ignore[arg-type]
        )
    else:
        layout = LayoutPreset(mode="center_crop")

    silence_cfg = SilenceConfig(
        enabled=req.silence.enabled,
        threshold_sec=req.silence.threshold_sec,
        noise_db=cfg.silence_db,
        padding_ms=cfg.padding_ms,
        crossfade_ms=cfg.crossfade_ms,
    )

    subtitles_cfg = SubtitleStyle(
        font_size=req.subtitles.font_size,
        active_color=req.subtitles.active_color,
        inactive_color=req.subtitles.inactive_color,
    )

    banner_cfg = BannerConfig(
        enabled=req.banner.enabled,
        text=req.banner.text,
        position=req.banner.position,  # type: ignore[arg-type]
    )

    job = ClipRenderJob(
        id=str(uuid.uuid4()),
        highlight=adjusted_highlight,
        layout=layout,
        silence=silence_cfg,
        subtitles=subtitles_cfg,
        subtitles_enabled=req.subtitles.enabled,
        banner=banner_cfg,
    )

    renderer = Renderer()
    loop = asyncio.get_running_loop()

    def on_progress(pct: int, stage_text: str) -> None:
        progress_mgr.broadcast_from_thread(pct, stage_text, loop=loop)

    try:
        await progress_mgr.broadcast(
            stage="Кадрирование 9:16 и обрезка пауз через FFmpeg...",
            percent=20,
            details="Запуск рендеринга...",
        )

        def do_render() -> Path:
            assert state.source_video is not None
            return renderer.render(
                job=job,
                source_video=state.source_video,
                session_dir=temp_dir,
                final_output_dir=cfg.output_dir,
                progress_callback=on_progress,
            )

        output_path = await loop.run_in_executor(None, do_render)

        await progress_mgr.broadcast(
            stage="Готово к скачиванию!",
            percent=100,
            details=f"Файл {output_path.name} успешно создан",
        )

        return {
            "success": True,
            "filename": output_path.name,
            "download_url": f"/api/download/{output_path.name}",
        }
    except Exception as exc:
        logger.error(f"Render short error: {exc}", exc_info=True)
        await progress_mgr.broadcast(stage="Ошибка рендеринга", percent=0, details=str(exc))
        raise HTTPException(status_code=500, detail=f"Ошибка рендеринга: {exc}") from exc


@app.get("/api/download/{filename}")
async def download_rendered_file(filename: str) -> FileResponse:
    """Download a rendered MP4 file from the output directory."""
    cfg = get_config()
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (".", "-", "_"))
    target = cfg.output_dir / safe_filename

    if not target.exists() or not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден в каталоге output",
        )

    return FileResponse(
        path=target,
        filename=safe_filename,
        media_type="video/mp4",
    )


@app.post("/api/regenerate-headline")
async def regenerate_headline(req: RegenHeadlineRequest) -> dict:
    """Regenerate viral hook headline via Gemini AI for a specific highlight."""
    target_highlight = next((h for h in state.highlights if h.id == req.highlight_id), None)
    if not target_highlight:
        raise HTTPException(status_code=404, detail="Момент не найден")

    cfg = get_config()
    service = HeadlineService()
    loop = asyncio.get_running_loop()

    try:
        def run_regen() -> str:
            assert target_highlight is not None
            return service.regenerate_headline(target_highlight, cfg)

        new_headline = await loop.run_in_executor(None, run_regen)
        target_highlight.suggested_headline = new_headline
        return {"success": True, "headline": new_headline}
    except Exception as exc:
        logger.error(f"Headline regeneration error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка генерации заголовка: {exc}") from exc


def launch(server_name: str = "0.0.0.0", server_port: int = 7860) -> None:  # noqa: S104
    """Launch the VideoAnalyzer web application using Uvicorn."""
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        with contextlib.suppress(Exception):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        with contextlib.suppress(Exception):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ensure_ffmpeg()
    print("\n=====================================================================")
    print(f"[OK] VideoAnalyzer Web Dashboard running at http://localhost:{server_port}")
    print("=====================================================================\n")
    uvicorn.run(app, host=server_name, port=server_port, log_level="info")


if __name__ == "__main__":
    launch()

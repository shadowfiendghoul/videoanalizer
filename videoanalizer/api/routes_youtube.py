"""FastAPI routes for YouTube OAuth 2.0 integration and video publication."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from videoanalizer.quiz.batch_queue import get_batch_queue_manager
from videoanalizer.services.youtube_service import get_youtube_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/youtube", tags=["YouTube Integration"])

# In-memory store for upload tasks
_upload_tasks: dict[str, dict[str, Any]] = {}


class YouTubeUploadRequest(BaseModel):
    """Payload to initiate YouTube video upload and publishing."""

    video_path: str | None = Field(default=None, description="Direct filesystem path to MP4")
    job_id: str | None = Field(default=None, description="Quiz job or history ID to resolve video")
    title: str = Field(..., min_length=1, max_length=100, description="Video title (up to 100 chars)")
    description: str = Field(default="", max_length=5000, description="Video description (up to 5000 chars)")
    tags: list[str] = Field(default_factory=list, description="List of search tags")
    privacy_status: Literal["public", "private", "unlisted"] = Field(
        default="public", description="Publication privacy status"
    )
    publish_at: str | None = Field(
        default=None,
        description="Optional scheduled publication datetime (RFC 3339 or ISO-8601 string)",
    )
    made_for_kids: bool = Field(default=False, description="Whether content is made for kids")
    channel_id: str | None = Field(default=None, description="Optional target channel ID or title override")


class SwitchAccountRequest(BaseModel):
    channel_id: str = Field(..., description="Target YouTube channel ID")


class DisconnectAccountRequest(BaseModel):
    channel_id: str | None = Field(default=None, description="Specific channel ID to disconnect")



def _resolve_video_path(video_path: str | None, job_id: str | None) -> Path:
    """Find video file from explicit path or job/history identifier."""
    if video_path:
        p = Path(video_path)
        if p.exists() and p.is_file():
            return p
        # Check relative to output directory
        for d in [Path("output"), Path("outputs")]:
            cand = d / p.name
            if cand.exists() and cand.is_file():
                return cand

    if job_id:
        clean_id = job_id.strip()

        # Check batch queue history
        manager = get_batch_queue_manager()
        for it in manager.get_history():
            if (
                it.job_id == clean_id
                or it.history_id == clean_id
                or Path(it.video_path).stem == clean_id
            ):
                cand = Path(it.video_path)
                if cand.exists() and cand.is_file():
                    return cand

        # Check candidate files in output dirs
        for d in [manager.config.output_dir, Path("output"), Path("outputs")]:
            for cand in [d / clean_id, d / f"{clean_id}.mp4"]:
                if cand.exists() and cand.is_file():
                    return cand

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Видеофайл не найден. Укажите корректный video_path или job_id.",
    )


@router.get("/status")
async def get_youtube_status() -> dict[str, Any]:
    """Get current YouTube OAuth setup and channel details."""
    service = get_youtube_service()
    return service.get_status()


@router.post("/client-secrets")
async def upload_client_secrets(
    file: UploadFile | None = File(None),
    raw_json: str | None = Form(None),
) -> dict[str, Any]:
    """Upload or provide client_secrets.json for Google OAuth."""
    service = get_youtube_service()

    if file and file.filename:
        content_bytes = await file.read()
        try:
            content_str = content_bytes.decode("utf-8")
            saved_path = service.save_client_secrets(content_str)
            return {"status": "ok", "message": f"Ключи сохранены в {saved_path.name}"}
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка парсинга client_secrets.json: {exc}",
            ) from exc

    if raw_json:
        try:
            saved_path = service.save_client_secrets(raw_json)
            return {"status": "ok", "message": f"Ключи сохранены в {saved_path.name}"}
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка парсинга client_secrets: {exc}",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Не передан файл или JSON-строка client_secrets.",
    )


@router.get("/auth-url")
async def get_authorization_url(
    redirect_uri: str = Query(default="http://localhost:7860/api/v1/youtube/oauth-callback"),
) -> dict[str, str]:
    """Generate OAuth 2.0 authorization URL for user to grant YouTube upload permissions."""
    service = get_youtube_service()
    try:
        url = service.get_auth_url(redirect_uri=redirect_uri)
        return {"auth_url": url}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/oauth-callback", response_class=HTMLResponse)
async def oauth_callback(code: str = Query(...)) -> HTMLResponse:
    """Handle OAuth redirect callback from Google, exchange authorization code, and notify UI."""
    service = get_youtube_service()
    redirect_uri = "http://localhost:7860/api/v1/youtube/oauth-callback"

    try:
        service.exchange_code(code=code, redirect_uri=redirect_uri)
        html_content = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
          <meta charset="UTF-8">
          <title>YouTube подключен</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #090a0f; color: #fff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .box { text-align: center; background: #13151f; padding: 40px; border-radius: 16px; border: 1px solid #232738; box-shadow: 0 10px 40px rgba(0,0,0,0.5); max-width: 420px; }
            .icon { font-size: 54px; margin-bottom: 16px; }
            h2 { margin: 0 0 10px; color: #10b981; font-size: 22px; }
            p { color: #9ca3af; font-size: 14px; line-height: 1.5; }
            button { margin-top: 20px; background: #2563eb; color: #fff; border: 0; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; }
          </style>
        </head>
        <body>
          <div class="box">
            <div class="icon">✅</div>
            <h2>YouTube успешно подключен!</h2>
            <p>Авторизация пройдена. Это окно можно закрыть, панель VideoAnalyzer сейчас обновится.</p>
            <button onclick="window.close(); if(window.opener) window.opener.location.reload();">Закрыть окно</button>
          </div>
          <script>
            if (window.opener) {
              window.opener.postMessage({ type: 'YOUTUBE_AUTH_SUCCESS' }, '*');
              setTimeout(() => window.close(), 1500);
            }
          </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content, status_code=200)
    except Exception as exc:
        logger.error("OAuth callback error: %s", exc)
        err_html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>Ошибка авторизации</title></head>
        <body style="background:#090a0f;color:#ef4444;font-family:sans-serif;padding:40px;text-align:center;">
          <h2>Ошибка авторизации YouTube</h2>
          <p style="color:#9ca3af;">{exc}</p>
          <button onclick="window.close()" style="padding:10px 20px;margin-top:20px;">Закрыть</button>
        </body>
        </html>
        """
        return HTMLResponse(content=err_html, status_code=400)


@router.post("/switch-account")
async def switch_youtube_account(payload: SwitchAccountRequest) -> dict[str, Any]:
    """Switch currently active YouTube channel."""
    service = get_youtube_service()
    success = service.set_active_account(payload.channel_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Канал '{payload.channel_id}' не найден в подключенных аккаунтах.",
        )
    return {"status": "ok", "active_channel_id": payload.channel_id}


@router.post("/disconnect")
async def disconnect_youtube(payload: DisconnectAccountRequest | None = None) -> dict[str, str]:
    """Disconnect YouTube account and remove stored tokens."""
    service = get_youtube_service()
    cid = payload.channel_id if payload else None
    service.disconnect(channel_id=cid)
    return {"status": "ok", "message": "YouTube аккаунт успешно отключен."}


def _run_youtube_upload_task(
    task_id: str,
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
    privacy_status: str,
    publish_at: str | None,
    made_for_kids: bool,
    channel_id: str | None = None,
) -> None:
    """Synchronous worker running in background thread for resumable chunk upload."""
    service = get_youtube_service()

    def progress_callback(pct: float, msg: str) -> None:
        _upload_tasks[task_id].update(
            {
                "status": "uploading",
                "progress_percent": pct,
                "stage": msg,
            }
        )

    try:
        _upload_tasks[task_id]["status"] = "uploading"
        _upload_tasks[task_id]["stage"] = "Подготовка видео к отправке..."

        result = service.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status=privacy_status,
            publish_at=publish_at,
            made_for_kids=made_for_kids,
            channel_id=channel_id,
            progress_callback=progress_callback,
        )

        _upload_tasks[task_id].update(
            {
                "status": "completed",
                "progress_percent": 100.0,
                "stage": "Опубликовано на YouTube",
                "result": result,
            }
        )
    except Exception as exc:
        logger.error("YouTube upload task %s failed: %s", task_id, exc, exc_info=True)
        _upload_tasks[task_id].update(
            {
                "status": "failed",
                "error": str(exc),
                "stage": f"Ошибка публикации: {exc}",
            }
        )


@router.post("/upload")
async def start_youtube_upload(
    payload: YouTubeUploadRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Start asynchronous YouTube video upload."""
    service = get_youtube_service()
    if not service.get_credentials(channel_id=payload.channel_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="YouTube аккаунт не подключен. Авторизуйтесь перед загрузкой.",
        )

    resolved_path = _resolve_video_path(payload.video_path, payload.job_id)

    task_id = f"yt_up_{uuid.uuid4().hex[:10]}"
    _upload_tasks[task_id] = {
        "task_id": task_id,
        "status": "queued",
        "progress_percent": 0.0,
        "stage": "В очереди на загрузку",
        "title": payload.title,
        "channel_id": payload.channel_id or service.get_active_account_id(),
        "video_path": str(resolved_path),
        "created_at": datetime.now(UTC).isoformat(),
        "result": None,
        "error": None,
    }

    background_tasks.add_task(
        _run_youtube_upload_task,
        task_id=task_id,
        video_path=resolved_path,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        privacy_status=payload.privacy_status,
        publish_at=payload.publish_at,
        made_for_kids=payload.made_for_kids,
        channel_id=payload.channel_id,
    )

    return {
        "status": "ok",
        "task_id": task_id,
        "message": "Загрузка на YouTube запущена в фоновом режиме.",
    }


@router.get("/upload/tasks/{task_id}")
async def get_upload_task_status(task_id: str) -> dict[str, Any]:
    """Poll progress status of an active or finished YouTube upload task."""
    task = _upload_tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Задача загрузки '{task_id}' не найдена.",
        )
    return task

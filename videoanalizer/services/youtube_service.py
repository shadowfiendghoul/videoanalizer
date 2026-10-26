"""YouTube API service for VideoAnalyzer.

Handles OAuth 2.0 authorization, channel information retrieval,
and resumable video uploads with scheduled publishing support.
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from videoanalizer.exceptions import YouTubeAuthError, YouTubeError

logger = logging.getLogger(__name__)

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeService:
    """Manages YouTube Data API v3 client, OAuth flow, and uploads."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir or Path("data/youtube")).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.client_secrets_file = self.data_dir / "client_secrets.json"
        self.token_file = self.data_dir / "token.json"

    def _resolve_secrets_file(self) -> Path | None:
        """Find client_secrets.json in data dir or fallback locations."""
        if self.client_secrets_file.exists() and self.client_secrets_file.is_file():
            return self.client_secrets_file
        # Check root or client_secret*.json patterns
        root_cand = Path("client_secrets.json")
        if root_cand.exists() and root_cand.is_file():
            return root_cand
        for p in Path(".").glob("client_secret*.json"):
            if p.is_file():
                return p
        return None

    def is_configured(self) -> bool:
        """Return True if OAuth client_secrets.json file is available."""
        return self._resolve_secrets_file() is not None

    def save_client_secrets(self, content: dict | str) -> Path:
        """Save OAuth 2.0 client secrets JSON to data directory."""
        if isinstance(content, str):
            parsed = json.loads(content)
        else:
            parsed = content

        if "web" not in parsed and "installed" not in parsed:
            raise YouTubeAuthError(
                "Неверный формат client_secrets.json. Файл должен содержать ключ 'installed' или 'web'."
            )

        with self.client_secrets_file.open("w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)

        return self.client_secrets_file

    def get_auth_url(self, redirect_uri: str) -> str:
        """Generate Google OAuth 2.0 authorization URL for YouTube permissions."""
        secrets_file = self._resolve_secrets_file()
        if not secrets_file:
            raise YouTubeAuthError(
                "Файл client_secrets.json не найден. Загрузите его в настройках YouTube."
            )

        flow = Flow.from_client_secrets_file(
            str(secrets_file),
            scopes=YOUTUBE_SCOPES,
            redirect_uri=redirect_uri,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def exchange_code(self, code: str, redirect_uri: str) -> Credentials:
        """Exchange authorization code from redirect callback for persistent tokens."""
        secrets_file = self._resolve_secrets_file()
        if not secrets_file:
            raise YouTubeAuthError("client_secrets.json отсутствует.")

        flow = Flow.from_client_secrets_file(
            str(secrets_file),
            scopes=YOUTUBE_SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        with self.token_file.open("w", encoding="utf-8") as f:
            f.write(creds.to_json())

        logger.info("YouTube OAuth credentials saved to %s", self.token_file)
        return creds

    def get_credentials(self) -> Credentials | None:
        """Load and refresh credentials if expired."""
        if not self.token_file.exists():
            return None

        try:
            with self.token_file.open("r", encoding="utf-8") as f:
                creds = Credentials.from_authorized_user_info(json.load(f), YOUTUBE_SCOPES)
        except Exception as exc:
            logger.warning("Failed to parse YouTube token file: %s", exc)
            return None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with self.token_file.open("w", encoding="utf-8") as f:
                    f.write(creds.to_json())
                logger.info("Successfully refreshed YouTube access token.")
            except Exception as exc:
                logger.warning("Failed to refresh YouTube access token: %s", exc)
                return None

        if creds and creds.valid:
            return creds
        return None

    def disconnect(self) -> bool:
        """Revoke local authentication state by deleting token file."""
        if self.token_file.exists():
            try:
                self.token_file.unlink()
                logger.info("Deleted YouTube token file %s", self.token_file)
                return True
            except OSError as exc:
                logger.warning("Failed to delete token file: %s", exc)
                return False
        return True

    def get_status(self) -> dict[str, Any]:
        """Check current authentication status and retrieve connected channel information."""
        configured = self.is_configured()
        creds = self.get_credentials()
        if not creds:
            return {
                "configured": configured,
                "authenticated": False,
                "channel": None,
                "error": None,
            }

        try:
            youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
            request = youtube.channels().list(
                part="snippet,statistics",
                mine=True,
            )
            response = request.execute()
            items = response.get("items", [])
            if not items:
                return {
                    "configured": configured,
                    "authenticated": True,
                    "channel": None,
                    "error": "На аккаунте Google не найден канал YouTube.",
                }

            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            thumbnails = snippet.get("thumbnails", {})
            avatar = (
                thumbnails.get("default", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or ""
            )

            channel_info = {
                "id": item.get("id"),
                "title": snippet.get("title", "Безымянный канал"),
                "custom_url": snippet.get("customUrl", ""),
                "description": snippet.get("description", ""),
                "avatar_url": avatar,
                "subscriber_count": stats.get("subscriberCount", "0"),
                "video_count": stats.get("videoCount", "0"),
            }

            return {
                "configured": configured,
                "authenticated": True,
                "channel": channel_info,
                "error": None,
            }
        except HttpError as exc:
            logger.error("YouTube API HTTP error in get_status: %s", exc)
            return {
                "configured": configured,
                "authenticated": False,
                "channel": None,
                "error": f"Ошибка YouTube API: {exc.reason if hasattr(exc, 'reason') else exc}",
            }
        except Exception as exc:
            logger.error("Error retrieving YouTube channel info: %s", exc)
            return {
                "configured": configured,
                "authenticated": False,
                "channel": None,
                "error": str(exc),
            }

    @staticmethod
    def format_publish_at(publish_at: str | datetime | None) -> str | None:
        """Validate and format scheduled publication time into RFC 3339 string (UTC)."""
        if not publish_at:
            return None

        dt: datetime
        if isinstance(publish_at, datetime):
            dt = publish_at
        else:
            clean_str = publish_at.strip()
            # Support HTML datetime-local format 'YYYY-MM-DDTHH:MM' or ISO formats
            if len(clean_str) == 16 and "T" in clean_str:
                dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M")
            else:
                try:
                    dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")

        if dt.tzinfo is None:
            # Assume local time if naive, convert to UTC
            local_tz = datetime.now().astimezone().tzinfo
            dt = dt.replace(tzinfo=local_tz).astimezone(UTC)
        else:
            dt = dt.astimezone(UTC)

        now_utc = datetime.now(UTC)
        if dt <= now_utc:
            raise YouTubeError(
                f"Время публикации {dt.isoformat()} должно быть в будущем (сейчас {now_utc.isoformat()})."
            )

        # RFC 3339 format required by YouTube (YYYY-MM-DDTHH:MM:SSZ)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def upload_video(
        self,
        video_path: Path | str,
        title: str,
        description: str = "",
        tags: list[str] | None = None,
        privacy_status: str = "public",
        publish_at: str | datetime | None = None,
        category_id: str = "24",
        made_for_kids: bool = False,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        """Upload video file to YouTube with resumable chunks and optional scheduling."""
        file_path = Path(video_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Файл видео не найден: {file_path}")

        creds = self.get_credentials()
        if not creds:
            raise YouTubeAuthError("Не авторизован в YouTube. Пройдите авторизацию через браузер.")

        scheduled_time_rfc3339 = self.format_publish_at(publish_at)

        # YouTube rule: if publishAt is specified, privacyStatus MUST be 'private'
        effective_privacy = "private" if scheduled_time_rfc3339 else (privacy_status or "public").lower()
        if effective_privacy not in {"public", "private", "unlisted"}:
            effective_privacy = "public"

        body: dict[str, Any] = {
            "snippet": {
                "title": title.strip()[:100],
                "description": description.strip()[:5000],
                "tags": [t.strip() for t in (tags or []) if t.strip()][:500],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": effective_privacy,
                "selfDeclaredMadeForKids": made_for_kids,
            },
        }

        if scheduled_time_rfc3339:
            body["status"]["publishAt"] = scheduled_time_rfc3339

        logger.info(
            "Uploading video to YouTube: '%s' (privacy: %s, publishAt: %s)",
            body["snippet"]["title"],
            effective_privacy,
            scheduled_time_rfc3339,
        )

        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

        media = MediaFileUpload(
            str(file_path),
            mimetype="video/mp4",
            chunksize=2 * 1024 * 1024,  # 2MB chunks for robust uploads
            resumable=True,
        )

        insert_request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        retry_count = 0
        max_retries = 5

        if progress_callback:
            progress_callback(1.0, "Старт загрузки на YouTube...")

        while response is None:
            try:
                status_chunk, response = insert_request.next_chunk()
                if status_chunk and progress_callback:
                    pct = round(status_chunk.progress() * 100.0, 1)
                    progress_callback(pct, f"Загрузка на YouTube: {pct}%")
                    logger.debug("Upload chunk progress: %s%%", pct)
            except HttpError as exc:
                if exc.resp.status in (500, 502, 503, 504) and retry_count < max_retries:
                    retry_count += 1
                    sleep_sec = 2**retry_count
                    logger.warning(
                        "Transient HTTP %s from YouTube, retrying in %ds (attempt %d/%d)",
                        exc.resp.status,
                        sleep_sec,
                        retry_count,
                        max_retries,
                    )
                    time.sleep(sleep_sec)
                else:
                    logger.error("Fatal YouTube upload HttpError: %s", exc)
                    raise YouTubeError(f"Ошибка загрузки на YouTube: {exc}") from exc
            except Exception as exc:
                logger.error("Fatal exception during YouTube upload chunk: %s", exc)
                raise YouTubeError(f"Ошибка передачи видео: {exc}") from exc

        video_id = response.get("id")
        if not video_id:
            raise YouTubeError(f"Видео загружено, но YouTube не вернул video_id: {response}")

        video_url = f"https://youtu.be/{video_id}"
        shorts_url = f"https://youtube.com/shorts/{video_id}"

        if progress_callback:
            progress_callback(100.0, "Видео успешно опубликовано!")

        logger.info("Video successfully uploaded to YouTube! ID: %s, URL: %s", video_id, video_url)

        return {
            "video_id": video_id,
            "url": video_url,
            "shorts_url": shorts_url,
            "title": body["snippet"]["title"],
            "privacy_status": effective_privacy,
            "publish_at": scheduled_time_rfc3339,
            "channel_id": response.get("snippet", {}).get("channelId"),
        }


# Global singleton instance
_youtube_service: YouTubeService | None = None


def get_youtube_service() -> YouTubeService:
    """Return YouTubeService singleton."""
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service

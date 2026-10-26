"""YouTube API service for VideoAnalyzer with multi-account support.

Handles OAuth 2.0 authorization, channel information retrieval,
multi-channel switching, and resumable video uploads with scheduled publishing.
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
    """Manages YouTube Data API v3 client, OAuth flows, and multi-channel uploads."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir or Path("data/youtube")).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_dir = self.data_dir / "accounts"
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
        self.client_secrets_file = self.data_dir / "client_secrets.json"
        self.token_file = self.data_dir / "token.json"
        self.active_account_file = self.data_dir / "active_account.json"
        self._states_file = self.data_dir / "oauth_states.json"
        self._oauth_verifiers: dict[str, str] = self._load_oauth_verifiers()
        self._migrate_legacy_token()

    def _load_oauth_verifiers(self) -> dict[str, str]:
        if self._states_file.exists():
            try:
                with self._states_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_oauth_verifier(self, state: str, verifier: str) -> None:
        self._oauth_verifiers[state] = verifier
        try:
            if len(self._oauth_verifiers) > 20:
                keys_to_remove = list(self._oauth_verifiers.keys())[:-20]
                for k in keys_to_remove:
                    self._oauth_verifiers.pop(k, None)
            with self._states_file.open("w", encoding="utf-8") as f:
                json.dump(self._oauth_verifiers, f)
        except Exception as exc:
            logger.warning("Could not persist oauth states: %s", exc)

    def _migrate_legacy_token(self) -> None:
        """Migrate single legacy token.json to multi-account structure if needed."""
        if self.token_file.exists() and not list(self.accounts_dir.glob("*.json")):
            try:
                with self.token_file.open("r", encoding="utf-8") as f:
                    token_data = json.load(f)
                creds = Credentials.from_authorized_user_info(token_data, YOUTUBE_SCOPES)
                channel_info = self._fetch_channel_info_for_credentials(creds)
                cid = channel_info.get("id") or "legacy_channel"
                self._save_account_data(cid, creds, channel_info)
                self.set_active_account(cid)
                logger.info("Migrated legacy token.json to account %s", cid)
            except Exception as exc:
                logger.debug("Legacy token migration skipped: %s", exc)

    def _resolve_secrets_file(self) -> Path | None:
        """Find client_secrets.json in data dir or fallback locations."""
        if self.client_secrets_file.exists() and self.client_secrets_file.is_file():
            return self.client_secrets_file
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
        auth_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent select_account",
        )
        if flow.code_verifier and state:
            self._save_oauth_verifier(state, flow.code_verifier)
        return auth_url

    def _fetch_channel_info_for_credentials(self, creds: Credentials) -> dict[str, Any]:
        """Query YouTube Data API for channel metadata of given credentials."""
        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
        request = youtube.channels().list(
            part="snippet,statistics",
            mine=True,
        )
        response = request.execute()
        items = response.get("items", [])
        if not items:
            return {
                "id": "unknown",
                "title": "Аккаунт без канала YouTube",
                "custom_url": "",
                "description": "",
                "avatar_url": "",
                "subscriber_count": "0",
                "video_count": "0",
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

        return {
            "id": item.get("id"),
            "title": snippet.get("title", "Безымянный канал"),
            "custom_url": snippet.get("customUrl", ""),
            "description": snippet.get("description", ""),
            "avatar_url": avatar,
            "subscriber_count": stats.get("subscriberCount", "0"),
            "video_count": stats.get("videoCount", "0"),
        }

    def _save_account_data(self, channel_id: str, creds: Credentials, channel_info: dict[str, Any]) -> None:
        """Save account token and channel metadata to accounts directory."""
        acc_file = self.accounts_dir / f"{channel_id}.json"
        data = {
            "channel_id": channel_id,
            "channel": channel_info,
            "credentials": json.loads(creds.to_json()),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        with acc_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def exchange_code(self, code: str, redirect_uri: str, state: str | None = None) -> dict[str, Any]:
        """Exchange authorization code, fetch channel info, and save to accounts store."""
        secrets_file = self._resolve_secrets_file()
        if not secrets_file:
            raise YouTubeAuthError("client_secrets.json отсутствует.")

        flow = Flow.from_client_secrets_file(
            str(secrets_file),
            scopes=YOUTUBE_SCOPES,
            redirect_uri=redirect_uri,
        )

        verifier = None
        if state:
            verifier = self._oauth_verifiers.get(state)
        if not verifier and self._oauth_verifiers:
            verifier = list(self._oauth_verifiers.values())[-1]

        if verifier:
            flow.code_verifier = verifier

        flow.fetch_token(code=code)
        if state:
            self._oauth_verifiers.pop(state, None)
            try:
                with self._states_file.open("w", encoding="utf-8") as f:
                    json.dump(self._oauth_verifiers, f)
            except Exception:
                pass

        creds = flow.credentials

        try:
            channel_info = self._fetch_channel_info_for_credentials(creds)
            cid = channel_info.get("id") or f"acc_{int(time.time())}"
        except Exception as exc:
            logger.warning("Could not probe channel info immediately: %s", exc)
            cid = f"acc_{int(time.time())}"
            channel_info = {
                "id": cid,
                "title": f"YouTube Channel ({cid[:8]})",
                "custom_url": "",
                "avatar_url": "",
                "subscriber_count": "0",
                "video_count": "0",
            }

        self._save_account_data(cid, creds, channel_info)
        self.set_active_account(cid)

        # Also write token_file for backward compatibility
        with self.token_file.open("w", encoding="utf-8") as f:
            f.write(creds.to_json())

        logger.info("Successfully connected YouTube account '%s' (ID: %s)", channel_info.get("title"), cid)
        return channel_info

    def list_accounts(self) -> list[dict[str, Any]]:
        """List all connected YouTube channels."""
        accounts: list[dict[str, Any]] = []
        for p in sorted(self.accounts_dir.glob("*.json")):
            try:
                with p.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                ch = data.get("channel") or {"id": p.stem, "title": p.stem}
                accounts.append(ch)
            except Exception as exc:
                logger.warning("Failed to parse account file %s: %s", p, exc)
        return accounts

    def get_active_account_id(self) -> str | None:
        """Return ID of currently selected YouTube channel."""
        if self.active_account_file.exists():
            try:
                with self.active_account_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    val = data.get("active_channel_id")
                    if val and (self.accounts_dir / f"{val}.json").exists():
                        return val
            except Exception:
                pass

        accs = sorted(self.accounts_dir.glob("*.json"))
        if accs:
            return accs[0].stem
        return None

    def set_active_account(self, channel_id: str) -> bool:
        """Switch active YouTube channel."""
        acc_file = self.accounts_dir / f"{channel_id}.json"
        if not acc_file.exists():
            found_id = None
            for p in self.accounts_dir.glob("*.json"):
                try:
                    with p.open("r", encoding="utf-8") as f:
                        d = json.load(f)
                    ch = d.get("channel", {})
                    if (
                        ch.get("title", "").lower() == channel_id.lower()
                        or ch.get("custom_url", "").lower().lstrip("@") == channel_id.lower().lstrip("@")
                    ):
                        found_id = p.stem
                        break
                except Exception:
                    pass
            if found_id:
                channel_id = found_id
            else:
                return False

        with self.active_account_file.open("w", encoding="utf-8") as f:
            json.dump({"active_channel_id": channel_id}, f)

        creds = self.get_credentials(channel_id=channel_id)
        if creds:
            with self.token_file.open("w", encoding="utf-8") as f:
                f.write(creds.to_json())

        logger.info("Active YouTube account switched to: %s", channel_id)
        return True

    def get_credentials(self, channel_id: str | None = None) -> Credentials | None:
        """Load and refresh credentials for specified channel (or active channel)."""
        target_id = channel_id or self.get_active_account_id()
        acc_file = (self.accounts_dir / f"{target_id}.json") if target_id else None

        token_payload = None
        if acc_file and acc_file.exists():
            try:
                with acc_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    token_payload = data.get("credentials")
            except Exception as exc:
                logger.warning("Failed to load account %s: %s", target_id, exc)

        if not token_payload and self.token_file.exists():
            try:
                with self.token_file.open("r", encoding="utf-8") as f:
                    token_payload = json.load(f)
            except Exception:
                pass

        if not token_payload:
            return None

        try:
            creds = Credentials.from_authorized_user_info(token_payload, YOUTUBE_SCOPES)
        except Exception as exc:
            logger.warning("Failed to parse YouTube credentials: %s", exc)
            return None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                if acc_file and acc_file.exists():
                    with acc_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    data["credentials"] = json.loads(creds.to_json())
                    data["updated_at"] = datetime.now(UTC).isoformat()
                    with acc_file.open("w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)

                with self.token_file.open("w", encoding="utf-8") as f:
                    f.write(creds.to_json())
                logger.info("Refreshed YouTube access token for channel %s", target_id)
            except Exception as exc:
                logger.warning("Failed to refresh YouTube token for channel %s: %s", target_id, exc)
                return None

        if creds and creds.valid:
            return creds
        return None

    def disconnect(self, channel_id: str | None = None) -> bool:
        """Disconnect specified channel or active channel if none specified."""
        target_id = channel_id or self.get_active_account_id()

        if target_id:
            acc_file = self.accounts_dir / f"{target_id}.json"
            if acc_file.exists():
                try:
                    acc_file.unlink()
                except OSError as exc:
                    logger.warning("Failed to remove account %s: %s", target_id, exc)

        remaining = self.list_accounts()
        if remaining:
            self.set_active_account(remaining[0]["id"])
        else:
            if self.active_account_file.exists():
                self.active_account_file.unlink(missing_ok=True)
            if self.token_file.exists():
                self.token_file.unlink(missing_ok=True)

        return True

    def get_status(self) -> dict[str, Any]:
        """Check authentication status, connected channels list, and active channel details."""
        configured = self.is_configured()
        accounts = self.list_accounts()
        active_id = self.get_active_account_id()

        creds = self.get_credentials(channel_id=active_id)
        if not creds:
            return {
                "configured": configured,
                "authenticated": False,
                "active_channel_id": None,
                "channel": None,
                "accounts": accounts,
                "error": None,
            }

        active_info = None
        for a in accounts:
            if a.get("id") == active_id:
                active_info = a
                break

        if not active_info:
            try:
                active_info = self._fetch_channel_info_for_credentials(creds)
            except Exception as exc:
                logger.warning("Could not refresh active channel info: %s", exc)
                active_info = {"id": active_id, "title": "YouTube канал"}

        return {
            "configured": configured,
            "authenticated": True,
            "active_channel_id": active_id,
            "channel": active_info,
            "accounts": accounts,
            "error": None,
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
            if len(clean_str) == 16 and "T" in clean_str:
                dt = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M")
            else:
                try:
                    dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.strptime(clean_str, "%Y-%m-%d %H:%M:%S")

        if dt.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo
            dt = dt.replace(tzinfo=local_tz).astimezone(UTC)
        else:
            dt = dt.astimezone(UTC)

        now_utc = datetime.now(UTC)
        if dt <= now_utc:
            raise YouTubeError(
                f"Время публикации {dt.isoformat()} должно быть в будущем (сейчас {now_utc.isoformat()})."
            )

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
        channel_id: str | None = None,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> dict[str, Any]:
        """Upload video file to YouTube with resumable chunks and optional channel selection."""
        file_path = Path(video_path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Файл видео не найден: {file_path}")

        creds = self.get_credentials(channel_id=channel_id)
        if not creds:
            raise YouTubeAuthError("Не авторизован в YouTube. Пройдите авторизацию через браузер.")

        scheduled_time_rfc3339 = self.format_publish_at(publish_at)
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
            "Uploading video to YouTube (channel: %s): '%s' (privacy: %s, publishAt: %s)",
            channel_id or "active",
            body["snippet"]["title"],
            effective_privacy,
            scheduled_time_rfc3339,
        )

        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

        media = MediaFileUpload(
            str(file_path),
            mimetype="video/mp4",
            chunksize=2 * 1024 * 1024,
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

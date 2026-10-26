"""Unit tests for YouTube OAuth service and video upload workflows."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from videoanalizer.exceptions import YouTubeAuthError, YouTubeError
from videoanalizer.services.youtube_service import YouTubeService
from videoanalizer.ui.app import app


@pytest.fixture
def temp_youtube_dir(tmp_path: Path) -> Path:
    yt_dir = tmp_path / "youtube"
    yt_dir.mkdir(parents=True, exist_ok=True)
    return yt_dir


@pytest.fixture
def yt_service(temp_youtube_dir: Path) -> YouTubeService:
    return YouTubeService(data_dir=temp_youtube_dir)


def test_format_publish_at_future_iso(yt_service: YouTubeService):
    future = datetime.now(UTC) + timedelta(days=2, hours=3)
    res = yt_service.format_publish_at(future)
    assert res is not None
    assert res.endswith("Z")
    assert "T" in res


def test_format_publish_at_datetime_local_string(yt_service: YouTubeService):
    future = datetime.now() + timedelta(days=1)
    future_str = future.strftime("%Y-%m-%dT%H:%M")
    res = yt_service.format_publish_at(future_str)
    assert res is not None
    assert res.endswith("Z")


def test_format_publish_at_past_raises_error(yt_service: YouTubeService):
    past = datetime.now(UTC) - timedelta(hours=1)
    with pytest.raises(YouTubeError, match="должно быть в будущем"):
        yt_service.format_publish_at(past)


def test_format_publish_at_none_returns_none(yt_service: YouTubeService):
    assert yt_service.format_publish_at(None) is None
    assert yt_service.format_publish_at("") is None


def test_save_client_secrets_valid(yt_service: YouTubeService):
    valid_secrets = {
        "installed": {
            "client_id": "test-client-id.apps.googleusercontent.com",
            "client_secret": "test-secret",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    saved_file = yt_service.save_client_secrets(valid_secrets)
    assert saved_file.exists()
    assert yt_service.is_configured() is True


def test_save_client_secrets_invalid_raises_error(yt_service: YouTubeService):
    invalid_secrets = {"foo": "bar"}
    with pytest.raises(YouTubeAuthError, match="Неверный формат"):
        yt_service.save_client_secrets(invalid_secrets)


def test_disconnect_removes_token(yt_service: YouTubeService):
    token_file = yt_service.token_file
    token_file.write_text("dummy token", encoding="utf-8")
    assert token_file.exists()
    assert yt_service.disconnect() is True
    assert not token_file.exists()


def test_upload_missing_file_raises_not_found(yt_service: YouTubeService):
    with pytest.raises(FileNotFoundError):
        yt_service.upload_video(video_path="non_existent_file.mp4", title="Test")


def test_upload_without_creds_raises_auth_error(yt_service: YouTubeService, tmp_path: Path):
    test_video = tmp_path / "sample.mp4"
    test_video.write_bytes(b"dummy mp4 video bytes")

    with pytest.raises(YouTubeAuthError, match="Не авторизован"):
        yt_service.upload_video(video_path=test_video, title="Test")


@patch("videoanalizer.services.youtube_service.build")
def test_upload_video_with_scheduled_publish(mock_build, yt_service: YouTubeService, tmp_path: Path):
    test_video = tmp_path / "sample.mp4"
    test_video.write_bytes(b"dummy mp4 video bytes")

    future = (datetime.now(UTC) + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_creds = MagicMock()
    mock_creds.valid = True
    yt_service.get_credentials = MagicMock(return_value=mock_creds)

    mock_insert = MagicMock()
    # Simulate chunk upload: first chunk 50%, second chunk 100% and finish
    chunk_status = MagicMock()
    chunk_status.progress.return_value = 0.5
    mock_insert.next_chunk.side_effect = [
        (chunk_status, None),
        (MagicMock(), {"id": "test_video_123", "snippet": {"channelId": "ch_123"}}),
    ]

    mock_videos = MagicMock()
    mock_videos.insert.return_value = mock_insert
    mock_youtube = MagicMock()
    mock_youtube.videos.return_value = mock_videos
    mock_build.return_value = mock_youtube

    progress_calls = []

    def on_progress(pct, msg):
        progress_calls.append((pct, msg))

    res = yt_service.upload_video(
        video_path=test_video,
        title="My Epic Quiz #shorts",
        description="Check this out!",
        tags=["quiz", "shorts"],
        privacy_status="public",  # Must be forced to 'private' when publish_at is set!
        publish_at=future,
        progress_callback=on_progress,
    )

    assert res["video_id"] == "test_video_123"
    assert res["url"] == "https://youtu.be/test_video_123"
    assert res["shorts_url"] == "https://youtube.com/shorts/test_video_123"
    assert res["privacy_status"] == "private"
    assert res["publish_at"] == future

    # Check that insert was called with status.privacyStatus == "private"
    _, kwargs = mock_videos.insert.call_args
    body = kwargs["body"]
    assert body["status"]["privacyStatus"] == "private"
    assert body["status"]["publishAt"] == future
    assert body["snippet"]["title"] == "My Epic Quiz #shorts"


def test_api_youtube_status_endpoint():
    client = TestClient(app)
    resp = client.get("/api/v1/youtube/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "configured" in data
    assert "authenticated" in data

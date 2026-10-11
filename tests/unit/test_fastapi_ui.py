"""Unit tests for the FastAPI web UI and API endpoints."""

import pytest
from fastapi.testclient import TestClient

from videoanalizer.ui.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_index_page(client: TestClient) -> None:
    """Verify that root URL serves index.html with 200 OK and correct branding."""
    response = client.get("/")
    assert response.status_code == 200
    assert "VideoAnalyzer" in response.text
    assert "text/html" in response.headers["content-type"]
    assert "Gemini 3.5 Flash" in response.text


def test_preview_frame_without_video(client: TestClient) -> None:
    """Verify preview-frame returns 400 when no video has been ingested yet."""
    payload = {
        "timestamp_sec": 10.0,
        "mode": "center_crop",
        "webcam_position": "top",
    }
    response = client.post("/api/preview-frame", json=payload)
    assert response.status_code == 400
    assert "Сначала загрузите и проанализируйте видео" in response.json()["detail"]


def test_render_without_video(client: TestClient) -> None:
    """Verify render returns 400 when no video has been ingested yet."""
    payload = {
        "highlight_id": "test-id",
        "start_sec": 10.0,
        "end_sec": 20.0,
        "layout": {"mode": "center_crop", "webcam_position": "top"},
        "silence": {"enabled": True, "threshold_sec": 1.0},
        "subtitles": {
            "enabled": True,
            "font_size": 42,
            "active_color": "#FFFF00",
            "inactive_color": "#FFFFFF",
        },
        "banner": {"enabled": True, "text": "Test Hook", "position": "top"},
    }
    response = client.post("/api/render", json=payload)
    assert response.status_code == 400
    assert "Сначала загрузите и проанализируйте видео" in response.json()["detail"]


def test_download_nonexistent_file(client: TestClient) -> None:
    """Verify 404 for missing download files."""
    response = client.get("/api/download/nonexistent_file_123.mp4")
    assert response.status_code == 404


def test_get_state_initial(client: TestClient) -> None:
    """Verify /api/state returns has_video=False initially."""
    response = client.get("/api/state")
    assert response.status_code == 200
    assert response.json()["has_video"] is False
    assert response.json()["highlights"] == []

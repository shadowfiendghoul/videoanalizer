"""Tests for FastAPI quiz routes."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from videoanalizer.api import app
from videoanalizer.api.routes_quiz import quiz_jobs

client = TestClient(app)


def test_generate_quiz_endpoint() -> None:
    """POST /api/v1/quiz/generate should accept payload and return 202."""
    with patch("videoanalizer.api.routes_quiz._run_quiz_job", new_callable=AsyncMock):
        payload = {
            "topic": "Мировая география",
            "language": "ru",
            "background_video": None,
            "voice": "ru-RU-DmitryNeural",
        }
        res = client.post("/api/v1/quiz/generate", json=payload)
        assert res.status_code == 202
        data = res.json()
        assert "job_id" in data
        assert data["job_id"].startswith("qz_")
        assert data["status"] == "pending"
        assert data["status_url"].endswith(data["job_id"])


def test_get_job_status_not_found() -> None:
    """GET /api/v1/quiz/jobs/{unknown} should return 404."""
    res = client.get("/api/v1/quiz/jobs/unknown_job_999")
    assert res.status_code == 404


def test_get_job_status_and_download(tmp_path: Path) -> None:
    """GET /api/v1/quiz/jobs/{id} and download when completed."""
    test_video = tmp_path / "test_out.mp4"
    test_video.write_bytes(b"dummy mp4 file content")

    job_id = "qz_mock123"
    quiz_jobs[job_id] = {
        "job_id": job_id,
        "status": "completed",
        "stage": "finished",
        "progress_percent": 100,
        "topic": "Geography",
        "created_at": "2026-10-10T21:00:00Z",
        "video_path": str(test_video),
        "download_url": f"/api/v1/quiz/jobs/{job_id}/download",
        "error_message": None,
        "challenge_summary": {
            "topic": "Geography",
            "total_questions": 9,
            "duration_seconds": 60.0,
        },
    }

    # Query status
    res = client.get(f"/api/v1/quiz/jobs/{job_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["progress_percent"] == 100
    assert data["download_url"] == f"/api/v1/quiz/jobs/{job_id}/download"

    # Download
    dl_res = client.get(f"/api/v1/quiz/jobs/{job_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "video/mp4"
    assert dl_res.content == b"dummy mp4 file content"


def test_list_backgrounds_endpoint() -> None:
    """GET /api/v1/quiz/backgrounds should return list of available background videos."""
    res = client.get("/api/v1/quiz/backgrounds")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if data:
        first = data[0]
        assert "id" in first
        assert "name" in first
        assert "filename" in first


def test_upload_banner_endpoint(tmp_path: Path) -> None:
    """POST /api/v1/quiz/upload-banner should save video and return metadata."""
    dummy_video_content = b"\x00\x00\x00 ftypisom\x00\x00\x02\x00isomiso2mp41"
    files = {"file": ("my_promo.mp4", dummy_video_content, "video/mp4")}

    res = client.post("/api/v1/quiz/upload-banner", files=files)
    assert res.status_code == 200
    data = res.json()
    assert "saved_filename" in data
    assert data["saved_filename"].startswith("banner_")
    assert data["saved_filename"].endswith(".mp4")
    assert data["filename"] == "my_promo.mp4"
    assert "duration_seconds" in data
    assert Path(data["banner_path"]).exists()

    # Cleanup created banner file
    Path(data["banner_path"]).unlink(missing_ok=True)


def test_upload_banner_invalid_extension() -> None:
    """POST /api/v1/quiz/upload-banner should reject non-video files with 400."""
    files = {"file": ("bad_file.txt", b"plain text", "text/plain")}
    res = client.post("/api/v1/quiz/upload-banner", files=files)
    assert res.status_code == 400
    assert "Unsupported video format" in res.json()["detail"]


def test_generate_quiz_with_banner() -> None:
    """POST /api/v1/quiz/generate should accept banner_video parameter."""
    with patch("videoanalizer.api.routes_quiz._run_quiz_job", new_callable=AsyncMock) as mock_job:
        payload = {
            "topic": "Кино и сериалы",
            "language": "ru",
            "background_video": "minecraft_parkour_1.mp4",
            "voice": "ru-RU-SvetlanaNeural",
            "banner_video": "banner_abc123_promo.mp4",
        }
        res = client.post("/api/v1/quiz/generate", json=payload)
        assert res.status_code == 202
        data = res.json()
        assert data["job_id"].startswith("qz_")
        mock_job.assert_called_once()
        req_arg = mock_job.call_args[0][1]
        assert req_arg.banner_video == "banner_abc123_promo.mp4"


def test_preview_questions_endpoint() -> None:
    """POST /api/v1/quiz/preview-questions should return 9 questions structure."""
    from tests.unit.quiz.test_orchestrator import make_sample_challenge

    sample = make_sample_challenge()
    with patch(
        "videoanalizer.quiz.script_service.ScriptService.generate_quiz",
        new_callable=AsyncMock,
        return_value=sample,
    ):
        payload = {"topic": "World Trivia", "language": "en"}
        res = client.post("/api/v1/quiz/preview-questions", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["topic"] == "World Trivia"
        assert len(data["tiers"]) == 3
        assert data["total_questions"] == 9


def test_generate_quiz_with_approved_challenge() -> None:
    """POST /api/v1/quiz/generate should accept pre-approved challenge structure."""
    from tests.unit.quiz.test_orchestrator import make_sample_challenge

    sample = make_sample_challenge()
    with patch("videoanalizer.api.routes_quiz._run_quiz_job", new_callable=AsyncMock) as mock_job:
        payload = {
            "topic": "World Trivia",
            "language": "en",
            "challenge": sample.model_dump(),
        }
        res = client.post("/api/v1/quiz/generate", json=payload)
        assert res.status_code == 202
        mock_job.assert_called_once()
        req_arg = mock_job.call_args[0][1]
        assert req_arg.challenge is not None
        assert req_arg.challenge.topic == "World Trivia"
        assert len(req_arg.challenge.all_questions()) == 9


def test_generate_quiz_with_retention_flags() -> None:
    """POST /api/v1/quiz/generate should accept viral retention configuration flags."""
    with patch("videoanalizer.api.routes_quiz._run_quiz_job", new_callable=AsyncMock) as mock_job:
        payload = {
            "topic": "Космос",
            "language": "ru",
            "retention_enabled": True,
            "rank_bar_enabled": True,
            "stress_timer_enabled": True,
            "streak_fire_enabled": True,
            "comment_trap_enabled": True,
        }
        res = client.post("/api/v1/quiz/generate", json=payload)
        assert res.status_code == 202
        mock_job.assert_called_once()
        req_arg = mock_job.call_args[0][1]
        assert req_arg.retention_enabled is True
        assert req_arg.rank_bar_enabled is True
        assert req_arg.stress_timer_enabled is True
        assert req_arg.streak_fire_enabled is True
        assert req_arg.comment_trap_enabled is True


def test_search_image_endpoint() -> None:
    """POST /api/v1/quiz/search-image should return candidate images."""
    mock_results = [
        {"image": "https://example.com/img1.jpg", "thumbnail": "https://example.com/thumb1.jpg"},
        {"image": "https://example.com/img2.jpg", "thumbnail": "https://example.com/thumb2.jpg"},
    ]
    with patch(
        "videoanalizer.quiz.image_service.ImageService._search_image_urls",
        new_callable=AsyncMock,
        return_value=mock_results,
    ):
        payload = {"query": "Флаг Бразилии", "max_results": 2}
        res = client.post("/api/v1/quiz/search-image", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert "images" in data
        assert len(data["images"]) == 2
        assert data["images"][0]["image"] == "https://example.com/img1.jpg"
        assert data["images"][0]["thumbnail"] == "https://example.com/thumb1.jpg"

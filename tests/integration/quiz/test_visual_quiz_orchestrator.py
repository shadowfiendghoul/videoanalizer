"""Integration tests for Visual Image Quiz pipeline coordination and Remotion rendering."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from videoanalizer.api import app
from videoanalizer.quiz.models import (
    VisualDifficulty,
    VisualQuizDataset,
    VisualQuizInterstitial,
    VisualQuizInterstitialType,
    VisualQuizItem,
    VisualQuizTimingSlot,
)
from videoanalizer.quiz.orchestrator import QuizOrchestrator


@pytest.fixture
def sample_visual_quiz_dataset() -> VisualQuizDataset:
    items = []
    difficulties = (
        [VisualDifficulty.EASY] * 3
        + [VisualDifficulty.MEDIUM] * 3
        + [VisualDifficulty.HARD] * 3
        + [VisualDifficulty.MASTER]
    )
    for i in range(1, 11):
        diff = difficulties[i - 1]
        items.append(
            VisualQuizItem(
                id=i,
                difficulty=diff,
                answer_text=f"Item {i}",
                image_query=f"item {i} query",
                image_url=f"http://example.com/img{i}.png",
                image_path=None,
                is_approved=True,
                prompt_tts="Что это?" if i == 1 else f"Номер {i}, что это?",
                answer_tts=f"Это Item {i}" if i < 10 else "Пиши свой ответ в комментариях!",
            )
        )

    interstitials = [
        VisualQuizInterstitial(
            after_question=3,
            type=VisualQuizInterstitialType.COMMENT_BAIT,
            tts_text="Оставь смайлик в комментариях!",
            duration_sec=2.0,
        ),
        VisualQuizInterstitial(
            after_question=6,
            type=VisualQuizInterstitialType.SHARE_BAIT,
            tts_text="Отправь видео другу!",
            duration_sec=2.0,
        ),
    ]

    return VisualQuizDataset(
        mode="visual_image_quiz",
        theme="Тестовая тема суперкаров",
        hook_tts="Угадай все 10 машин в этом тесте!",
        rapid_flip_duration_ms=120,
        timer_duration_sec=2.0,
        items=items,
        interstitials=interstitials,
    )


@pytest.mark.asyncio
async def test_visual_quiz_orchestrator_render_flow(sample_visual_quiz_dataset, tmp_path):
    """Verify that QuizOrchestrator renders VisualImageQuiz with composition_id='VisualImageQuiz'."""
    orchestrator = QuizOrchestrator()
    dummy_wav = tmp_path / "dummy_master.wav"
    dummy_wav.write_bytes(b"RIFF" + b"\x00" * 40)

    timing_slots = [
        VisualQuizTimingSlot(
            question_id=i,
            start_frame=i * 200,
            prompt_audio_start_frame=i * 200,
            timer_start_frame=i * 200 + 10,
            timer_duration_frames=120,
            answer_audio_start_frame=i * 200 + 130,
            reveal_frame=i * 200 + 130,
            end_frame=(i + 1) * 200,
        )
        for i in range(1, 11)
    ]

    mock_audio_result = (
        dummy_wav,
        timing_slots,
        [{"word": "тест", "start_frame": 0, "end_frame": 10}],
        2400,
        210,
        None,
    )

    output_video = tmp_path / "output_visual.mp4"

    async def fake_render_remotion(*args, **kwargs):
        assert kwargs.get("composition_id") == "VisualImageQuiz"
        # Simulate creating the video file
        output_video.write_bytes(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom")

    with (
        patch.object(
            orchestrator.audio_service,
            "generate_visual_quiz_audio",
            new=AsyncMock(return_value=mock_audio_result),
        ),
        patch.object(orchestrator, "_render_remotion", side_effect=fake_render_remotion),
        patch("videoanalizer.media.uniquifier.strip_video_metadata", return_value=None),
        patch.object(orchestrator.image_service, "search_and_download", new=AsyncMock(return_value=None)),
    ):
        result_path = await orchestrator.render_visual_quiz(
            dataset=sample_visual_quiz_dataset,
            output_path=output_video,
        )

        assert result_path == output_video
        assert output_video.exists()


def test_visual_quiz_api_endpoints(sample_visual_quiz_dataset):
    """Test REST API endpoints /api/v1/quiz/visual/generate and /render."""
    client = TestClient(app)

    # 1. Test /visual/generate endpoint
    with patch(
        "videoanalizer.quiz.script_service.ScriptService.generate_visual_quiz_dataset",
        new=AsyncMock(return_value=sample_visual_quiz_dataset),
    ):
        resp = client.post(
            "/api/v1/quiz/visual/generate",
            json={"theme": "Суперкары мира", "auto_search_images": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "visual_image_quiz"
        assert len(data["items"]) == 10
        assert data["theme"] == "Тестовая тема суперкаров"

    # 2. Test /visual/render endpoint
    with patch(
        "videoanalizer.quiz.orchestrator.QuizOrchestrator.render_visual_quiz",
        new=AsyncMock(return_value=Path("output/test_video.mp4")),
    ):
        render_resp = client.post(
            "/api/v1/quiz/visual/render",
            json={"dataset": sample_visual_quiz_dataset.model_dump()},
        )
        assert render_resp.status_code == 200
        render_data = render_resp.json()
        assert render_data["status"] == "completed"
        assert "download_url" in render_data
        assert Path(render_data["video_path"]) == Path("output/test_video.mp4")

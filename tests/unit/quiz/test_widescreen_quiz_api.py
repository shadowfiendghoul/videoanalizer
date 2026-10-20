"""Unit tests for Widescreen Gaming Quiz REST API routes."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from videoanalizer.api.routes_quiz import router
from videoanalizer.quiz.models import (
    AssetDisplayMode,
    WidescreenIntroConfig,
    WidescreenOutroConfig,
    WidescreenQuizDataset,
    WidescreenQuizItem,
    WidescreenQuizRound,
)

app = FastAPI()
app.include_router(router)


@pytest.fixture
def sample_dataset() -> WidescreenQuizDataset:
    return WidescreenQuizDataset(
        mode="widescreen_gaming_quiz",
        title="Gaming API Test",
        language="ru",
        intro=WidescreenIntroConfig(
            hook_tts="50 вопросов. Поехали!",
            duration_sec=8.0,
            challenge_title="GAMING TEST",
        ),
        outro=WidescreenOutroConfig(
            duration_sec=15.0,
            outro_tts="Конец игры!",
            call_to_action="ПОДПИШИСЬ!",
            score_tiers=[],
        ),
        rounds=[
            WidescreenQuizRound(
                round_number=1,
                round_title="РАУНД 1",
                asset_mode=AssetDisplayMode.SCREENSHOT,
                pass_rate_statistic="90% PASS",
                badge_theme_color="#58A6FF",
                splash_duration_sec=4.0,
                questions=[
                    WidescreenQuizItem(
                        item_index=1,
                        global_question_number=1,
                        prompt_text="Угадайте игру",
                        answer_text="MINECRAFT",
                        asset_search_query="Minecraft screenshot",
                    )
                ],
            )
        ],
    )


@pytest.mark.asyncio
async def test_api_widescreen_generate(sample_dataset: WidescreenQuizDataset):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "videoanalizer.quiz.script_service.ScriptService.generate_widescreen_quiz_dataset",
            new=AsyncMock(return_value=sample_dataset),
        ):
            resp = await client.post(
                "/api/v1/quiz/widescreen/generate",
                json={
                    "topic_prompt": "Культовые видеоигры",
                    "rounds_count": 1,
                    "questions_per_round": 1,
                    "language": "ru",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "Gaming API Test"
            assert len(data["rounds"]) == 1


@pytest.mark.asyncio
async def test_api_widescreen_search_audio():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/quiz/widescreen/search-audio",
            json={"query": "cs awp shot", "max_duration_sec": 4.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "candidates" in data
        assert len(data["candidates"]) >= 1


@pytest.mark.asyncio
async def test_api_widescreen_search_image():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "videoanalizer.quiz.image_service.ImageService._search_image_urls",
            new=AsyncMock(return_value=[{"image": "http://example.com/skyrim.png", "title": "Skyrim"}]),
        ):
            resp = await client.post(
                "/api/v1/quiz/widescreen/search-image",
                json={"query": "Skyrim", "asset_mode": "screenshot"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["candidates"]) == 1
            assert data["candidates"][0]["image_url"] == "http://example.com/skyrim.png"


@pytest.mark.asyncio
async def test_api_widescreen_render(tmp_path: Path, sample_dataset: WidescreenQuizDataset):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        dummy_video = tmp_path / "rendered_wide.mp4"
        dummy_video.write_bytes(b"dummy_mp4_bytes")

        with patch(
            "videoanalizer.quiz.orchestrator.QuizOrchestrator.render_widescreen_quiz",
            new=AsyncMock(return_value=dummy_video),
        ):
            resp = await client.post(
                "/api/v1/quiz/widescreen/render",
                json={
                    "dataset": sample_dataset.model_dump(),
                    "render_profile": "gpu_fast",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "completed"
            assert "wide_" in data["job_id"]
            assert data["video_path"] == str(dummy_video)

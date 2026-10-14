"""Unit tests for single and batch AI topic ideation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from videoanalizer.quiz.models import BatchTopicList, TopicSuggestion
from videoanalizer.quiz.script_service import ScriptService


@pytest.fixture
def mock_script_service():
    service = ScriptService()
    # Use 0.0s interval for rate limiter in unit tests
    from videoanalizer.quiz.rate_limiter import PacedLimiter

    with patch(
        "videoanalizer.quiz.script_service.get_gemini_rate_limiter", return_value=PacedLimiter(0.0)
    ):
        yield service


@pytest.mark.asyncio
async def test_suggest_single_topic_success(mock_script_service):
    fake_payload = {
        "topic": "Анатомические парадоксы тела",
        "category": "Биология",
        "curiosity_hook": (
            "Почему мозг чувствует боль других органов, но сам не имеет болевых рецепторов?"
        ),
    }

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_payload)

    with patch.object(
        mock_script_service._client.aio.models,
        "generate_content",
        new=AsyncMock(return_value=mock_resp),
    ):
        suggestion = await mock_script_service.suggest_topic(
            category_hint="Биология", language="ru"
        )

        assert isinstance(suggestion, TopicSuggestion)
        assert suggestion.topic == "Анатомические парадоксы тела"
        assert suggestion.category == "Биология"
        assert "болевых рецепторов" in suggestion.curiosity_hook


@pytest.mark.asyncio
async def test_suggest_single_topic_random_angle(mock_script_service):
    fake_payload = {
        "topic": "Парадоксы видеоигр",
        "category": "Видеоигры",
        "curiosity_hook": "Узнаешь игру по реплике NPC?",
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_payload)

    with (
        patch.object(
            mock_script_service._client.aio.models,
            "generate_content",
            new=AsyncMock(return_value=mock_resp),
        ) as mock_gen,
        patch("random.choice", return_value="культовые видеоигры (узнай игру по фразе NPC)"),
    ):
        suggestion = await mock_script_service.suggest_topic(category_hint=None, language="ru")

        assert isinstance(suggestion, TopicSuggestion)
        assert suggestion.topic == "Парадоксы видеоигр"
        called_prompt = mock_gen.call_args.kwargs["contents"]
        assert "Вектор для вдохновения" in called_prompt
        assert "культовые видеоигры" in called_prompt


@pytest.mark.asyncio
async def test_suggest_batch_topics_success(mock_script_service):
    fake_topics = [
        {"topic": f"Парадокс #{i}", "category": f"Ниша {i}", "curiosity_hook": f"Крючок {i}"}
        for i in range(1, 6)
    ]
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"topics": fake_topics})

    with patch.object(
        mock_script_service._client.aio.models,
        "generate_content",
        new=AsyncMock(return_value=mock_resp),
    ):
        batch = await mock_script_service.suggest_batch_topics(count=5, language="ru")

        assert isinstance(batch, BatchTopicList)
        assert len(batch.topics) == 5
        assert batch.topics[0].topic == "Парадокс #1"
        assert batch.topics[4].category == "Ниша 5"


@pytest.mark.asyncio
async def test_suggest_batch_topics_branching(mock_script_service):
    fake_topics = [
        {"topic": f"Тема #{i}", "category": "Космос", "curiosity_hook": f"Крючок #{i}"}
        for i in range(1, 3)
    ]
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"topics": fake_topics})

    with patch.object(
        mock_script_service._client.aio.models,
        "generate_content",
        new=AsyncMock(return_value=mock_resp),
    ) as mock_gen:
        # 1. With category_hint
        await mock_script_service.suggest_batch_topics(
            count=2, category_hint="Космос", language="ru"
        )
        prompt_with_hint = mock_gen.call_args.kwargs["contents"]
        assert "Все 2 тем должны быть внутри ниши «Космос»" in prompt_with_hint

        # 2. Without category_hint
        await mock_script_service.suggest_batch_topics(count=2, category_hint=None, language="ru")
        prompt_no_hint = mock_gen.call_args.kwargs["contents"]
        assert (
            "Каждая из тем обязана относиться к совершенно разной жизненной"
            in prompt_no_hint
        )

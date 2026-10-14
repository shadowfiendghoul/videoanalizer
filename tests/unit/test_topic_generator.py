"""Unit tests for single and batch AI topic ideation."""

import json
from unittest.mock import MagicMock, patch
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

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        suggestion = await mock_script_service.suggest_topic(
            category_hint="Биология", language="ru"
        )

        assert isinstance(suggestion, TopicSuggestion)
        assert suggestion.topic == "Анатомические парадоксы тела"
        assert suggestion.category == "Биология"
        assert "болевых рецепторов" in suggestion.curiosity_hook


@pytest.mark.asyncio
async def test_suggest_batch_topics_success(mock_script_service):
    fake_topics = [
        {"topic": f"Парадокс #{i}", "category": f"Ниша {i}", "curiosity_hook": f"Крючок {i}"}
        for i in range(1, 6)
    ]
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({"topics": fake_topics})

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        batch = await mock_script_service.suggest_batch_topics(count=5, language="ru")

        assert isinstance(batch, BatchTopicList)
        assert len(batch.topics) == 5
        assert batch.topics[0].topic == "Парадокс #1"
        assert batch.topics[4].category == "Ниша 5"

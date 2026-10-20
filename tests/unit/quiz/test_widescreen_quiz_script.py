"""Unit tests for ScriptService widescreen quiz dataset generation."""

import pytest
from unittest.mock import MagicMock, patch

from videoanalizer.quiz.config import QuizConfig
from videoanalizer.quiz.models import WidescreenQuizDataset
from videoanalizer.quiz.script_service import ScriptService


@pytest.mark.asyncio
async def test_generate_widescreen_quiz_dataset_fallback():
    config = QuizConfig()
    service = ScriptService(config=config)

    # Without API key, should gracefully return the curated default dataset
    dataset = await service.generate_widescreen_quiz_dataset(
        topic_prompt="Культовые игры",
        language="ru",
        num_rounds=5,
        questions_per_round=10,
    )

    assert isinstance(dataset, WidescreenQuizDataset)
    assert dataset.mode == "widescreen_gaming_quiz"
    assert len(dataset.rounds) == 5
    assert dataset.total_questions_count == 50

    # Check that all 5 asset modes are represented across rounds
    modes = [r.asset_mode for r in dataset.rounds]
    assert "screenshot" in modes
    assert "audio_sfx" in modes
    assert "game_over" in modes
    assert "minimap" in modes
    assert "silhouette" in modes


@pytest.mark.asyncio
async def test_generate_widescreen_quiz_dataset_mocked_gemini():
    config = QuizConfig(gemini_api_key="dummy_key")
    service = ScriptService(config=config)

    # Prepare mocked Gemini JSON response
    mock_dataset = WidescreenQuizDataset(
        mode="widescreen_gaming_quiz",
        title="Custom Gemini Show",
        language="en",
        guessing_duration_sec=6.0,
        reveal_hold_duration_sec=3.0,
        intro={
            "hook_tts": "Welcome to the ultimate gaming challenge!",
            "duration_sec": 8.0,
            "challenge_title": "CUSTOM CHALLENGE",
        },
        outro={
            "duration_sec": 15.0,
            "outro_tts": "Thanks for watching, leave your score!",
            "call_to_action": "SUBSCRIBE!",
            "score_tiers": [
                {"tier_name": "Noob", "min_score": 0, "max_score": 5, "badge_color": "#94A3B8"},
                {"tier_name": "God Tier", "min_score": 6, "max_score": 10, "badge_color": "#F59E0B"},
            ],
        },
        rounds=[
            {
                "round_number": 1,
                "round_title": "ROUND 1: GUESS THE GAME",
                "asset_mode": "screenshot",
                "pass_rate_statistic": "95% PASS",
                "badge_theme_color": "#00E5FF",
                "splash_duration_sec": 4.0,
                "questions": [
                    {
                        "item_index": 1,
                        "global_question_number": 1,
                        "prompt_text": "Guess the game",
                        "answer_text": "MINECRAFT",
                        "asset_search_query": "Minecraft screenshot",
                    }
                ],
            }
        ],
    )

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = mock_dataset.model_dump_json()
    mock_client.models.generate_content.return_value = mock_resp

    with patch.object(service, "_client", mock_client):
        result = await service.generate_widescreen_quiz_dataset(
            topic_prompt="Mock Topic",
            language="en",
            num_rounds=1,
            questions_per_round=1,
        )
        assert result.title == "Custom Gemini Show"
        assert result.total_questions_count == 1
        assert result.rounds[0].questions[0].answer_text == "MINECRAFT"

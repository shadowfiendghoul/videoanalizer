"""Unit tests for ScriptService quiz generation via Gemini REST API."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from videoanalizer.quiz.models import (
    DifficultyTier,
    QuizChallenge,
    QuizItem,
    QuizTier,
)
from videoanalizer.quiz.script_service import ScriptService
from videoanalizer.quiz.workspace import QuizWorkspace


def make_mock_challenge() -> QuizChallenge:
    tiers = []
    configs = [
        (DifficultyTier.EASY, 1, "#22C55E", 1),
        (DifficultyTier.MEDIUM, 2, "#F59E0B", 4),
        (DifficultyTier.HARD, 3, "#EF4444", 7),
    ]
    for tier_level, tier_idx, color, start_q in configs:
        items = []
        for i in range(3):
            q_num = start_q + i
            items.append(
                QuizItem(
                    question_number=q_num,
                    difficulty=tier_level,
                    tier_index=tier_idx,
                    question_text=f"Question text {q_num}?",
                    correct_answer=f"Answer {q_num}",
                    fun_fact=f"Fact {q_num}",
                    image_query="Flag of France" if q_num == 1 else None,
                    local_image_path=None,
                )
            )
        tiers.append(
            QuizTier(
                tier_level=tier_level,
                tier_index=tier_idx,
                theme_color=color,
                questions=items,
            )
        )
    return QuizChallenge(
        topic="Flags of the World",
        language="ru",
        total_questions=9,
        tiers=tiers,
    )


@pytest.mark.asyncio
async def test_generate_quiz_success(tmp_path: Path) -> None:
    """Verify ScriptService parses structured Gemini response and resolves images."""
    mock_challenge = make_mock_challenge()

    with QuizWorkspace(job_id="test_script_job") as ws:
        service = ScriptService()

        # Mock Gemini call
        with patch.object(service, "_call_gemini", new=AsyncMock(return_value=mock_challenge)):
            # Mock ImageService search_and_download
            fake_img_path = ws.get_image_path("q1.png")
            fake_img_path.touch()
            with patch.object(
                service.image_service,
                "search_and_download",
                new=AsyncMock(return_value=fake_img_path),
            ):
                result = await service.generate_quiz(
                    topic="Flags of the World", language="ru", workspace=ws
                )

                assert result.total_questions == 9
                assert len(result.tiers) == 3
                assert len(result.all_questions()) == 9
                # Check that question 1 resolved image path
                q1 = result.all_questions()[0]
                assert q1.local_image_path == str(fake_img_path)

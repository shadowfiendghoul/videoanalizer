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


def test_quiz_system_prompt_layout_guard_constraints() -> None:
    """Verify QUIZ_SYSTEM_PROMPT contains <= 65 and <= 25 character constraints."""
    from videoanalizer.quiz.script_service import QUIZ_SYSTEM_PROMPT

    assert "65 characters" in QUIZ_SYSTEM_PROMPT
    assert "25 characters" in QUIZ_SYSTEM_PROMPT
    assert "80 characters" in QUIZ_SYSTEM_PROMPT
    assert "35 characters" in QUIZ_SYSTEM_PROMPT


def test_quiz_item_within_layout_guard_bounds() -> None:
    """Verify QuizItem accepts questions <= 65 chars and answers <= 25 chars."""
    item = QuizItem(
        question_number=1,
        difficulty=DifficultyTier.EASY,
        tier_index=1,
        question_text="Какая столица у Франции?",  # 25 chars
        correct_answer="Париж",  # 5 chars
        fun_fact="Париж называют городом огней.",
    )
    assert len(item.question_text) <= 65
    assert len(item.correct_answer) <= 25


def test_quiz_item_rejects_question_over_80_chars() -> None:
    """Verify QuizItem raises ValidationError when question exceeds hard 80-char limit."""
    from pydantic import ValidationError

    overlong_q = (
        "Это очень длинный тестовый вопрос, длина которого заведомо превышает восемьдесят символов!"
    )
    assert len(overlong_q) > 80

    with pytest.raises(ValidationError) as exc_info:
        QuizItem(
            question_number=1,
            difficulty=DifficultyTier.EASY,
            tier_index=1,
            question_text=overlong_q,
            correct_answer="Париж",
            fun_fact="Факт",
        )
    assert "80" in str(exc_info.value)


def test_quiz_item_rejects_answer_over_35_chars() -> None:
    """Verify QuizItem raises ValidationError when answer exceeds hard 35-char limit."""
    from pydantic import ValidationError

    overlong_a = "Невероятно длинный и подробный ответ на вопрос"
    assert len(overlong_a) > 35

    with pytest.raises(ValidationError) as exc_info:
        QuizItem(
            question_number=1,
            difficulty=DifficultyTier.EASY,
            tier_index=1,
            question_text="Вопрос нормальной длины?",
            correct_answer=overlong_a,
            fun_fact="Факт",
        )
    assert "35" in str(exc_info.value)


@pytest.mark.asyncio
async def test_two_stage_fact_checking_pass() -> None:
    """Verify generate_quiz invokes both creative generation and secondary fact-checking pass."""
    from videoanalizer.quiz.script_service import FACT_CHECK_SYSTEM_PROMPT

    assert "scientific fact-checker" in FACT_CHECK_SYSTEM_PROMPT
    assert "Strict Factual Veracity" in FACT_CHECK_SYSTEM_PROMPT

    service = ScriptService()
    initial_challenge = make_mock_challenge()

    # Fact-checker corrects a debunked myth in Q1
    refined_challenge = make_mock_challenge()
    refined_challenge.tiers[0].questions[0].fun_fact = "Научно доказанный факт без мифов."

    with (
        patch.object(
            service, "_call_gemini", new=AsyncMock(return_value=initial_challenge)
        ) as mock_creative,
        patch.object(
            service, "_verify_and_refine_facts", new=AsyncMock(return_value=refined_challenge)
        ) as mock_verifier,
    ):
        result = await service.generate_quiz(
            topic="Bizarre Science",
            language="ru",
            creative_temperature=0.95,
            fact_check=True,
        )

        mock_creative.assert_called_once_with("Bizarre Science", "ru", temperature=0.95)
        mock_verifier.assert_called_once_with(initial_challenge, "ru")
        assert result.tiers[0].questions[0].fun_fact == "Научно доказанный факт без мифов."


@pytest.mark.asyncio
async def test_fact_checking_bypassed_when_disabled() -> None:
    """Verify fact-checking pass is skipped when fact_check=False."""
    service = ScriptService()
    mock_challenge = make_mock_challenge()

    with (
        patch.object(
            service, "_call_gemini", new=AsyncMock(return_value=mock_challenge)
        ) as mock_creative,
        patch.object(service, "_verify_and_refine_facts", new=AsyncMock()) as mock_verifier,
    ):
        result = await service.generate_quiz(
            topic="Quick Trivia",
            language="ru",
            fact_check=False,
        )

        mock_creative.assert_called_once()
        mock_verifier.assert_not_called()
        assert result == mock_challenge

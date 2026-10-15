"""Unit tests for Visual Image Quiz script generation and Pydantic v2 schemas."""
import pytest
from videoanalizer.quiz.models import (
    VisualDifficulty,
    VisualQuizItem,
    VisualQuizInterstitial,
    VisualQuizInterstitialType,
    VisualQuizDataset,
    VisualQuizRenderProps,
    VisualQuizTimingSlot,
)


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
                image_path=f"assets/quizzes/sample/img_{i}.png",
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
        theme="Тестовая тема",
        hook_tts="Угадай все предметы в этом тесте!",
        rapid_flip_duration_ms=120,
        timer_duration_sec=2.0,
        items=items,
        interstitials=interstitials,
    )


def test_visual_quiz_dataset_validation(sample_visual_quiz_dataset: VisualQuizDataset):
    """Dataset must have exactly 10 items and valid structure."""
    assert len(sample_visual_quiz_dataset.items) == 10
    assert sample_visual_quiz_dataset.items[0].prompt_tts == "Что это?"
    assert sample_visual_quiz_dataset.items[9].difficulty == VisualDifficulty.MASTER
    assert len(sample_visual_quiz_dataset.interstitials) == 2

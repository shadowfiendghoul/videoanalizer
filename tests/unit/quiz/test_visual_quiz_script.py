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


@pytest.mark.asyncio
async def test_generate_visual_quiz_with_custom_items_prompt(monkeypatch):
    """Verify that custom multi-line theme with items is passed into prompt with strict instructions."""
    from unittest.mock import AsyncMock
    from videoanalizer.quiz.script_service import ScriptService, VISUAL_QUIZ_SYSTEM_PROMPT

    service = ScriptService()
    custom_theme = (
        "«Guess The Game by Its Weapon» (Угадай игру по оружию):\n\n"
        "Easy: Diamond Sword (Minecraft), Portal Gun (Portal), Pokeball.\n"
        "Medium: Blades of Chaos (God of War), Hidden Blade (Assassin's Creed), Crowbar (Half-Life).\n"
        "Hard: Ray Gun (CoD Zombies), BFG 9000 (DOOM), Buster Sword (FF VII).\n"
        "Master 10: Energy Sword (Halo) или AWP Dragon Lore (CS2)."
    )

    captured_prompt = None
    captured_sys_instruction = None

    async def mock_generate_structured(prompt, system_instruction, response_schema, temperature=None):
        nonlocal captured_prompt, captured_sys_instruction
        captured_prompt = prompt
        captured_sys_instruction = system_instruction
        # Return a dummy dataset
        from videoanalizer.quiz.models import VisualQuizDataset, VisualQuizItem, VisualDifficulty
        items = [
            VisualQuizItem(
                id=i,
                difficulty=VisualDifficulty.EASY if i <= 3 else (VisualDifficulty.MEDIUM if i <= 6 else (VisualDifficulty.HARD if i <= 9 else VisualDifficulty.MASTER)),
                answer_text="MINECRAFT" if i == 1 else ("Пиши в коммы" if i == 10 else f"GAME {i}"),
                image_query="Minecraft diamond sword" if i == 1 else f"weapon {i}",
                prompt_tts="Что за игра?" if i == 1 else f"Номер {i}, что за игра?",
                answer_tts="Это Minecraft!" if i == 1 else ("Пиши в коммы!" if i == 10 else f"Это Game {i}!"),
            )
            for i in range(1, 11)
        ]
        return VisualQuizDataset(
            mode="visual_image_quiz",
            theme="Guess The Game by Its Weapon",
            hook_tts="Угадай игру по оружию! Погнали!",
            rapid_flip_duration_ms=120,
            timer_duration_sec=1.75,
            items=items,
        )

    monkeypatch.setattr(service, "_generate_structured", mock_generate_structured)
    monkeypatch.setattr(service, "_resolve_visual_quiz_images", AsyncMock())

    dataset = await service.generate_visual_quiz_dataset(theme=custom_theme, language="ru")

    assert captured_prompt is not None
    assert captured_sys_instruction is not None
    # User's items must be in the prompt sent to Gemini
    assert "Diamond Sword (Minecraft)" in captured_prompt
    assert "Blades of Chaos (God of War)" in captured_prompt
    assert "Ray Gun (CoD Zombies)" in captured_prompt
    assert "Energy Sword (Halo)" in captured_prompt
    # Strict instructions must be present in prompt and system instruction
    assert "ТЫ ОБЯЗАН СТРОГО ИСПОЛЬЗОВАТЬ ИМЕННО ЭТИ ПРЕДМЕТЫ" in captured_prompt
    assert "Различай показываемый объект и правильный ответ" in captured_prompt
    assert "УГАДАЙ X ПО Y" in captured_sys_instruction
    # Title must be cleanly extracted, not the full multi-line blob
    assert "\n" not in dataset.theme
    assert "Guess The Game by Its Weapon" in dataset.theme


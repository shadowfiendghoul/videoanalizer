"""Unit tests for QuizOrchestrator render_widescreen_quiz pipeline."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from videoanalizer.quiz.config import QuizConfig
from videoanalizer.quiz.models import (
    AssetDisplayMode,
    WidescreenIntroConfig,
    WidescreenOutroConfig,
    WidescreenQuizDataset,
    WidescreenQuizItem,
    WidescreenQuizRound,
    WidescreenTimingSlot,
)
from videoanalizer.quiz.orchestrator import QuizOrchestrator


@pytest.fixture
def sample_widescreen_dataset() -> WidescreenQuizDataset:
    return WidescreenQuizDataset(
        mode="widescreen_gaming_quiz",
        title="Test Widescreen Quiz",
        language="ru",
        intro=WidescreenIntroConfig(
            hook_tts="50 игровых вопросов. Сможешь ли ты победить?",
            duration_sec=8.0,
            challenge_title="50 GAMING QUESTIONS",
        ),
        outro=WidescreenOutroConfig(
            duration_sec=15.0,
            outro_tts="Оставь свой счет в комментариях!",
            call_to_action="ПОДПИШИСЬ!",
            score_tiers=[],
        ),
        rounds=[
            WidescreenQuizRound(
                round_number=1,
                round_title="РАУНД 1: СКРИНШОТЫ",
                asset_mode=AssetDisplayMode.SCREENSHOT,
                pass_rate_statistic="95% PASS",
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
            ),
            WidescreenQuizRound(
                round_number=2,
                round_title="РАУНД 2: ЗВУКИ",
                asset_mode=AssetDisplayMode.AUDIO_SFX,
                pass_rate_statistic="80% PASS",
                badge_theme_color="#00E5FF",
                splash_duration_sec=4.0,
                questions=[
                    WidescreenQuizItem(
                        item_index=1,
                        global_question_number=2,
                        prompt_text="Угадайте звук",
                        answer_text="AWP",
                        asset_search_query="CS AWP shot",
                    )
                ],
            ),
        ],
    )


@pytest.mark.asyncio
async def test_render_widescreen_quiz_orchestrator(tmp_path: Path, sample_widescreen_dataset: WidescreenQuizDataset):
    config = QuizConfig(
        temp_dir=tmp_path / "temp",
        output_dir=tmp_path / "output",
    )
    orchestrator = QuizOrchestrator(config=config)

    dummy_output = tmp_path / "output" / "test_out.mp4"
    dummy_audio_mix = tmp_path / "temp" / "mix.wav"
    dummy_audio_mix.parent.mkdir(parents=True, exist_ok=True)
    dummy_audio_mix.write_bytes(b"RIFFdummywave")

    dummy_slots = [
        WidescreenTimingSlot(
            slot_type="intro",
            start_frame=0,
            duration_frames=480,
            end_frame=480,
        )
    ]

    with patch.object(
        orchestrator.audio_service,
        "generate_widescreen_quiz_audio",
        new=AsyncMock(return_value=(dummy_audio_mix, dummy_slots, 480)),
    ), patch.object(
        orchestrator.image_service,
        "search_and_download_gaming_asset",
        new=AsyncMock(return_value=tmp_path / "img.png"),
    ), patch(
        "videoanalizer.quiz.orchestrator.SoundService.resolve_sound_cue",
        new=AsyncMock(return_value=tmp_path / "sound.wav"),
    ), patch.object(
        orchestrator,
        "_render_remotion",
        new=AsyncMock(return_value=None),
    ), patch(
        "videoanalizer.media.uniquifier.strip_video_metadata",
        return_value=None,
    ):
        result_path = await orchestrator.render_widescreen_quiz(
            dataset=sample_widescreen_dataset,
            output_path=dummy_output,
        )

        assert result_path == dummy_output
        orchestrator._render_remotion.assert_awaited_once()
        call_kwargs = orchestrator._render_remotion.await_args.kwargs
        assert call_kwargs["composition_id"] == "WidescreenGamingQuiz"

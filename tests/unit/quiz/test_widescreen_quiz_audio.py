"""Unit tests for widescreen gaming quiz audio timeline and timing calculator."""

import pytest

from videoanalizer.quiz.audio_service import WidescreenTimingCalculator
from videoanalizer.quiz.models import (
    AssetDisplayMode,
    WidescreenIntroConfig,
    WidescreenOutroConfig,
    WidescreenQuizDataset,
    WidescreenQuizItem,
    WidescreenQuizRound,
    WidescreenScoreTier,
)


@pytest.fixture
def minimal_widescreen_dataset() -> WidescreenQuizDataset:
    return WidescreenQuizDataset(
        mode="widescreen_gaming_quiz",
        title="Minimal 1-Round 3-Question Test",
        language="ru",
        guessing_duration_sec=6.0,
        reveal_hold_duration_sec=3.0,
        intro=WidescreenIntroConfig(
            hook_tts="Тестовое интро для викторины 16:9",
            duration_sec=8.0,
            challenge_title="CHALLENGE",
        ),
        outro=WidescreenOutroConfig(
            duration_sec=15.0,
            outro_tts="Тестовое аутро для викторины 16:9",
            call_to_action="SUBSCRIBE",
            score_tiers=[
                WidescreenScoreTier(tier_name="Noob", min_score=0, max_score=1, badge_color="#94A3B8"),
                WidescreenScoreTier(tier_name="God Tier", min_score=2, max_score=3, badge_color="#F59E0B"),
            ],
        ),
        rounds=[
            WidescreenQuizRound(
                round_number=1,
                round_title="ROUND 1: SCREENSHOTS",
                asset_mode=AssetDisplayMode.SCREENSHOT,
                pass_rate_statistic="90% PASS",
                splash_duration_sec=4.0,
                questions=[
                    WidescreenQuizItem(
                        item_index=1,
                        global_question_number=1,
                        prompt_text="Game 1",
                        answer_text="DARK SOULS",
                        asset_search_query="Dark Souls screenshot",
                    ),
                    WidescreenQuizItem(
                        item_index=2,
                        global_question_number=2,
                        prompt_text="Game 2",
                        answer_text="MINECRAFT",
                        asset_search_query="Minecraft screenshot",
                    ),
                    WidescreenQuizItem(
                        item_index=3,
                        global_question_number=3,
                        prompt_text="Game 3",
                        answer_text="FORTNITE",
                        asset_search_query="Fortnite screenshot",
                    ),
                ],
            )
        ],
    )


def test_widescreen_timing_calculator_single_round(minimal_widescreen_dataset: WidescreenQuizDataset):
    calc = WidescreenTimingCalculator(fps=60)
    slots, total_frames = calc.calculate_timeline(minimal_widescreen_dataset)

    # 1 intro + 3 questions + 1 outro = 5 slots
    assert len(slots) == 5

    # Intro slot
    intro = slots[0]
    assert intro.slot_type == "intro"
    assert intro.start_frame == 0
    assert intro.duration_frames == 480  # 8.0s * 60fps
    assert intro.end_frame == 480

    # Question 1: 9.0s = 540 frames
    q1 = slots[1]
    assert q1.slot_type == "question"
    assert q1.question_global_number == 1
    assert q1.start_frame == 480
    assert q1.timer_start_frame == 480
    assert q1.timer_duration_frames == 360  # 6.0s * 60fps
    assert q1.reveal_frame == 840  # 480 + 360
    assert q1.duration_frames == 540  # 9.0s * 60fps
    assert q1.end_frame == 1020

    # Question 2
    q2 = slots[2]
    assert q2.start_frame == 1020
    assert q2.reveal_frame == 1380
    assert q2.end_frame == 1560

    # Question 3
    q3 = slots[3]
    assert q3.start_frame == 1560
    assert q3.reveal_frame == 1920
    assert q3.end_frame == 2100

    # Outro: 15.0s = 900 frames
    outro = slots[4]
    assert outro.slot_type == "outro"
    assert outro.start_frame == 2100
    assert outro.duration_frames == 900
    assert outro.end_frame == 3000

    assert total_frames == 3000


def test_widescreen_timing_calculator_multi_round_with_splash(minimal_widescreen_dataset: WidescreenQuizDataset):
    # Add second round (Audio SFX)
    round2 = WidescreenQuizRound(
        round_number=2,
        round_title="ROUND 2: WEAPON SOUNDS",
        asset_mode=AssetDisplayMode.AUDIO_SFX,
        pass_rate_statistic="75% PASS",
        splash_duration_sec=4.0,
        questions=[
            WidescreenQuizItem(
                item_index=1,
                global_question_number=4,
                prompt_text="Sound 1",
                answer_text="AWP",
                asset_search_query="AWP shot sound",
                audio_cue_duration_sec=3.5,
            )
        ],
    )
    dataset = minimal_widescreen_dataset.model_copy(deep=True)
    dataset.rounds.append(round2)

    calc = WidescreenTimingCalculator(fps=60)
    slots, total_frames = calc.calculate_timeline(dataset)

    # 1 intro + 3 questions (R1) + 1 splash (R2) + 1 question (R2) + 1 outro = 7 slots
    assert len(slots) == 7

    # Splash for Round 2
    splash = slots[4]
    assert splash.slot_type == "splash"
    assert splash.round_number == 2
    assert splash.start_frame == 2100
    assert splash.duration_frames == 240  # 4.0s * 60fps
    assert splash.end_frame == 2340

    # Question in Round 2 (Audio SFX)
    q4 = slots[5]
    assert q4.slot_type == "question"
    assert q4.question_global_number == 4
    assert q4.start_frame == 2340
    # Audio cue start: 0.5s into question = 30 frames
    assert q4.audio_cue_start_frame == 2340 + 30
    # Audio cue end: 3.5s duration = 210 frames
    assert q4.audio_cue_end_frame == 2340 + 30 + 210


@pytest.mark.asyncio
async def test_generate_widescreen_quiz_audio(minimal_widescreen_dataset: WidescreenQuizDataset, tmp_path):
    from unittest.mock import AsyncMock, patch
    from videoanalizer.quiz.audio_service import AudioService
    from videoanalizer.quiz.config import QuizConfig
    from videoanalizer.quiz.workspace import QuizWorkspace

    config = QuizConfig()
    service = AudioService(config=config)
    workspace = QuizWorkspace(base_dir=tmp_path / "workspaces", job_id="test_ws_audio")

    with patch.object(service, "synthesize_speech_with_cues", new_callable=AsyncMock) as mock_synth:
        mock_synth.return_value = (1500, [])
        with patch.object(service, "_render_audio_events_mix", new_callable=AsyncMock) as mock_mix:
            mock_mix.return_value = None

            master_path, slots, total_frames = await service.generate_widescreen_quiz_audio(
                dataset=minimal_widescreen_dataset,
                workspace=workspace,
                fps=60,
            )

            assert len(slots) == 5
            assert total_frames == 3000
            assert master_path.name == "widescreen_quiz_master_mix.wav"
            assert mock_mix.called

"""Unit tests for AudioService speech synthesis and AudioCueSheet compilation."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from videoanalizer.quiz.audio_service import AudioService
from videoanalizer.quiz.models import (
    DifficultyTier,
    QuizChallenge,
    QuizItem,
    QuizTier,
    WordCue,
)
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
        topic="General Knowledge",
        language="ru",
        total_questions=9,
        tiers=tiers,
    )


@pytest.mark.asyncio
async def test_generate_challenge_audio(tmp_path: Path) -> None:
    """Verify AudioService compiles a valid AudioCueSheet with 9 question cues."""
    challenge = make_mock_challenge()
    service = AudioService()

    with QuizWorkspace(job_id="test_audio_job") as ws:
        # Mock speech synthesis returning dummy (duration_ms, words)
        mock_cues = (
            1500,
            [
                WordCue(word="Test", start_ms=0, end_ms=700),
                WordCue(word="Question", start_ms=750, end_ms=1500),
            ],
        )

        with patch.object(
            service, "synthesize_speech_with_cues", new=AsyncMock(return_value=mock_cues)
        ):
            cue_sheet = await service.generate_challenge_audio(challenge, ws)

            assert len(cue_sheet.cues) == 9
            assert cue_sheet.total_duration_ms >= 30000
            assert cue_sheet.total_duration_frames > 0

            # Verify blitz progressive timings across tiers
            q1_cue = cue_sheet.cues[0]
            assert q1_cue.question_number == 1
            assert q1_cue.think_duration_ms == 3000

            q4_cue = cue_sheet.cues[3]
            assert q4_cue.question_number == 4
            assert q4_cue.think_duration_ms == 2500

            q7_cue = cue_sheet.cues[6]
            assert q7_cue.question_number == 7
            assert q7_cue.think_duration_ms == 1800

            assert q1_cue.reveal_frame > q1_cue.think_start_frame >= q1_cue.start_frame
            assert q1_cue.end_frame > q1_cue.reveal_frame


@pytest.mark.asyncio
async def test_generate_challenge_audio_with_retention_config(tmp_path: Path) -> None:
    """Verify AudioService applies explicit QuizRetentionConfig stress tiers."""
    from videoanalizer.quiz.models import QuizRetentionConfig, StressTimerTier

    challenge = make_mock_challenge()
    service = AudioService()

    custom_retention = QuizRetentionConfig(
        stress_timer_enabled=True,
        stress_tiers=[
            StressTimerTier(
                tier_level="easy",
                think_duration_sec=3.2,
                theme_color="#00A3FF",
                sfx_file="tick.wav",
            ),
            StressTimerTier(
                tier_level="medium",
                think_duration_sec=2.2,
                theme_color="#F59E0B",
                sfx_file="tick.wav",
            ),
            StressTimerTier(
                tier_level="hard",
                think_duration_sec=1.5,
                theme_color="#EF4444",
                sfx_file="panic.wav",
                panic_vignette=True,
            ),
        ],
    )

    with QuizWorkspace(job_id="test_custom_retention_audio_job") as ws:
        mock_cues = (1000, [WordCue(word="Test", start_ms=0, end_ms=1000)])
        with patch.object(
            service, "synthesize_speech_with_cues", new=AsyncMock(return_value=mock_cues)
        ):
            cue_sheet = await service.generate_challenge_audio(
                challenge, ws, retention_config=custom_retention
            )
            assert cue_sheet.cues[0].think_duration_ms == 3200
            assert cue_sheet.cues[3].think_duration_ms == 2200
            assert cue_sheet.cues[6].think_duration_ms == 1500


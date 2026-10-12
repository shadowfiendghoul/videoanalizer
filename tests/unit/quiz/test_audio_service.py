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


@pytest.mark.asyncio
async def test_synthesize_speech_offline_fallback_on_error(tmp_path: Path) -> None:
    """Verify that when edge-tts raises NoAudioReceived, offline fallback produces valid audio."""
    import edge_tts.exceptions

    service = AudioService()
    test_out = tmp_path / "fallback_speech.mp3"

    with patch(
        "edge_tts.Communicate.stream",
        side_effect=edge_tts.exceptions.NoAudioReceived("No audio received"),
    ):
        dur_ms, words = await service.synthesize_speech_with_cues(
            text="Тестовый вопрос номер один?",
            voice="ru-RU-SvetlanaNeural",
            output_path=test_out,
        )

        assert test_out.exists()
        assert dur_ms > 0
        assert len(words) == 4
        assert words[0].word == "Тестовый"


@pytest.mark.asyncio
async def test_synthesize_speech_voice_profiles(tmp_path: Path) -> None:
    """Verify custom voice profiles route to edge-tts with appropriate rate/filters."""
    service = AudioService()
    test_out = tmp_path / "voice_profile.mp3"

    # Mock edge_tts streaming
    async def mock_stream(*args: object, **kwargs: object):  # noqa: ANN202
        yield {"type": "audio", "data": b"mock_audio_data"}

    with (
        patch("edge_tts.Communicate.stream", side_effect=mock_stream),
        patch("videoanalizer.quiz.audio_service.probe_audio_duration_ms", return_value=1200),
        patch("subprocess.run") as mock_subproc,
    ):
        dur_ms, _ = await service.synthesize_speech_with_cues(
            text="Тест голоса",
            voice="ru-RU-MaleBaritone",
            output_path=test_out,
        )

        assert test_out.exists()
        assert dur_ms == 1200
        # Check that FFmpeg was invoked to apply acoustic pitch shift filter
        assert mock_subproc.called
        cmd = mock_subproc.call_args[0][0]
        assert "-af" in cmd
        assert "asetrate=" in cmd[cmd.index("-af") + 1]



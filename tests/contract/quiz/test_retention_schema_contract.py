"""Contract tests for QuizRetentionConfig and retention models."""

import pytest
from pydantic import ValidationError

from tests.contract.quiz.test_quiz_schema_contract import make_valid_quiz_challenge
from videoanalizer.quiz.models import (
    AudioCueSheet,
    ComboStreakConfig,
    QuestionAudioCue,
    QuizRetentionConfig,
    RankTierConfig,
    RemotionRenderProps,
    SfxPaths,
    StressTimerTier,
    WordCue,
)


def test_default_quiz_retention_config() -> None:
    """Verify default retention config has all mechanics enabled and valid tiers."""
    cfg = QuizRetentionConfig()
    assert cfg.enabled is True
    assert cfg.rank_bar_enabled is True
    assert len(cfg.rank_tiers) == 4
    assert cfg.rank_tiers[0].rank_title == "NPC"
    assert cfg.rank_tiers[3].rank_title == "1% Гениев"
    assert cfg.stress_timer_enabled is True
    assert len(cfg.stress_tiers) == 3
    assert cfg.stress_tiers[0].think_duration_sec == 3.0
    assert cfg.stress_tiers[1].think_duration_sec == 2.5
    assert cfg.stress_tiers[2].think_duration_sec == 1.8
    assert cfg.streak_fire.enabled is True
    assert cfg.streak_fire.ultra_threshold == 7
    assert cfg.comment_trap.enabled is True
    assert cfg.seamless_loop is True
    assert cfg.anti_cheat_callout is True


def test_rank_tier_config_validation() -> None:
    """Verify validation boundaries for rank tiers."""
    # Valid
    tier = RankTierConfig(
        min_question=1,
        max_question=3,
        rank_title="NPC",
        rank_color="#123456",
        rank_icon="🤡",
        iq_label="IQ: 80",
    )
    assert tier.min_question == 1

    # Invalid question range (<1 or >9)
    with pytest.raises(ValidationError):
        RankTierConfig(
            min_question=0,
            max_question=3,
            rank_title="NPC",
            rank_color="#123456",
            rank_icon="🤡",
            iq_label="IQ: 80",
        )

    # Invalid hex color
    with pytest.raises(ValidationError):
        RankTierConfig(
            min_question=1,
            max_question=3,
            rank_title="NPC",
            rank_color="red",
            rank_icon="🤡",
            iq_label="IQ: 80",
        )


def test_stress_timer_tier_validation() -> None:
    """Verify stress timer validation."""
    tier = StressTimerTier(
        tier_level="easy",
        think_duration_sec=3.0,
        theme_color="#00A3FF",
        sfx_file="timer_tick.wav",
        panic_vignette=False,
    )
    assert tier.tier_level == "easy"

    # Invalid tier level
    with pytest.raises(ValidationError):
        StressTimerTier(
            tier_level="impossible",
            think_duration_sec=3.0,
            theme_color="#00A3FF",
            sfx_file="timer_tick.wav",
            panic_vignette=False,
        )


def test_combo_streak_validation() -> None:
    """Verify combo streak validation boundaries."""
    streak = ComboStreakConfig(ultra_threshold=7)
    assert streak.fire_color_ultra == "#38BDF8"

    with pytest.raises(ValidationError):
        ComboStreakConfig(ultra_threshold=2)  # ge=3


def test_sfx_paths_extended_fields() -> None:
    """Verify SfxPaths accepts both legacy and new retention sound effects."""
    sfx = SfxPaths(
        timer_tick="tick.wav",
        reveal_ding="ding.wav",
        level_up="up.wav",
        heartbeat_panic="heart.wav",
        streak_fire="fire.wav",
        rank_levelup="rank.wav",
        comment_buzzer="buzz.wav",
    )
    assert sfx.heartbeat_panic == "heart.wav"
    assert sfx.comment_buzzer == "buzz.wav"


def test_remotion_render_props_contains_default_retention() -> None:
    """Verify RemotionRenderProps includes default retention config automatically."""
    challenge = make_valid_quiz_challenge()
    cues = []
    current_frame = 0
    for i in range(1, 10):
        q_cue = QuestionAudioCue(
            question_number=i,
            start_frame=current_frame,
            question_audio_file=f"q_{i}.mp3",
            question_duration_ms=2000,
            question_words=[WordCue(word="Test", start_ms=0, end_ms=2000)],
            think_start_frame=current_frame + 120,
            think_duration_ms=3000,
            reveal_frame=current_frame + 300,
            answer_audio_file=f"a_{i}.mp3",
            answer_duration_ms=1000,
            answer_words=[WordCue(word="Answer", start_ms=0, end_ms=1000)],
            end_frame=current_frame + 375,
        )
        cues.append(q_cue)
        current_frame += 375

    cue_sheet = AudioCueSheet(
        total_duration_ms=50000,
        total_duration_frames=current_frame,
        cues=cues,
    )
    sfx = SfxPaths(timer_tick="tick.wav", reveal_ding="ding.wav", level_up="up.wav")
    props = RemotionRenderProps(
        challenge=challenge,
        cue_sheet=cue_sheet,
        background_video_path="bg.mp4",
        sfx_paths=sfx,
    )
    assert props.retention is not None
    assert props.retention.enabled is True
    assert props.retention.stress_timer_enabled is True
    assert len(props.retention.rank_tiers) == 4
    assert len(props.retention.stress_tiers) == 3


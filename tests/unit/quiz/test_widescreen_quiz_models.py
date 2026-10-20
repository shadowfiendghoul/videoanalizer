"""Unit tests and synthetic fixtures for 008-widescreen-gaming-quiz Pydantic v2 models."""

import pytest
from pydantic import ValidationError

from videoanalizer.quiz.models import (
    AssetDisplayMode,
    WidescreenIntroConfig,
    WidescreenOutroConfig,
    WidescreenQuizDataset,
    WidescreenQuizItem,
    WidescreenQuizRenderProps,
    WidescreenQuizRound,
    WidescreenScoreTier,
    WidescreenTimingSlot,
)


@pytest.fixture
def synthetic_widescreen_item() -> WidescreenQuizItem:
    return WidescreenQuizItem(
        item_index=1,
        global_question_number=1,
        prompt_text="Назовите игру по скриншоту",
        answer_text="DARK SOULS III",
        asset_url="https://example.com/screenshot.jpg",
        asset_path="/local/path/screenshot.jpg",
        asset_search_query="Dark Souls 3 gameplay screenshot",
        apply_procedural_mask=True,
        is_approved=True,
        difficulty_tag="Easy",
        audio_cue_duration_sec=4.0,
    )


@pytest.fixture
def synthetic_widescreen_round(synthetic_widescreen_item: WidescreenQuizItem) -> WidescreenQuizRound:
    return WidescreenQuizRound(
        round_number=1,
        round_title="ROUND 01: GUESS THE GAME",
        asset_mode=AssetDisplayMode.SCREENSHOT,
        pass_rate_statistic="94% PASS RATE",
        badge_theme_color="#00E5FF",
        splash_duration_sec=4.0,
        questions=[synthetic_widescreen_item],
    )


@pytest.fixture
def synthetic_widescreen_dataset(synthetic_widescreen_round: WidescreenQuizRound) -> WidescreenQuizDataset:
    return WidescreenQuizDataset(
        mode="widescreen_gaming_quiz",
        title="Ultimate Gaming Quiz: 50 Questions",
        language="ru",
        guessing_duration_sec=6.0,
        reveal_hold_duration_sec=3.0,
        bgm_track_path="/media/bgm/tension_beat.mp3",
        bgm_ducking_volume=0.18,
        bgm_base_volume=0.30,
        intro=WidescreenIntroConfig(
            hook_tts="50 вопросов. 5 уникальных раундов. Дойдешь ли ты до God Tier?",
            duration_sec=8.0,
            challenge_title="50 GAMING QUESTIONS CHALLENGE",
        ),
        outro=WidescreenOutroConfig(
            duration_sec=15.0,
            outro_tts="Напиши свой результат в комментариях!",
            call_to_action="COMMENT YOUR SCORE & SUBSCRIBE!",
            score_tiers=[
                WidescreenScoreTier(tier_name="Noob", min_score=0, max_score=20, badge_color="#94A3B8"),
                WidescreenScoreTier(tier_name="Gamer", min_score=21, max_score=35, badge_color="#3B82F6"),
                WidescreenScoreTier(tier_name="Pro", min_score=36, max_score=45, badge_color="#8B5CF6"),
                WidescreenScoreTier(tier_name="God Tier", min_score=46, max_score=50, badge_color="#F59E0B"),
            ],
        ),
        rounds=[synthetic_widescreen_round],
    )


def test_asset_display_mode_enum():
    assert AssetDisplayMode.SCREENSHOT == "screenshot"
    assert AssetDisplayMode.AUDIO_SFX == "audio_sfx"
    assert AssetDisplayMode.GAME_OVER == "game_over"
    assert AssetDisplayMode.MINIMAP == "minimap"
    assert AssetDisplayMode.SILHOUETTE == "silhouette"
    assert AssetDisplayMode.CUSTOM == "custom"


def test_widescreen_item_validation(synthetic_widescreen_item: WidescreenQuizItem):
    assert synthetic_widescreen_item.item_index == 1
    assert synthetic_widescreen_item.global_question_number == 1
    assert synthetic_widescreen_item.apply_procedural_mask is True
    assert len(synthetic_widescreen_item.id) > 0

    # Test invalid prompt_text length
    with pytest.raises(ValidationError):
        WidescreenQuizItem(
            item_index=1,
            global_question_number=1,
            prompt_text="a",  # min_length=2
            answer_text="DARK SOULS",
            asset_search_query="query",
        )


def test_widescreen_round_validation(synthetic_widescreen_round: WidescreenQuizRound):
    assert synthetic_widescreen_round.round_number == 1
    assert synthetic_widescreen_round.asset_mode == AssetDisplayMode.SCREENSHOT
    assert len(synthetic_widescreen_round.questions) == 1

    # Empty questions list should fail
    with pytest.raises(ValidationError):
        WidescreenQuizRound(
            round_number=1,
            round_title="ROUND 1",
            asset_mode=AssetDisplayMode.SCREENSHOT,
            questions=[],
        )


def test_widescreen_dataset_properties(synthetic_widescreen_dataset: WidescreenQuizDataset):
    assert synthetic_widescreen_dataset.mode == "widescreen_gaming_quiz"
    assert synthetic_widescreen_dataset.total_questions_count == 1
    assert synthetic_widescreen_dataset.guessing_duration_sec == 6.0
    assert synthetic_widescreen_dataset.reveal_hold_duration_sec == 3.0


def test_widescreen_timing_slot():
    slot = WidescreenTimingSlot(
        slot_type="question",
        round_number=1,
        question_global_number=1,
        start_frame=480,
        duration_frames=540,
        end_frame=1020,
        timer_start_frame=480,
        timer_duration_frames=360,
        reveal_frame=840,
    )
    assert slot.start_frame == 480
    assert slot.duration_frames == 540
    assert slot.reveal_frame == 840


def test_asset_modes_and_procedural_mask_flags():
    # Audio SFX item and round
    sfx_item = WidescreenQuizItem(
        item_index=1,
        global_question_number=11,
        prompt_text="Угадайте звук оружия",
        answer_text="AWP",
        asset_search_query="AWP fire sound",
        audio_cue_duration_sec=3.0,
    )
    sfx_round = WidescreenQuizRound(
        round_number=2,
        round_title="ROUND 02: WEAPON SOUNDS",
        asset_mode=AssetDisplayMode.AUDIO_SFX,
        pass_rate_statistic="78% PASS RATE",
        badge_theme_color="#00E5FF",
        questions=[sfx_item],
    )
    assert sfx_round.asset_mode == "audio_sfx"
    assert sfx_item.audio_cue_duration_sec == 3.0

    # Minimap item with mask bypass
    radar_item = WidescreenQuizItem(
        item_index=1,
        global_question_number=31,
        prompt_text="Угадайте игру по миникарте",
        answer_text="THE WITCHER 3",
        asset_search_query="Witcher 3 radar hud",
        apply_procedural_mask=False,
    )
    radar_round = WidescreenQuizRound(
        round_number=4,
        round_title="ROUND 04: MINIMAPS",
        asset_mode=AssetDisplayMode.MINIMAP,
        pass_rate_statistic="42% PASS RATE",
        badge_theme_color="#F59E0B",
        questions=[radar_item],
    )
    assert radar_item.apply_procedural_mask is False
    assert radar_round.asset_mode == "minimap"
    assert radar_round.badge_theme_color == "#F59E0B"

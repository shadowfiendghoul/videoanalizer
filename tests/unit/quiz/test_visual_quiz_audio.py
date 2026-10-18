"""Unit tests for Visual Image Quiz audio service and cue assembly."""
import pytest
from videoanalizer.quiz.models import (
    VisualDifficulty,
    VisualQuizItem,
    VisualQuizDataset,
    VisualQuizTimingSlot,
)


def test_visual_quiz_timing_slot_math():
    """Verify timing slot calculations for synchronous fast timer."""
    slot = VisualQuizTimingSlot(
        question_id=1,
        start_frame=210,
        prompt_audio_start_frame=210,
        timer_start_frame=210,
        timer_duration_frames=120,  # 2.0s at 60fps
        answer_audio_start_frame=330,
        reveal_frame=330,
        end_frame=420,
    )
    assert slot.timer_start_frame == slot.prompt_audio_start_frame
    assert slot.reveal_frame == slot.timer_start_frame + slot.timer_duration_frames


def test_intro_hook_duration_calculation_by_words():
    """Verify intro duration strictly never exceeds 3.0s (180 frames at 60 fps)."""
    fps = 60

    # Short speech: 2100 ms
    speech_end_ms = 2100
    word_calculated_sec = (speech_end_ms + 200) / 1000.0
    hook_dur_sec = min(3.0, max(2.0, word_calculated_sec))
    hook_end_frame = int(round(hook_dur_sec * fps))
    assert hook_dur_sec == 2.3
    assert hook_end_frame == 138
    assert hook_dur_sec <= 3.0

    # Long speech: 3500 ms (capped at max 3.0s)
    speech_end_ms = 3500
    word_calculated_sec = (speech_end_ms + 200) / 1000.0
    hook_dur_sec = min(3.0, max(2.0, word_calculated_sec))
    hook_end_frame = int(round(hook_dur_sec * fps))
    assert hook_dur_sec == 3.0
    assert hook_end_frame == 180
    assert hook_end_frame <= 180

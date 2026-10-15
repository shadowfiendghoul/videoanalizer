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

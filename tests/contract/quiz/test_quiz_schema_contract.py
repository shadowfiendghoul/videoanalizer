"""Contract tests verifying Pydantic models against JSON Schema specifications."""

import pytest
from pydantic import ValidationError

from videoanalizer.quiz.models import (
    AudioCueSheet,
    DifficultyTier,
    QuestionAudioCue,
    QuizChallenge,
    QuizItem,
    QuizTier,
    RemotionRenderProps,
    SfxPaths,
    WordCue,
)


def make_valid_quiz_challenge() -> QuizChallenge:
    """Helper creating a fully valid 9-question 3-tier challenge."""
    tiers = []
    tiers_config = [
        (DifficultyTier.EASY, 1, "#22C55E", 1),
        (DifficultyTier.MEDIUM, 2, "#F59E0B", 4),
        (DifficultyTier.HARD, 3, "#EF4444", 7),
    ]
    for tier_level, tier_idx, color, start_q in tiers_config:
        items = []
        for i in range(3):
            q_num = start_q + i
            items.append(
                QuizItem(
                    question_number=q_num,
                    difficulty=tier_level,
                    tier_index=tier_idx,
                    question_text=f"Question number {q_num} text prompt?",
                    correct_answer=f"Answer {q_num}",
                    fun_fact=f"Interesting fun fact for question {q_num}.",
                    image_query="Sample query" if q_num % 2 == 0 else None,
                    local_image_path=None,
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
        topic="World Geography",
        language="ru",
        total_questions=9,
        tiers=tiers,
    )


def test_quiz_challenge_serialization() -> None:
    """Verify QuizChallenge serializes to dict and JSON cleanly."""
    challenge = make_valid_quiz_challenge()
    assert challenge.total_questions == 9
    assert len(challenge.tiers) == 3
    assert len(challenge.all_questions()) == 9

    data = challenge.model_dump()
    assert data["topic"] == "World Geography"
    assert len(data["tiers"]) == 3
    assert data["tiers"][0]["questions"][0]["question_number"] == 1


def test_quiz_challenge_validation_errors() -> None:
    """Verify validation fails on incorrect counts or missing fields."""
    with pytest.raises(ValidationError):
        # Missing required fields
        QuizItem(
            question_number=1, difficulty=DifficultyTier.EASY, tier_index=1, question_text="Short"
        )  # type: ignore

    with pytest.raises(ValidationError):
        # Tier with only 2 questions instead of 3
        QuizTier(
            tier_level=DifficultyTier.EASY,
            tier_index=1,
            theme_color="#22C55E",
            questions=[
                QuizItem(
                    question_number=1,
                    difficulty=DifficultyTier.EASY,
                    tier_index=1,
                    question_text="Valid question text?",
                    correct_answer="Yes",
                    fun_fact="Fact",
                ),
                QuizItem(
                    question_number=2,
                    difficulty=DifficultyTier.EASY,
                    tier_index=1,
                    question_text="Valid question text 2?",
                    correct_answer="Yes",
                    fun_fact="Fact",
                ),
            ],
        )


def test_remotion_render_props_contract() -> None:
    """Verify full RemotionRenderProps schema validation."""
    challenge = make_valid_quiz_challenge()
    cues = []
    fps = 60
    current_frame = 0

    for i in range(1, 10):
        q_dur_ms = 2000
        think_dur_ms = 3000
        ans_dur_ms = 1500

        q_frames = int(q_dur_ms * fps / 1000)
        think_frames = int(think_dur_ms * fps / 1000)
        ans_frames = int(ans_dur_ms * fps / 1000)

        start_frame = current_frame
        think_start_frame = start_frame + q_frames
        reveal_frame = think_start_frame + think_frames
        end_frame = reveal_frame + ans_frames
        current_frame = end_frame

        cues.append(
            QuestionAudioCue(
                question_number=i,
                start_frame=start_frame,
                question_audio_file=f"audio/q{i}.mp3",
                question_duration_ms=q_dur_ms,
                question_words=[
                    WordCue(word="Question", start_ms=0, end_ms=500),
                    WordCue(word="Prompt", start_ms=500, end_ms=1000),
                ],
                think_start_frame=think_start_frame,
                think_duration_ms=think_dur_ms,
                reveal_frame=reveal_frame,
                answer_audio_file=f"audio/a{i}.mp3",
                answer_duration_ms=ans_dur_ms,
                answer_words=[
                    WordCue(word="Answer", start_ms=0, end_ms=500),
                ],
                end_frame=end_frame,
            )
        )

    cue_sheet = AudioCueSheet(
        total_duration_ms=58500,
        total_duration_frames=current_frame,
        cues=cues,
    )

    props = RemotionRenderProps(
        challenge=challenge,
        cue_sheet=cue_sheet,
        background_video_path="assets/backgrounds/default_bg.mp4",
        sfx_paths=SfxPaths(
            timer_tick="assets/sfx/timer_tick.wav",
            reveal_ding="assets/sfx/reveal_ding.wav",
            level_up="assets/sfx/level_up.wav",
        ),
        fps=60,
        width=1080,
        height=1920,
    )

    assert props.width == 1080
    assert props.height == 1920
    assert props.fps == 60
    assert len(props.cue_sheet.cues) == 9

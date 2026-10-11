"""Pydantic v2 data contracts and domain entities for Quiz Shorts Generator."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DifficultyTier(StrEnum):
    """Progressive difficulty tiers for the 9-question challenge."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuizItem(BaseModel):
    """An individual open-recall trivia question item."""

    model_config = ConfigDict(extra="ignore")

    question_number: int = Field(
        ...,
        ge=1,
        le=9,
        description="Sequential index of the question (1 to 9).",
    )
    difficulty: DifficultyTier = Field(
        ...,
        description="Progressive difficulty level of the question.",
    )
    tier_index: int = Field(
        ...,
        ge=1,
        le=3,
        description="Tier index (1=Easy, 2=Medium, 3=Hard).",
    )
    question_text: str = Field(
        ...,
        min_length=5,
        max_length=150,
        description="Question text presented to the viewer.",
    )
    correct_answer: str = Field(
        ...,
        min_length=1,
        max_length=60,
        description="The definitive correct answer displayed on reveal.",
    )
    fun_fact: str = Field(
        ...,
        max_length=200,
        description="Educational takeaway or brief punchline spoken after reveal.",
    )
    image_query: str | None = Field(
        default=None,
        description="Search query for visual topics (e.g. 'Flag of Brazil').",
    )
    local_image_path: str | None = Field(
        default=None,
        description="Local cached file path to the verified image asset.",
    )


class QuizTier(BaseModel):
    """A difficulty tier grouping exactly 3 questions."""

    model_config = ConfigDict(extra="ignore")

    tier_level: DifficultyTier = Field(
        ...,
        description="Difficulty level identifier.",
    )
    tier_index: int = Field(
        ...,
        ge=1,
        le=3,
        description="Tier group index (1, 2, or 3).",
    )
    theme_color: str = Field(
        ...,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Neon accent hex color for this tier.",
    )
    questions: list[QuizItem] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="Exactly 3 questions belonging to this tier.",
    )


class QuizChallenge(BaseModel):
    """Complete 9-question 3-tier trivia challenge dataset."""

    model_config = ConfigDict(extra="ignore")

    topic: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Quiz category or custom user prompt.",
    )
    language: str = Field(
        default="ru",
        pattern=r"^(ru|en)$",
        description="Language code for narration and prompts.",
    )
    total_questions: int = Field(
        default=9,
        description="Total questions across all tiers (must be 9).",
    )
    tiers: list[QuizTier] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="The 3 difficulty tiers (Easy, Medium, Hard).",
    )

    def all_questions(self) -> list[QuizItem]:
        """Flatten and return all 9 questions in sequential order."""
        result = []
        for tier in self.tiers:
            result.extend(tier.questions)
        return sorted(result, key=lambda q: q.question_number)


class WordCue(BaseModel):
    """Word-level alignment timestamp for dynamic karaoke captions."""

    model_config = ConfigDict(extra="forbid")

    word: str = Field(..., description="Spoken word token.")
    start_ms: int = Field(..., ge=0, description="Start millisecond timestamp.")
    end_ms: int = Field(..., ge=0, description="End millisecond timestamp.")


class QuestionAudioCue(BaseModel):
    """Audio timing breakdown for a single question cycle."""

    model_config = ConfigDict(extra="forbid")

    question_number: int = Field(..., ge=1, le=9)
    start_frame: int = Field(default=0, ge=0)
    question_audio_file: str = Field(..., description="Path to question narration audio.")
    question_duration_ms: int = Field(..., ge=0)
    question_words: list[WordCue] = Field(default_factory=list)
    think_start_frame: int = Field(default=0, ge=0)
    think_duration_ms: int = Field(default=3000, ge=1000)
    reveal_frame: int = Field(default=0, ge=0)
    answer_audio_file: str = Field(..., description="Path to answer narration audio.")
    answer_duration_ms: int = Field(..., ge=0)
    answer_words: list[WordCue] = Field(default_factory=list)
    end_frame: int = Field(default=0, ge=0)


class AudioCueSheet(BaseModel):
    """Master synchronized audio and video cue sheet for the full challenge."""

    model_config = ConfigDict(extra="ignore")

    total_duration_ms: int = Field(..., ge=30000, le=120000)
    total_duration_frames: int = Field(..., ge=1800, le=7200)
    cues: list[QuestionAudioCue] = Field(..., min_length=9, max_length=9)


class SfxPaths(BaseModel):
    """Sound effect file paths."""

    model_config = ConfigDict(extra="forbid")

    timer_tick: str
    reveal_ding: str
    level_up: str


class RemotionRenderProps(BaseModel):
    """Unified JSON input contract passed to Remotion CLI."""

    model_config = ConfigDict(extra="forbid")

    challenge: QuizChallenge
    cue_sheet: AudioCueSheet
    background_video_path: str
    sfx_paths: SfxPaths
    fps: int = Field(default=60)
    width: int = Field(default=1080)
    height: int = Field(default=1920)
    banner_video_path: str | None = Field(default=None)
    banner_start_frame: int | None = Field(default=None)
    banner_duration_frames: int | None = Field(default=None)

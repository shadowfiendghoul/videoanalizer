"""Pydantic v2 data contracts and domain entities for Quiz Shorts Generator."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
        max_length=80,
        description="Question text presented to the viewer (target <= 65 chars, hard limit 80).",
    )
    correct_answer: str = Field(
        ...,
        min_length=1,
        max_length=35,
        description=(
            "The definitive correct answer displayed on reveal (target <= 25 chars, hard limit 35)."
        ),
    )

    @field_validator("question_text")
    @classmethod
    def validate_question_text_length(cls, v: str) -> str:
        if len(v) > 80:
            raise ValueError(f"Question text exceeds maximum 80 characters limit: {len(v)} chars")
        return v

    @field_validator("correct_answer")
    @classmethod
    def validate_correct_answer_length(cls, v: str) -> str:
        if len(v) > 35:
            raise ValueError(f"Correct answer exceeds maximum 35 characters limit: {len(v)} chars")
        return v
    fun_fact: str = Field(
        ...,
        max_length=200,
        description="Educational takeaway or brief punchline spoken after reveal.",
    )
    image_query: str | None = Field(
        default=None,
        description="Search query for visual topics (e.g. 'Flag of Brazil').",
    )
    image_url: str | None = Field(
        default=None,
        description="Direct URL or web preview of the selected image asset.",
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

    model_config = ConfigDict(extra="ignore")

    timer_tick: str
    reveal_ding: str
    level_up: str
    heartbeat_panic: str | None = Field(
        default=None, description="Fast heartbeat for hard timer."
    )
    streak_fire: str | None = Field(default=None, description="Whoosh sound for combo streak.")
    rank_levelup: str | None = Field(default=None, description="Chime for rank tier increase.")
    comment_buzzer: str | None = Field(
        default=None, description="Accent buzzer/boom for outro trap."
    )


class RankTierConfig(BaseModel):
    """Configuration for a specific rank status tier."""

    model_config = ConfigDict(extra="ignore")

    min_question: int = Field(..., ge=1, le=9, description="Starting question number (inclusive)")
    max_question: int = Field(..., ge=1, le=9, description="Ending question number (inclusive)")
    rank_title: str = Field(
        ..., min_length=2, max_length=30, description="Name of the rank (e.g. NPC, Нормис)"
    )
    rank_color: str = Field(
        ..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color theme for this rank tier"
    )
    rank_icon: str = Field(..., min_length=1, max_length=10, description="Emoji or symbol icon")
    iq_label: str = Field(
        ..., min_length=2, max_length=20, description="IQ label (e.g. 'IQ: 85', 'IQ: 160+')"
    )


class StressTimerTier(BaseModel):
    """Timing and style parameters for difficulty levels."""

    model_config = ConfigDict(extra="ignore")

    tier_level: str = Field(..., pattern=r"^(easy|medium|hard)$")
    think_duration_sec: float = Field(..., ge=1.0, le=4.0, description="Think window in seconds")
    theme_color: str = Field(
        ..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color for countdown pill"
    )
    sfx_file: str = Field(..., description="SFX audio identifier/path")
    panic_vignette: bool = Field(
        default=False, description="Enable pulsing red vignette on screen edges"
    )


class ComboStreakConfig(BaseModel):
    """Combo streak tracker configuration."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    fire_color_normal: str = Field(default="#FF4500", pattern=r"^#[0-9A-Fa-f]{6}$")
    fire_color_ultra: str = Field(default="#38BDF8", pattern=r"^#[0-9A-Fa-f]{6}$")
    ultra_threshold: int = Field(
        default=7, ge=3, le=9, description="Streak count triggering blue fire mode"
    )
    sfx_pitch_step: float = Field(
        default=1.059463, ge=1.0, le=1.2, description="Pitch multiplier per streak step"
    )


class CommentTrapConfig(BaseModel):
    """Comment baiting and controversy outro trigger."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    trap_question_number: int = Field(
        default=8, ge=6, le=9, description="Question containing a counter-intuitive fact"
    )
    outro_challenge_text: str = Field(
        default="Если набрал 8+ — ты соврал. Пиши честный счет в комменты! 👇",
        min_length=10,
        max_length=150,
    )
    duration_frames: int = Field(
        default=90,
        ge=30,
        le=180,
        description="Duration in frames at 60fps (1.5s = 90 frames)",
    )


def get_default_rank_tiers() -> list[RankTierConfig]:
    """Return default 4-tier psychological status progression."""
    return [
        RankTierConfig(
            min_question=1,
            max_question=2,
            rank_title="NPC",
            rank_color="#64748B",
            rank_icon="🤡",
            iq_label="IQ: 85",
        ),
        RankTierConfig(
            min_question=3,
            max_question=5,
            rank_title="Нормис",
            rank_color="#22C55E",
            rank_icon="🤓",
            iq_label="IQ: 110",
        ),
        RankTierConfig(
            min_question=6,
            max_question=8,
            rank_title="Эрудит",
            rank_color="#A855F7",
            rank_icon="🧠",
            iq_label="IQ: 135",
        ),
        RankTierConfig(
            min_question=9,
            max_question=9,
            rank_title="1% Гениев",
            rank_color="#F59E0B",
            rank_icon="👑",
            iq_label="IQ: 160+",
        ),
    ]


def get_default_stress_tiers() -> list[StressTimerTier]:
    """Return default accelerating blitz timer parameters."""
    return [
        StressTimerTier(
            tier_level="easy",
            think_duration_sec=3.0,
            theme_color="#00A3FF",
            sfx_file="timer_tick.wav",
            panic_vignette=False,
        ),
        StressTimerTier(
            tier_level="medium",
            think_duration_sec=2.5,
            theme_color="#F59E0B",
            sfx_file="timer_tick.wav",
            panic_vignette=False,
        ),
        StressTimerTier(
            tier_level="hard",
            think_duration_sec=1.8,
            theme_color="#EF4444",
            sfx_file="heartbeat_panic.wav",
            panic_vignette=True,
        ),
    ]


class QuizRetentionConfig(BaseModel):
    """Aggregate retention and virality configuration passed to Remotion."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Master toggle for retention mechanics")
    rank_bar_enabled: bool = Field(default=True)
    rank_tiers: list[RankTierConfig] = Field(default_factory=get_default_rank_tiers)
    stress_timer_enabled: bool = Field(default=True)
    stress_tiers: list[StressTimerTier] = Field(default_factory=get_default_stress_tiers)
    streak_fire: ComboStreakConfig = Field(default_factory=ComboStreakConfig)
    comment_trap: CommentTrapConfig = Field(default_factory=CommentTrapConfig)
    seamless_loop: bool = Field(
        default=True, description="Align intro and outro for infinite looping"
    )
    anti_cheat_callout: bool = Field(
        default=True, description="Display '👀 Без паузы!' banner on Q9"
    )


class RemotionRenderProps(BaseModel):
    """Unified JSON input contract passed to Remotion CLI."""

    model_config = ConfigDict(extra="ignore")

    challenge: QuizChallenge
    cue_sheet: AudioCueSheet
    background_video_path: str
    sfx_paths: SfxPaths
    retention: QuizRetentionConfig = Field(default_factory=QuizRetentionConfig)
    fps: int = Field(default=60)
    width: int = Field(default=1080)
    height: int = Field(default=1920)
    banner_video_path: str | None = Field(default=None)
    banner_start_frame: int | None = Field(default=None)
    banner_duration_frames: int | None = Field(default=None)


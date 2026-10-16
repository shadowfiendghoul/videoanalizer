"""Pydantic v2 data contracts and domain entities for Quiz Shorts Generator."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class DifficultyTier(StrEnum):
    """Progressive difficulty tiers for the 9-question challenge."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class RenderProfile(StrEnum):
    """Rendering execution profile."""

    GPU_FAST = "gpu_fast"  # Hardware GPU encoding (AMF/NVENC/QSV/MF) + ANGLE + Webpack Cache
    CPU_SAFE = "cpu_safe"  # Software CPU encoding (libx264) + Standard rasterization


class GpuVendor(StrEnum):
    """Detected graphics processor vendor category."""

    AMD = "amd"
    NVIDIA = "nvidia"
    INTEL = "intel"
    APPLE = "apple"
    GENERIC_WINDOWS = "windows_mf"
    UNKNOWN = "unknown"


class HardwareCapabilities(BaseModel):
    """Detected host system graphics capabilities and active video encoders."""

    model_config = ConfigDict(extra="ignore")

    gpu_available: bool = Field(
        ...,
        description="Whether an accelerated GPU was detected on host.",
    )
    gpu_name: str = Field(
        default="Unknown GPU",
        description="Human-readable graphics card name.",
    )
    gpu_vendor: GpuVendor = Field(
        default=GpuVendor.UNKNOWN,
        description="Detected GPU vendor category.",
    )
    active_hw_encoder: str | None = Field(
        default=None,
        description="Primary validated hardware encoder ('h264_amf', 'h264_nvenc', 'h264_mf').",
    )
    supported_encoders: list[str] = Field(
        default_factory=list,
        description="List of operational FFmpeg video encoders discovered on host.",
    )
    gl_backend: str = Field(
        default="angle",
        description="Chromium OpenGL/DirectX rasterization backend ('angle', 'egl', etc.).",
    )
    recommended_profile: RenderProfile = Field(
        default=RenderProfile.GPU_FAST,
        description="Recommended rendering profile based on host hardware.",
    )
    bundle_cache_enabled: bool = Field(
        default=True,
        description="Whether persistent Remotion Webpack bundle caching is active.",
    )
    cpu_logical_cores: int = Field(
        default=4,
        description="Number of logical processor cores detected on host.",
    )
    ram_total_gb: float = Field(
        default=8.0,
        description="Total physical RAM in Gigabytes.",
    )
    ram_available_gb: float = Field(
        default=4.0,
        description="Available physical RAM in Gigabytes.",
    )
    optimal_concurrency: int = Field(
        default=4,
        description="Calculated optimal Remotion concurrency (75-80% CPU with OOM guard).",
    )
    build_reuse_enabled: bool = Field(
        default=True,
        description="Whether Remotion pre-built React bundle caching and reuse is active.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def gpu_device_name(self) -> str:
        """Alias for gpu_name for API compatibility."""
        return self.gpu_name

    @computed_field  # type: ignore[prop-decorator]
    @property
    def active_encoder(self) -> str | None:
        """Alias for active_hw_encoder for API compatibility."""
        return self.active_hw_encoder



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


class RegeneratedQuestionsPayload(BaseModel):
    """Container schema for selectively regenerated trivia questions from Gemini."""

    model_config = ConfigDict(extra="ignore")

    questions: list[QuizItem] = Field(
        ...,
        description="List of selectively regenerated trivia questions.",
    )


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
    intro_hook_text: str | None = Field(
        default=None, description="Custom hook phrase spoken at start."
    )
    intro_hook_audio_file: str | None = Field(
        default=None, description="Path to intro hook narration audio."
    )
    intro_hook_duration_ms: int = Field(default=0, ge=0)
    intro_hook_words: list[WordCue] = Field(default_factory=list)
    intro_hook_duration_frames: int = Field(default=0, ge=0)


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
    banner_width: int | None = Field(default=None)
    banner_height: int | None = Field(default=None)
    background_music_path: str | None = Field(default=None)
    background_music_volume: float = Field(default=0.18, ge=0.0, le=1.0)


# ==============================================================================
# Topic Ideation & Batch Queue Contracts (005-batch-queue-topics)
# ==============================================================================


class TopicSuggestion(BaseModel):
    """Individual viral trivia topic suggestion generated by Gemini."""

    model_config = ConfigDict(extra="ignore")

    topic: str = Field(..., min_length=3, max_length=70, description="Viral quiz topic title")
    category: str = Field(..., min_length=2, max_length=40, description="Topic niche/category")
    curiosity_hook: str = Field(
        ..., min_length=5, max_length=120, description="Why this topic triggers viewer curiosity"
    )


class VisualTopicSuggestion(BaseModel):
    """Viral visual quiz topic with catchy rapid-flip hook."""

    model_config = ConfigDict(extra="ignore")

    topic: str = Field(..., min_length=3, max_length=80, description="Short visual quiz theme title")
    category: str = Field(..., min_length=2, max_length=40, description="Category/niche")
    flip_hook: str = Field(..., min_length=5, max_length=140, description="Catchy rapid-flip hook spoken at intro")
    sample_items: list[str] = Field(default_factory=list, description="Sample recognizable visual items")


class BatchTopicList(BaseModel):
    """Collection of N diverse topics generated in a single Gemini API request."""

    model_config = ConfigDict(extra="ignore")

    topics: list[TopicSuggestion] = Field(
        ..., min_length=1, max_length=25, description="List of generated unique topics"
    )


class SingleTopicSuggestRequest(BaseModel):
    """Payload to request a single viral topic suggestion."""

    category_hint: str | None = Field(
        default=None, max_length=300, description="Optional theme or category guidance"
    )
    language: Literal["ru", "en"] = Field(
        default="ru", description="Output language (ru or en)"
    )
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Sampling temperature (0.0-2.0, default 1.05)"
    )
    previous_topic: str | None = Field(
        default=None, max_length=300, description="Optional previous topic to avoid repeating"
    )


class BatchTopicSuggestRequest(BaseModel):
    """Payload to request N diverse topics in a single Gemini API call."""

    count: int = Field(default=10, ge=2, le=20, description="Number of topics to generate (2-20)")
    category_hint: str | None = Field(
        default=None, max_length=300, description="Optional theme or category guidance"
    )
    language: Literal["ru", "en"] = Field(
        default="ru", description="Output language (ru or en)"
    )
    temperature: float | None = Field(
        default=None, ge=0.0, le=2.0, description="Sampling temperature (0.0-2.0, default 1.05)"
    )


class BatchQueueItemStatus(StrEnum):
    """Lifecycle states of a video task inside a batch queue."""

    PENDING_GENERATION = "pending_generation"  # Script is being generated by AI
    PENDING_APPROVAL = "pending_approval"      # Script ready, waiting for user review & approval
    QUEUED = "queued"                          # Approved, waiting in FIFO render queue
    RENDERING = "rendering"                    # Actively rendering in Remotion
    COMPLETED = "completed"                    # Finished, MP4 ready for preview and download
    FAILED = "failed"                          # Generation or render failed with error
    CANCELLED = "cancelled"                    # Cancelled by user


class BatchQueueItem(BaseModel):
    """Represents a single video task within a batch queue session."""

    model_config = ConfigDict(extra="ignore")

    item_id: str = Field(..., description="Unique item identifier (e.g. bqi_...)")
    index: int = Field(..., ge=1, le=20, description="1-based position in batch")
    topic: str = Field(..., min_length=3, max_length=80, description="Quiz topic title")
    challenge: QuizChallenge | None = Field(
        default=None, description="Generated 9-question challenge structure"
    )
    status: BatchQueueItemStatus = Field(
        default=BatchQueueItemStatus.PENDING_GENERATION, description="Current lifecycle status"
    )
    progress_percent: int = Field(
        default=0, ge=0, le=100, description="Progress percentage (0-100)"
    )
    stage: str = Field(default="", description="Human-readable stage description")
    video_path: str | None = Field(default=None, description="Local path to finished MP4")
    download_url: str | None = Field(default=None, description="API endpoint to download MP4")
    error_message: str | None = Field(default=None, description="Error details if status is failed")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="UTC timestamp of creation"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="UTC timestamp of last update"
    )


class BatchQueueState(BaseModel):
    """Snapshot of active batch queue status and execution metrics."""

    model_config = ConfigDict(extra="ignore")

    batch_id: str = Field(..., description="Unique batch session ID")
    items: list[BatchQueueItem] = Field(
        default_factory=list, description="All items in the batch session"
    )
    is_rendering: bool = Field(default=False, description="True if a video is actively rendering")
    active_item_id: str | None = Field(
        default=None, description="ID of the item currently being rendered"
    )
    completed_count: int = Field(default=0, ge=0, description="Number of completed items")
    total_count: int = Field(default=0, ge=0, description="Total count of items in batch")
    rate_limit_waiting: bool = Field(
        default=False, description="True if paused waiting for 15 RPM Gemini quota pacing"
    )
    rate_limit_delay_sec: float = Field(
        default=0.0, description="Seconds remaining before next Gemini call can be made"
    )


class BatchRenderStartRequest(BaseModel):
    """Payload to trigger sequential Remotion rendering for an approved batch of items."""

    model_config = ConfigDict(extra="ignore")

    batch_id: str = Field(..., description="Batch session identifier")
    items: list[BatchQueueItem] = Field(
        ..., min_length=1, description="List of approved items with QuizChallenge structures"
    )
    voice: str | None = Field(default=None, description="Voice override for speech synthesis")
    voice_config: VoiceConfig | None = Field(
        default=None, description="Optional voice pipeline and cloning config"
    )
    background_video: str | None = Field(
        default="random", description="Background video filename, path, or 'random'"
    )
    banner_video: str | None = Field(default=None, description="Optional banner video")
    background_music: str | None = Field(default=None, description="Optional background music")
    background_music_volume: float = Field(default=0.18, ge=0.0, le=1.0)
    retention_enabled: bool = Field(default=True)
    rank_bar_enabled: bool = Field(default=True)
    stress_timer_enabled: bool = Field(default=True)
    streak_fire_enabled: bool = Field(default=True)
    comment_trap_enabled: bool = Field(default=True)
    intro_hook: str | None = Field(
        default=None,
        description=(
            "Optional custom greeting/hook phrase spoken at start. "
            "If omitted or None, video starts directly with Question 1."
        ),
    )
    uniquifier: Any | None = Field(default=None, description="Optional uniquifier config")
    render_profile: RenderProfile = Field(default=RenderProfile.GPU_FAST)


class GenerationHistoryItem(BaseModel):
    """Persistent history record of a completed quiz video."""

    model_config = ConfigDict(extra="ignore")

    history_id: str = Field(..., description="Unique history record identifier (e.g. gh_...)")
    job_id: str = Field(..., description="Original generation job/item ID")
    topic: str = Field(..., min_length=3, description="Quiz topic title")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="UTC timestamp of completion"
    )
    video_path: str = Field(..., description="Local path to MP4")
    download_url: str = Field(..., description="API download URL")
    duration_seconds: float = Field(default=60.0, ge=5.0, description="Video duration in seconds")


class VoiceMode(StrEnum):
    """Execution mode of the speech synthesis and cloning pipeline."""

    EDGE_TTS = "edge_tts"
    CUSTOM_RVC = "custom_rvc"
    QWEN3_RVC = "qwen3_rvc"
    OFFLINE_FALLBACK = "offline_fallback"


class RvcPitchMethod(StrEnum):
    """F0 pitch extraction method for RVC voice conversion."""

    RMVPE = "rmvpe"
    PM = "pm"
    HARVEST = "harvest"


class VoiceConfig(BaseModel):
    """Configuration for speech synthesis and RVC voice cloning."""

    model_config = ConfigDict(extra="ignore")

    voice_mode: VoiceMode = Field(
        default=VoiceMode.EDGE_TTS,
        description="Active synthesis mode: edge_tts, custom_rvc, qwen3_rvc, or offline_fallback",
    )
    allow_fallback: bool = Field(
        default=False,
        description=(
            "Whether to allow degrading to a different voice mode on failure "
            "(default: False to guarantee 100% session voice consistency)."
        ),
    )
    base_voice: str = Field(
        default="ru-RU-DmitryNeural",
        description="Base neural speaker for pristine diction and word timings",
    )
    rvc_model_path: str | None = Field(
        default=None,
        max_length=255,
        description="Relative or absolute path to target .pth checkpoint",
    )
    rvc_index_path: str | None = Field(
        default=None,
        max_length=255,
        description="Optional feature index file .index for RVC retrieval",
    )
    pitch_shift: int = Field(
        default=0,
        ge=-12,
        le=12,
        description="Pitch transposition in semitones (-12..+12). 0 = preserve",
    )
    speech_rate: float = Field(
        default=1.15,
        ge=0.8,
        le=1.5,
        description="Speech rate multiplier (1.0 = normal, 1.15 = +15% for Shorts)",
    )
    pitch_method: RvcPitchMethod = Field(
        default=RvcPitchMethod.RMVPE,
        description="Pitch extraction algorithm for F0",
    )
    device: Literal["auto", "cuda", "cpu"] = Field(
        default="auto",
        description="Inference execution device target",
    )
    qwen3_model_path: str = Field(
        default="assets/models/qwen3_tts",
        description="Path to local Qwen3-TTS checkpoint directory",
    )
    qwen3_ref_audio: str = Field(
        default="assets/voices/mellstroy_ref.wav",
        description="Reference audio path for speaker cloning in Qwen3-TTS",
    )
    tighten_pauses: bool = Field(
        default=True,
        description="Whether to detect and compress long silences between words",
    )
    max_pause_sec: float = Field(
        default=0.13,
        ge=0.04,
        le=0.5,
        description="Target maximum silence duration between words in seconds",
    )


class RvcModelInfo(BaseModel):
    """Metadata describing a discovered local RVC voice model."""

    model_config = ConfigDict(extra="ignore")

    model_id: str = Field(..., description="Unique model identifier (stem name)")
    name: str = Field(..., description="Human-readable model name")
    file_path: str = Field(..., description="Relative or absolute path to .pth")
    index_path: str | None = Field(default=None, description="Path to .index file if present")
    file_size_bytes: int = Field(..., ge=0, description="Model file size in bytes")
    is_valid: bool = Field(default=True, description="Whether checkpoint is valid")


class RvcModelListResponse(BaseModel):
    """Response containing discovered RVC voice models."""

    model_config = ConfigDict(extra="ignore")

    models: list[RvcModelInfo] = Field(default_factory=list)
    active_model_id: str | None = Field(default=None)
    total_count: int = Field(default=0)


class WordTiming(BaseModel):
    """Word-level timing marker for karaoke subtitle alignment."""

    model_config = ConfigDict(extra="ignore")

    word: str = Field(..., description="Spoken word text")
    start_ms: int = Field(..., ge=0, description="Start offset in milliseconds")
    end_ms: int = Field(..., ge=0, description="End offset in milliseconds")

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)


class SynthesizedSpeechResult(BaseModel):
    """Synthesized speech output with audio path, duration, and word markers."""

    model_config = ConfigDict(extra="ignore")

    audio_path: str = Field(..., description="Path to output WAV/MP3 file")
    duration_ms: int = Field(..., ge=0, description="Total audio duration in milliseconds")
    words: list[WordTiming] = Field(default_factory=list, description="Word boundaries")
    voice_mode_used: VoiceMode = Field(..., description="Actual mode used for synthesis")
    model_name: str | None = Field(default=None, description="RVC model name if converted")


class VoicePreviewRequest(BaseModel):
    """Payload to synthesize a short audio preview."""

    model_config = ConfigDict(extra="ignore")

    text: str = Field(
        default="Привет! Это проверка моего нового кастомного голоса для викторин.",
        max_length=200,
        description="Sample phrase for preview synthesis",
    )
    config: VoiceConfig = Field(..., description="Voice configuration to test")


class VoicePreviewResponse(BaseModel):
    """Response containing URL and metadata for voice preview audio."""

    model_config = ConfigDict(extra="ignore")

    audio_url: str = Field(..., description="Streaming/download URL of preview audio")
    duration_ms: int = Field(..., ge=0, description="Sample duration in milliseconds")
    voice_mode_used: VoiceMode = Field(..., description="Mode applied during preview")


# ==========================================
# 007-visual-image-quiz Data Models
# ==========================================


class VisualDifficulty(StrEnum):
    """Difficulty levels for Visual Image Quiz."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MASTER = "master"


class VisualQuizItem(BaseModel):
    """Single question specification for Visual Image Quiz."""

    model_config = ConfigDict(extra="ignore")

    id: int = Field(..., ge=1, le=10, description="Question number 1..10")
    difficulty: VisualDifficulty = Field(..., description="Difficulty level")
    answer_text: str = Field(..., min_length=1, max_length=60, description="Item name for ladder")
    image_query: str = Field(..., min_length=2, max_length=120, description="Web search query for image")
    image_url: str | None = Field(default=None, description="Direct URL of image")
    image_path: str | None = Field(default=None, description="Local cached path")
    is_approved: bool = Field(default=False, description="Whether image was approved by user")
    prompt_tts: str = Field(..., min_length=2, max_length=120, description="Announcer question text")
    answer_tts: str = Field(..., min_length=2, max_length=140, description="Announcer answer/cliffhanger text")


class VisualQuizInterstitialType(StrEnum):
    """Types of engagement interstitials."""

    COMMENT_BAIT = "comment_bait"
    SHARE_BAIT = "share_bait"


class VisualQuizInterstitial(BaseModel):
    """Interstitial bait cue."""

    model_config = ConfigDict(extra="ignore")

    after_question: int = Field(..., ge=1, le=9, description="Question number after which interstitial displays")
    type: VisualQuizInterstitialType = Field(..., description="Type of bait activity")
    tts_text: str = Field(..., min_length=3, max_length=140, description="Voice call to action")
    duration_sec: float = Field(default=2.0, ge=1.0, le=4.0, description="Duration in seconds")


class VisualQuizDataset(BaseModel):
    """Complete dataset for Visual Image Quiz."""

    model_config = ConfigDict(extra="ignore")

    mode: Literal["visual_image_quiz"] = Field(default="visual_image_quiz", description="Mode identifier")
    theme: str = Field(..., min_length=2, max_length=100, description="Quiz theme")
    hook_tts: str = Field(..., min_length=5, max_length=250, description="Intro hook narration")
    rapid_flip_duration_ms: int = Field(default=120, ge=80, le=200, description="Intro flip speed in ms")
    timer_duration_sec: float = Field(default=2.0, ge=1.5, le=3.0, description="Question timer duration")
    items: list[VisualQuizItem] = Field(..., min_length=10, max_length=10, description="Exactly 10 questions")
    interstitials: list[VisualQuizInterstitial] = Field(default_factory=list, description="Engagement baits")


class VisualQuizTimingSlot(BaseModel):
    """Timing coordinates for each question round in Remotion."""

    model_config = ConfigDict(extra="ignore")

    question_id: int
    start_frame: int
    prompt_audio_start_frame: int
    timer_start_frame: int
    timer_duration_frames: int
    answer_audio_start_frame: int
    reveal_frame: int
    end_frame: int


class VisualQuizWordTiming(BaseModel):
    """Word boundary timing for karaoke captions."""

    model_config = ConfigDict(extra="ignore")

    word: str
    start_frame: int
    end_frame: int


class VisualQuizRenderProps(BaseModel):
    """Props passed to Remotion VisualImageQuiz composition."""

    model_config = ConfigDict(extra="ignore")

    dataset: VisualQuizDataset
    fps: int = Field(default=60)
    width: int = Field(default=1080)
    height: int = Field(default=1920)
    total_duration_frames: int
    hook_end_frame: int
    timing_slots: list[VisualQuizTimingSlot]
    subtitles: list[dict[str, Any]] = Field(default_factory=list)
    audio_mix_path: str
    background_video_path: str | None = None
    background_music_path: str | None = None
    background_music_volume: float = 0.18
    banner_video_path: str | None = None
    banner_start_frame: int | None = None
    banner_duration_frames: int | None = None
    banner_height: int | None = None





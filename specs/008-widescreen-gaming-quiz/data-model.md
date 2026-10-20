# Data Model: 008-widescreen-gaming-quiz

**Feature Branch**: `008-widescreen-gaming-quiz`  
**Date**: 2026-10-20  
**Spec Reference**: [spec.md](spec.md)  
**Plan Reference**: [plan.md](plan.md)  

---

## 1. Domain Entities & Schemas

### 1.1 Enumerations

#### `AssetDisplayMode`
Specifies how the central asset container (`1200x600 px`) renders content for a round.
- `SCREENSHOT`: Standard gameplay screenshot or high-res graphic fitted inside 1140x540 px.
- `AUDIO_SFX`: Dark sound stage with pulsing cyan (#00E5FF) waveform while cue audio plays.
- `GAME_OVER`: Cropped or masked game over / death screen without spoiler text.
- `MINIMAP`: Circular radar display (`clip-path: circle()`) with tactical SVG HUD grid overlay.
- `SILHOUETTE`: High-contrast character silhouette (`filter: brightness(0)`) revealing color on answer hold.
- `CUSTOM`: User-defined layout or raw asset without procedural filters.

```python
class AssetDisplayMode(StrEnum):
    SCREENSHOT = "screenshot"
    AUDIO_SFX = "audio_sfx"
    GAME_OVER = "game_over"
    MINIMAP = "minimap"
    SILHOUETTE = "silhouette"
    CUSTOM = "custom"
```

---

### 1.2 Core Question Item: `WidescreenQuizItem`

Represents a single trivia question within a round.

| Field Name | Type | Validation / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `str` | Non-empty uuid/hash string | Unique identifier for item |
| `item_index` | `int` | `ge=1, le=50` | 1-based index within current round (e.g., 1–10) |
| `global_question_number` | `int` | `ge=1, le=100` | Monotonically increasing question number (e.g., 1–50) |
| `prompt_text` | `str` | `min_length=2, max_length=120` | Guiding question text displayed above asset |
| `answer_text` | `str` | `min_length=1, max_length=60` | Correct answer revealed at 6.0s mark |
| `asset_url` | `str \| None` | Valid URL format or None | Remote asset URL |
| `asset_path` | `str \| None` | Valid local path or None | Local resolved path (image or audio) |
| `asset_search_query` | `str` | `min_length=2, max_length=120` | Automated search query for media asset |
| `apply_procedural_mask` | `bool` | Default: `True` | Whether to apply CSS radar circle or silhouette |
| `is_approved` | `bool` | Default: `False` | Moderation approval status in verification UI |
| `difficulty_tag` | `str \| None` | e.g., "Easy", "Medium", "Hard" | Optional item-level difficulty badge |
| `audio_cue_duration_sec` | `float` | `ge=0.5, le=5.0`, Default: `4.0` | Maximum playback length for audio cue |

```python
class WidescreenQuizItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: secrets.token_hex(6))
    item_index: int = Field(..., ge=1, le=50, description="1-indexed question in round")
    global_question_number: int = Field(..., ge=1, le=100, description="1-indexed global question number")
    prompt_text: str = Field(..., min_length=2, max_length=120, description="Question prompt text")
    answer_text: str = Field(..., min_length=1, max_length=60, description="Correct answer text")
    asset_url: str | None = Field(default=None, description="Remote asset URL")
    asset_path: str | None = Field(default=None, description="Local asset path")
    asset_search_query: str = Field(..., min_length=2, max_length=120, description="Search query")
    apply_procedural_mask: bool = Field(default=True, description="Toggle procedural CSS mask")
    is_approved: bool = Field(default=False, description="Approval flag in UI")
    difficulty_tag: str | None = Field(default=None, description="Optional difficulty tag")
    audio_cue_duration_sec: float = Field(default=4.0, ge=0.5, le=5.0, description="Max cue duration in seconds")
```

---

### 1.3 Round Specification: `WidescreenQuizRound`

Encapsulates an entire round (default 10 questions) and its transition metadata.

| Field Name | Type | Validation / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `round_number` | `int` | `ge=1, le=20` | 1-based round sequence number |
| `round_title` | `str` | `min_length=2, max_length=50` | e.g. "ROUND 01: GUESS THE GAME" |
| `asset_mode` | `AssetDisplayMode` | Enum | Mode for asset container in this round |
| `pass_rate_statistic` | `str` | `min_length=2, max_length=40` | e.g. "94% OF PLAYERS PASS THIS ROUND" |
| `badge_theme_color` | `str` | Hex color string (e.g. `#00E5FF`) | Color accent for round badges & HUD |
| `splash_duration_sec` | `float` | `ge=2.0, le=6.0`, Default: `4.0` | Duration of inter-round splash stinger |
| `questions` | `list[WidescreenQuizItem]` | `min_length=1, max_length=30` | Ordered question items in this round |

```python
class WidescreenQuizRound(BaseModel):
    model_config = ConfigDict(extra="ignore")

    round_number: int = Field(..., ge=1, le=20)
    round_title: str = Field(..., min_length=2, max_length=50)
    asset_mode: AssetDisplayMode = Field(default=AssetDisplayMode.SCREENSHOT)
    pass_rate_statistic: str = Field(default="90% PASS RATE", min_length=2, max_length=40)
    badge_theme_color: str = Field(default="#00E5FF", pattern=r"^#[0-9a-fA-F]{6}$")
    splash_duration_sec: float = Field(default=4.0, ge=2.0, le=6.0)
    questions: list[WidescreenQuizItem] = Field(..., min_length=1, max_length=30)
```

---

### 1.4 Intro & Outro Configurations

#### `WidescreenIntroConfig`
| Field Name | Type | Validation / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `hook_tts` | `str` | `min_length=10, max_length=300` | Narration voice script for teaser |
| `duration_sec` | `float` | `ge=4.0, le=12.0`, Default: `8.0` | Intro hook duration |
| `challenge_title` | `str` | `min_length=3, max_length=80` | Large header text on intro card |

#### `WidescreenScoreTier`
| Field Name | Type | Validation / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `tier_name` | `str` | e.g. "Noob", "Gamer", "Pro", "God Tier" | Name of rank |
| `min_score` | `int` | `ge=0` | Minimum score threshold |
| `max_score` | `int` | `ge=min_score` | Maximum score threshold |
| `badge_color` | `str` | Hex color code | Color coding for rank pill |

#### `WidescreenOutroConfig`
| Field Name | Type | Validation / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `duration_sec` | `float` | `ge=10.0, le=25.0`, Default: `15.0` | Outro sequence duration |
| `outro_tts` | `str` | `min_length=10, max_length=400` | Closing voice script |
| `call_to_action` | `str` | `min_length=5, max_length=120` | e.g. "COMMENT YOUR SCORE & SUBSCRIBE!" |
| `score_tiers` | `list[WidescreenScoreTier]` | Exactly 4 tiers default | Ranking brackets |

```python
class WidescreenScoreTier(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tier_name: str = Field(..., min_length=2, max_length=30)
    min_score: int = Field(..., ge=0)
    max_score: int = Field(..., ge=0)
    badge_color: str = Field(default="#00E5FF", pattern=r"^#[0-9a-fA-F]{6}$")


class WidescreenIntroConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hook_tts: str = Field(..., min_length=10, max_length=300)
    duration_sec: float = Field(default=8.0, ge=4.0, le=12.0)
    challenge_title: str = Field(default="50 GAMING QUESTIONS CHALLENGE", min_length=3, max_length=80)


class WidescreenOutroConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    duration_sec: float = Field(default=15.0, ge=10.0, le=25.0)
    outro_tts: str = Field(..., min_length=10, max_length=400)
    call_to_action: str = Field(default="COMMENT YOUR SCORE & SUBSCRIBE!", min_length=5, max_length=120)
    score_tiers: list[WidescreenScoreTier] = Field(
        default_factory=lambda: [
            WidescreenScoreTier(tier_name="Noob", min_score=0, max_score=20, badge_color="#94A3B8"),
            WidescreenScoreTier(tier_name="Gamer", min_score=21, max_score=35, badge_color="#3B82F6"),
            WidescreenScoreTier(tier_name="Pro", min_score=36, max_score=45, badge_color="#8B5CF6"),
            WidescreenScoreTier(tier_name="God Tier", min_score=46, max_score=50, badge_color="#F59E0B"),
        ]
    )
```

---

### 1.5 Root Dataset: `WidescreenQuizDataset`

Root configuration model driving the complete 16:9 quiz generation.

| Field Name | Type | Validation / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `mode` | `Literal["widescreen_gaming_quiz"]` | Constant | Mode discriminator |
| `title` | `str` | `min_length=3, max_length=100` | Full show title |
| `language` | `str` | Pattern `^(ru\|en)$` | Quiz language |
| `guessing_duration_sec` | `float` | `ge=3.0, le=10.0`, Default: `6.0` | Countdown phase duration |
| `reveal_hold_duration_sec`| `float` | `ge=1.5, le=5.0`, Default: `3.0` | Answer reveal hold duration |
| `bgm_track_path` | `str \| None` | Valid path or None | Background music track |
| `bgm_ducking_volume` | `float` | `ge=0.05, le=0.5`, Default: `0.18` | BGM volume during ducking |
| `bgm_base_volume` | `float` | `ge=0.1, le=1.0`, Default: `0.30` | Normal BGM playback volume |
| `ambient_background_video`| `str \| None` | Valid path or None | Ambient blurred video loop |
| `intro` | `WidescreenIntroConfig` | Nested model | Intro teaser settings |
| `outro` | `WidescreenOutroConfig` | Nested model | Outro tier card settings |
| `rounds` | `list[WidescreenQuizRound]` | `min_length=1, max_length=10` | Ordered list of rounds |

```python
class WidescreenQuizDataset(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: Literal["widescreen_gaming_quiz"] = "widescreen_gaming_quiz"
    title: str = Field(default="Ultimate Gaming Quiz: 50 Questions", min_length=3, max_length=100)
    language: str = Field(default="ru", pattern=r"^(ru|en)$")
    guessing_duration_sec: float = Field(default=6.0, ge=3.0, le=10.0)
    reveal_hold_duration_sec: float = Field(default=3.0, ge=1.5, le=5.0)
    bgm_track_path: str | None = Field(default=None)
    bgm_ducking_volume: float = Field(default=0.18, ge=0.05, le=0.5)
    bgm_base_volume: float = Field(default=0.30, ge=0.1, le=1.0)
    ambient_background_video: str | None = Field(default=None)
    intro: WidescreenIntroConfig
    outro: WidescreenOutroConfig
    rounds: list[WidescreenQuizRound] = Field(..., min_length=1, max_length=10)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_questions_count(self) -> int:
        return sum(len(r.questions) for r in self.rounds)
```

---

### 1.6 Timing Coordinates: `WidescreenTimingSlot`

Frame-precise bounding points calculated by `@audio-service` for each question and splash in Remotion.

```python
class WidescreenTimingSlot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slot_type: Literal["intro", "splash", "question", "outro"]
    round_number: int | None = None
    question_global_number: int | None = None
    start_frame: int = Field(..., ge=0)
    duration_frames: int = Field(..., ge=1)
    end_frame: int = Field(..., ge=1)

    # Question specific markers (None if splash/intro/outro)
    timer_start_frame: int | None = None
    timer_duration_frames: int | None = None
    reveal_frame: int | None = None
    audio_cue_start_frame: int | None = None
    audio_cue_end_frame: int | None = None
```

---

### 1.7 Remotion Render Props: `WidescreenQuizRenderProps`

Contract serializable to JSON and fed directly into the Remotion CLI.

```python
class WidescreenQuizRenderProps(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dataset: WidescreenQuizDataset
    fps: int = Field(default=60)
    width: int = Field(default=1920)
    height: int = Field(default=1080)
    total_duration_frames: int
    timing_slots: list[WidescreenTimingSlot]
    audio_mix_path: str | None = None
    bgm_audio_path: str | None = None
    sfx_ticking_path: str
    sfx_chime_path: str
    sfx_stinger_path: str
    intro_tts_audio_path: str | None = None
    outro_tts_audio_path: str | None = None
    ambient_background_path: str | None = None
```

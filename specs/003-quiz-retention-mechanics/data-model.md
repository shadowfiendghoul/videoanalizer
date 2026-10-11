# Data Model: Quiz Retention Mechanics & Viral Features

**Feature ID**: `003-quiz-retention-mechanics`  
**Status**: Ready  
**Date**: 2026-10-11  

---

## 1. Domain Entities & Pydantic Contracts

### 1.1. `RankTierConfig` (Конфигурация шкалы рангов)
Определяет параметры отображения статуса зрителя на разных этапах квиза.

```python
class RankTierConfig(BaseModel):
    """Configuration for a specific rank status tier."""
    model_config = ConfigDict(extra="ignore")

    min_question: int = Field(..., ge=1, le=9, description="Starting question number (inclusive)")
    max_question: int = Field(..., ge=1, le=9, description="Ending question number (inclusive)")
    rank_title: str = Field(..., min_length=2, max_length=30, description="Name of the rank (e.g., 'NPC', 'Нормис')")
    rank_color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color theme for this rank tier")
    rank_icon: str = Field(..., min_length=1, max_length=10, description="Emoji or symbol icon (e.g. '🤡', '👑')")
    iq_label: str = Field(..., min_length=2, max_length=20, description="IQ label (e.g. 'IQ: 85', 'IQ: 160+')")
```

---

### 1.2. `StressTimerTier` (Конфигурация ускоряющегося стресс-таймера)
Определяет прогрессивное сжатие времени на размышление и аудиовизуальный накал страстей.

```python
class StressTimerTier(BaseModel):
    """Timing and style parameters for difficulty levels."""
    model_config = ConfigDict(extra="ignore")

    tier_level: str = Field(..., pattern=r"^(easy|medium|hard)$")
    think_duration_sec: float = Field(..., ge=1.0, le=4.0, description="Think window: 3.0s (easy), 2.5s (med), 1.8s (hard)")
    theme_color: str = Field(..., pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color for countdown pill")
    sfx_file: str = Field(..., description="SFX audio identifier/path (tick, stopwatch, heartbeat)")
    panic_vignette: bool = Field(default=False, description="Enable pulsing red vignette on screen edges")
```

---

### 1.3. `ComboStreakConfig` (Шкала комбо-стрика и огня)
Конфигурация отображения серии правильных ответов.

```python
class ComboStreakConfig(BaseModel):
    """Combo streak tracker configuration."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    fire_color_normal: str = Field(default="#FF4500", pattern=r"^#[0-9A-Fa-f]{6}$")
    fire_color_ultra: str = Field(default="#38BDF8", pattern=r"^#[0-9A-Fa-f]{6}$")
    ultra_threshold: int = Field(default=7, ge=3, le=9, description="Streak count triggering blue fire mode")
    sfx_pitch_step: float = Field(default=1.059463, ge=1.0, le=1.2, description="Pitch multiplier per streak step")
```

---

### 1.4. `CommentTrapConfig` (Байт на комментарии и дебаты)
Параметры провокации споров для взрывного роста Comment Velocity.

```python
class CommentTrapConfig(BaseModel):
    """Comment baiting and controversy outro trigger."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True)
    trap_question_number: int = Field(default=8, ge=6, le=9, description="Question containing a counter-intuitive fact")
    outro_challenge_text: str = Field(
        default="Если набрал 8+ — ты соврал. Пиши честный счет в комменты! 👇",
        min_length=10,
        max_length=150,
    )
    duration_frames: int = Field(default=90, ge=30, le=180, description="Duration in frames at 60fps (1.5s = 90 frames)")
```

---

### 1.5. `QuizRetentionConfig` (Мастер-конфигурация удержания)
Агрегирующая структура с тумблерами включения/отключения каждой вирусной механики.

```python
class QuizRetentionConfig(BaseModel):
    """Aggregate retention and virality configuration passed to Remotion."""
    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(default=True, description="Master toggle for retention mechanics")
    rank_bar_enabled: bool = Field(default=True)
    rank_tiers: list[RankTierConfig] = Field(default_factory=list)
    stress_timer_enabled: bool = Field(default=True)
    stress_tiers: list[StressTimerTier] = Field(default_factory=list)
    streak_fire: ComboStreakConfig = Field(default_factory=ComboStreakConfig)
    comment_trap: CommentTrapConfig = Field(default_factory=CommentTrapConfig)
    seamless_loop: bool = Field(default=True, description="Align intro and outro for infinite looping")
    anti_cheat_callout: bool = Field(default=True, description="Display '👀 Без паузы!' banner on Q9")
```

---

### 1.6. Расширение `RemotionRenderProps`
Обновленный контракт передачи параметров в Remotion CLI:

```python
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
```

---

## 2. Remotion TypeScript Data Contracts (`types.ts`)

```typescript
export interface RankTierConfig {
  min_question: number;
  max_question: number;
  rank_title: string;
  rank_color: string;
  rank_icon: string;
  iq_label: string;
}

export interface StressTimerTier {
  tier_level: 'easy' | 'medium' | 'hard';
  think_duration_sec: number;
  theme_color: string;
  sfx_file: string;
  panic_vignette: boolean;
}

export interface ComboStreakConfig {
  enabled: boolean;
  fire_color_normal: string;
  fire_color_ultra: string;
  ultra_threshold: number;
  sfx_pitch_step: number;
}

export interface CommentTrapConfig {
  enabled: boolean;
  trap_question_number: number;
  outro_challenge_text: string;
  duration_frames: number;
}

export interface QuizRetentionConfig {
  enabled: boolean;
  rank_bar_enabled: boolean;
  rank_tiers: RankTierConfig[];
  stress_timer_enabled: boolean;
  stress_tiers: StressTimerTier[];
  streak_fire: ComboStreakConfig;
  comment_trap: CommentTrapConfig;
  seamless_loop: boolean;
  anti_cheat_callout: boolean;
}

export interface RemotionRenderProps extends Record<string, unknown> {
  challenge: QuizChallenge;
  cue_sheet: AudioCueSheet;
  background_video_path: string;
  sfx_paths: SfxPaths;
  retention: QuizRetentionConfig;
  fps: number;
  width: number;
  height: number;
  banner_video_path?: string | null;
  banner_start_frame?: number | null;
  banner_duration_frames?: number | null;
}
```

---

## 3. Entity Relationships & Lifecycle

```
[FastAPI UI / Request]
         │
         ▼
[ScriptService] ──────────► [QuizChallenge (9 questions, length <= 65 chars)]
         │
         ▼
[AudioService] ───────────► [AudioCueSheet (Dynamic audio durations + blitz timers: 3.0/2.5/1.8s)]
         │
         ▼
[QuizOrchestrator] ───────► [Assembles RemotionRenderProps + QuizRetentionConfig]
         │
         ▼
[FIFO Render Queue] ──────► [asyncio.Semaphore(1) guarantees single Remotion process]
         │
         ▼
[Remotion CLI Render] ────► [Chromium (concurrency=3) renders React 9:16 comps]
         │
         ▼
[Final MP4 Output] (<= 50s total runtime, 1080x1920 60fps)
```

### Lifecycle States of a Render Job:
1. `pending`: Задача создана, ожидает валидации входных данных.
2. `queued`: Задача ожидает освобождения `asyncio.Semaphore(1)` (в очереди).
3. `generating_script`: Генерация вопросов в Gemini.
4. `synthesizing_audio`: Синтез голоса Edge-TTS и сборка `AudioCueSheet`.
5. `rendering_video`: Выполнение Remotion CLI с отображением прогресса кадров.
6. `completed`: Готовый MP4 файл сохранен в `outputs/`.
7. `failed`: Ошибка на любом этапе с записью понятной причины в ответ API.

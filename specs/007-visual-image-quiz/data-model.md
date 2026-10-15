# Data Model Specification: 007-visual-image-quiz

**Feature**: `007-visual-image-quiz`  
**Date**: 2026-10-15  
**Spec Reference**: [spec.md](spec.md)  
**Research Reference**: [research.md](research.md)  

---

## 1. Pydantic v2 Models (`videoanalizer/quiz/models.py`)

Все структуры данных строго типизированы и наследуются от `pydantic.BaseModel` с `extra = "forbid"`.

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class VisualDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MASTER = "master"

class VisualQuizItem(BaseModel):
    """Спецификация одного вопроса визуальной викторины."""
    id: int = Field(..., ge=1, le=10, description="Порядковый номер вопроса (1..10)")
    difficulty: VisualDifficulty = Field(..., description="Уровень сложности вопроса")
    answer_text: str = Field(..., min_length=1, max_length=50, description="Название предмета для левой лестницы")
    image_query: str = Field(..., min_length=3, max_length=120, description="Поисковый запрос для нахождения изображения")
    image_url: Optional[str] = Field(None, description="Прямой URL выбранного изображения")
    image_path: Optional[str] = Field(None, description="Локальный путь к скачанному кэшированному изображению")
    is_approved: bool = Field(False, description="Подтверждено ли изображение пользователем")
    prompt_tts: str = Field(..., min_length=3, max_length=100, description="Реплика диктора с вопросом")
    answer_tts: str = Field(..., min_length=3, max_length=120, description="Реплика диктора с ответом или призывом писать в коммы")

class VisualQuizInterstitialType(str, Enum):
    COMMENT_BAIT = "comment_bait"
    SHARE_BAIT = "share_bait"

class VisualQuizInterstitial(BaseModel):
    """Описание вовлекающей вставки между раундами."""
    after_question: int = Field(..., ge=1, le=9, description="Номер вопроса, после которого показывается вставка (3 или 6)")
    type: VisualQuizInterstitialType = Field(..., description="Тип активности (комментарии или репост)")
    tts_text: str = Field(..., min_length=5, max_length=120, description="Голосовой призыв диктора")
    duration_sec: float = Field(2.0, ge=1.0, le=4.0, description="Длительность показа вставки в секундах")

class VisualQuizDataset(BaseModel):
    """Полный сценарий визуальной викторины."""
    mode: str = Field("visual_image_quiz", pattern="^visual_image_quiz$", description="Режим викторины")
    theme: str = Field(..., min_length=2, max_length=80, description="Название темы викторины")
    hook_tts: str = Field(..., min_length=10, max_length=200, description="Интригующая интро-реплика диктора")
    rapid_flip_duration_ms: int = Field(120, ge=80, le=200, description="Интервал смены картинок в интро (мс)")
    timer_duration_sec: float = Field(2.0, ge=1.5, le=3.0, description="Длительность синхронного таймера вопроса (сек)")
    items: List[VisualQuizItem] = Field(..., min_length=10, max_length=10, description="Ровно 10 вопросов викторины")
    interstitials: List[VisualQuizInterstitial] = Field(default_factory=list, description="Список вовлекающих вставок")

class VisualQuizTimingSlot(BaseModel):
    """Таймкоды отдельного раунда вопроса для Remotion."""
    question_id: int
    start_frame: int
    prompt_audio_start_frame: int
    timer_start_frame: int
    timer_duration_frames: int
    answer_audio_start_frame: int
    reveal_frame: int
    end_frame: int

class VisualQuizRenderProps(BaseModel):
    """Входные данные для Remotion-композиции VisualImageQuiz."""
    dataset: VisualQuizDataset
    fps: int = Field(60, ge=30, le=60)
    width: int = Field(1080)
    height: int = Field(1920)
    total_duration_frames: int = Field(..., ge=600)
    hook_end_frame: int = Field(..., ge=120)
    timing_slots: List[VisualQuizTimingSlot]
    subtitles: List[dict] = Field(default_factory=list, description="Пословные караоке-метки со временем старта и окончания")
    audio_mix_path: str = Field(..., description="Относительный или публичный путь к итоговому мастер-аудиофайлу")
    background_video_path: Optional[str] = Field(None, description="Путь к фоновому видеоряду")
```

---

## 2. Валидационные правила и инварианты

1. **Количество вопросов**: Ровно 10 (`len(items) == 10`).
2. **Распределение сложности**:
   - `items[0..2]`: `VisualDifficulty.EASY`
   - `items[3..5]`: `VisualDifficulty.MEDIUM`
   - `items[6..8]`: `VisualDifficulty.HARD`
   - `items[9]`: `VisualDifficulty.MASTER`
3. **Вопрос №1**: `items[0].prompt_tts` не должен начинаться с фраз «Вопрос номер один» или «Вопрос 1».
4. **Вопрос №10 (Клиффхэнгер)**:
   - `items[9].answer_text` строго равен `"Пиши в коммы"`.
   - `items[9].answer_tts` призывает зрителей писать свои ответы в комментариях.
5. **Безопасная зона**: Текстовые оверлеи в Remotion не выходят за пределы `y: 1520px` (снизу) и `x: 960px` (справа).

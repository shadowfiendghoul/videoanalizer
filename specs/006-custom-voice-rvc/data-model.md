# Data Model: 006-custom-voice-rvc

Данный документ описывает Pydantic v2 модели данных и строгие типизированные контракты для голосового модуля (Voice Pipeline & Voice Cloning).

---

## 1. Перечисления (Enums)

### 1.1 `VoiceMode`
Режим генерации аудиопотока.

```python
from enum import StrEnum

class VoiceMode(StrEnum):
    EDGE_TTS = "edge_tts"
    CUSTOM_RVC = "custom_rvc"
    OFFLINE_FALLBACK = "offline_fallback"
```

### 1.2 `RvcPitchMethod`
Алгоритм извлечения высоты основного тона (F0) для RVC инференса.

```python
class RvcPitchMethod(StrEnum):
    RMVPE = "rmvpe"      # Рекомендуемый: высокое качество, малый вес
    PM = "pm"            # Максимально быстрый на CPU
    HARVEST = "harvest"  # Традиционный точный, но тяжелый
```

---

## 2. Модели Конфигурации (Configuration Schemas)

### 2.1 `VoiceConfig`
Параметры голосового конвейера для викторин и видеороликов.

```python
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field

class VoiceConfig(BaseModel):
    voice_mode: VoiceMode = Field(
        default=VoiceMode.EDGE_TTS,
        description="Режим синтеза: edge_tts, custom_rvc или offline_fallback"
    )
    base_voice: str = Field(
        default="ru-RU-DmitryNeural",
        description="Имя базового нейросетевого диктора Edge-TTS для дикции и таймингов"
    )
    rvc_model_path: str | None = Field(
        default=None,
        max_length=255,
        description="Относительный или абсолютный путь к файлу чекпоинта .pth"
    )
    rvc_index_path: str | None = Field(
        default=None,
        max_length=255,
        description="Опциональный путь к файлу индекса фич .index"
    )
    pitch_shift: int = Field(
        default=0,
        ge=-12,
        le=12,
        description="Сдвиг тона в полутонах (-12..+12). 0 - без изменений, +12 - на октаву выше"
    )
    speech_rate: float = Field(
        default=1.15,
        ge=0.8,
        le=1.5,
        description="Множитель темпа речи (1.0 = нормальный, 1.15 = +15% для Shorts)"
    )
    pitch_method: RvcPitchMethod = Field(
        default=RvcPitchMethod.RMVPE,
        description="Алгоритм извлечения F0 основного тона"
    )
    device: Literal["auto", "cuda", "cpu"] = Field(
        default="auto",
        description="Целевое вычислительное устройство для инференса"
    )
```

---

## 3. Реестр Моделей (Model Registry Schemas)

### 3.1 `RvcModelInfo`
Метаданные обнаруженной модели клонирования в каталоге `assets/models/rvc/`.

```python
class RvcModelInfo(BaseModel):
    model_id: str = Field(..., description="Уникальный идентификатор модели (stem имени файла)")
    name: str = Field(..., description="Отображаемое человекочитаемое имя модели")
    file_path: str = Field(..., description="Относительный путь к файлу .pth")
    index_path: str | None = Field(default=None, description="Путь к сопутствующему .index (если найден)")
    file_size_bytes: int = Field(..., ge=0, description="Размер файла модели на диске")
    is_valid: bool = Field(default=True, description="Флаг валидности чекпоинта")
```

### 3.2 `RvcModelListResponse`
Список доступных для выбора моделей клонирования.

```python
class RvcModelListResponse(BaseModel):
    models: list[RvcModelInfo] = Field(default_factory=list)
    active_model_id: str | None = Field(default=None)
    total_count: int = Field(default=0)
```

---

## 4. Данные Синхронизации и Синтеза (Synthesis & Cue Schemas)

### 4.1 `WordTiming`
Пословный тайминг для анимации караоке-субтитров.

```python
class WordTiming(BaseModel):
    word: str = Field(..., description="Текст произнесенного слова")
    start_ms: int = Field(..., ge=0, description="Время старта произношения в мс")
    end_ms: int = Field(..., ge=0, description="Время завершения слова в мс")

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)
```

### 4.2 `SynthesizedSpeechResult`
Результат полного цикла синтеза и тембральной конверсии.

```python
class SynthesizedSpeechResult(BaseModel):
    audio_path: str = Field(..., description="Путь к итоговому нормализованному WAV/MP3 аудиофайлу")
    duration_ms: int = Field(..., ge=0, description="Полная измеренная длительность аудио в мс")
    words: list[WordTiming] = Field(default_factory=list, description="Список пословных меток")
    voice_mode_used: VoiceMode = Field(..., description="Фактический примененный режим генерации")
    model_name: str | None = Field(default=None, description="Имя использованной модели RVC (если был клонирован)")
```

### 4.3 `VoicePreviewRequest` & `VoicePreviewResponse`
Схемы для тестового прослушивания голоса в веб-интерфейсе.

```python
class VoicePreviewRequest(BaseModel):
    text: str = Field(
        default="Привет! Это проверка моего нового кастомного голоса для викторин.",
        max_length=200,
        description="Тестовая фраза для синтеза"
    )
    config: VoiceConfig = Field(..., description="Настройки голоса для тестирования")

class VoicePreviewResponse(BaseModel):
    audio_url: str = Field(..., description="URL для воспроизведения аудиофрагмента в плеере")
    duration_ms: int = Field(..., ge=0, description="Длительность фразы в мс")
    voice_mode_used: VoiceMode = Field(...)
```

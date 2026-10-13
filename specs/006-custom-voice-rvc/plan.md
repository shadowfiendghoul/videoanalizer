# Implementation Plan: 006-custom-voice-rvc

**Branch**: `006-custom-voice-rvc` | **Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-custom-voice-rvc/spec.md`

---

## Summary

Реализация высокопроизводительного гибридного голосового модуля (`Voice Pipeline & Voice Cloning`) для генерации видеороликов и викторин. Модуль объединяет:
1. Мгновенный синтез эталонной дикции и точных пословных меток (`WordBoundary`) через `edge-tts` (голос `ru-RU-DmitryNeural`).
2. Быструю замену тембра на кастомный авторский голос через локальный RVC (Retrieval-based Voice Conversion) инференс с подстановкой чекпоинтов `.pth` из `assets/models/rvc/` и настройкой сдвига тона `pitch_shift` (-12..+12).
3. Многоуровневый автоматический офлайн-резерв (`offline_fallback`) при недоступности внешних сервисов.
4. Полную синхронизацию длительности аудио и пословных таймингов для анимированных караоке-субтитров Remotion.

---

## Technical Context

**Language/Version**: Python 3.11+ (типизация с Pydantic v2, `asyncio`, `pathlib.Path`).  
**Primary Dependencies**:
- `edge-tts`: асинхронный синтез речи и извлечение пословных меток `WordBoundary`.
- `torch` / `onnxruntime` / `rvc-python`: легковесный инференс RVC модели.
- `ffmpeg` / `ffprobe`: нормализация аудио (16-bit PCM WAV, 44.1/48 kHz), изменение частоты дискретизации.
- `pydantic` v2 & `pydantic-settings`: строгие схемы конфигурации и валидации контрактов.
- `fastapi`: эндпоинты реестра моделей и предпросмотра голоса.

**Storage**:
- Директория моделей: `assets/models/rvc/` (файлы `*.pth` и сопутствующие `*.index`).
- Временная рабочая область: изолированные временные директории под управлением контекстного менеджера `QuizWorkspace`.

**Testing**: `pytest`, `pytest-asyncio`, синтетические моки без обязательного наличия весов RVC в CI.  
**Target Platform**: Windows 10/11, Linux (Ubuntu), macOS; с поддержкой аппаратного ускорения NVIDIA CUDA и автоматическим CPU-фоллбэком.  
**Project Type**: Модульный сервис в составе десктопного веб-приложения VideoAnalyzer.  
**Performance Goals**:
- Синтез 60 секунд речи в режиме `custom_rvc`: < 8 секунд на GPU CUDA, < 25 секунд на CPU.
- Потребление видеопамяти при RVC инференсе: < 2.0 ГБ VRAM.  
**Constraints**:
- Расхождение между звуком и караоке-субтитрами: не более 50 мс по всей длине ролика.
- 100% изоляция сбоев: при отсутствии модели или интернета ролик не падает, а собирается в резервном режиме.  
**Scale/Scope**: Пакетная очередь до 20 роликов подряд, поддержка неограниченного числа пользовательских чекпоинтов голосов.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I: Strict Type Safety & Pydantic Data Contracts**  
  *Status*: **PASS**  
  Все конфигурации и структуры данных строго типизированы: `VoiceConfig`, `VoiceMode`, `RvcModelInfo`, `WordTiming`, `SynthesizedSpeechResult`. Входные параметры валидируются до запуска инференса.
- **Principle II: Declarative Motion Rendering & Media Processing**  
  *Status*: **PASS**  
  Аудиофайлы генерируются во временном каталоге сессии и монтируются в `public/audio/`. Временные чанки удаляются при завершении задачи. Длительность дорожек строго синхронизирована с `duration_in_frames` Remotion.
- **Principle III: Asynchronous & Resilient AI Engine**  
  *Status*: **PASS**  
  Сетевой синтез Edge-TTS изолирован с экспоненциальным бэкоффом и тайм-аутами.
- **Principle IV: Isolated Testing & Contract Verification**  
  *Status*: **PASS**  
  Инференс RVC и внешние вызовы Edge-TTS изолированы за абстракциями и снабжаются детерминированными моками для автоматического тестирования без тяжелых бинарных моделей в репозитории.
- **Principle V: Decoupled Sub-Service Boundaries**  
  *Status*: **PASS**  
  Сервис `VoiceService` изолирован в доменной области `@audio-service`. Он не имеет прямых связей с логикой генерации вопросов (`@script-service`) или шаблонами React (`@template-engine`).

---

## Project Structure

### Documentation (this feature)

```text
specs/006-custom-voice-rvc/
├── spec.md              # Спецификация требований и пользовательских историй
├── plan.md              # Настоящий план реализации архитектуры
├── research.md          # Исследования и технические обоснования (Phase 0)
├── data-model.md        # Pydantic v2 модели и схемы данных (Phase 1)
├── quickstart.md        # Пошаговое руководство по сквозному тестированию (Phase 1)
├── contracts/           # Спецификации интерфейсов API (OpenAPI JSON) (Phase 1)
│   └── voice_api.json
├── checklists/
│   └── requirements.md
└── tasks.md             # Пошаговый граф задач реализации (Phase 2, /speckit-tasks)
```

### Source Code (repository root)

```text
videoanalizer/
├── quiz/
│   ├── models.py               # [EXTEND] Добавление схем VoiceConfig, VoiceMode, RvcModelInfo
│   ├── voice_service.py        # [NEW] Сервис синтеза и тембральной конверсии VoiceService
│   ├── rvc_engine.py           # [NEW] Локальный движок инференса RvcInferenceEngine (CUDA/CPU)
│   ├── audio_service.py        # [MODIFY] Интеграция VoiceService в процесс сборки AudioCueSheet
│   └── orchestrator.py         # [MODIFY] Проброс VoiceConfig в QuizOrchestrator.generate()
├── api/
│   └── routes_quiz.py          # [EXTEND] Новые REST эндпоинты /api/v1/voice/models и /preview
└── ui/
    └── templates/
        └── quiz.html           # [EXTEND] UI селектор кастомного голоса, слайдер pitch_shift, предпросмотр

assets/
└── models/
    └── rvc/                    # [NEW] Каталог для пользовательских .pth моделей голосов

tests/
└── unit/
    └── quiz/
        ├── test_voice_service.py # [NEW] Модульные тесты VoiceService и 3 режимов
        └── test_rvc_engine.py    # [NEW] Тесты RvcInferenceEngine (с моками и реальными вызовами)
```

**Structure Decision**:  
Расширение существующего пакета `videoanalizer.quiz` с выделением двух специализированных модулей:
1. `videoanalizer/quiz/voice_service.py` — координатор 3 режимов синтеза (`edge_tts`, `custom_rvc`, `offline_fallback`) и сборщик таймингов.
2. `videoanalizer/quiz/rvc_engine.py` — изолированный модуль инференса нейросетевой конверсии тембра.  
Это сохраняет архитектурную чистоту и модульность без утяжеления базового `AudioService`.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Введение гибридного двухэтапного конвейера вместо единой TTS-модели | RVC заменяет тембр за 1-2 сек, но не умеет генерировать дикцию из текста; Edge-TTS даёт идеальную русскую дикцию и точные пословные метки караоке | Прямой синтез через XTTS v2 занимает 40-60 с на фразу, перегружает VRAM и не даёт пословных меток для Remotion |
| Выделение отдельного `rvc_engine.py` | Изолирует работу с весами PyTorch/ONNX и CUDA от остального кода генератора | Размещение инференса внутри `audio_service.py` привело бы к раздуванию файла (сейчас 670 строк) и смешению SFX логики с нейросетевым инференсом |

# Tasks: 006-custom-voice-rvc

**Feature Branch**: `006-custom-voice-rvc`  
**Input**: Design artifacts from `specs/006-custom-voice-rvc/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Подготовка файловой структуры и системных зависимостей

- [ ] T001 Create RVC model directory structure in `assets/models/rvc/` and add `.gitkeep`
- [ ] T002 Verify audio and speech processing dependencies (`edge-tts`, `soundfile`, `numpy`) in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Базовые схемы данных и тестовые фикстуры, необходимые для всех пользовательских историй

**⚠️ CRITICAL**: Реализация пользовательских историй не может начаться до завершения этой фазы

- [ ] T003 [P] Implement core voice schemas (`VoiceMode`, `VoiceConfig`, `RvcModelInfo`, `WordTiming`, `SynthesizedSpeechResult`, `VoicePreviewRequest`, `VoicePreviewResponse`) with Pydantic v2 validation in `videoanalizer/quiz/models.py`
- [ ] T004 [P] Implement RVC model scanner utility (`RvcModelRegistry.discover_models()`) in `videoanalizer/quiz/voice_service.py` to scan `assets/models/rvc/` for `*.pth` and `*.index`
- [ ] T005 Create base unit test fixtures and synthetic mocks for voice synthesis and RVC models in `tests/unit/quiz/test_voice_service.py`

**Checkpoint**: Базовые модели и утилиты готовы — начинается реализация пользовательских историй

---

## Phase 3: User Story 1 - Стандартный синтез речи с пословными таймингами (Edge-TTS Only) (Priority: P1) 🎯 MVP

**Goal**: Быстрый синтез дикторского звука через `ru-RU-DmitryNeural` с извлечением точных пословных меток `WordBoundary` и масштабированием под `speech_rate`.

**Independent Test**: Передача контрольного текста возвращает валидный WAV-файл и список `WordTiming`, совпадающий по суммарной длительности со звуком (`pytest tests/unit/quiz/test_voice_service.py -k test_edge_tts`).

### Implementation for User Story 1

- [ ] T006 [P] [US1] Write unit tests for `VoiceService` in `edge_tts` mode with word timing extraction in `tests/unit/quiz/test_voice_service.py`
- [ ] T007 [US1] Implement `VoiceService._synthesize_edge_tts()` with `WordBoundary` event capture, rate scaling (`speech_rate`), and format normalization in `videoanalizer/quiz/voice_service.py`
- [ ] T008 [US1] Integrate `VoiceService` into `AudioService.synthesize_speech_with_cues()` in `videoanalizer/quiz/audio_service.py`
- [ ] T009 [US1] Verify end-to-end question cue sheet and intro audio synthesis with `VoiceService` in `videoanalizer/quiz/audio_service.py`

**Checkpoint**: User Story 1 (MVP) полностью работоспособна, протестирована и обеспечивает качественную озвучку с караоке-таймингами.

---

## Phase 4: User Story 2 - Клонирование голоса автора через гибридный конвейер RVC (Priority: P1)

**Goal**: Моментальная замена тембра диктора на кастомный голос из чекпоинта `.pth` с сохранением длительности и пословных таймингов караоке-субтитров.

**Independent Test**: Обработка аудио через RVC возвращает файл с целевым тембром, длительность которого совпадает с исходной (погрешность < 50 мс), а `WordTiming` остаются валидными (`pytest tests/unit/quiz/test_rvc_engine.py`).

### Implementation for User Story 2

- [ ] T010 [P] [US2] Write unit tests for `RvcInferenceEngine` (validating pitch_shift -12..+12, missing model fallback, audio normalization) in `tests/unit/quiz/test_rvc_engine.py`
- [ ] T011 [US2] Implement `RvcInferenceEngine` in `videoanalizer/quiz/rvc_engine.py` supporting `RMVPE`/`PM` pitch extraction, CUDA/CPU device selection, and graceful fallback on missing `.pth`
- [ ] T012 [US2] Implement `VoiceService._convert_rvc()` in `videoanalizer/quiz/voice_service.py` connecting Edge-TTS output to `RvcInferenceEngine` with timing alignment
- [ ] T013 [US2] Integrate custom voice cloning into `QuizOrchestrator.generate()` in `videoanalizer/quiz/orchestrator.py`
- [ ] T014 [US2] Add integration test for complete quiz generation with `custom_rvc` mode in `tests/unit/quiz/test_orchestrator.py`

**Checkpoint**: User Story 1 и User Story 2 функционируют независимо и в связке.

---

## Phase 5: User Story 3 - Тихий офлайн-резерв при недоступности внешних сервисов (Priority: P2)

**Goal**: Бесшовное автоматическое переключение на локальный синтез речи при отсутствии интернета или сбое внешних сервисов без остановки видеогенератора.

**Independent Test**: Синтез речи при симулированном отключении сети успешно завершается через резервный движок (`pytest tests/unit/quiz/test_voice_service.py -k test_offline_fallback`).

### Implementation for User Story 3

- [ ] T015 [P] [US3] Write unit tests for multi-tier offline fallback in `tests/unit/quiz/test_voice_service.py`
- [ ] T016 [US3] Implement `VoiceService._synthesize_offline_fallback()` with Piper TTS / SAPI5 / synthetic wav fallback in `videoanalizer/quiz/voice_service.py`
- [ ] T017 [US3] Implement automatic silent error-catching and degradation ladder (`custom_rvc` -> `edge_tts` -> `offline_fallback`) in `videoanalizer/quiz/voice_service.py`

**Checkpoint**: Система полностью отказоустойчива к сетевым сбоям и отсутствию моделей.

---

## Phase 6: User Story 4 - Конфигурация параметров голоса и предпросмотр в интерфейсе (Priority: P3)

**Goal**: Управление параметрами голоса через REST API и элементы веб-интерфейса (селектор режима, выбор модели, слайдер сдвига тона, кнопка предпросмотра аудио).

**Independent Test**: Запрос к `POST /api/v1/voice/preview` возвращает валидный URL аудиофрагмента, а `GET /api/v1/voice/models` отдаёт список обнаруженных файлов `.pth`.

### Implementation for User Story 4

- [ ] T018 [P] [US4] Implement REST API endpoints `GET /api/v1/voice/models`, `POST /api/v1/voice/preview`, and `GET /api/v1/voice/preview/audio/{preview_id}` in `videoanalizer/api/routes_quiz.py`
- [ ] T019 [P] [US4] Write contract tests for voice endpoints in `tests/unit/quiz/test_api_routes.py`
- [ ] T020 [US4] Add UI controls in `videoanalizer/ui/templates/quiz.html` for Voice Mode selection, RVC model dropdown, Pitch Shift slider (-12..+12), and audio preview button
- [ ] T021 [US4] Connect UI voice settings to single generation and batch queue requests in `videoanalizer/ui/templates/quiz.html`

**Checkpoint**: Все 4 пользовательские истории полностью интегрированы в GUI и API.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Финальная валидация, тестирование качества и документация

- [ ] T022 [P] Validate entire test suite (`pytest tests/unit/ -v`) ensuring 100% test pass rate
- [ ] T023 [P] Run Ruff linter and formatter on all modified files (`ruff check videoanalizer/ tests/`)
- [ ] T024 Execute validation scenarios from `specs/006-custom-voice-rvc/quickstart.md`
- [ ] T025 Update documentation and `walkthrough.md` with voice pipeline and cloning capabilities

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Без зависимостей — можно запускать немедленно.
- **Foundational (Phase 2)**: Зависит от Phase 1 — БЛОКИРУЕТ все пользовательские истории.
- **User Stories (Phase 3+)**: Зависят от Phase 2.
  - Phase 3 (US1 - MVP): Базовый синтез Edge-TTS.
  - Phase 4 (US2): RVC тембральное клонирование (расширяет базовый синтез US1).
  - Phase 5 (US3): Офлайн-резерв (дополняет лестницу деградации).
  - Phase 6 (US4): REST API и GUI (визуализирует и предоставляет управление).
- **Polish (Phase 7)**: Зависит от завершения историй.

### Parallel Opportunities

- Задачи с меткой `[P]` внутри одной фазы выполняются параллельно:
  - Phase 2: `T003` (Pydantic schemas) и `T004` (Model scanner) независимы.
  - Phase 3: `T006` (Tests) может писаться параллельно.
  - Phase 4: `T010` (RVC Tests) и каркас `T011` (RVC Engine) изолированы.
  - Phase 6: `T018` (Backend routes) и `T020` (Frontend HTML) могут разрабатываться параллельно.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Выполнить Phase 1 (Setup) и Phase 2 (Foundational).
2. Реализовать Phase 3 (User Story 1 - Edge-TTS с пословными таймингами).
3. Проверить базовый синтез и караоке-тайминги. Это полноценный рабочий MVP.

### Incremental Delivery
1. MVP: Стандартная чистая дикция Edge-TTS + субтитры (US1).
2. Инкремент 2: Добавление тембрального RVC инференса для авторских голосов (US2).
3. Инкремент 3: Добавление офлайн-резерва (US3).
4. Инкремент 4: Веб-интерфейс и предпросмотр аудио в UI (US4).
5. Инкремент 5: Полировка, прогон всех 90+ тестов, линтинг (Phase 7).

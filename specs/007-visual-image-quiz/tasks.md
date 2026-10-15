# Tasks: 007-visual-image-quiz

**Feature**: `007-visual-image-quiz`  
**Date**: 2026-10-15  
**Spec Reference**: [spec.md](spec.md)  
**Plan Reference**: [plan.md](plan.md)  
**Data Model**: [data-model.md](data-model.md)  
**Contracts**: [contracts/visual_quiz_api.json](contracts/visual_quiz_api.json)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Подготовка базовых контрактов, структур и TypeScript типов для нового режима викторины.

- [X] T001 Добавить TypeScript интерфейсы `VisualQuizItem`, `VisualQuizDataset`, `VisualQuizTimingSlot`, `VisualQuizRenderProps` в `templates/quiz-remotion/src/types.ts`
- [X] T002 [P] Зарегистрировать новую Remotion-композицию `VisualImageQuiz` (1080x1920, 60fps) в `templates/quiz-remotion/src/Root.tsx`
- [X] T003 [P] Создать модульные тестовые файлы-заготовки `tests/unit/quiz/test_visual_quiz_script.py` и `tests/unit/quiz/test_visual_quiz_audio.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Базовые модели Pydantic v2 и оркестрация, блокирующие реализацию пользовательских историй.

- [X] T004 Реализовать Pydantic v2 модели `VisualDifficulty`, `VisualQuizItem`, `VisualQuizInterstitial`, `VisualQuizDataset`, `VisualQuizRenderProps` со строгой валидацией в `videoanalizer/quiz/models.py`
- [X] T005 [P] Создать синтетические фикстуры датасета `sample_visual_quiz_dataset` для тестов в `tests/unit/quiz/test_visual_quiz_script.py`
- [X] T006 Добавить обработку режима `visual_image_quiz` в базовый пайплайн сборки `QuizOrchestrator` в `videoanalizer/quiz/orchestrator.py`

**Checkpoint**: Базовые структуры данных и скелет Remotion готовы — можно приступать к пользовательским историям.

---

## Phase 3: User Story 1 - Генерация сценария и подбор ассетов для произвольной темы (Priority: P1) 🎯 MVP

**Goal**: Генерация сценария из 10 вопросов для произвольной темы через Gemini REST API, автопоиск картинок и ручное утверждение в UI.

**Independent Test**: Запуск сценария генерации для темы "Ретро-автомобили" возвращает валидный `VisualQuizDataset` с 10 предметами, поисковыми запросами и превью картинок.

### Tests for User Story 1

- [X] T007 [P] [US1] Написать unit-тесты генерации визуального сценария и валидации схемы в `tests/unit/quiz/test_visual_quiz_script.py`

### Implementation for User Story 1

- [X] T008 [US1] Реализовать промпт генерации произвольной темы и метод `generate_visual_quiz_dataset()` в `videoanalizer/quiz/script_service.py`
- [X] T009 [US1] Реализовать автопоиск изображений по `image_query` через существующий DuckDuckGo модуль в `videoanalizer/quiz/script_service.py`
- [X] T010 [US1] Создать REST-эндпоинт `POST /api/v1/quiz/visual/generate` в `videoanalizer/api/routes_quiz.py`
- [X] T011 [US1] Добавить в веб-интерфейс `videoanalizer/ui/templates/quiz.html` блок выбора режима "Visual Image Quiz" и плитку предпросмотра 10 картинок с кнопками утверждения/смены

**Checkpoint**: Пользователь может сгенерировать викторину на любую тему и утвердить картинки в UI.

---

## Phase 4: User Story 2 - Динамичный визуальный хук интро с быстрым флипом (Priority: P1)

**Goal**: Быстрое циклическое перелистывание 10 картинок в центральной точке (`x: 780, y: 450`) за 0:00–0:03.5s под Rapid Flip SFX.

**Independent Test**: Рендер интро-композиции подтверждает смену текстур каждые 120 мс в единых координатах бокса без видимости левой лестницы.

### Implementation for User Story 2

- [X] T012 [P] [US2] Создать компонент `RapidCenterFlip.tsx` с циклической сменой картинок в координатах `x: 780, y: 450` (380x380 px) в `templates/quiz-remotion/src/components/RapidCenterFlip.tsx`
- [X] T013 [US2] Реализовать генерацию аудиодорожки интро `hook_tts` с наложением циклического `card_flip_rapid.wav` (-4 dB) в `videoanalizer/quiz/audio_service.py`
- [X] T014 [US2] Интегрировать `RapidCenterFlip` в главную композицию `templates/quiz-remotion/src/VisualImageQuiz.tsx` со скрытием левой панели при `frame < hookEndFrame`

**Checkpoint**: Первые 3.5 секунды ролика воспроизводят мощный визуальный калейдоскоп с щелкающим звуком перелистывания.

---

## Phase 5: User Story 3 - Геймплей с прогрессивной лестницей и таймером (Priority: P1)

**Goal**: Показ вопросов Q1–Q10 с пружинящим эффектом картинки, 4-уровневой лестницей сложности, быстрым синхронным таймером (1.5–2.0 сек) и пословными караоке-субтитрами.

**Independent Test**: Прогон вопросов Q1–Q9 подтверждает синхронный таймер, появление карточки пружиной (`scale 0 -> 1.1 -> 1.0`), открытие ответа после звука Ding и караоке-субтитры в слоте `y: 1420..1500`.

### Tests for User Story 3

- [X] T015 [P] [US3] Написать unit-тесты сборщика таймингов вопросов и пословных меток в `tests/unit/quiz/test_visual_quiz_audio.py`

### Implementation for User Story 3

- [X] T016 [P] [US3] Создать компонент `SpringImageCard.tsx` с анимацией `scale 0 -> 1.1 -> 1.0` за 200 мс в `templates/quiz-remotion/src/components/SpringImageCard.tsx`
- [X] T017 [P] [US3] Создать компонент `ProgressiveLadder.tsx` с 4 блоками («Лёгкий», «Средний», «Эксперт», «Мастер / Финал») и отложенным показом ответов в `templates/quiz-remotion/src/components/ProgressiveLadder.tsx`
- [X] T018 [P] [US3] Создать компонент `SyncHorizontalTimer.tsx` на позиции `y: 1350` (850 px) с градиентным переходом цвета в `templates/quiz-remotion/src/components/SyncHorizontalTimer.tsx`
- [X] T019 [US3] Реализовать метод сборки аудиоряда раундов `build_visual_quiz_audio()` с синхронным таймером и звуками Ding в `videoanalizer/quiz/audio_service.py`
- [X] T020 [US3] Разместить компонент `KaraokeCaptions.tsx` в слоте `y: 1420..1500` в `templates/quiz-remotion/src/VisualImageQuiz.tsx`

**Checkpoint**: Полный игровой процесс от Q1 до Q9 функционирует с лестницей уровней, таймером и субтитрами.

---

## Phase 6: User Story 4 - Интерстишлы вовлечения и финальная коммент-ловушка Q10 (Priority: P2)

**Goal**: Показ стикера комментариев после Q3, стрелки репоста после Q6 и удержание интриги на Q10 (сокрытие ответа с текстом «10. Пиши в коммы» под клиффхэнгер SFX).

**Independent Test**: На таймлайне после Q3 отображается плашка комментариев, после Q6 — стрелка репоста, а на Q10 ответ диктором не озвучивается и отображается плашка «Пиши в коммы».

### Implementation for User Story 4

- [X] T021 [P] [US4] Создать анимированный оверлей `EngagementOverlay.tsx` для плашки комментариев и стрелки репоста в `templates/quiz-remotion/src/components/EngagementOverlay.tsx`
- [X] T022 [US4] Добавить логику клиффхэнгера Q10: сокрытие правильного ответа, подстановка «Пиши в коммы» и SFX барабанной дроби в `videoanalizer/quiz/audio_service.py`
- [X] T023 [US4] Интегрировать вовлекающие интерстишлы и оверлей финала в `templates/quiz-remotion/src/VisualImageQuiz.tsx`

**Checkpoint**: Ролик максимизирует виральные метрики (комментарии, репосты) и завершается интригующим клиффхэнгером.

---

## Phase 7: User Story 5 - Параметризация стилей, темпа речи и сквозной рендер (Priority: P3)

**Goal**: Настройка скорости диктора, длительности флипа, уровней громкости аудиомикса и запуск рендера из UI и CLI.

**Independent Test**: Запуск сквозного рендера создает валидный MP4-видеофайл 1080x1920 60fps длительностью 45–55 секунд с идеальной синхронизацией звука.

### Implementation for User Story 5

- [X] T024 [P] [US5] Реализовать метод рендера `render_visual_quiz()` в `videoanalizer/quiz/orchestrator.py`
- [X] T025 [US5] Создать REST-эндпоинт `POST /api/v1/quiz/visual/render` в `videoanalizer/api/routes_quiz.py`
- [X] T026 [US5] Добавить кнопку запуска рендера и плеер готового видео в `videoanalizer/ui/templates/quiz.html`
- [X] T027 [P] [US5] Написать интеграционный тест сквозной генерации и сборки пропсов в `tests/integration/quiz/test_visual_quiz_orchestrator.py`

**Checkpoint**: Полный цикл от выбора темы до готового MP4-видео доступен через веб-интерфейс и CLI.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Проверка верстки по безопасным зонам, очистка временных ассетов и верификация по `quickstart.md`.

- [X] T028 [P] Проверить отступы безопасной зоны (снизу >= 400px, справа >= 120px) в `templates/quiz-remotion/src/VisualImageQuiz.tsx`
- [X] T029 Обеспечить детерминированную очистку временных картинок и чанков аудио в контекстном менеджере `videoanalizer/quiz/orchestrator.py`
- [X] T030 Прогнать сценарий валидации по `specs/007-visual-image-quiz/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Независима, запускается немедленно.
- **Foundational (Phase 2)**: Зависит от Phase 1, блокирует все пользовательские истории.
- **User Story 1 (Phase 3)**: Зависит от Phase 2 — MVP этап.
- **User Story 2 (Phase 4)**: Зависит от Phase 2 и T008 (генерация ассетов).
- **User Story 3 (Phase 5)**: Зависит от Phase 2, Phase 3 и Phase 4.
- **User Story 4 (Phase 6)**: Зависит от Phase 5.
- **User Story 5 (Phase 7)**: Зависит от всех предыдущих историй (сборка в MP4).
- **Polish (Phase 8)**: Завершающий контроль качества.

### Parallel Opportunities
- `T002` и `T003` могут выполняться параллельно с `T001`.
- `T005` может выполняться параллельно с `T004`.
- Компоненты Remotion `T016` (`SpringImageCard`), `T017` (`ProgressiveLadder`), `T018` (`SyncHorizontalTimer`) могут создаваться параллельно разными разработчиками/агентами.
- Тесты `T007`, `T015`, `T027` могут выполняться параллельно с подготовкой шаблонов.

---

## Implementation Strategy: MVP First (User Stories 1 & 2 & 3)

1. **Шаг 1**: Выполнить Setup (Phase 1) + Foundational (Phase 2).
2. **Шаг 2**: Реализовать генерацию сценария и подбор картинок (US1). Проверить работу API и веб-модерации.
3. **Шаг 3**: Собрать Remotion-компоненты интро (US2) и геймплея лестницы (US3).
4. **Шаг 4**: Добавить вовлекающие вставки (US4) и сквозной рендер MP4 (US5).
5. **Шаг 5**: Финальная валидация по `quickstart.md` и контроль безопасных зон.

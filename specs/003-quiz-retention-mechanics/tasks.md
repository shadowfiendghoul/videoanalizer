# Tasks: Quiz Retention Mechanics & Viral Features

**Feature**: Quiz Retention Mechanics & Viral Features  
**Branch**: `003-quiz-retention-mechanics`  
**Plan**: [specs/003-quiz-retention-mechanics/plan.md](file:///c:/Users/User/Desktop/videoanalizer/specs/003-quiz-retention-mechanics/plan.md)  
**Spec**: [specs/003-quiz-retention-mechanics/spec.md](file:///c:/Users/User/Desktop/videoanalizer/specs/003-quiz-retention-mechanics/spec.md)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Подготовка структуры звуковых ассетов и базовых конфигурационных шаблонов.

- [x] T001 Create SFX asset files with synthetic fallback helpers in `assets/sfx/` (`heartbeat_panic.wav`, `streak_fire.wav`, `rank_levelup.wav`, `comment_buzzer.wav`)
- [x] T002 [P] Verify Remotion dependencies and package structure in `templates/quiz-remotion/package.json`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Реализация контрактов данных Pydantic v2 и TypeScript, блокирующих реализацию всех пользовательских историй.

**⚠️ CRITICAL**: Работа над пользовательскими историями не может начаться до завершения этих задач.

- [x] T003 [P] Implement Pydantic retention schemas (`RankTierConfig`, `StressTimerTier`, `ComboStreakConfig`, `CommentTrapConfig`, `QuizRetentionConfig`) in `videoanalizer/quiz/models.py`
- [x] T004 [P] Implement TypeScript retention interfaces (`RankTierConfig`, `StressTimerTier`, `ComboStreakConfig`, `CommentTrapConfig`, `QuizRetentionConfig`) in `templates/quiz-remotion/src/types.ts`
- [x] T005 [P] Implement contract tests for retention schemas in `tests/contract/quiz/test_retention_schema_contract.py`
- [x] T006 Update `RemotionRenderProps` in `videoanalizer/quiz/models.py` and `templates/quiz-remotion/src/types.ts` to include `retention: QuizRetentionConfig`
- [x] T007 Implement audio synthesis fallback methods in `videoanalizer/quiz/audio_service.py` for `heartbeat_panic.wav`, `streak_fire.wav`, and `rank_levelup.wav`


**Checkpoint**: Базовые контракты и модели данных готовы и протестированы.

---

## Phase 3: User Story 1 - Core Viewer Retention & Blitz Mechanics (Priority: P1) 🎯 MVP

**Goal**: Зритель TikTok/Reels смотрит динамичный ролик хронометражем $\le 50$ секунд со шкалой статуса (NPC -> 1% Гениев), ускоряющимся стресс-таймером (3.0с -> 2.5с -> 1.8с), звуком сердцебиения, панической виньеткой и комбо-огнем.

**Independent Test**: Запуск рендера тестовой композиции в Remotion и проверка хронометража ролика строго в пределах 45–50 секунд с отображением Rank Bar, стресс-таймера и счетчика огня.

### Tests for User Story 1
- [x] T008 [P] [US1] Unit test for dynamic blitz audio timing calculation and cue sheet compilation in `tests/unit/quiz/test_audio_service.py`

### Implementation for User Story 1
- [x] T009 [P] [US1] Create `RankStatusBar.tsx` component in `templates/quiz-remotion/src/components/RankStatusBar.tsx` (Y=160px, 4 tiers: NPC `#64748B`, Нормис `#22C55E`, Эрудит `#A855F7`, 1% Гениев `#F59E0B` with spring fill animation)
- [x] T010 [P] [US1] Create `StressTimer.tsx` component in `templates/quiz-remotion/src/components/StressTimer.tsx` (tier-based durations 3.0s/2.5s/1.8s, color shift blue `#00A3FF` -> amber `#F59E0B` -> red `#EF4444`, 1-second shake)
- [x] T011 [P] [US1] Create `PanicVignette.tsx` component in `templates/quiz-remotion/src/components/PanicVignette.tsx` (pulsing red radial vignette on screen edges during Hard tier questions)
- [x] T012 [P] [US1] Create `StreakFire.tsx` component in `templates/quiz-remotion/src/components/StreakFire.tsx` (flame counter `🔥 x1`–`🔥 x9` at X=880px, Y=280px with blue fire `#38BDF8` ultra mode at >=7)
- [x] T013 [US1] Integrate `StressTimer`, `RankStatusBar`, `PanicVignette`, and `StreakFire` into `templates/quiz-remotion/src/QuizChallenge.tsx`
- [x] T014 [US1] Update `AudioService.calculate_cue_sheet` in `videoanalizer/quiz/audio_service.py` to enforce blitz think durations (3.0s for Easy, 2.5s for Medium, 1.8s for Hard) and max total duration $\le 50$s

**Checkpoint**: User Story 1 полностью функционирует как самостоятельный MVP продукт.


---

## Phase 4: User Story 2 - Creator Config & Viral Growth Controls (Priority: P2)

**Goal**: Создатель контента может включать/отключать вирусные механики в веб-интерфейсе, настраивать ловушку комментариев, а сервер безопасно выполняет рендеринг через FIFO-очередь с `asyncio.Semaphore(1)`.

**Independent Test**: Отправка POST запроса на `/api/v1/quiz/generate` с флагами удержания, проверка постановки в очередь и формирования итогового MP4 с финальным баннером комментариев.

### Tests for User Story 2
- [x] T015 [P] [US2] Unit test for `/api/v1/quiz/generate` accepting retention toggles and queuing jobs in `tests/unit/quiz/test_api_routes.py`

### Implementation for User Story 2
- [x] T016 [P] [US2] Create `CommentTrapOutro.tsx` component in `templates/quiz-remotion/src/components/CommentTrapOutro.tsx` (outro challenge banner on final 1.5s: "Если набрал 8+ — ты соврал. Пиши честный счет в комменты! 👇")
- [x] T017 [P] [US2] Create `AntiCheatCallout.tsx` component in `templates/quiz-remotion/src/components/AntiCheatCallout.tsx` (HUD sticker overlay on Q9: "👀 Без паузы и Гугла!")
- [x] T018 [US2] Update `QuizOrchestrator` in `videoanalizer/quiz/orchestrator.py` to enforce `asyncio.Semaphore(1)` render queue and Chromium `--concurrency=3`
- [x] T019 [US2] Update `QuizGenerateRequest` schema and endpoint in `videoanalizer/api/routes_quiz.py` to pass `retention_enabled`, `rank_bar_enabled`, `stress_timer_enabled`, `streak_fire_enabled`, `comment_trap_enabled`
- [x] T020 [US2] Add retention toggles and queue status indicators to web dashboard in `videoanalizer/ui/templates/quiz.html`

**Checkpoint**: Создатель контента имеет полный контроль над всеми механиками через UI и API.

---

## Phase 5: User Story 3 - Resilient Rendering & Layout Guard (Priority: P3)

**Goal**: Предотвратить вылет текста за пределы плашек 9:16 при длинных ответах Gemini и гарантировать непрерывный рендер при коротких видеофонах.

**Independent Test**: Генерация квиза с коротким 15-секундным фоновым роликом и длинным текстом вопросов; подтверждение бесшовного зацикливания видео и адаптивного кегля шрифта без наложений.

### Tests for User Story 3
- [x] T021 [P] [US3] Unit tests for Gemini prompt text length limits and Pydantic validators in `tests/unit/quiz/test_script_service.py`

### Implementation for User Story 3
- [x] T022 [US3] Update `QUIZ_SYSTEM_PROMPT` and add Pydantic validators in `videoanalizer/quiz/script_service.py` (question $\le 65$ chars, answer $\le 25$ chars, reject $>80$ / $>35$)
- [x] T023 [P] [US3] Create `DecoyFakeOut.tsx` component in `templates/quiz-remotion/src/components/DecoyFakeOut.tsx` (0.3s fake answer stamp `❌ НЕ ПАРИЖ` $\rightarrow$ `✅ ЛИОН` on Q4/Q7)
- [x] T024 [US3] Wrap background video layer in `<Loop>` in `templates/quiz-remotion/src/components/BackgroundLayer.tsx` for seamless looping of short backgrounds
- [x] T025 [US3] Implement dynamic CSS `clamp(26px, 3.2vw, 44px)` font scaling in `templates/quiz-remotion/src/components/QuestionCard.tsx` and `QuestionLadder.tsx`

**Checkpoint**: Система полностью защищена от оверфлоу текста и обрывов фонового видео.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Финальная полировка, согласование дефолтных props и сквозная верификация.

- [x] T026 [P] Update defaultProps with retention configuration in `templates/quiz-remotion/src/Root.tsx`
- [x] T027 [P] Run Ruff linter and formatting checks across Python codebase (`python -m ruff check videoanalizer/ tests/`)
- [x] T028 Run full automated test suite (`python -m pytest tests/unit/quiz tests/contract/quiz`)
- [x] T029 Execute end-to-end quickstart validation scenario from `specs/003-quiz-retention-mechanics/quickstart.md`

---

## Phase 7: Visual Hierarchy, Banner Pause & Subtitle Sync Polish

**Purpose**: Выполнение доработок по запросу пользователя: масштабирование верхнего интерфейса, смещение элементов ниже, пауза видео при показе баннера и синхронизация субтитров с голосом.

- [x] T030 Enlarge upper UI elements in `RankStatusBar.tsx` (scale width to 880px, larger font/badges, thicker bar), `LevelHeader.tsx` (text-5xl, larger padding/glow), and `StreakFire.tsx` (larger flame icon, font, badge)
- [x] T031 Shift layout down vertically in `RankStatusBar.tsx` (top: 230px), `LevelHeader.tsx` (top: 335px), `StreakFire.tsx` (top: 430px), and `QuestionLadder.tsx` (top: 48% / ~920px)
- [x] T032 Pause video during promo banner:
  - In `orchestrator.py`: cleanly insert promo banner midway (after Q4), shifting subsequent cues by `banner_duration_frames` and extending `total_duration_frames`
  - In `BackgroundLayer.tsx`: during banner duration, freeze/pause the background video using `<Freeze>` or sequence split
  - In `QuizChallenge.tsx`: pass banner timing props to `BackgroundLayer`
- [x] T033 Align subtitles with voice in `KaraokeCaptions.tsx`: remove negative offset and calibrate subtitle appearance delay so words sync perfectly with spoken voice; remove unstable `rate="+20%"` in `audio_service.py`
- [x] T034 Validate changes with `npm.cmd run typecheck`, pytest test suite, and ruff checks

---

## Phase 8: Two-Stage Creative Generation & Strict Fact-Checking Pipeline

**Purpose**: Реализация двухэтапного пайплайна: первичная высокотемпературная ($T=0.95$) генерация оригинальных фактов и парадоксов + вторичный низкотемпературный ($T=0.1$) строгий факт-чекинг для устранения мифов и неточностей.

- [x] T035 [P] Implement `verify_and_refine_facts` with `FACT_CHECK_SYSTEM_PROMPT` ($T=0.1$) in `videoanalizer/quiz/script_service.py`
- [x] T036 Update `QuizConfig` in `videoanalizer/quiz/config.py` with `creative_temperature: float = 0.95`, `verifier_temperature: float = 0.1`, and `fact_check_enabled: bool = True`
- [x] T037 Update API routes and schemas in `videoanalizer/api/routes_quiz.py` (`QuizPreviewRequest`, `QuizGenerateRequest`)
- [x] T038 Update Web UI in `videoanalizer/ui/templates/quiz.html` with temperature slider/preset selector, fact-check toggle, and 2-stage status indicator
- [x] T039 Add unit tests for fact-checking pass and verifier corrections in `tests/unit/quiz/test_script_service.py`
- [x] T040 Verify end-to-end with pytest, TypeScript typecheck, and ruff linter

---

## Phase 8: User Story 6 - Video Uniquifier & Anti-Fingerprinting Engine (Уникализатор видео)

**Goal**: Полноценный уникализатор видео против Content ID и алгоритмических фильтров соцсетей (TikTok, YouTube Shorts, Reels) с цветокоррекцией (яркость, контраст, насыщенность, гамма), микро-зумом (101-103%), незаметным цифровым шумом (film grain), микро-сдвигом аудио-темпа (Acoustic Fingerprint Disruption) и полной подменой метаданных.

- [x] T041 [P] Create `VideoUniquifierConfig` model in `videoanalizer/media/uniquifier.py`
- [x] T042 [P] Implement `apply_video_uniquifier` core function in `videoanalizer/media/uniquifier.py`
- [x] T043 [P] Add unit tests in `tests/unit/test_uniquifier.py`
- [x] T044 Integrate uniquifier into `videoanalizer/quiz/orchestrator.py` and `routes_quiz.py`
- [x] T045 Integrate uniquifier into `videoanalizer/media/renderer.py`
- [x] T046 Add Uniquifier UI controls and persistence in `videoanalizer/ui/templates/quiz.html`
- [x] T047 Verify end-to-end with pytest and ruff linter


---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion — **BLOCKS all user stories**.
- **User Story 1 (Phase 3 - MVP)**: Depends on Foundational completion.
- **User Story 2 (Phase 4)**: Depends on Foundational completion; integrates with US1 Remotion components.
- **User Story 3 (Phase 5)**: Depends on Foundational completion; strengthens resilience of US1/US2.
- **Polish (Phase 6)**: Depends on all user stories being completed.

### Parallel Opportunities
- In Phase 2: T003 (Python models), T004 (TS types), and T005 (contract tests) can run in parallel.
- In Phase 3: Remotion components T009 (`RankStatusBar`), T010 (`StressTimer`), T011 (`PanicVignette`), and T012 (`StreakFire`) can all be built in parallel.
- In Phase 4: T015 (API tests), T016 (`CommentTrapOutro`), and T017 (`AntiCheatCallout`) can run in parallel.
- In Phase 5: T021 (tests), T023 (`DecoyFakeOut`), and T024 (`BackgroundLayer`) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1)
1. Complete Setup (Phase 1) + Foundational (Phase 2)
2. Complete User Story 1 (Phase 3)
3. **STOP and VALIDATE**: Verify blitz timing ($\le 50$s) and visual retention mechanics in Remotion Studio
4. Incrementally add User Story 2 (UI toggles & OOM guard) and User Story 3 (Layout guard & loops)

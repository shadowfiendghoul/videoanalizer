# Implementation Tasks: Batch Queue & AI Topic Generator

**Feature Branch**: `005-batch-queue-topics`  
**Date**: 2026-10-13  
**Spec**: [specs/005-batch-queue-topics/spec.md](file:///C:/Users/User/Desktop/videoanalizer/specs/005-batch-queue-topics/spec.md)  
**Plan**: [specs/005-batch-queue-topics/plan.md](file:///C:/Users/User/Desktop/videoanalizer/specs/005-batch-queue-topics/plan.md)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare project structure and environment for batch queue and rate limiting features.

- [ ] T001 Inspect and prepare module structure for batch queue in `videoanalizer/quiz/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and 15 RPM rate-limiting infrastructure that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Define `TopicSuggestion` (`topic: str (3..70 chars)`, `category: str (2..40 chars)`, `curiosity_hook: str (5..120 chars)`) and `BatchTopicList` schemas in `videoanalizer/quiz/models.py`
- [ ] T003 [P] Define `BatchQueueItemStatus`, `BatchQueueItem`, `BatchQueueState`, `BatchRenderStartRequest`, and `GenerationHistoryItem` schemas in `videoanalizer/quiz/models.py`
- [ ] T004 Implement `PacedLimiter` async rate limiter enforcing $\ge 5.0$ seconds delay between requests ($\le 12$ RPM) with exponential backoff on HTTP 429 in `videoanalizer/quiz/rate_limiter.py`
- [ ] T005 [P] Implement unit tests for `PacedLimiter` rate pacing and backoff behavior in `tests/unit/test_rate_limiter.py`

**Checkpoint**: Foundation ready — models and rate limiter verified.

---

## Phase 3: User Story 1 - Single Video AI Topic Suggestion (Priority: P1) 🎯 MVP

**Goal**: Enable creators to click "🎲 Придумать тему" to generate a viral, high-curiosity quiz topic via Gemini in under 3.5 seconds.

**Independent Test**: Click "🎲 Придумать тему" on the quiz creation screen without entering a topic; verify the topic field populates with a catchy, valid topic title.

- [ ] T006 [US1] Implement `suggest_topic(category_hint: str | None, language: str)` in `videoanalizer/quiz/script_service.py` using Gemini REST API and `TopicSuggestion` schema
- [ ] T007 [US1] Implement `POST /api/v1/quiz/topics/suggest-single` endpoint with schema validation and error handling in `videoanalizer/api/routes_quiz.py`
- [ ] T008 [P] [US1] Add unit tests for single topic generation and schema validation in `tests/unit/test_topic_generator.py`
- [ ] T009 [US1] Add "🎲 Придумать тему" action button, loading spinner, and input autofill logic in `videoanalizer/ui/templates/quiz.html`

**Checkpoint**: User Story 1 is fully functional and independently testable.

---

## Phase 4: User Story 2 - Batch Topic Ideation & Review (Priority: P2)

**Goal**: Generate $N$ (2–20) diverse, non-overlapping topics in a SINGLE Gemini API request to conserve the 15 RPM quota, allowing creators to edit or replace topics before generating questions.

**Independent Test**: Switch to Batch Mode, enter count (e.g. 5), click "Сгенерировать темы", verify 5 distinct topics appear in a single request, and test editing/refreshing an individual topic.

- [ ] T010 [US2] Implement `suggest_batch_topics(count: int, category_hint: str | None, language: str)` in `videoanalizer/quiz/script_service.py` requesting $N$ topics in a single Gemini prompt
- [ ] T011 [US2] Implement `POST /api/v1/quiz/topics/suggest-batch` endpoint adhering to `contracts/api_topics.json` in `videoanalizer/api/routes_quiz.py`
- [ ] T012 [P] [US2] Add unit tests for batch topic ideation ensuring 1 API call produces $N$ unique items in `tests/unit/test_topic_generator.py`
- [ ] T013 [US2] Add Batch Mode tab, count slider/input (2–20), topic list card display, inline editing, and single-topic refresh buttons in `videoanalizer/ui/templates/quiz.html`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Sequential Multi-Video Question Approval Flow (Priority: P1)

**Goal**: Provide a step-by-step wizard ("Видео k из N") allowing users to inspect, edit, pick images, and selectively regenerate questions for each video while background generation runs with 5s pacing.

**Independent Test**: Launch a 3-video batch, review Video 1 questions, edit a question, click "Одобрить и далее", verify Video 2 loads with its questions, and navigate back/forward without losing edits.

- [ ] T014 [US3] Implement progressive background script generation worker with `PacedLimiter` integration in `videoanalizer/quiz/batch_queue.py`
- [ ] T015 [US3] Implement `POST /api/v1/quiz/batch/init` and batch item retrieval endpoints in `videoanalizer/api/routes_quiz.py`
- [ ] T016 [P] [US3] Add unit tests for progressive script generation and rate-limiting queue in `tests/unit/test_batch_queue.py`
- [ ] T017 [US3] Build sequential review wizard modal ("Видео k из N: [Тема]") with step navigation pills, question editor, and image picker in `videoanalizer/ui/templates/quiz.html`
- [ ] T018 [US3] Wire selective question regeneration and delete/skip video action inside the batch wizard in `videoanalizer/ui/templates/quiz.html`

**Checkpoint**: Approval wizard allows sequential review of all batch items without violating the 15 RPM quota.

---

## Phase 6: User Story 4 - Background Sequential Render Queue & Monitoring (Priority: P1)

**Goal**: Execute video rendering strictly sequentially (`concurrency = 1` via `asyncio.Semaphore(1)`) to safeguard GPU/CPU hardware, providing live progress, fault isolation, individual/bulk download buttons, and a persistent generation history panel.

**Independent Test**: Enqueue 3 approved jobs; verify Video 1 renders while Videos 2 and 3 wait in queue. When Video 1 completes, verify Video 2 begins rendering and Video 1 displays a preview and "Скачать MP4" button, and appears in "История генераций".

- [ ] T019 [US4] Implement `BatchQueueManager` with `asyncio.Semaphore(1)` FIFO render worker and failure isolation in `videoanalizer/quiz/batch_queue.py`
- [ ] T020 [US4] Implement `POST /api/v1/quiz/batch/queue/start`, `GET /api/v1/quiz/batch/queue/status`, `POST /api/v1/quiz/batch/queue/cancel/{item_id}`, and `POST /api/v1/quiz/batch/queue/clear` endpoints in `videoanalizer/api/routes_quiz.py`
- [ ] T021 [US4] Implement `GET /api/v1/quiz/batch/queue/download-all` (streaming ZIP archive generator) and `GET /api/v1/quiz/history` (load persistent video generation history) endpoints in `videoanalizer/api/routes_quiz.py`
- [ ] T022 [P] [US4] Add unit tests for `BatchQueueManager` sequential execution lock, failure isolation, history logging, and ZIP creation in `tests/unit/test_batch_queue.py`
- [ ] T023 [US4] Implement Queue Monitoring and dedicated "История генераций" section in `videoanalizer/ui/templates/quiz.html` with real-time status badges, live progress bars, topic titles, video preview players, and "Скачать MP4" / "Скачать все (ZIP)" buttons

**Checkpoint**: Complete batch workflow renders videos sequentially and stably without system crashes.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality checks, formatting, and end-to-end verification.

- [ ] T024 [P] Run Ruff linter and formatter on all modified Python modules in `videoanalizer/` and `tests/`
- [ ] T025 Execute end-to-end quickstart validation scenarios defined in `specs/005-batch-queue-topics/quickstart.md`
- [ ] T026 Update user documentation and release notes for batch queue and AI topic ideation

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup; BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational phase. Delivers MVP topic ideation.
- **User Story 2 (Phase 4)**: Depends on Foundational phase and US1 topic schemas.
- **User Story 3 (Phase 5)**: Depends on US2 batch topics and Foundational rate limiter.
- **User Story 4 (Phase 6)**: Depends on US3 approved batch items and orchestrator.
- **Polish (Phase 7)**: Depends on all user stories being complete.

### Parallel Opportunities
- T002 and T003 can be implemented in parallel.
- T005, T008, T012, T016, T022 (tests) can be developed alongside corresponding services.
- T009, T013, T017, T023 (UI components) can be styled once backend endpoints and contracts are defined.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Setup) and Phase 2 (Foundational: models + rate limiter).
2. Complete Phase 3 (User Story 1: "🎲 Придумать тему" button & endpoint).
3. Validate User Story 1 directly in the browser.

### Incremental Delivery
1. Add User Story 2 (Batch topic generation in 1 API call).
2. Add User Story 3 (Progressive background generation + step-by-step approval wizard).
3. Add User Story 4 (Sequential background render queue with Semaphore=1).
4. Run Polish phase and verify 100% adherence to 15 RPM limit and hardware safety.

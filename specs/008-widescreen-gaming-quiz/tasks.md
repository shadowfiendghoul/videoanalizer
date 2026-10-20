# Tasks: 008-widescreen-gaming-quiz

**Feature**: `008-widescreen-gaming-quiz`  
**Date**: 2026-10-20  
**Spec Reference**: [spec.md](spec.md)  
**Plan Reference**: [plan.md](plan.md)  
**Data Model**: [data-model.md](data-model.md)  
**Contracts**: [contracts/remotion_props_schema.json](contracts/remotion_props_schema.json), [contracts/widescreen_quiz_api.json](contracts/widescreen_quiz_api.json)  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffolding for 16:9 widescreen 1920x1080 60fps Remotion composition and base TypeScript types.

- [X] T001 Define TypeScript interfaces `WidescreenQuizItem`, `WidescreenQuizRound`, `WidescreenQuizDataset`, `WidescreenTimingSlot`, and `WidescreenQuizRenderProps` in `templates/quiz-remotion/src/types.ts`
- [X] T002 [P] Register `WidescreenGamingQuiz` composition (1920x1080, 60fps) with default test props in `templates/quiz-remotion/src/Root.tsx`
- [X] T003 [P] Create initial test scaffold and synthetic fixtures in `tests/unit/quiz/test_widescreen_quiz_models.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Pydantic v2 data models, timing calculation utilities, and sound effect library setup that block user story implementation.

- [X] T004 Implement Pydantic v2 models `AssetDisplayMode`, `WidescreenQuizItem`, `WidescreenQuizRound`, `WidescreenIntroConfig`, `WidescreenScoreTier`, `WidescreenOutroConfig`, `WidescreenQuizDataset`, `WidescreenTimingSlot`, and `WidescreenQuizRenderProps` in `videoanalizer/quiz/models.py`
- [X] T005 [P] Implement `WidescreenTimingCalculator` for 60fps frame coordinates and timing slot generation in `videoanalizer/quiz/audio_service.py`
- [X] T006 [P] Verify and curate base SFX assets (`timer_tick.wav`, `reveal_ding.wav`, `sub_bass_stinger.wav`) in `assets/sfx/`

**Checkpoint**: Foundation ready — all user stories can now proceed.

---

## Phase 3: User Story 1 - 16:9 Question Stage & Timing Synchronization (Priority: P1) 🎯 MVP

**Goal**: Clean, high-impact 1920x1080 stage with synchronized 9.0s question cycle (6.0s guessing countdown + 3.0s bounce answer hold) and procedural SFX.

**Independent Test**: Render a standalone 1-round sequence of questions and test that each question strictly abides by the 6.0s countdown bar depletion, chime at 6.0s, and 3.0s answer hold before transitioning.

### Tests for User Story 1

- [X] T007 [P] [US1] Unit test for 9.0s question cycle timing calculator (frames 0–360 guessing, 360–540 reveal hold) in `tests/unit/quiz/test_widescreen_quiz_audio.py`

### Implementation for User Story 1

- [X] T008 [P] [US1] Create `WidescreenStatusBar.tsx` component (Round badge at X:120 Y:50 W:480 H:60, Question tracker at X:1480 Y:50 W:320 H:60) in `templates/quiz-remotion/src/components/WidescreenStatusBar.tsx`
- [X] T009 [P] [US1] Create base `WidescreenAssetContainer.tsx` component (X:360 Y:170 W:1200 H:600, fitted 1140x540 max image, 12px rounded corners) in `templates/quiz-remotion/src/components/WidescreenAssetContainer.tsx`
- [X] T010 [P] [US1] Create `WidescreenTimerBar.tsx` component (X:360 Y:800 W:1200 H:16, linear depletion over 6.0s, amber #F59E0B transitioning to red #EF4444 in final 1.5s) in `templates/quiz-remotion/src/components/WidescreenTimerBar.tsx`
- [X] T011 [P] [US1] Create `WidescreenAnswerPanel.tsx` component (X:460 Y:860 W:1000 H:90, hidden 0–6s, spring scale bounce at 6.0s, hold until 9.0s) in `templates/quiz-remotion/src/components/WidescreenAnswerPanel.tsx`
- [X] T012 [US1] Implement multi-track audio assembly for 9.0s cycle (ticking during 0.0s–6.0s, reveal chime stinger at exactly 6.0s) in `videoanalizer/quiz/audio_service.py`
- [X] T013 [US1] Assemble complete question stage coordinating status bar, asset container, timer bar, answer panel, and SFX in `templates/quiz-remotion/src/WidescreenGamingQuiz.tsx`

**Checkpoint**: User Story 1 (MVP) is functional and independently testable at 60 fps.

---

## Phase 4: User Story 2 - Multi-Round Progression & Multi-Modal Asset Mechanics (Priority: P2)

**Goal**: Support 5 distinct asset gameplay modes (screenshots, audio SFX with pulsing waveform, game-over screens, circular minimap radar with HUD, silhouettes with CSS filters) and procedural mask toggles.

**Independent Test**: Configure a dataset containing at least one image round and one audio SFX round, verifying that image rounds render fitted graphics and audio rounds render the glowing animated waveform icon while playing cue audio between 0.5s and 4.5s.

### Tests for User Story 2

- [X] T014 [P] [US2] Unit tests for asset mode validation and procedural mask flags in `tests/unit/quiz/test_widescreen_quiz_models.py`

### Implementation for User Story 2

- [X] T015 [P] [US2] Implement animated glowing cyan (#00E5FF) pulse and waveform visualizer in `templates/quiz-remotion/src/components/WidescreenAssetContainer.tsx` for `AUDIO_SFX` mode
- [X] T016 [P] [US2] Implement procedural circular radar mask (`clip-path: circle()`) and tactical SVG HUD grid overlay with rotating sweep line in `templates/quiz-remotion/src/components/WidescreenAssetContainer.tsx` for `MINIMAP` mode
- [X] T017 [P] [US2] Implement procedural silhouette mask (`filter: brightness(0)`) with smooth reveal transition on answer hold in `templates/quiz-remotion/src/components/WidescreenAssetContainer.tsx` for `SILHOUETTE` mode
- [X] T018 [US2] Implement audio cue playback window (0.5s–4.5s) with 250ms fade-out for `AUDIO_SFX` mode questions in `videoanalizer/quiz/audio_service.py`
- [X] T019 [US2] Implement dynamic round badge styling and theme color switching in `templates/quiz-remotion/src/components/WidescreenStatusBar.tsx`

**Checkpoint**: User Stories 1 and 2 operate cohesively with all 5 asset modalities.

---

## Phase 5: User Story 3 - Cinematic Round Splash Transitions & Gamified Outro (Priority: P3)

**Goal**: 4.0s interstitial round splash screens with pass rate callouts and sub-bass stingers, 8.0s intro hook with TTS narration, and 15.0s outro card with 4-tier score brackets.

**Independent Test**: Transition between Round 1 and Round 2 verifying the 4.0s splash screen with zoom and audio stinger, followed by rendering the final outro card at the conclusion of all rounds.

### Tests for User Story 3

- [X] T020 [P] [US3] Unit tests for splash screen and outro timing slot calculations in `tests/unit/quiz/test_widescreen_quiz_audio.py`

### Implementation for User Story 3

- [X] T021 [P] [US3] Create `WidescreenRoundSplash.tsx` component (4.0s duration, upcoming round number, round title, pass rate callout, sub-bass stinger) in `templates/quiz-remotion/src/components/WidescreenRoundSplash.tsx`
- [X] T022 [P] [US3] Create `WidescreenOutro.tsx` component (15.0s duration, 4-tier score evaluation Noob/Gamer/Pro/God Tier, subscriber CTA) in `templates/quiz-remotion/src/components/WidescreenOutro.tsx`
- [X] T023 [US3] Implement Edge-TTS speech narration synthesis for 8.0s Intro Hook and 15.0s Outro Card in `videoanalizer/quiz/audio_service.py`
- [X] T024 [US3] Integrate Intro Hook, Round Splash intervals, and Outro sequence into master timeline in `templates/quiz-remotion/src/WidescreenGamingQuiz.tsx`

**Checkpoint**: Complete broadcast structure from Intro to Outro functions seamlessly.

---

## Phase 6: User Story 4 - Modular Content Generation & Review UI (Priority: P4)

**Goal**: Gemini REST API generation of 50-question 16:9 quiz datasets, automated audio SFX and image search, Gradio/FastAPI moderation review UI, and continuous BGM ducking.

**Independent Test**: Supply an alternate custom dataset (e.g., Cinema Trivia) with 3 rounds of 6 questions, verifying that the system successfully parses, lays out, and renders the video according to the provided dataset.

### Tests for User Story 4

- [X] T025 [P] [US4] Unit tests for Gemini prompt generation and structured output parsing in `tests/unit/quiz/test_widescreen_quiz_script.py`
- [X] T026 [P] [US4] Unit tests for audio SFX search and clipping in `tests/unit/quiz/test_widescreen_quiz_sound.py`

### Implementation for User Story 4

- [X] T027 [US4] Implement prompt engineering and `generate_widescreen_quiz_dataset()` via Gemini REST API in `videoanalizer/quiz/script_service.py`
- [X] T028 [P] [US4] Implement `SoundService` for automated audio SFX retrieval (Freesound API, web soundboards, curated local fallback) in `videoanalizer/quiz/sound_service.py`
- [X] T029 [P] [US4] Extend `ImageService` for specialized gaming screenshot, minimap, and silhouette queries in `videoanalizer/quiz/image_service.py`
- [X] T030 [US4] Implement continuous ambient BGM track playback with automated 18% audio ducking during speech & audio cues in `videoanalizer/quiz/audio_service.py`
- [X] T031 [US4] Implement REST endpoints (`/api/v1/quiz/widescreen/generate`, `/search-audio`, `/search-image`, `/render`) in `videoanalizer/api/routes_quiz.py`
- [X] T032 [US4] Build Gradio/FastAPI review and moderation tab (grid of 50 questions across 5 rounds, asset preview, audio audition, filter toggles, file upload) in `videoanalizer/ui/app.py`

**Checkpoint**: End-to-end user journey from topic prompt to moderation UI and batch approval is operational.

---

## Phase 7: Polish & Pipeline Integration

**Purpose**: Edge cases (text overflow, missing assets, letterboxing), end-to-end 50-question pipeline, and integration tests.

- [X] T033 [P] Implement dynamic font autoscaling (26px–38px) for long answer titles (>35 chars) in `templates/quiz-remotion/src/components/WidescreenAnswerPanel.tsx`
- [X] T034 [P] Implement branded fallback placeholder card for missing or corrupted asset files in `templates/quiz-remotion/src/components/WidescreenAssetContainer.tsx`
- [X] T035 [P] Implement aspect ratio letterbox/pillarbox preservation without stretching in `templates/quiz-remotion/src/components/WidescreenAssetContainer.tsx`
- [X] T036 Integrate `widescreen_gaming_quiz` pipeline coordination, asset staging, and CLI render dispatch in `videoanalizer/quiz/orchestrator.py`
- [X] T037 Implement end-to-end integration test verifying 1-round 3-question render in `tests/integration/quiz/test_widescreen_quiz_orchestrator.py`
- [X] T038 Run quickstart validation test render per `specs/008-widescreen-gaming-quiz/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1). BLOCKS all user stories.
- **US1 Question Stage (Phase 3)**: Depends on Phase 2. Forms the core MVP.
- **US2 Multi-Round & Multi-Modal (Phase 4)**: Depends on Phase 3 components.
- **US3 Splash Screens & Outro (Phase 5)**: Depends on Phase 3 and Phase 4.
- **US4 Generation & Review UI (Phase 6)**: Can proceed in parallel once Phase 2 is complete.
- **Polish (Phase 7)**: Depends on all user stories being integrated.

### Parallel Opportunities
- All tasks marked `[P]` touch independent files and have no mutual dependencies.
- Component development in Phase 3 (`WidescreenStatusBar`, `WidescreenAssetContainer`, `WidescreenTimerBar`, `WidescreenAnswerPanel`) can proceed in parallel.
- Audio and image services in Phase 6 (`SoundService`, `ImageService`) can be implemented concurrently.

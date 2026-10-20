# Implementation Plan: 008-widescreen-gaming-quiz

**Branch**: `008-widescreen-gaming-quiz` | **Date**: 2026-10-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-widescreen-gaming-quiz/spec.md`

---

## Summary

Implement a modular 16:9 widescreen (1920x1080 @ 60fps) gaming trivia quiz video system inspired by "Quiz Please", designed for long-form YouTube broadcasting (~9–10 minutes, 50 questions across 5 rounds).
1. **Rhythmic Question Stage & Timing**: Strict 9.0s question cycle (6.0s guessing countdown + 3.0s reveal hold) with zero timing drift, using rhythmic ticking audio and positive reveal chimes. Speech narration is strictly restricted to Intro Hook (8s) and Outro Card (15s).
2. **Multi-Modal Asset Mechanics**: Round-specific asset display modes including standard screenshots, audio SFX guessing with glowing cyan animated waveforms, masked game-over screens, tactical radar minimaps with procedural circular `clip-path` masks and HUD grid overlays, and character silhouettes with procedural CSS `filter: brightness(0)` masks.
3. **Cinematic Broadcast Structure**: 4.0-second interstitial round splash screens with pass rate callouts and sub-bass stingers, plus a gamified 15-second 4-tier score evaluation outro (Noob, Gamer, Pro, God Tier) with subscriber call-to-action.
4. **AI Generation, Asset Sourcing & Review**: Gemini REST API prompt generation (@script-service), automated image and audio retrieval pipelines with local caching and sound clipping, interactive review and moderation UI in Gradio/FastAPI, and automated BGM ducking during audio cues and narration.

---

## Technical Context

**Language/Version**: Python 3.11+ (Backend orchestrator & services), TypeScript / React 18+ (Remotion rendering engine).  
**Primary Dependencies**:
- Backend: `fastapi`, `uvicorn`, `pydantic` v2, `google-genai` / `httpx` (Gemini REST API), `edge-tts`, `ffmpeg-python`, `pillow`, `duckduckgo_search`.
- Frontend/Rendering: Remotion (CLI & React runtime), Tailwind CSS, Lucide icons, Gradio.

**Storage**:
- Media Assets & Cache: `assets/quizzes/widescreen/`, `assets/sfx/`, `assets/backgrounds/`, `assets/music/`.
- Isolated Workspace: `QuizWorkspace` managed per job in `temp/`.
- Render Output: `output/`.

**Testing**: `pytest`, `pytest-asyncio` with synthetic offline fixtures (Python); `vitest` / Remotion test runner (TypeScript).  
**Target Platform**: YouTube 16:9 1080p60 landscape video on Windows, Linux, and macOS.  
**Project Type**: Video rendering pipeline with web UI extension in VideoAnalyzer.  
**Performance Goals**:
- 60.0 fps render via Remotion CLI with GPU acceleration (NVENC/AMF/QSV) or safe CPU fallbacks.
- Complete 50-question video pipeline execution in < 15 minutes on modern 6+ core machines.
- Answer reveal snaps into view within 1 video frame (16.6ms) of the 6.0s mark.

**Constraints**:
- Strict 9.0s duration per question (6.0s guessing + 3.0s reveal hold).
- Zero spoken speech narration during round questions to guarantee zero timing drift.
- Full compliance with YouTube 16:9 safe margins (no critical elements clipped by player UI).

**Scale/Scope**: Single-user content creator desktop tool generating broadcast-quality 9–10 minute trivia show episodes.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Principle I: Strict Type Safety & Pydantic Data Contracts**  
  *Status*: **PASS**  
  All entities (`WidescreenQuizDataset`, `WidescreenQuizRound`, `WidescreenQuizItem`, `WidescreenTimingSlot`, `WidescreenOutroConfig`, `WidescreenQuizRenderProps`) are modeled as strict Pydantic v2 schemas. Dynamic dictionaries and raw tuples across boundaries are strictly forbidden.

- **Principle II: Declarative Motion Rendering & Media Processing (Remotion & FFmpeg)**  
  *Status*: **PASS**  
  Visual composition is handled declaratively in Remotion (1920x1080, 60fps) via typed props without mutating template components directly. Supplementary audio and video processing (ducking, slicing, caching) is isolated in `@audio-service` and FFmpeg subprocesses with context manager cleanup.

- **Principle III: Asynchronous & Resilient AI Engine (Gemini REST API)**  
  *Status*: **PASS**  
  Generation of 50-question datasets uses exclusively the official Gemini REST API (`gemini-2.5-flash`) via `google-genai` / `httpx` with Pydantic structured outputs and exponential backoff with jitter. WebSocket APIs are strictly avoided.

- **Principle IV: Isolated Testing & Contract Verification (NON-NEGOTIABLE)**  
  *Status*: **PASS**  
  Every sub-service is covered by independent unit tests with lightweight synthetic fixtures. No network dependencies are required during standard CI/test runs.

- **Principle V: Decoupled Sub-Service Boundaries & Presentation Layer Modularity**  
  *Status*: **PASS**  
  Sub-service responsibilities remain strictly segregated:
  - `@script-service`: Quiz generation and topic parsing.
  - `@audio-service`: Speech synthesis, SFX mixing, timing calculation, and audio ducking.
  - `@template-engine`: Declarative 1920x1080 React/Remotion visual presentation components.
  - `@orchestrator`: Asset staging, props assembly, and CLI render triggering.
  The FastAPI / Gradio UI functions strictly as a presentation and moderation surface.

---

## Project Structure

### Documentation (this feature)

```text
specs/008-widescreen-gaming-quiz/
├── spec.md              # Requirements and user stories with integrated clarifications
├── plan.md              # Architectural implementation plan (this document)
├── research.md          # Technical investigations (procedural masks, ducking, audio search)
├── data-model.md        # Pydantic v2 domain schemas and data contracts
├── quickstart.md        # Minimal 1-round 3-question verification guide
├── contracts/           # API and Remotion JSON schema contracts
│   ├── remotion_props_schema.json
│   └── widescreen_quiz_api.json
└── tasks.md             # Implementation tasks breakdown (Phase 2)
```

### Source Code (repository root)

```text
videoanalizer/
├── quiz/
│   ├── models.py                   # [EXTEND] WidescreenQuizDataset, Round, Item, TimingSlot, RenderProps
│   ├── script_service.py            # [EXTEND] 16:9 quiz generation prompt and structured output parsing
│   ├── sound_service.py             # [NEW] Audio SFX search & download (Freesound / web / curated cache)
│   ├── audio_service.py            # [EXTEND] Widescreen timing calculation, SFX track mixing, BGM ducking
│   ├── image_service.py            # [EXTEND] Screenshot, minimap, and silhouette query formatting
│   └── orchestrator.py             # [EXTEND] WidescreenGamingQuiz render pipeline coordination
├── api/
│   └── routes_quiz.py              # [EXTEND] REST endpoints for widescreen quiz generate, search, and render
└── ui/
    └── app.py                      # [EXTEND] Gradio / FastAPI UI for 16:9 quiz generation & moderation

templates/quiz-remotion/src/
├── Root.tsx                        # [EXTEND] Register WidescreenGamingQuiz composition (1920x1080 @ 60fps)
├── WidescreenGamingQuiz.tsx        # [NEW] Root widescreen composition controller
├── components/
│   ├── WidescreenStatusBar.tsx     # [NEW] Top-Left Round badge & Top-Right Question tracker
│   ├── WidescreenAssetContainer.tsx# [NEW] Central 1200x600 container (screenshot, waveform, minimap, silhouette)
│   ├── WidescreenTimerBar.tsx      # [NEW] 1200x16px linear countdown bar (amber to red)
│   ├── WidescreenAnswerPanel.tsx   # [NEW] 1000x90px bouncing answer reveal panel
│   ├── WidescreenRoundSplash.tsx   # [NEW] 4.0s cinematic interstitial round transition card
│   └── WidescreenOutro.tsx         # [NEW] 15.0s gamified 4-tier score evaluation outro card
└── types.ts                        # [EXTEND] TypeScript interfaces matching WidescreenQuizRenderProps

tests/
├── unit/quiz/
│   ├── test_widescreen_quiz_models.py      # [NEW] Pydantic models validation and computed fields
│   ├── test_widescreen_quiz_script.py      # [NEW] Gemini prompt generation & schema tests
│   ├── test_widescreen_quiz_sound.py       # [NEW] Audio search, caching, and clipping tests
│   └── test_widescreen_quiz_audio.py       # [NEW] Timing calculator & ducking tests
└── integration/quiz/
    └── test_widescreen_quiz_orchestrator.py # [NEW] End-to-end 1-round minimal test render
```

**Structure Decision**: Fully extends the established decoupled service architecture in `videoanalizer/quiz/` and adds declarative 16:9 React components under `templates/quiz-remotion/src/components/`.

---

## Complexity Tracking

*No constitutional violations identified. Standard technology stack and architecture.*

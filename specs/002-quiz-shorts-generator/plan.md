# Implementation Plan: Automated Quiz & Trivia Shorts Generator (QuizyPeasy Style)

**Branch**: `002-quiz-shorts-generator` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-quiz-shorts-generator/spec.md`

## Summary

Build an automated end-to-end vertical video generator producing viral 9-question 3-tier trivia challenges in the signature style of TikTok account QuizyPeasy. The system operates in an Open-Recall format (no multiple-choice buttons) across three difficulty levels (Level 1: Easy/Green, Level 2: Medium/Yellow, Level 3: Hard/Red). Questions are generated via Gemini REST API with strict Pydantic v2 schemas, narrated with Microsoft neural voices via `edge-tts` with word-level alignment, paired with 3-second ticking countdowns and reveal chimes, and rendered at 1080x1920 60fps with premium neon glassmorphism and TikTok karaoke typography using Remotion (React/TypeScript/Tailwind CSS) controlled headlessly by Python.

## Technical Context

**Language/Version**: Python 3.11+ (backend orchestration & services), Node.js 18+ / TypeScript 5.0+ (Remotion motion engine).

**Primary Dependencies**:
- Python: `google-genai>=1.0.0`, `pydantic>=2.5.0`, `fastapi>=0.110.0`, `uvicorn>=0.28.0`, `edge-tts>=6.1.9`, `duckduckgo_search>=4.4.0`, `ffmpeg-python>=0.2.0`, `httpx>=0.25.0`.
- Node.js / Remotion: `remotion>=4.0.0`, `@remotion/cli>=4.0.0`, `react@^18.2.0`, `react-dom@^18.2.0`, `tailwindcss@^3.4.0`.

**Storage**: Local filesystem with managed task workspaces. Intermediate media (audio cuts, word timestamps, downloaded images, Remotion props) are isolated in task-scoped temporary directories and purged deterministically upon job completion. Preset assets stored in `assets/backgrounds/` and `assets/sfx/`. Rendered videos exported to `outputs/`.

**Testing**: `pytest` and `pytest-asyncio` for Python unit and contract testing with deterministic synthetic fixtures; isolated visual validation via Remotion Preview and test compositions.

**Target Platform**: Windows 11, Linux, macOS (cross-platform compatible).

**Project Type**: Headless Python microservice and CLI pipeline orchestrating a declarative Remotion template engine, with optional FastAPI REST endpoints.

**Performance Goals**:
- Full 9-question video generation and render time $\le 60$ seconds on modern desktop hardware.
- Smooth 60.0 fps video stream with zero dropped frames.
- Audiovisual synchronization between speech narration and visual karaoke word highlights within 50 milliseconds.

**Constraints**:
- Exact 1080x1920 (9:16) resolution.
- Challenge video duration strictly bounded between 55 and 65 seconds.
- 100% deterministic cleanup of temporary frames and audio files (zero disk leakage).

**Scale/Scope**: Exactly 9 questions per challenge structured across 3 tiers (3 Easy, 3 Medium, 3 Hard).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle / Rule | Compliance Status | Architectural Implementation & Evidence |
| :--- | :--- | :--- |
| **I. Strict Type Safety & Pydantic Data Contracts** | **PASS** | All inter-module communication is governed by Pydantic v2 schemas (`QuizChallenge`, `QuizItem`, `AudioCueSheet`, `RemotionRenderProps`). Untyped dictionaries across boundaries are prohibited. |
| **II. Declarative Motion Rendering & Media Processing** | **PASS** | Remotion (React / TS / Tailwind) handles all 1080x1920 60fps visual layouts, animations, and typography via Remotion CLI. FFmpeg is used strictly for low-level media tasks. Managed context managers guarantee temporary file cleanup. |
| **III. Asynchronous & Resilient AI Engine** | **PASS** | AI generation uses exclusively Gemini REST API (`gemini-2.5-flash` / `gemini-3.8-flash`) via `google-genai` with `response_schema`. The Audio-only WebSocket Live API is completely avoided. |
| **IV. Isolated Testing & Contract Verification** | **PASS** | Unit and contract test suites cover each sub-service independently (`test_script_service.py`, `test_audio_service.py`, `test_orchestrator.py`) using deterministic offline fixtures before end-to-end assembly. |
| **V. Decoupled Sub-Service Boundaries** | **PASS** | Clear separation of responsibilities: `@script-service` (content only), `@audio-service` (speech/SFX/cues only), `@template-engine` (React/Remotion only), `@orchestrator` (pipeline execution only). |

## Project Structure

### Documentation (this feature)

```text
specs/002-quiz-shorts-generator/
├── plan.md              # This implementation plan
├── research.md          # Technical decisions and research findings
├── data-model.md        # Domain entities, audio cue sheets, and state model
├── quickstart.md        # Validation guide and run commands
├── checklists/
│   └── requirements.md  # Quality checklist for spec readiness
└── contracts/
    ├── quiz-schema.json    # JSON schema for 9-question 3-tier quiz
    ├── remotion-props.json # JSON schema for Remotion CLI props
    └── api-routes.md       # REST API contracts for FastAPI
```

### Source Code (repository layout)

```text
videoanalizer/
├── quiz/
│   ├── __init__.py
│   ├── config.py             # Quiz generator configuration & voice mapping
│   ├── models.py             # Pydantic v2 schemas (QuizItem, QuizChallenge, AudioCueSheet)
│   ├── script_service.py     # @script-service: Gemini REST generation & image search
│   ├── audio_service.py      # @audio-service: edge-tts synthesis & word boundary timing
│   ├── image_service.py      # Dynamic image search and download with local caching
│   ├── orchestrator.py       # @orchestrator: Pipeline coordination & Remotion CLI invocation
│   └── cli.py                # Command-line interface for quiz generation
├── api/
│   ├── routes_quiz.py        # FastAPI routes for async quiz job management
│   └── dependencies.py
assets/
├── backgrounds/              # Curated 9:16 vertical gameplay & 3D background loops
└── sfx/                      # Curated sound effects (timer_tick.wav, reveal_ding.wav, level_up.wav)
templates/
└── quiz-remotion/            # @template-engine: Declarative React 18 + Remotion video project
    ├── package.json
    ├── remotion.config.ts
    ├── tailwind.config.js
    ├── src/
    │   ├── index.ts          # Remotion root entry
    │   ├── Root.tsx          # Composition definitions (1080x1920, 60fps)
    │   ├── types.ts          # TypeScript interfaces matching remotion-props.json
    │   ├── QuizChallenge.tsx # Master 9-question challenge composition
    │   ├── components/
    │   │   ├── BackgroundLayer.tsx   # Looped background video with ambient dark overlay
    │   │   ├── TierHeader.tsx        # Dynamic tier banner (Level 1/2/3, neon badges, counter)
    │   │   ├── QuestionCard.tsx      # Open-Recall question prompt or image container
    │   │   ├── CountdownBar.tsx      # Smooth 3.0s progress bar animation at 60fps
    │   │   ├── KaraokeCaptions.tsx   # Word-by-word synchronized neon glow typography
    │   │   └── AnswerRevealCard.tsx  # High-impact answer pop-in card with glow pulse
tests/
├── unit/
│   └── quiz/
│       ├── test_models.py
│       ├── test_script_service.py
│       ├── test_audio_service.py
│       └── test_orchestrator.py
└── contract/
    └── quiz/
        ├── test_quiz_schema_contract.py
        └── test_remotion_props_contract.py
```

**Structure Decision**: Selected a modular decoupled architecture where Python handles AI data generation, audio synthesis, and headless pipeline execution, while the dedicated Remotion template (`templates/quiz-remotion/`) provides declarative React/Tailwind visual composition executed via CLI.

## Complexity Tracking

> No constitution violations detected. All requirements align with Constitution Principles I through V.

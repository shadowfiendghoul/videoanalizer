<!--
Sync Impact Report:
- Version change: 1.0.0 → 1.1.0 (expanded guidance & Remotion/FastAPI/Service isolation)
- List of modified principles:
  - II. Robust Media Processing & FFmpeg Isolation → II. Declarative Motion Rendering & Media Processing (Remotion & FFmpeg)
  - III. Asynchronous & Resilient External Communication (httpx & google-genai) → III. Asynchronous & Resilient AI Engine (Gemini REST API & Structured Outputs)
  - IV. Test-Driven & Contract Verification (NON-NEGOTIABLE) → IV. Isolated Testing & Contract Verification (NON-NEGOTIABLE)
  - V. Decoupled Architecture & Gradio UI Modularity → V. Decoupled Sub-Service Boundaries & Presentation Layer Modularity
- Added sections:
  - Sub-Service Boundaries & Execution Roles (@script-service, @audio-service, @template-engine, @orchestrator)
  - Motion Graphics & Visual Design Standards (Neon Dark Mode, Glassmorphism, Fluid 1080x1920 Layout)
- Removed sections:
  - None
- Follow-up TODOs:
  - None
-->

# VideoAnalyzer Constitution

## Core Principles

### I. Strict Type Safety & Pydantic Data Contracts
All internal data structures, application configurations, external API schemas, and inter-module exchanges MUST be modeled with strict Pydantic v2 schemas. Dynamic untyped dictionaries, raw tuples, and primitive-heavy argument lists across component boundaries are strictly prohibited. Data validation MUST occur immediately at system ingress and egress to ensure fail-fast guarantees. All cross-module communication MUST transmit strictly validated JSON contracts.

### II. Declarative Motion Rendering & Media Processing (Remotion & FFmpeg)
Video motion graphics, visual composition, and vertical layouts MUST be driven by Remotion (React / TypeScript / Tailwind CSS) as the declarative 9:16 rendering engine. The Python backend MUST orchestrate Remotion strictly via the Remotion CLI, passing typed props and input datasets without mutating template components directly. Supplementary media operations (audio extraction, waveform probing, video clipping, codec transcoding) MUST be isolated into dedicated media pipeline modules utilizing structured FFmpeg subprocesses or `ffmpeg-python`. All pipelines MUST enforce deterministic resource cleanup: temporary audio slices, frame caches, and render buffers MUST be managed via context managers and purged immediately upon job completion or failure.

### III. Asynchronous & Resilient AI Engine (Gemini REST API & Structured Outputs)
Multimodal reasoning and quiz batch generation MUST interact exclusively with the official Gemini REST API (targeting `gemini-2.5-flash` or `gemini-3.8-flash`) utilizing `google-genai` or `httpx` with native structured outputs enforced by Pydantic schemas. 
The Audio-only WebSocket Live API is STRICTLY PROHIBITED for batch question generation and offline content synthesis due to state non-determinism, ephemeral lifecycle, and lack of rigid schema validation contracts.
All network operations MUST implement explicit connection timeouts, exponential backoff with jitter for transient errors, and robust rate-limiting controls. Sensitive credentials (Google GenAI API keys) MUST NEVER be logged, persisted to disk, or committed to source control; they MUST be loaded via secure environment variables managed by Pydantic Settings.

### IV. Isolated Testing & Contract Verification (NON-NEGOTIABLE)
Each sub-service and module MUST be accompanied by comprehensive, isolated automated test suites before being merged into the orchestrator pipeline. External network dependencies (Gemini API endpoints, Edge TTS network requests) MUST be mocked with deterministic synthetic fixtures during standard test execution to guarantee rapid, reproducible, and offline-capable CI/CD runs. Media processing tests MUST provide minimal, lightweight synthetic fixtures rather than heavy external video files. No end-to-end pipeline may be assembled until all contributing module contracts have passed independent verification.

### V. Decoupled Sub-Service Boundaries & Presentation Layer Modularity
The application architecture MUST enforce strict role isolation among autonomous sub-services:
- `@script-service`: Exclusively responsible for trivia content generation and topic parsing via Gemini REST API, outputting strictly validated `QuizDatasetSchema` objects.
- `@audio-service`: Exclusively responsible for speech synthesis via `edge-tts`, pause timing analysis, audio duration extraction, and sound effects mixing.
- `@template-engine`: Exclusively responsible for React/Remotion presentation components (1080x1920 canvas, fluid CSS animations, countdown timer bar, option state highlights).
- `@orchestrator`: Exclusively responsible for binding datasets, audio cue sheets, and triggering the final MP4 render via Remotion/FFmpeg CLI without modifying internal component logic.
User interface and presentation layers (FastAPI / Uvicorn REST endpoints, Gradio interactive UI) MUST function strictly as presentation surfaces, completely decoupled from core domain services. The entire pipeline MUST remain fully executable and testable headlessly via Python CLI or service calls.

## Technology Stack & Operational Constraints

The VideoAnalyzer architecture is strictly bound to the following core technology standards:
- **Backend & Logic Runtime**: Python 3.11+ (leveraging modern type annotations, match-case, exception groups, and asyncio).
- **Web & API Framework**: FastAPI with Uvicorn (for high-performance asynchronous REST endpoints) and Gradio (for interactive GUI and prototyping).
- **Validation & Schemas**: Pydantic v2 (`BaseModel`, strict type validation, and Pydantic Settings).
- **AI Multimodal Engine**: Gemini REST API (`gemini-2.5-flash` / `gemini-3.8-flash`) via `google-genai` SDK and `httpx` with structured outputs.
- **Voice Narration & SFX**: `edge-tts` (Microsoft Neural Voices) for asynchronous speech synthesis, paired with a curated local sound effects (SFX) library.
- **Motion & Video Engine**: Remotion (Node.js runtime, React 18+, TypeScript, Tailwind CSS) for declarative 1080x1920 60fps rendering, executed via Remotion CLI from Python.
- **Audio/Video Utility Engine**: FFmpeg (system binary) orchestrated via structured subprocesses or `ffmpeg-python`.
- **Filesystem & OS Compatibility**: Cross-platform portability across Windows, Linux, and macOS using `pathlib.Path`.

## Sub-Service Boundaries & Execution Roles

To ensure maintainability, testability, and clarity across agentic workflows, responsibilities are partitioned as follows:

| Service / Sub-Agent | Primary Responsibility | Input Contract | Output Contract | Prohibitions |
| :--- | :--- | :--- | :--- | :--- |
| **`@script-service`** | Quiz batch generation & structured parsing | Topic prompt, batch size, target language | `QuizDatasetSchema` (Pydantic v2 validated JSON) | MUST NOT perform audio synthesis, image rendering, or video encoding. |
| **`@audio-service`** | Speech synthesis & audio timeline assembly | Text narration strings, voice configuration, SFX cues | Synthesized audio track + `AudioCueSheet` (timestamps & durations) | MUST NOT generate question content or compile video frames. |
| **`@template-engine`** | Declarative 9:16 motion components & visual styling | React props conforming to `QuizRenderProps` | Rendered 1080x1920 60fps video frames / composition bundle | MUST NOT make network calls or directly trigger backend APIs. |
| **`@orchestrator`** | Pipeline coordination & headless render triggering | User request parameters, environment config | Finalized MP4 video path & render execution report | MUST NOT alter internal layout code or bypass Pydantic contract validation. |

## Motion Graphics & Visual Design Standards

All visual templates generated for vertical platforms (TikTok, YouTube Shorts, Instagram Reels) MUST adhere to the following design system constraints:
- **Canvas Specifications**: Exactly 1080x1920 resolution, 9:16 vertical aspect ratio, rendered at 60.0 frames per second.
- **Visual Aesthetic**: Premium neon Dark Mode with Glassmorphism (semi-transparent frosted cards, subtle neon borders, high-contrast readable typography).
- **Responsive & Fluid Layout**: Layouts MUST use Tailwind CSS flexbox, grid, and relative viewport units (`vh`, `vw`, `%`). Manual pixel calculations (`top: 342px`) that risk truncation or breakage on varying text lengths are strictly forbidden.
- **Color Semantics**:
  - Background: Dark ambient overlay (`#0F172A` / `#020617` with subtle blur) over looped video.
  - Neutral Options: Translucent slate pill buttons (`bg-white/10 backdrop-blur-md text-white border-white/20`).
  - Correct Answer Highlight: Vivid neon emerald/green (`#22C55E` / `#10B981`) with glow pulse.
  - Incorrect Answer State: Dimmed and desaturated (`opacity-40 grayscale`).
  - Timer Bar: Vibrant neon accent (e.g., `#F59E0B` or `#EC4899`) depleting smoothly at 60 fps.

## Development Workflow & Quality Gates

To maintain high code quality, security, and architectural integrity:
- **Linting & Formatting**: Code MUST adhere to strict standards with automated linting and formatting (Ruff for Python, Biome / ESLint / Prettier for TypeScript).
- **Static Typing**: Strict static typing MUST be enforced across all Python modules (`mypy` / Ruff) and Remotion components (`tsc` with strict mode enabled).
- **Error Handling**: Custom domain exception hierarchies MUST be used to isolate media processing errors, network failures, and schema parsing rejections. Generic `except Exception:` blocks that swallow errors are strictly forbidden.
- **Resource Management**: Any file system artifacts created in temporary directories during video composition MUST be isolated by task/job IDs and purged upon completion or error.

## Governance

This Constitution represents the supreme architectural and development policy for VideoAnalyzer. All feature specifications, implementation plans, code contributions, and pull requests MUST comply with the principles and constraints established herein.

- **Amendment Policy**: Amending this constitution requires explicit rationale, impact analysis, and consensus.
- **Versioning Policy**: This document follows Semantic Versioning:
  - **MAJOR** version increments indicate breaking governance shifts, removals, or fundamental architectural redesigns.
  - **MINOR** version increments indicate the addition of new principles, expanded guidance, or added technology stack constraints.
  - **PATCH** version increments indicate wording clarifications, formatting adjustments, or typo fixes.
- **Compliance Gates**: Implementation plans (`plan.md`) and task breakdowns (`tasks.md`) MUST reference and conform to the principles defined in this constitution.

**Version**: 1.1.0 | **Ratified**: 2026-10-10 | **Last Amended**: 2026-10-10

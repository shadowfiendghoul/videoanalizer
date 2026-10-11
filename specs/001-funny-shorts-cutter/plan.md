# Implementation Plan: Automated Funny Moments TikTok/Shorts Generator

**Branch**: `001-funny-shorts-cutter` | **Date**: 2026-10-10 | **Spec**: [spec.md](file:///c:/Users/User/Desktop/videoanalizer/specs/001-funny-shorts-cutter/spec.md)

**Input**: Feature specification from `specs/001-funny-shorts-cutter/spec.md`

## Summary

Build a Gradio web application that accepts YouTube links or local video uploads, analyzes them with Google Gemini 2.5 Flash (Native Audio Dialog) to detect funny moments, reframes content vertically (9:16) with streamer split-screen support, trims silences with micro-crossfades, overlays TikTok karaoke-style subtitles and AI-generated hook headlines, then renders and exports final MP4 shorts to the user's local machine.

## Technical Context

**Language/Version**: Python 3.11+ (type hints, pattern matching, asyncio, exception groups)

**Primary Dependencies**:
- `google-genai` — official Google GenAI SDK for Gemini 2.5 Flash multimodal analysis (humor detection, transcription, hook headline generation)
- `ffmpeg-python` — FFmpeg process orchestration for video probing, clipping, reframing, silence detection, subtitle burning, and final H.264/AAC encoding
- `gradio` — web UI framework for video upload, parameter controls, crop coordinate inputs, preview player, and file download
- `pydantic` + `pydantic-settings` — strict data model validation for all entities, configurations, and API response schemas
- `httpx` — async HTTP client for YouTube video metadata resolution and any supplemental network operations
- `yt-dlp` — YouTube video download engine (called as subprocess or library)

**Storage**: Local filesystem only. Temporary processing workspace per session under `tempfile`-managed directories with `pathlib.Path`. Output MP4 files to user-designated local directory.

**Testing**: `pytest` with `pytest-asyncio`. Mock `google-genai` and `httpx` calls with deterministic fixtures. Minimal synthetic video fixtures (short 1-2 second clips) for FFmpeg pipeline tests.

**Target Platform**: Windows/Linux/macOS desktop (local Gradio server at `http://localhost:7860`)

**Project Type**: Desktop web application (Gradio-based local server + Python backend)

**Performance Goals**: Analysis results within 60 seconds for videos under 15 minutes (SC-001). Full render pipeline under 5 minutes end-to-end (SC-005).

**Constraints**: No cloud deployment required. API key loaded from environment variable `GOOGLE_API_KEY` via Pydantic Settings. FFmpeg must be pre-installed on PATH.

**Scale/Scope**: Single-user local application. 1-10 concurrent highlight clips per analysis session. Source video duration up to 60 minutes (primary), up to 2+ hours (edge case with chunked processing).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Evidence |
|---|-----------|--------|----------|
| I | Strict Type Safety & Pydantic Data Contracts | ✅ PASS | All entities (SourceVideo, HighlightSegment, LayoutPreset, ClipRenderJob) modeled as Pydantic BaseModel. Config via Pydantic Settings. No untyped dicts at component boundaries. |
| II | Robust Media Processing & FFmpeg Isolation | ✅ PASS | Dedicated `media/` package isolates all FFmpeg operations (probing, clipping, silence detection, reframing, subtitle burning). Context managers for temp file lifecycle. Chunked processing for long videos. |
| III | Asynchronous & Resilient External Communication | ✅ PASS | `google-genai` SDK and `httpx` used for all external calls. Timeouts, exponential backoff, rate-limit compliance configured. API key loaded from env via Pydantic Settings, never logged or persisted. |
| IV | Test-Driven & Contract Verification | ✅ PASS | pytest test suites with mocked GenAI responses and synthetic media fixtures. No real network calls in CI. Lightweight 1-2 second test videos. |
| V | Decoupled Architecture & Gradio UI Modularity | ✅ PASS | Gradio UI in `ui/` package is strictly presentation layer. All domain logic in `services/` and `media/` packages. Core engine testable as standalone library without Gradio. |

No constitution violations. No complexity justification required.

## Project Structure

### Documentation (this feature)

```text
specs/001-funny-shorts-cutter/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── gemini-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
videoanalizer/
├── __init__.py
├── __main__.py              # Entry point: python -m videoanalizer
├── config.py                # Pydantic Settings (API keys, defaults, paths)
├── exceptions.py            # Custom domain exception hierarchy
├── models/
│   ├── __init__.py
│   ├── source_video.py      # SourceVideo model
│   ├── highlight.py         # HighlightSegment model
│   ├── layout.py            # LayoutPreset, CropBox models
│   └── render_job.py        # ClipRenderJob model
├── services/
│   ├── __init__.py
│   ├── ingestion.py         # Video download (yt-dlp) & local file validation
│   ├── analyzer.py          # Gemini API humor analysis orchestrator
│   ├── transcriber.py       # Word-level transcription for karaoke subtitles
│   ├── silence.py           # Audio silence detection & segment computation
│   └── headline.py          # AI hook headline generation
├── media/
│   ├── __init__.py
│   ├── probe.py             # FFmpeg probe: resolution, duration, codec info
│   ├── clipper.py           # Segment extraction from source video
│   ├── reframer.py          # 16:9 → 9:16 conversion (center crop & split screen)
│   ├── silence_cutter.py    # Audio silence removal with crossfade padding
│   ├── subtitler.py         # TikTok karaoke subtitle overlay via FFmpeg drawtext
│   ├── overlay.py           # Top banner / hook headline text overlay
│   └── renderer.py          # Final composition pipeline → H.264/AAC MP4
├── ui/
│   ├── __init__.py
│   ├── app.py               # Gradio app assembly & launch
│   ├── tabs/
│   │   ├── __init__.py
│   │   ├── ingest_tab.py    # Video input + analysis parameters tab
│   │   ├── highlights_tab.py # Highlight list + timestamp adjustment tab
│   │   ├── layout_tab.py    # Crop coordinates + split-screen config tab
│   │   ├── effects_tab.py   # Silence removal + subtitles + banner tab
│   │   └── export_tab.py    # Preview player + render + download tab
│   └── components/
│       ├── __init__.py
│       ├── crop_preview.py  # Real-time 9:16 frame preview component
│       └── video_player.py  # Integrated video preview player
└── utils/
    ├── __init__.py
    ├── tempfiles.py         # Session-scoped temp directory management
    └── ffmpeg_check.py      # FFmpeg availability verification

tests/
├── __init__.py
├── conftest.py              # Shared fixtures (synthetic videos, mock responses)
├── fixtures/
│   ├── sample_short.mp4     # 2-second synthetic test video
│   └── gemini_responses/    # Deterministic JSON mock responses
├── unit/
│   ├── test_models.py
│   ├── test_silence.py
│   ├── test_analyzer.py
│   └── test_reframer.py
├── integration/
│   ├── test_clipper_pipeline.py
│   └── test_render_pipeline.py
└── contract/
    └── test_gemini_contract.py
```

**Structure Decision**: Single-project flat layout. Gradio serves as the only user interface; no separate frontend/backend split. All domain logic resides in `videoanalizer/` package with clear sub-package boundaries (`models/`, `services/`, `media/`, `ui/`). Tests mirror source structure under `tests/`.

## Complexity Tracking

No constitution violations detected. Table intentionally left empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| — | — | — |

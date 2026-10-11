# Tasks: Automated Funny Moments TikTok/Shorts Generator

**Feature**: `001-funny-shorts-cutter` | **Date**: 2026-10-10 | **Spec**: [spec.md](specs/001-funny-shorts-cutter/spec.md) | **Plan**: [plan.md](specs/001-funny-shorts-cutter/plan.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency management, and base package structure

- [x] T001 Create project directory structure per plan.md layout (`videoanalizer/`, `videoanalizer/models/`, `videoanalizer/services/`, `videoanalizer/media/`, `videoanalizer/ui/`, `videoanalizer/ui/tabs/`, `videoanalizer/ui/components/`, `videoanalizer/utils/`, `tests/`, `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/fixtures/`)
- [x] T002 Create `pyproject.toml` with project metadata, Python 3.11+ requirement, and dependencies: `google-genai`, `ffmpeg-python`, `gradio`, `pydantic`, `pydantic-settings`, `httpx`, `yt-dlp`; dev dependencies: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`
- [x] T003 [P] Create all `__init__.py` files for packages: `videoanalizer/`, `videoanalizer/models/`, `videoanalizer/services/`, `videoanalizer/media/`, `videoanalizer/ui/`, `videoanalizer/ui/tabs/`, `videoanalizer/ui/components/`, `videoanalizer/utils/`, `tests/`
- [x] T004 [P] Create `videoanalizer/__main__.py` entry point (imports and launches Gradio app via `ui.app.launch()`)
- [x] T005 [P] Create `ruff.toml` with Python 3.11 target, line-length 100, select rules: E, W, F, I, N, UP, ANN, S, B, SIM

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T006 Implement `videoanalizer/config.py` — Pydantic Settings class `AppConfig` with fields: `google_api_key: SecretStr` (env `GOOGLE_API_KEY`, required), `gemini_model: str` (default `"gemini-2.5-flash"`), `output_dir: Path` (default `Path("./output")`), `temp_dir: Path | None` (default `None`), `default_clip_count: int` (range 1–10, default 3), `default_min_duration: float` (range 15.0–90.0, default 30.0), `default_max_duration: float` (range 15.0–90.0, default 60.0), `silence_threshold_sec: float` (default 1.0, min 0.3), `silence_db: float` (default -30.0), `crossfade_ms: int` (default 25), `padding_ms: int` (default 100). Validator: `default_min_duration` ≤ `default_max_duration`.
- [x] T007 [P] Implement `videoanalizer/exceptions.py` — Custom exception hierarchy: `VideoAnalyzerError` (base), `IngestionError`, `DownloadError(IngestionError)`, `UnsupportedFormatError(IngestionError)`, `AnalysisError`, `AnalysisTimeoutError(AnalysisError)`, `RateLimitError(AnalysisError)`, `SchemaValidationError(AnalysisError)`, `ContentFilteredError(AnalysisError)`, `MediaProcessingError`, `RenderError(MediaProcessingError)`, `FFmpegNotFoundError(MediaProcessingError)`, `ConfigurationError`
- [x] T008 [P] Implement `videoanalizer/models/source_video.py` — Pydantic model `SourceVideo` with fields per data-model.md: `id: str` (UUID4 default_factory), `origin: Literal["youtube", "local"]`, `original_url: str | None` (required if origin=="youtube"), `local_path: Path` (must exist), `filename: str`, `duration_sec: float` (>0), `width: int` (>0), `height: int` (>0), `fps: float` (>0), `codec: str`, `audio_codec: str | None`, `file_size_bytes: int` (≥0)
- [x] T009 [P] Implement `videoanalizer/models/highlight.py` — Pydantic models `WordTiming` (fields: `word: str` non-empty, `start_sec: float` ≥0, `end_sec: float` > start_sec) and `HighlightSegment` (fields per data-model.md: `id: str` UUID4, `source_video_id: str`, `start_sec: float` ≥0, `end_sec: float` > start_sec, `humor_score: float` range 0.0–10.0, `summary: str` max 200 chars, `transcript: str`, `word_timings: list[WordTiming]`, `suggested_headline: str` max 100 chars, `is_selected: bool` default True, computed property `duration_sec`)
- [x] T010 [P] Implement `videoanalizer/models/layout.py` — Pydantic models `CropBox` (fields: `x: int` ≥0, `y: int` ≥0, `width: int` >0, `height: int` >0) and `LayoutPreset` (fields: `mode: Literal["center_crop", "split_screen"]`, `webcam_box: CropBox | None`, `gameplay_box: CropBox | None`, `webcam_position: Literal["top", "bottom"]` default "top"). Validator: if mode=="split_screen" then webcam_box and gameplay_box MUST be non-None
- [x] T011 [P] Implement `videoanalizer/models/render_job.py` — Pydantic models `SubtitleStyle` (fields per data-model.md: font_name default "Arial Bold", font_size range 16–72 default 42, active_color default "#FFFF00", inactive_color default "#FFFFFF", outline_color default "#000000", outline_width range 1–8 default 4, position_vertical_pct range 0.5–0.95 default 0.78), `SilenceConfig` (enabled default True, threshold_sec default 1.0 min 0.3, noise_db default -30.0, padding_ms default 100 min 0, crossfade_ms default 25 min 0), `BannerConfig` (enabled default True, text max 120 chars, font_size range 20–60 default 36, font_color default "#FFFFFF", bg_color default "#000000AA", position default "top"), `ClipRenderJob` (id UUID4, highlight: HighlightSegment, layout: LayoutPreset, silence: SilenceConfig, subtitles: SubtitleStyle, subtitles_enabled default True, banner: BannerConfig, output_width default 1080, output_height default 1920, output_fps allowed [30,60] default 30, output_path: Path | None, status: Literal["pending","rendering","complete","failed"] default "pending", error_message: str | None)
- [x] T012 [P] Implement `videoanalizer/models/__init__.py` — Re-export all model classes: SourceVideo, WordTiming, HighlightSegment, CropBox, LayoutPreset, SubtitleStyle, SilenceConfig, BannerConfig, ClipRenderJob
- [x] T013 [P] Implement `videoanalizer/utils/tempfiles.py` — `SessionTempDir` context manager class: creates unique temp directory (under config.temp_dir or system tempdir) named with session UUID, provides `path` property, recursively deletes directory on `__exit__` or explicit `cleanup()`. Must handle Windows file-locking gracefully.
- [x] T014 [P] Implement `videoanalizer/utils/ffmpeg_check.py` — Function `ensure_ffmpeg() -> str` that verifies `ffmpeg` is on PATH via `subprocess.run(["ffmpeg", "-version"])`, returns FFmpeg version string, raises `FFmpegNotFoundError` if not found
- [x] T015 Create `tests/conftest.py` — Shared pytest fixtures: `tmp_session_dir` (temporary directory), `sample_config` (AppConfig with test API key), `mock_source_video` (SourceVideo instance with test values)
- [x] T016 [P] Create `tests/fixtures/gemini_responses/humor_analysis.json` — Deterministic mock Gemini response per contracts/gemini-api.md mock response section

**Checkpoint**: Foundation ready — all models, config, exceptions, and utilities are in place. User story implementation can now begin.

---

## Phase 3: User Story 1 — Video Ingestion & AI Funny Moments Detection (Priority: P1) 🎯 MVP

**Goal**: User submits a YouTube URL or uploads a local video file, configures clip count and duration range, and receives a ranked list of detected funny moments with timestamps, humor scores, transcripts, and hook headlines.

**Independent Test**: Submit a 5-minute video with target count 2 and duration 30-45s. Verify system detects funny conversational peaks and displays them with timestamps in the web interface.

### Implementation for User Story 1

- [x] T017 [US1] Implement `videoanalizer/media/probe.py` — Function `probe_video(path: Path) -> dict` using `ffmpeg.probe()` to extract: duration, width, height, fps, video codec, audio codec, file size. Return parsed dict. Raise `MediaProcessingError` on probe failure or unsupported format.
- [x] T018 [US1] Implement `videoanalizer/services/ingestion.py` — Class `IngestionService` with methods: `download_youtube(url: str, dest_dir: Path) -> Path` (runs `yt-dlp` subprocess with format selection `bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best`, raises `DownloadError` on failure), `validate_local_file(path: Path) -> None` (checks file exists, extension in [.mp4,.mkv,.mov,.webm], probes with FFmpeg, raises `UnsupportedFormatError` if invalid), `ingest(source: str, session_dir: Path) -> SourceVideo` (detects URL vs path, downloads if YouTube, probes, returns populated SourceVideo model)
- [x] T019 [US1] Implement `videoanalizer/services/analyzer.py` — Class `AnalyzerService` with method `analyze(video: SourceVideo, clip_count: int, min_duration: float, max_duration: float, config: AppConfig) -> list[HighlightSegment]`. Uploads video to Gemini 2.5 Flash via `google-genai` SDK using structured JSON output mode per contracts/gemini-api.md. Parses response into HighlightSegment models. Implements: 120s timeout, exponential backoff (base 2s, max 3 retries) for 429 errors, raises `AnalysisTimeoutError`, `RateLimitError`, `SchemaValidationError`, `ContentFilteredError` as appropriate. For videos >100MB, extracts audio via FFmpeg and sends audio-only.
- [x] T020 [US1] Implement `videoanalizer/ui/tabs/ingest_tab.py` — Gradio Blocks tab with: URL text input OR file upload component (accept: .mp4,.mkv,.mov,.webm), clip count slider (1-10, default 3), min duration slider (15-90, default 30), max duration slider (15-90, default 60), "Analyze Video" button. On click: calls IngestionService.ingest() then AnalyzerService.analyze(), stores results in Gradio State, switches to highlights tab. Shows progress indicator during analysis. Displays error messages for invalid URLs, unsupported formats, or API failures.
- [x] T021 [US1] Implement `videoanalizer/ui/tabs/highlights_tab.py` — Gradio Blocks tab displaying detected highlights as a list/table: columns for start time, end time, duration, humor score, summary, hook headline. Each row has a checkbox for selection (is_selected). Start/end time fields are editable number inputs for manual boundary adjustment. Sorted by humor_score descending.
- [x] T022 [US1] Implement `videoanalizer/ui/app.py` — Gradio Blocks app assembly: creates tabbed interface with IngestTab and HighlightsTab (Layout, Effects, Export tabs added in later phases). Shared Gradio State for SourceVideo and list[HighlightSegment]. Launch function with `server_name="0.0.0.0"`, `server_port=7860`.

**Checkpoint**: User Story 1 complete. User can input video, run AI analysis, and see ranked funny moments. This is the functional MVP.

---

## Phase 4: User Story 2 — Vertical (9:16) Reframing & Streamer Layout (Priority: P2)

**Goal**: User configures 16:9 → 9:16 conversion with center crop or streamer split-screen using coordinate-based crop boxes with live frame preview.

**Independent Test**: Select a highlight, toggle between centered crop and split-screen, adjust crop coordinates, and verify the 9:16 preview frame renders correctly.

### Implementation for User Story 2

- [x] T023 [US2] Implement `videoanalizer/media/clipper.py` — Function `extract_clip(source_path: Path, start_sec: float, end_sec: float, output_path: Path) -> Path` using ffmpeg-python to extract segment with re-encoding. Raise `MediaProcessingError` on failure. Function `extract_frame(source_path: Path, timestamp_sec: float, output_path: Path) -> Path` to extract a single JPEG frame at given timestamp.
- [x] T024 [US2] Implement `videoanalizer/media/reframer.py` — Class `Reframer` with methods: `center_crop(input_path: Path, output_path: Path, target_w: int=1080, target_h: int=1920) -> Path` (FFmpeg crop=ih*9/16:ih centered, then scale to target), `split_screen(input_path: Path, output_path: Path, webcam_box: CropBox, gameplay_box: CropBox, webcam_position: str="top", target_w: int=1080, target_h: int=1920) -> Path` (two crop filters with user coordinates, each scaled to target_w × target_h//2, vstack). `preview_frame(source_path: Path, timestamp_sec: float, layout: LayoutPreset) -> bytes` returns JPEG bytes of a single reframed preview frame.
- [x] T025 [US2] Implement `videoanalizer/ui/components/crop_preview.py` — Gradio component function that takes source video path + LayoutPreset + timestamp, calls `Reframer.preview_frame()`, returns PIL Image for display in Gradio Image component.
- [x] T026 [US2] Implement `videoanalizer/ui/tabs/layout_tab.py` — Gradio Blocks tab with: radio selector "Center Crop" / "Streamer Split Screen", webcam coordinate inputs (X, Y, Width, Height number fields, visible only in split_screen mode), gameplay coordinate inputs (X, Y, Width, Height number fields, visible only in split_screen mode), webcam position radio (Top/Bottom), "Preview Frame" button displaying 9:16 preview image. On mode change, toggle visibility of coordinate fields.
- [x] T027 [US2] Update `videoanalizer/ui/app.py` — Add LayoutTab to tabbed interface, wire LayoutPreset state to shared Gradio State.

**Checkpoint**: User Story 2 complete. User can configure vertical reframing and preview the 9:16 layout before rendering.

---

## Phase 5: User Story 3 — Silence Trimming, Dynamic Captions & Text Overlays (Priority: P3)

**Goal**: User enables silence removal with smooth crossfades, toggles TikTok karaoke subtitles, and edits AI-suggested hook headlines.

**Independent Test**: Process a clip with 2-second pauses. Verify pauses are cut with smooth audio transitions, karaoke subtitles display with word-level highlighting, and hook banner renders at top.

### Implementation for User Story 3

- [x] T028 [US3] Implement `videoanalizer/services/silence.py` — Class `SilenceDetector` with method `detect_silences(audio_path: Path, config: SilenceConfig) -> list[tuple[float, float]]` that runs FFmpeg `silencedetect` filter (noise=config.noise_db, d=config.threshold_sec), parses output for silence_start/silence_end timestamps. Method `compute_keep_segments(duration: float, silences: list[tuple[float, float]], padding_ms: int) -> list[tuple[float, float]]` that calculates speech segments to keep with config.padding_ms safety padding around speech boundaries, merging overlapping segments.
- [x] T029 [US3] Implement `videoanalizer/media/silence_cutter.py` — Function `cut_silences(input_path: Path, keep_segments: list[tuple[float, float]], output_path: Path, crossfade_ms: int=25) -> Path` that extracts each keep segment, applies `afade` in/out (duration=crossfade_ms) at splice points, concatenates via FFmpeg concat demuxer maintaining A/V sync. Returns output path.
- [x] T030 [US3] Implement `videoanalizer/services/transcriber.py` — Class `TranscriptionService` with method `get_word_timings(highlight: HighlightSegment) -> list[WordTiming]` that returns word_timings already extracted from Gemini response. Fallback method `estimate_word_timings(transcript: str, duration: float) -> list[WordTiming]` that proportionally spaces words across duration when Gemini word timings are missing or incomplete.
- [x] T031 [US3] Implement `videoanalizer/media/subtitler.py` — Function `generate_ass_subtitles(word_timings: list[WordTiming], style: SubtitleStyle, frame_width: int=1080, frame_height: int=1920) -> str` that creates ASS subtitle file content with karaoke `\kf` tags: active word in style.active_color with style.outline_width outline, inactive words in style.inactive_color, positioned at style.position_vertical_pct. Function `burn_subtitles(video_path: Path, ass_content: str, output_path: Path) -> Path` that writes ASS to temp file and applies FFmpeg `ass` filter.
- [x] T032 [US3] Implement `videoanalizer/media/overlay.py` — Function `add_banner(video_path: Path, banner: BannerConfig, output_path: Path, frame_width: int=1080) -> Path` that applies FFmpeg `drawbox` (semi-transparent background) + `drawtext` (banner text, font, color) at top or bottom position per banner.position.
- [x] T033 [US3] Implement `videoanalizer/services/headline.py` — Class `HeadlineService` with method `get_headline(highlight: HighlightSegment) -> str` that returns `highlight.suggested_headline` (already populated by Gemini analysis). Method `regenerate_headline(highlight: HighlightSegment, config: AppConfig) -> str` for user-requested re-generation via separate Gemini call with prompt: "Generate a short viral TikTok hook headline (max 100 chars) for this funny moment: {highlight.summary}".
- [x] T034 [US3] Implement `videoanalizer/ui/tabs/effects_tab.py` — Gradio Blocks tab with: checkbox "Remove Silences" (default checked), silence threshold slider (0.3-3.0s, default 1.0), checkbox "Auto Subtitles" (default checked), subtitle font size slider (16-72, default 42), active color picker (default #FFFF00), inactive color picker (default #FFFFFF), outline width slider (1-8, default 4), hook headline text input (pre-filled with AI suggestion), checkbox "Show Banner" (default checked), banner position radio (Top/Bottom).
- [x] T035 [US3] Update `videoanalizer/ui/app.py` — Add EffectsTab to tabbed interface, wire SilenceConfig, SubtitleStyle, and BannerConfig state objects.

**Checkpoint**: User Story 3 complete. User can configure silence removal, karaoke subtitles, and hook banners for their clips.

---

## Phase 6: User Story 4 — Interactive Preview & Local Video Export (Priority: P4)

**Goal**: User previews the fully composed vertical short and downloads the rendered MP4 to their local machine.

**Independent Test**: Click "Render Short", verify rendered MP4 is valid H.264/AAC 1080×1920, audio and video are synchronized, subtitles burned in, banner visible. Download the file and play in external player.

### Implementation for User Story 4

- [x] T036 [US4] Implement `videoanalizer/media/renderer.py` — Class `Renderer` with method `render(job: ClipRenderJob, source_video: SourceVideo, session_dir: Path) -> Path` that orchestrates the full pipeline: 1) extract clip (clipper), 2) reframe to 9:16 (reframer), 3) optionally cut silences (silence_cutter), 4) optionally burn subtitles (subtitler), 5) optionally add banner (overlay), 6) final encode to H.264/AAC MP4 at job.output_fps. Updates job.status through lifecycle. Returns output path. Raises `RenderError` on failure. All intermediate files use session_dir for isolation.
- [x] T037 [US4] Implement `videoanalizer/ui/components/video_player.py` — Gradio component function wrapping `gr.Video` for preview playback of rendered MP4 files.
- [x] T038 [US4] Implement `videoanalizer/ui/tabs/export_tab.py` — Gradio Blocks tab with: "Render Short" button (triggers Renderer.render() for selected highlight with current layout/effects config), progress bar during rendering, video preview player for rendered result, "Download" file download component for the rendered MP4, "Render All Selected" button for batch mode (iterates selected highlights sequentially, renders each, provides zip or multiple download links). Displays render status and errors.
- [x] T039 [US4] Update `videoanalizer/ui/app.py` — Add ExportTab to tabbed interface, wire render job execution with full state (SourceVideo, HighlightSegment, LayoutPreset, SilenceConfig, SubtitleStyle, BannerConfig). Ensure temp cleanup on session end via SessionTempDir context manager.

**Checkpoint**: User Story 4 complete. Full end-to-end pipeline functional: ingest → analyze → layout → effects → render → download.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quality improvements, tests, validation, and documentation

- [x] T040 [P] Create `tests/unit/test_models.py` — Unit tests for all Pydantic models: validation constraints (ranges, required fields, computed properties), serialization/deserialization, edge cases (min/max values, invalid inputs raise ValidationError)
- [x] T041 [P] Create `tests/unit/test_silence.py` — Unit tests for SilenceDetector: parse silencedetect output, compute_keep_segments with various silence/speech patterns, padding overlap merging, edge case with no silences
- [x] T042 [P] Create `tests/unit/test_analyzer.py` — Unit tests for AnalyzerService with mocked google-genai responses: successful analysis, empty highlights, API timeout, rate limit retry, invalid JSON response, content filtered
- [x] T043 [P] Create `tests/unit/test_reframer.py` — Unit tests for Reframer with synthetic video fixture: center_crop produces correct resolution, split_screen stacks correctly, preview_frame returns valid JPEG bytes
- [x] T044 [P] Create `tests/contract/test_gemini_contract.py` — Contract test verifying Gemini response JSON matches HighlightSegment schema using mock fixture from tests/fixtures/gemini_responses/humor_analysis.json
- [x] T045 [P] Create `tests/integration/test_render_pipeline.py` — Integration test: create minimal SourceVideo + HighlightSegment + config, run full Renderer.render() pipeline with synthetic 2-second video fixture, verify output MP4 exists, has correct resolution (1080×1920), contains audio track
- [x] T046 Create `tests/fixtures/sample_short.mp4` — Generate minimal 2-second synthetic test video via FFmpeg CLI: `ffmpeg -f lavfi -i testsrc=duration=2:size=1920x1080:rate=30 -f lavfi -i sine=frequency=440:duration=2 -c:v libx264 -c:a aac -shortest tests/fixtures/sample_short.mp4`
- [x] T047 [P] Create `README.md` at project root with: project description, prerequisites (Python 3.11+, FFmpeg, yt-dlp, Google API key), installation instructions, usage instructions (`python -m videoanalizer`), project structure overview, license
- [x] T048 [P] Create `.gitignore` at project root with entries: `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `output/`, `*.egg-info/`, `dist/`, `.pytest_cache/`, `.ruff_cache/`, `temp_*/`
- [x] T049 Run `quickstart.md` validation scenarios 1-6 to verify end-to-end functionality
- [x] T050 Code cleanup: run `ruff check --fix videoanalizer/ tests/` and `ruff format videoanalizer/ tests/`, fix any remaining lint issues

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational; uses clipper independently but integrates with US1 highlights
- **User Story 3 (Phase 5)**: Depends on Foundational; uses silence/subtitle modules independently but integrates with US1 highlights
- **User Story 4 (Phase 6)**: Depends on US1 (highlights), US2 (layout), US3 (effects) — orchestrates full pipeline
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — No dependencies on other stories — **MVP deliverable**
- **US2 (P2)**: After Foundational — Can be implemented independently of US1 (uses its own clip extraction)
- **US3 (P3)**: After Foundational — Can be implemented independently of US1/US2 (uses its own audio processing)
- **US4 (P4)**: After US1 + US2 + US3 — Orchestrates all prior stories into final pipeline

### Within Each User Story

- Models before services
- Services before media processing modules
- Media modules before UI tabs
- UI tabs before app.py integration

### Parallel Opportunities

- T003, T004, T005 (Phase 1 setup files) — all parallel
- T007–T016 (Phase 2 foundational) — all models, exceptions, utils are parallel
- T017, T018, T019 (US1 core services) — probe, ingestion, analyzer can parallelize partially
- T023, T024 (US2 clipper, reframer) — different files, parallel
- T028–T033 (US3 silence, subtitler, overlay, headline) — different files, parallel
- T040–T045 (Phase 7 tests) — all parallel

---

## Parallel Example: User Story 3

```
# Launch all US3 services in parallel (different files, no cross-dependencies):
T028: SilenceDetector in videoanalizer/services/silence.py
T029: silence_cutter in videoanalizer/media/silence_cutter.py
T030: TranscriptionService in videoanalizer/services/transcriber.py
T031: subtitler in videoanalizer/media/subtitler.py
T032: overlay in videoanalizer/media/overlay.py
T033: HeadlineService in videoanalizer/services/headline.py

# Then UI (depends on services):
T034: effects_tab in videoanalizer/ui/tabs/effects_tab.py
T035: app.py update
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T005)
2. Complete Phase 2: Foundational (T006–T016)
3. Complete Phase 3: User Story 1 (T017–T022)
4. **STOP and VALIDATE**: Test video ingestion + AI analysis independently
5. User can already submit videos and see detected funny moments

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → **MVP!** (ingest + analyze)
3. Add US2 → Test independently → Vertical reframing works
4. Add US3 → Test independently → Silence removal + subtitles + banners work
5. Add US4 → Test independently → Full render + export pipeline
6. Polish → Tests, docs, lint, validation

### Parallel Team Strategy

With multiple developers after Foundational:
- Developer A: User Story 1 (T017–T022)
- Developer B: User Story 2 (T023–T027)
- Developer C: User Story 3 (T028–T035)
- All converge: User Story 4 (T036–T039) — integration

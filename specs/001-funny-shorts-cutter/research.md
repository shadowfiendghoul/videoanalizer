# Research: Automated Funny Moments TikTok/Shorts Generator

**Feature**: `001-funny-shorts-cutter` | **Date**: 2026-10-10

## R1: Gemini 2.5 Flash Native Audio Dialog — Humor Detection

**Decision**: Use `google-genai` SDK with model `gemini-2.5-flash` and `Native Audio Dialog` mode. Send the full video (or audio-extracted segments for long videos) as multimodal input. Prompt instructs the model to return structured JSON with timestamped funny moment segments, humor scores, dialogue transcript, and suggested hook headlines.

**Rationale**: Gemini 2.5 Flash natively understands audio dialogue, comedic timing, tone, laughter, and emotional peaks without requiring separate ASR + NLP pipelines. Native Audio Dialog mode processes conversational audio directly, providing richer comedy detection than text-only analysis. The `google-genai` SDK provides structured output (JSON mode) for reliable parsing into Pydantic models.

**Alternatives considered**:
- OpenAI Whisper + GPT-4o: Requires separate transcription step, doubles latency and cost. No native audio understanding for comedic timing.
- Assembly AI + custom scoring: Adds third-party dependency, less accurate for humor/emotion detection than multimodal Gemini.

---

## R2: YouTube Video Download Strategy

**Decision**: Use `yt-dlp` as a subprocess (`subprocess.run`) rather than as a Python library import. Download best quality video+audio with format selection `bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best`. Store downloaded file in session-scoped temp directory.

**Rationale**: `yt-dlp` is the most actively maintained YouTube downloader, handles age-restricted videos (with cookies), geo-restrictions, and format negotiation. Subprocess invocation isolates yt-dlp crashes from the main Python process and avoids import-time dependency conflicts. Constitution Principle II mandates isolated media processing.

**Alternatives considered**:
- `pytube`: Abandoned, frequently breaks with YouTube changes.
- `yt-dlp` as Python library: Tighter coupling, harder to upgrade independently, and complex internal API.

---

## R3: Word-Level Transcription for TikTok Karaoke Subtitles

**Decision**: Use Gemini 2.5 Flash to produce word-level timestamps alongside humor detection in a single multimodal call. The structured JSON output includes per-word timing data for karaoke highlighting. For segments where Gemini returns sentence-level only, fall back to FFmpeg's `silencedetect` + proportional word spacing.

**Rationale**: Single API call for both humor detection and word-level transcription minimizes latency and API cost. Gemini 2.5 Flash's audio understanding provides accurate word boundaries for conversational speech. Constitution Principle III requires using `google-genai` for all multimodal operations.

**Alternatives considered**:
- OpenAI Whisper (`whisper.cpp`): Requires local GPU, separate dependency, and doesn't integrate with humor detection.
- Google Cloud Speech-to-Text: Separate API, additional billing, not covered by `google-genai` SDK.

---

## R4: Silence Detection & Removal with Crossfades

**Decision**: Use FFmpeg `silencedetect` audio filter to identify silent segments, then compute cut points with 100ms speech-boundary padding. Apply 25ms audio crossfades at each splice point using FFmpeg `acrossfade` or `afade` filters. Video frames are trimmed in sync using `concat` demuxer.

**Rationale**: FFmpeg's `silencedetect` is industry-standard for audio-level silence detection with configurable dB threshold and minimum duration. The padding + crossfade approach (per clarification FR-009) prevents word truncation and audio clicks. All processing stays within FFmpeg pipelines per Constitution Principle II.

**Alternatives considered**:
- `pydub` / `librosa` silence detection: Adds Python-level audio processing dependency, slower than FFmpeg for large files, requires loading full audio into memory.
- WebRTC VAD: More complex setup, designed for real-time applications, overkill for offline processing.

---

## R5: Vertical Reframing & Split-Screen Composition

**Decision**: Implement two modes via FFmpeg filter chains:
1. **Center Crop**: `crop=ih*9/16:ih` centered on horizontal midpoint, then `scale=1080:1920`.
2. **Streamer Split Screen**: Two `crop` filters with user-specified (X, Y, W, H) coordinate boxes, each scaled to 1080×960, then vertically stacked via `vstack` filter to produce 1080×1920.

**Rationale**: FFmpeg filter graphs handle all reframing natively without frame-by-frame Python processing. Coordinate-based cropping (per clarification FR-008) gives precise control. Constitution Principle II mandates FFmpeg for all media operations.

**Alternatives considered**:
- `moviepy`: Python frame-by-frame processing, orders of magnitude slower than FFmpeg filter graphs for full video processing.
- `Pillow` / `OpenCV` frame extraction: Requires decoding every frame into Python memory, not viable for 60-minute videos.

---

## R6: TikTok Karaoke Subtitle Rendering

**Decision**: Generate an ASS (Advanced SubStation Alpha) subtitle file with per-word timing and karaoke highlighting styles (active word in yellow `#FFFF00` with bold 4px black outline, inactive words in white `#FFFFFF` with 2px outline). Burn subtitles into video using FFmpeg `ass` filter. Position in lower-third (vertical ~70-85% of frame height).

**Rationale**: ASS format supports per-word karaoke timing natively (`\k` / `\kf` tags), rich styling (colors, outlines, positioning, animation), and is universally supported by FFmpeg's `libass` filter. This avoids frame-by-frame Python text rendering and keeps processing within FFmpeg per Constitution Principle II.

**Alternatives considered**:
- FFmpeg `drawtext` filter: Limited to line-level timing, no native karaoke word-highlight support.
- Pillow text rendering: Frame-by-frame Python processing, extremely slow, no animation support.
- SRT subtitles: No per-word styling or karaoke highlighting capability.

---

## R7: Gradio UI Architecture

**Decision**: Multi-tab Gradio Blocks interface with 5 tabs (Ingest, Highlights, Layout, Effects, Export). Each tab delegates to service/media layer functions. State management via Gradio `State` objects holding Pydantic model instances serialized to dict. File uploads and downloads use Gradio's built-in file components.

**Rationale**: Gradio Blocks API provides flexible multi-tab layouts, interactive components (sliders, number inputs, image preview, video preview), and built-in file upload/download. Constitution Principle V mandates Gradio as pure presentation layer with no domain logic.

**Alternatives considered**:
- Streamlit: Less flexible layout system, harder to build multi-step workflows, weaker video component support.
- Flask/FastAPI + React: Excessive complexity for a local single-user tool, requires maintaining two codebases.

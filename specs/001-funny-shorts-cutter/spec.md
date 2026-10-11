# Feature Specification: Automated Funny Moments TikTok/Shorts Generator

**Feature Branch**: `001-funny-shorts-cutter`

**Created**: 2026-10-10

**Status**: Ready for Planning

**Input**: User description: "Выполни speckit-specify. Мне нужно сделать прогу с веб интерфейсом которая будет принимать ссылку на ютуб видео либо локальное видео обрабатывать анализировать его на самые смешные моменты нарезать через google api модель Gemini 2.5 Flash Native Audio Dialog делать простенький монтаж типа субтитров добавление надписей по желанию обрезки смещения вебки например если стример убрать пустоты молчания потом сохранять готовое тик ток видео мне на комп."

## Clarifications

### Session 2026-10-10
- Q: How should the user configure the webcam and screen crop regions when creating a vertical streamer clip? (FR-008) → A: Interactive coordinate boxes (X, Y, Width, Height) with real-time visual crop preview in the web interface.
- Q: How should the system determine the quantity and duration of funny highlight clips extracted from a video? (FR-004) → A: Configurable clip count (1-10, default 3) and target duration slider (15-90s, default 30-60s) selectable prior to analysis.
- Q: How should the automated subtitles be styled and animated on the vertical video? (FR-010) → A: TikTok Karaoke Style: dynamic word-by-word highlighting (active word emphasized in vibrant yellow/green with bold high-contrast stroke) centered in lower third.
- Q: How should the top text banner / hook headline be generated for each short? (FR-011) → A: AI-suggested hook headline automatically generated per highlight with manual editing capability in the web interface.
- Q: How should the silence removal filter handle audio transitions between speech cuts? (FR-009) → A: Padded micro-crossfades: 100ms safety padding around speech boundaries with a 25ms audio crossfade to prevent audio clicks, pops, and unnatural word truncation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Video Ingestion & AI Funny Moments Detection (Priority: P1)

A content creator or editor provides either an online video link (YouTube) or uploads a local video file from their computer, specifies the target number of highlights (e.g. 3) and desired duration range (e.g. 30–60s). The system analyzes the audio dialogue, comedic timing, reactions, and conversational punchlines, returning a ranked list of the funniest highlights with timestamps, descriptions, and comedy ratings matching the requested constraints.

**Why this priority**: Without accurate ingestion and intelligent highlight identification, no clips can be edited or generated. This is the foundation of the tool.

**Independent Test**: Can be fully tested by submitting a 5-minute video with target count set to 2 clips of 30-45s, verifying that the system detects funny conversational peaks within that duration, and reviewing the generated timestamp segments in the web interface.

**Acceptance Scenarios**:

1. **Given** a valid YouTube URL or an uploaded local video file and user-defined clip count (1-10) and duration range (15-90s), **When** the user clicks "Analyze Video", **Then** the system downloads/ingests the media, processes the audio and visual streams, and presents the requested number of detected highlights with start time, end time, and humor score.
2. **Given** an invalid or inaccessible URL, **When** ingestion is initiated, **Then** the system displays a clear, actionable error message without crashing.
3. **Given** a video without spoken dialogue or discernible comedic moments, **When** analysis finishes, **Then** the system notifies the user that no high-confidence funny moments were detected and suggests adjusting the sensitivity threshold.

---

### User Story 2 - Vertical (9:16) Reframing & Streamer Layout Setup (Priority: P2)

The user configures the visual presentation of a selected clip for vertical platforms (TikTok, YouTube Shorts, Instagram Reels). For standard content, the user can apply a centered crop. For streamer broadcasts featuring both gameplay and a face camera, the user can configure a split-screen vertical layout (e.g. webcam on top, gameplay on bottom) by adjusting exact crop boundary boxes.

**Why this priority**: Modern short-form platforms require a 9:16 vertical aspect ratio. Providing streamer-aware split layouts is essential to prevent losing the speaker's reaction or critical gameplay details.

**Independent Test**: Can be tested on a single video clip by toggling between centered vertical crop and dual-pane split mode, adjusting coordinate boundaries, and generating a 9:16 preview frame.

**Acceptance Scenarios**:

1. **Given** a 16:9 horizontal video highlight, **When** the user selects "Streamer Split Screen", **Then** the interface provides coordinate boundary controls (X, Y, Width, Height) for both webcam and game screen zones, updating an instant 9:16 layout preview.
2. **Given** a standard landscape video without a facecam, **When** the user selects "Center Vertical Crop", **Then** the system frames the primary action within a 9:16 canvas.
3. **Given** user adjustments to framing boundaries, **When** the user requests a frame preview, **Then** the interface displays an accurate still frame showing the resulting 9:16 layout.

---

### User Story 3 - Silence Trimming, Dynamic Captions & Text Overlays (Priority: P3)

The user applies pacing and engagement enhancements to the selected highlight. The system automatically detects and cuts silent pauses (dead air) to speed up comedic rhythm with smooth padded crossfades. The user can toggle automated synchronized TikTok karaoke subtitles and edit or toggle an AI-suggested top banner hook headline.

**Why this priority**: Short-form audiences require fast pacing and dynamic subtitles for sound-off viewing and maximum audience retention.

**Independent Test**: Can be tested on a dialogue clip with deliberate 2-second pauses, confirming that pauses exceeding the threshold are cut smoothly with micro-crossfades, speech is captioned with accurate timestamps, and hook banner text renders properly.

**Acceptance Scenarios**:

1. **Given** a clip with pauses and dead air, **When** "Remove Silences" is enabled, **Then** the system cuts segments with silence exceeding 1.0 second using 100ms safety padding and 25ms audio micro-crossfades, eliminating audio pops and preserving natural speech cadence.
2. **Given** audio dialogue in the clip, **When** "Auto Subtitles" is checked, **Then** the system overlays dynamic TikTok karaoke-style captions (word-by-word synchronized highlighting with bold high-contrast outlines) in the lower-third vertical zone.
3. **Given** an AI-detected highlight, **When** the clip is prepared for editing, **Then** the system generates a suggested catchy hook headline (e.g. viral title) which the user can edit, re-style, or disable before rendering.

---

### User Story 4 - Interactive Preview & Local Video Export (Priority: P4)

The user previews the fully edited short video (layout, cuts, silence trimming, captions, and overlays) in the web interface. Once satisfied, the user triggers final rendering and downloads or saves the resulting MP4 video directly to their computer.

**Why this priority**: Delivers the final tangible asset to the user for immediate publication on social media.

**Independent Test**: Can be tested by clicking "Render & Save", confirming the file is saved to the local disk in valid MP4 format with synchronized audio/video, and playing the file in an external media player.

**Acceptance Scenarios**:

1. **Given** a configured clip, **When** the user clicks "Render Short", **Then** the system renders the vertical video and plays it in the built-in media previewer.
2. **Given** a rendered short video, **When** the user clicks "Download / Save to Local Disk", **Then** the MP4 file is saved to the user's local downloads or designated destination directory.
3. **Given** multiple detected highlights, **When** the user chooses batch rendering, **Then** all selected highlights are processed sequentially and saved with distinct descriptive filenames.

---

### Edge Cases

- **Corrupted or Unsupported Media Formats**: System validates incoming video and audio streams upon ingestion; if unreadable, it aborts gracefully with a user-friendly error message.
- **YouTube Age-Restricted or Geo-Blocked Videos**: If external video download fails due to platform restrictions, system notifies the user and suggests uploading the video file locally.
- **Overlapping Speech & Background Music**: When intense background music or multiple overlapping voices exist, the subtitle generator and silence trimmer maintain audio continuity without abruptly clipping speech mid-word.
- **Ultra-Long Videos (2+ hours)**: Large video streams must be processed efficiently in chunks to avoid browser timeouts or unbounded system resource consumption.
- **Videos Without Detectable Silences**: If a fast-paced clip has no silences exceeding the threshold, silence removal safely passes through without modifying timestamps.
- **Silence Trimming Artifacts**: 100ms word-boundary padding and 25ms micro-crossfades ensure quiet consonant sounds, breathing, and trailing syllables are not clipped prematurely.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a responsive web interface allowing users to either paste a YouTube video URL or upload a local video file (MP4, MKV, MOV, WEBM).
- **FR-002**: System MUST download and store external videos locally in a managed temporary workspace before processing.
- **FR-003**: System MUST perform automated conversational and comedic analysis on the video audio/dialogue track to identify humorous highlights, emotional peaks, and punchlines.
- **FR-004**: System MUST allow users to configure the desired number of clips (range 1–10, default: 3) and preferred duration window (range 15–90 seconds, default: 30–60 seconds) prior to analysis, returning ranked highlight segments that match these constraints with start timestamp, end timestamp, calculated comedy score, and concise moment summary.
- **FR-005**: System MUST allow users to preview and manually adjust highlight start and end boundaries prior to final video rendering.
- **FR-006**: System MUST convert landscape (16:9) video content into vertical (9:16) orientation suitable for TikTok, YouTube Shorts, and Reels.
- **FR-007**: System MUST provide a "Streamer Split Screen" mode that divides the 9:16 canvas into two stacked sections: an upper section for webcam/face reaction and a lower section for gameplay/content.
- **FR-008**: System MUST allow users to specify and adjust exact crop coordinate boxes (X, Y, Width, Height) for both the webcam and primary content zones in the web interface, with live frame preview.
- **FR-009**: System MUST support automated silence detection and cutting to eliminate pauses exceeding a configurable duration threshold (default: 1.0 second), applying 100ms word-boundary padding and 25ms audio micro-crossfades to prevent clicks and abrupt word cutoff.
- **FR-010**: System MUST generate synchronized dynamic subtitle captions using a TikTok karaoke style (word-by-word color highlighting with bold high-contrast outlines) positioned in the lower-third region of the vertical canvas.
- **FR-011**: System MUST automatically generate and propose a contextual hook headline for each detected highlight, allowing users to edit the text or toggle off the top banner overlay prior to rendering.
- **FR-012**: System MUST provide an integrated video preview player in the web UI for playback of generated vertical clips.
- **FR-013**: System MUST save rendered clips as standardized H.264/AAC MP4 files to a designated local directory or make them downloadable through the web interface.
- **FR-014**: System MUST ensure deterministic cleanup of temporary frame caches, audio buffers, and intermediate files upon task completion or cancellation.

### Key Entities

- **Source Video**: Represents the raw input media (origin: YouTube link or local upload, duration, resolution, audio tracks, local storage path).
- **Highlight Segment**: A detected or user-adjusted section of the source video (start time, end time, duration, humor score, summary, dialogue transcript, suggested hook headline).
- **Layout Preset**: Configuration defining how 16:9 frames map to 9:16 (Centered Crop vs. Streamer Split Screen with explicit X, Y, Width, Height coordinate boxes for webcam and gameplay).
- **Clip Render Job**: A rendering specification combining a Highlight Segment, Layout Preset, Silence Trimming settings (with padded crossfades), TikTok karaoke caption styling, and Text Overlays into a final MP4 output.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can ingest a video and receive detected funny moments within 60 seconds for videos under 15 minutes.
- **SC-002**: 90% of detected highlight clips capture coherent comedic dialogue segments without cutting off sentences mid-word.
- **SC-003**: Generated vertical videos strictly conform to 1080x1920 (9:16) resolution with 30/60 fps playback and synchronized audio.
- **SC-004**: Silence removal successfully cuts non-speech dead air while preserving natural speech cadence, reducing clip dead-time by at least 15% on casual gameplay streams.
- **SC-005**: Non-technical users can complete the entire pipeline from video link to downloaded TikTok clip in under 5 minutes without command-line intervention.
- **SC-006**: 100% of temporary intermediate media files are cleaned up from disk, preventing gradual storage leakage.

## Assumptions

- **Target Audience**: Content creators, streamers, and video editors seeking rapid short-form content generation without complex manual NLE editing software.
- **Target Video Duration**: Primary optimization target is source videos between 2 minutes and 60 minutes long.
- **Highlight Length**: Default target length for generated shorts is between 30 and 60 seconds (optimal for TikTok and YouTube Shorts algorithms), configurable from 15 to 90 seconds.
- **Silence Threshold**: Natural speech pauses under 1.0 second are preserved to maintain natural rhythm, while dead pauses over 1.0 second are trimmed by default using 100ms safety padding and 25ms micro-crossfades.
- **Hardware & Environment**: The application runs on the user's local machine with internet access for downloading YouTube links and communicating with remote AI analysis services.
- **Audio Language**: Dialogue analysis and subtitle generation primarily target standard conversational languages (e.g. Russian, English) supported by multimodal conversational models.

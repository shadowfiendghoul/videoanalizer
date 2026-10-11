# Data Model: Automated Funny Moments TikTok/Shorts Generator

**Feature**: `001-funny-shorts-cutter` | **Date**: 2026-10-10

All entities are implemented as strict Pydantic `BaseModel` classes per Constitution Principle I.

---

## Entity: AppConfig

**Purpose**: Application-wide configuration loaded from environment variables via Pydantic Settings.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `google_api_key` | `SecretStr` | Required, loaded from env `GOOGLE_API_KEY` | Gemini API key. NEVER logged or persisted to disk. |
| `gemini_model` | `str` | Default: `"gemini-2.5-flash"` | Model identifier for google-genai SDK. |
| `output_dir` | `Path` | Default: `Path("./output")` | Directory for rendered MP4 files. Created if missing. |
| `temp_dir` | `Path \| None` | Default: `None` (system tempdir) | Override for temporary processing directory. |
| `default_clip_count` | `int` | Range 1–10, default: `3` | Default number of highlights to detect. |
| `default_min_duration` | `float` | Range 15.0–90.0, default: `30.0` | Default minimum clip duration in seconds. |
| `default_max_duration` | `float` | Range 15.0–90.0, default: `60.0` | Default maximum clip duration in seconds. |
| `silence_threshold_sec` | `float` | Default: `1.0`, min: `0.3` | Silence duration threshold for trimming. |
| `silence_db` | `float` | Default: `-30.0` | dB level below which audio is considered silence. |
| `crossfade_ms` | `int` | Default: `25` | Audio crossfade duration in milliseconds for silence cuts. |
| `padding_ms` | `int` | Default: `100` | Speech-boundary safety padding in milliseconds. |

**Validation**: `default_min_duration` MUST be ≤ `default_max_duration`.

---

## Entity: SourceVideo

**Purpose**: Represents ingested raw video media (from YouTube URL or local upload).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `str` | UUID4, auto-generated | Unique session identifier for this video. |
| `origin` | `Literal["youtube", "local"]` | Required | Source type. |
| `original_url` | `str \| None` | Required if `origin == "youtube"` | YouTube URL provided by user. |
| `local_path` | `Path` | Required, must exist | Path to downloaded/uploaded video file on disk. |
| `filename` | `str` | Required | Original filename (for display and output naming). |
| `duration_sec` | `float` | > 0 | Total duration in seconds from FFmpeg probe. |
| `width` | `int` | > 0 | Video width in pixels. |
| `height` | `int` | > 0 | Video height in pixels. |
| `fps` | `float` | > 0 | Frames per second. |
| `codec` | `str` | Required | Video codec name (e.g. `"h264"`, `"vp9"`). |
| `audio_codec` | `str \| None` | Nullable | Audio codec (e.g. `"aac"`, `"opus"`). None if no audio. |
| `file_size_bytes` | `int` | ≥ 0 | File size on disk. |

**State transitions**: Created → Probed (after FFmpeg probe fills metadata) → Analyzed (after Gemini returns highlights).

---

## Entity: WordTiming

**Purpose**: Represents a single word with precise timing for karaoke subtitle synchronization.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `word` | `str` | Required, non-empty | The spoken word text. |
| `start_sec` | `float` | ≥ 0 | Word start time relative to highlight segment start. |
| `end_sec` | `float` | > `start_sec` | Word end time relative to highlight segment start. |

---

## Entity: HighlightSegment

**Purpose**: A detected or user-adjusted funny moment within the source video.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `str` | UUID4, auto-generated | Unique identifier for this highlight. |
| `source_video_id` | `str` | Required, references SourceVideo.id | Parent video. |
| `start_sec` | `float` | ≥ 0 | Highlight start time in source video (seconds). |
| `end_sec` | `float` | > `start_sec` | Highlight end time in source video (seconds). |
| `duration_sec` | `float` | Computed: `end_sec - start_sec` | Clip duration. |
| `humor_score` | `float` | Range 0.0–10.0 | AI-assigned comedy rating. |
| `summary` | `str` | Required, max 200 chars | Brief AI-generated moment description. |
| `transcript` | `str` | Required | Full dialogue transcript for this segment. |
| `word_timings` | `list[WordTiming]` | Required | Per-word timing data for karaoke subtitles. |
| `suggested_headline` | `str` | Required, max 100 chars | AI-generated hook headline for top banner. |
| `is_selected` | `bool` | Default: `True` | Whether user has selected this clip for rendering. |

**Validation**: `end_sec` MUST be > `start_sec`. `duration_sec` is a computed property. `humor_score` clamped to [0.0, 10.0].

---

## Entity: CropBox

**Purpose**: Defines a rectangular crop region within a source video frame.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `x` | `int` | ≥ 0 | Left edge X coordinate in source pixels. |
| `y` | `int` | ≥ 0 | Top edge Y coordinate in source pixels. |
| `width` | `int` | > 0 | Crop width in source pixels. |
| `height` | `int` | > 0 | Crop height in source pixels. |

**Validation**: `x + width` MUST be ≤ source video width. `y + height` MUST be ≤ source video height.

---

## Entity: LayoutPreset

**Purpose**: Configuration defining how 16:9 source frames are mapped to 9:16 vertical output.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `mode` | `Literal["center_crop", "split_screen"]` | Required | Layout mode. |
| `webcam_box` | `CropBox \| None` | Required if `mode == "split_screen"` | Webcam region bounding box. |
| `gameplay_box` | `CropBox \| None` | Required if `mode == "split_screen"` | Primary content region bounding box. |
| `webcam_position` | `Literal["top", "bottom"]` | Default: `"top"` | Webcam placement in split-screen vertical stack. |

**Validation**: If `mode == "split_screen"`, both `webcam_box` and `gameplay_box` MUST be non-None.

---

## Entity: SubtitleStyle

**Purpose**: Caption styling configuration for TikTok karaoke subtitles.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `font_name` | `str` | Default: `"Arial Bold"` | Font family for subtitle text. |
| `font_size` | `int` | Range 16–72, default: `42` | Font size in pixels. |
| `active_color` | `str` | Hex color, default: `"#FFFF00"` | Highlighted (current word) color. |
| `inactive_color` | `str` | Hex color, default: `"#FFFFFF"` | Non-highlighted word color. |
| `outline_color` | `str` | Hex color, default: `"#000000"` | Text outline/stroke color. |
| `outline_width` | `int` | Range 1–8, default: `4` | Outline stroke width in pixels. |
| `position_vertical_pct` | `float` | Range 0.5–0.95, default: `0.78` | Vertical position as fraction of frame height (lower third). |

---

## Entity: SilenceConfig

**Purpose**: Silence detection and removal configuration.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `enabled` | `bool` | Default: `True` | Whether silence removal is active. |
| `threshold_sec` | `float` | Default: `1.0`, min: `0.3` | Minimum silence duration to cut. |
| `noise_db` | `float` | Default: `-30.0` | dB level below which audio is silence. |
| `padding_ms` | `int` | Default: `100`, min: `0` | Safety padding around speech boundaries. |
| `crossfade_ms` | `int` | Default: `25`, min: `0` | Audio crossfade duration at splice points. |

---

## Entity: BannerConfig

**Purpose**: Top text banner / hook headline overlay configuration.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `enabled` | `bool` | Default: `True` | Whether top banner is rendered. |
| `text` | `str` | Max 120 chars | Banner text (AI-suggested, user-editable). |
| `font_size` | `int` | Range 20–60, default: `36` | Banner font size. |
| `font_color` | `str` | Hex color, default: `"#FFFFFF"` | Banner text color. |
| `bg_color` | `str` | Hex color, default: `"#000000AA"` | Semi-transparent background color (with alpha). |
| `position` | `Literal["top", "bottom"]` | Default: `"top"` | Banner placement. |

---

## Entity: ClipRenderJob

**Purpose**: Complete rendering specification for one output short video.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | `str` | UUID4, auto-generated | Unique render job identifier. |
| `highlight` | `HighlightSegment` | Required | Source highlight to render. |
| `layout` | `LayoutPreset` | Required | Vertical layout configuration. |
| `silence` | `SilenceConfig` | Required | Silence removal settings. |
| `subtitles` | `SubtitleStyle` | Required | Karaoke caption styling. |
| `subtitles_enabled` | `bool` | Default: `True` | Whether subtitles are rendered. |
| `banner` | `BannerConfig` | Required | Top banner configuration. |
| `output_width` | `int` | Default: `1080` | Output video width. |
| `output_height` | `int` | Default: `1920` | Output video height. |
| `output_fps` | `int` | Default: `30`, allowed: `[30, 60]` | Output framerate. |
| `output_path` | `Path \| None` | Set after render | Path to rendered MP4 file. |
| `status` | `Literal["pending", "rendering", "complete", "failed"]` | Default: `"pending"` | Render job state. |
| `error_message` | `str \| None` | Nullable | Error description if status is `"failed"`. |

**State transitions**: `pending` → `rendering` → `complete` | `failed`.

---

## Entity Relationships

```
AppConfig (singleton)
    │
    └── used by all services

SourceVideo
    │ 1
    └──── * HighlightSegment
              │ 1            └── * WordTiming
              │
              └──── 1 ClipRenderJob
                        ├── 1 LayoutPreset
                        │       ├── 0..1 CropBox (webcam)
                        │       └── 0..1 CropBox (gameplay)
                        ├── 1 SilenceConfig
                        ├── 1 SubtitleStyle
                        └── 1 BannerConfig
```

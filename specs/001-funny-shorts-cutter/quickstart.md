# Quickstart: Automated Funny Moments TikTok/Shorts Generator

**Feature**: `001-funny-shorts-cutter` | **Date**: 2026-10-10

## Prerequisites

1. **Python 3.11+** installed and available on PATH
2. **FFmpeg** installed and available on PATH (`ffmpeg -version` must succeed)
3. **yt-dlp** installed (`pip install yt-dlp` or system package)
4. **Google GenAI API Key** with Gemini 2.5 Flash access

## Setup

```bash
# Clone and navigate to project
cd videoanalizer

# Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Set API key (required)
# Windows PowerShell:
$env:GOOGLE_API_KEY = "your-key-here"
# Linux/macOS:
export GOOGLE_API_KEY="your-key-here"

# Verify FFmpeg
ffmpeg -version
```

## Run Application

```bash
python -m videoanalizer
# Opens Gradio UI at http://localhost:7860
```

## Validation Scenarios

### Scenario 1: Local Video Analysis (P1 — Core Pipeline)

**Steps**:
1. Open `http://localhost:7860` in browser
2. In "Ingest" tab, upload a local MP4 video file (2-5 minutes, with dialogue)
3. Set clip count to `2`, duration range `30-60s`
4. Click "Analyze Video"

**Expected**:
- Progress indicator shows analysis in progress
- Within 60 seconds, highlights tab populates with 2 detected segments
- Each segment shows: start/end timestamps, humor score (0-10), summary text, suggested hook headline
- No errors in terminal output

### Scenario 2: YouTube URL Ingestion (P1 — Download Pipeline)

**Steps**:
1. In "Ingest" tab, paste a public YouTube URL
2. Set clip count to `3`, duration range `30-45s`
3. Click "Analyze Video"

**Expected**:
- Download progress shown in UI
- Video downloaded to temp directory
- Analysis proceeds as in Scenario 1
- Temp files created in session-scoped directory

### Scenario 3: Streamer Split-Screen Layout (P2 — Reframing)

**Steps**:
1. After analysis, select a highlight in "Highlights" tab
2. Navigate to "Layout" tab
3. Select "Streamer Split Screen" mode
4. Set webcam box: X=0, Y=0, W=320, H=320 (top-left corner)
5. Set gameplay box: X=0, Y=0, W=1920, H=1080 (full frame)
6. Click "Preview Frame"

**Expected**:
- Preview image shows 1080×1920 vertical frame
- Top half: cropped webcam face region
- Bottom half: cropped gameplay region
- No black bars or distortion

### Scenario 4: Silence Removal + Subtitles (P3 — Effects)

**Steps**:
1. Navigate to "Effects" tab
2. Enable "Remove Silences" (threshold: 1.0s)
3. Enable "Auto Subtitles"
4. Edit or accept AI-suggested hook headline
5. Click "Apply Preview"

**Expected**:
- Timeline visualization shows removed silence gaps
- Subtitle preview shows karaoke-style word highlighting
- Hook headline appears at top of preview frame
- Audio transitions sound natural (no clicks or pops)

### Scenario 5: Render & Export (P4 — Final Output)

**Steps**:
1. Navigate to "Export" tab
2. Click "Render Short"
3. Wait for render to complete
4. Click "Download"

**Expected**:
- Rendered file is valid H.264/AAC MP4
- Resolution: 1080×1920 (9:16)
- Audio and video are synchronized
- Subtitles are burned in with karaoke styling
- Hook headline banner is visible at top
- File plays correctly in external media player (VLC, Windows Media Player)
- Temp processing files are cleaned up after download

### Scenario 6: Error Handling (Edge Cases)

**Steps**:
1. Submit an invalid YouTube URL → Expect clear error message
2. Upload a corrupted video file → Expect graceful abort with user-friendly message
3. Analyze a video with no dialogue → Expect "no funny moments detected" notification

**Expected**:
- No unhandled exceptions or application crashes
- Error messages are actionable (suggest what to do next)

## Run Tests

```bash
# Run full test suite
pytest tests/ -v

# Run only unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/ --cov=videoanalizer --cov-report=term-missing
```

**Expected**: All tests pass. No network calls made during testing (all external dependencies mocked).

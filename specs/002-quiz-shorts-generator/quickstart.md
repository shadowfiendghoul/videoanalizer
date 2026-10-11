# Quickstart & Verification Guide: Quiz Shorts Generator

**Feature**: `002-quiz-shorts-generator`  
**Date**: 2026-10-10  
**Status**: Ready for Implementation Testing

---

## 1. Prerequisites

Ensure system runtimes and environment keys are available:
1. **Python 3.11+** installed with virtual environment activated.
2. **Node.js 18+** and `npm` installed (required for Remotion CLI rendering).
3. **FFmpeg** installed and accessible in system `PATH`.
4. **Google Gemini API Key** set in environment:
   ```bash
   export GEMINI_API_KEY="your-api-key"
   # On Windows PowerShell:
   $env:GEMINI_API_KEY="your-api-key"
   ```

---

## 2. Setup & Installation

### Step A: Python Dependencies
```bash
rtk pip install edge-tts duckduckgo_search pydantic fastapi uvicorn google-genai
```

### Step B: Remotion Template Setup
From repository root:
```bash
cd templates/quiz-remotion
npm install
```

---

## 3. Independent Service Verification Scenarios

### Scenario 1: Verify Quiz Generation (`@script-service`)
Validates that Gemini REST API produces 9 questions divided across 3 tiers conforming to [`quiz-schema.json`](contracts/quiz-schema.json).
```bash
python -m pytest tests/unit/quiz/test_script_service.py -v
```
**Expected Outcome**: 9 questions generated with 3 Easy, 3 Medium, and 3 Hard items, non-empty correct answers, and validated Pydantic schema.

---

### Scenario 2: Verify Audio Narration & Karaoke Cues (`@audio-service`)
Validates that `edge-tts` produces audio files and extracts word-level boundary timestamps (`WordCue`).
```bash
python -m pytest tests/unit/quiz/test_audio_service.py -v
```
**Expected Outcome**: MP3/WAV files generated with non-empty word boundary lists, 3.0s think intervals, and accurate total duration.

---

### Scenario 3: Verify Remotion Composition Preview (`@template-engine`)
Validates the React 18 / Tailwind CSS canvas in the interactive Remotion Studio player.
```bash
cd templates/quiz-remotion
npx remotion preview
```
**Expected Outcome**: Browser opens at `http://localhost:3000`. The 1080x1920 canvas renders neon dark mode cards, dynamic color shifts (Green $\rightarrow$ Yellow $\rightarrow$ Red), countdown timer bar, and active word highlighting.

---

### Scenario 4: End-to-End Headless CLI Render (`@orchestrator`)
Executes the full automated pipeline from topic prompt to finished 1080x1920 60fps MP4 video.
```bash
python -m videoanalizer.quiz.cli --topic "Мировая география" --language "ru" --output "outputs/test_quiz.mp4"
```
**Expected Outcome**:
1. Output file `outputs/test_quiz.mp4` exists.
2. Resolution is exactly 1080x1920 at 60.0 fps.
3. Total duration is between 55 and 65 seconds.
4. Audio track has synchronized narration, ticking SFX, and reveal chimes.
5. All temporary cache directories (`temp/quiz_*`) are completely deleted.

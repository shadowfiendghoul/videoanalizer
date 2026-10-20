# Quickstart & Verification Guide: 008-widescreen-gaming-quiz

**Feature**: `008-widescreen-gaming-quiz`  
**Date**: 2026-10-20  
**Spec Reference**: [spec.md](spec.md)  
**Plan Reference**: [plan.md](plan.md)  
**Data Model**: [data-model.md](data-model.md)  

---

## 1. Minimal 1-Round 3-Question Test Render

To validate the Remotion composition, visual hierarchy, exact 9.0s question cycle, procedural masks, and audio synchronization without waiting for a full 50-question 10-minute render:

### Step 1: Run Synthetic Fixture Render via CLI
```bash
# Execute standalone test render with minimal 1-round (3 questions) dataset:
python -m videoanalizer.quiz.cli --mode widescreen_gaming_quiz \
  --test-fixture minimal_1round_3q \
  --profile gpu_fast \
  --output output/test_widescreen_quiz.mp4
```

### Step 2: Validate Timing & Coordinates in Render Output
Open `output/test_widescreen_quiz.mp4` in VLC or inspect with `ffprobe`:

```bash
ffprobe -v error -show_entries stream=width,height,r_frame_rate,duration -of default=noprint_wrappers=1 output/test_widescreen_quiz.mp4
```
**Expected Output**:
- `width=1920`
- `height=1080`
- `r_frame_rate=60/1`
- `duration=~50.0` seconds (8s intro + 3 x 9.0s questions + 15s outro = 50.0s).

---

## 2. Remotion Studio Local Preview

You can interactively inspect layout coordinates and spring animations inside the Remotion Studio preview:

```bash
cd templates/quiz-remotion
npm run start
```
1. Open `http://localhost:3000` in Google Chrome.
2. Select the **`WidescreenGamingQuiz`** composition in the left sidebar.
3. Verify visual hierarchy:
   - **Top Status Bar**: Round badge at `(120, 50)` and Question tracker at `(1480, 50)`.
   - **Central Asset Container**: `(360, 170, 1200, 600)` with fitted 1140x540 graphic.
   - **Countdown Timer Bar**: Linear shrinkage across frames `0–360` (0–6s) from amber to red.
   - **Answer Reveal Panel**: Frame `360` instant spring pop with sound stinger and 3s hold.
   - **Procedural Minimap**: Circular crop `clip-path: circle()` with rotating tactical radar sweep line.
   - **Procedural Silhouette**: High-contrast dark mask (`brightness: 0`) cross-fading to full color at frame `360`.

---

## 3. Automated Test Suite Execution

Run isolated unit and contract tests:

```bash
# Test 1: Pydantic v2 data models, validations, and bounds
pytest tests/unit/quiz/test_widescreen_quiz_models.py -v

# Test 2: Gemini @script-service prompt generation & schema parsing
pytest tests/unit/quiz/test_widescreen_quiz_script.py -v

# Test 3: @audio-service timeline calculator, ticking SFX, and ducking curves
pytest tests/unit/quiz/test_widescreen_quiz_audio.py -v

# Test 4: End-to-end headless render orchestrator verification
pytest tests/integration/quiz/test_widescreen_quiz_orchestrator.py -v
```

---

## 4. Web UI Verification & Moderation Workflow

1. Start the VideoAnalyzer web service:
   ```bash
   python -m videoanalizer.main
   ```
2. Navigate to `http://localhost:8000/quiz`.
3. In the Quiz Mode selector, select **"16:9 Widescreen Gaming Quiz"**.
4. Enter a theme prompt (e.g. *"50 Greatest PC & Console Games of All Time"*).
5. Click **"Сгенерировать викторину"** (`Generate Quiz`):
   - The `@script-service` generates 5 rounds of 10 questions.
   - Automated search gathers candidate screenshots and audio SFX cues.
6. In the Review & Moderation Panel:
   - Verify question prompts and uppercase answers.
   - Preview weapon audio cues with built-in mini audio player.
   - Toggle procedural radar circular mask or character silhouette filter.
   - Swap any candidate image with 1-click alternative search or local file upload.
7. Click **"Утвердить и отрендерить 1080p60"** (`Approve & Render`):
   - Real-time progress bar streams bundling, frame rendering, and encoding progress.
   - Final MP4 is saved to `output/` and displayed in the web player.

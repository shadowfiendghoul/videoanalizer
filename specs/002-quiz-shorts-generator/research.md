# Research & Technical Decisions: Quiz Shorts Generator

**Feature**: `002-quiz-shorts-generator`  
**Date**: 2026-10-10  
**Status**: Completed (Phase 0)

---

## 1. AI Quiz Generation & Schema Enforcement

### Decision
Use the official `google-genai` Python SDK calling the Gemini REST API with `model="gemini-2.5-flash"` (or `gemini-3.8-flash`) and enforce structured JSON output using Pydantic v2 schemas (`response_schema=QuizChallengeSchema`, `response_mime_type="application/json"`).

### Rationale
- **Constitution Principle I & III Compliance**: The constitution explicitly mandates Pydantic v2 data contracts and restricts AI communication to the official Gemini REST API with structured outputs.
- **Strict Schema Adherence**: Gemini's structured output mode guarantees 100% syntactically valid JSON strictly adhering to the requested fields (`difficulty`, `question_number`, `question_text`, `correct_answer`, `fun_fact`, `image_query`).
- **Low Latency & Cost Efficiency**: `gemini-2.5-flash` delivers sub-2-second generation latency for structured text prompts with negligible token costs.

### Alternatives Considered & Rejected
- **Audio-only WebSocket Live API**: *Strictly prohibited* by Constitution Principle III for batch generation due to lack of rigid schema validation, non-deterministic latency, and ephemeral state.
- **Free-form Markdown prompting with regex parsing**: Fragile and error-prone; prone to missing keys or unexpected syntax across difficulty levels.
- **Local LLMs (Ollama / Llama.cpp)**: High hardware requirement; unpredictable output schemas without substantial grammar constraints; inconsistent response latency on user hardware.

---

## 2. Voiceover Synthesis & Word-Level Timing Extraction

### Decision
Use `edge-tts` (asynchronous Microsoft Neural Voices) to synthesize:
1. Question text narration.
2. Correct answer narration with fun fact.
Extract word-level boundary timestamps (`offset`, `duration`, `text`) using `edge_tts.SubMaker` or the `WordBoundary` events emitted by the `Communicate` stream.

### Rationale
- **Zero Cost & High Quality**: `edge-tts` provides studio-quality neural voices (`ru-RU-DmitryNeural`, `en-US-ChristopherNeural`, `en-US-JennyNeural`) without requiring paid API keys or subscription services.
- **Native Word-Level Alignment**: `edge-tts` transmits exact millisecond offsets for each spoken word, which is the foundational prerequisite for synchronized TikTok karaoke captions.
- **Async Python Integration**: Integrates directly into `asyncio` workflows in `@audio-service`.

### Alternatives Considered & Rejected
- **Kokoro / Piper (Local TTS)**: Requires additional binary dependencies, ONNX runtimes, or PyTorch weights (~300MB–2GB), complicating user setup on Windows.
- **ElevenLabs / PlayHT**: Commercial paid services with monthly token limits; violates the requirement for accessible, lightweight generation.
- **pyttsx3 (SAPI5)**: Robotic, obsolete voice quality unsuitable for viral short-form social video.

---

## 3. Motion Graphics & Video Rendering Engine

### Decision
Use **Remotion** (React 18+, TypeScript, Tailwind CSS) orchestrated via the Remotion CLI (`npx remotion render`) from the Python backend.

### Rationale
- **Constitution Principle II Compliance**: Mandates Remotion as the declarative 9:16 motion engine.
- **Declarative Animation & High-End Aesthetics**: React + Tailwind CSS enables glassmorphism (`backdrop-blur-md`, semi-transparent frosted cards), responsive viewport scaling (`vh`, `vw`, `flex`, `grid`), and frame-perfect 60 FPS transitions via `useCurrentFrame()` and `interpolate()`.
- **Karaoke Caption Synchrony**: Remotion can precisely activate neon highlight classes based on the current frame matching word millisecond boundaries (`frame / fps * 1000 >= word.start_ms`).
- **Headless CLI Execution**: Python `@orchestrator` writes `render-props.json` and executes `npx remotion render <entry> <comp_id> --props=<path> --output=<out_path>`, keeping component code cleanly decoupled from backend logic.

### Alternatives Considered & Rejected
- **Pure FFmpeg complex filter graphs**: Generating 9 animated question transitions, progress bars, neon borders, and dynamic word-by-word highlights using `drawtext` and `overlay` filter graphs in FFmpeg is notoriously brittle, mathematically tedious (thousands of character-escape lines), and nearly impossible to design collaboratively.
- **MoviePy / OpenCV**: Slow software rendering, high memory usage, lacks modern CSS styling and hardware-accelerated text rendering.

---

## 4. Automated Image Search for Visual Topics

### Decision
Implement an asynchronous image search service in `@script-service` using DuckDuckGo Images (`duckduckgo_search` library) or an authenticated search endpoint, with an automatic fallback mechanism:
1. When a question has `image_query` (e.g. "Flag of Brazil", "Nike Logo"), search for high-resolution transparent PNG/SVG images.
2. Download and validate the image dimensions/format into a local cache directory (`temp/images/`).
3. If search fails or the file is corrupted, fall back to a stylized text/emoji card.

### Rationale
- Satisfies the clarified requirement (Option B) for dynamic image retrieval on the fly.
- Local caching ensures fast reuse and prevents broken remote URL links during video rendering.
- Robust exception handling ensures rendering never crashes due to a 404 or image download timeout.

### Alternatives Considered & Rejected
- **Pure dynamic URL passing to Remotion**: Dangerous during headless rendering; network hiccups during frame export can cause missing assets or blank frames.
- **AI Image Generation (Imagen / DALL-E)**: High cost and 5–10s generation time per image (x9 = 45–90s extra delay), which exceeds the performance budget.

---

## 5. Background Video & Sound Effects Orchestration

### Decision
- **Backgrounds**: Maintain a curated local directory `assets/backgrounds/` with 9:16 vertical 60fps MP4 loops (gameplay, 3D tunnel, abstract gradients). Python `@orchestrator` randomly selects a video and passes its path to Remotion's `<Video>` or `<Loop>` element.
- **Sound Effects (SFX)**: Curated local library in `assets/sfx/`:
  - `timer_tick.wav`: 3-second tension ticking audio loop.
  - `reveal_ding.wav`: Crisp victory chime.
  - `level_up.wav`: Dynamic synth riser/stinger played at tier boundaries (Easy $\rightarrow$ Medium $\rightarrow$ Hard).
- Remotion natively mixes SFX audio streams with `<Audio>` elements anchored to exact frame timestamps, preventing external FFmpeg audio-video drift.

---

## 6. Service Boundaries & Data Contracts

| Component | Technology | Input | Output |
| :--- | :--- | :--- | :--- |
| **`@script-service`** | Python 3.11, `google-genai`, `httpx` | Topic, Language | `QuizChallenge` (9 questions, 3 tiers, image paths) |
| **`@audio-service`** | Python 3.11, `edge-tts`, `soundfile` | Spoken strings, Voice | Audio WAV/MP3 files + `AudioCueSheet` |
| **`@template-engine`** | Remotion, React 18, Tailwind CSS | `RemotionRenderProps` (JSON) | 1080x1920 60fps MP4 video |
| **`@orchestrator`** | Python 3.11, Subprocess CLI | User request | Finalized video file & execution report |

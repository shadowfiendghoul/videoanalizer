# Research & Architectural Decisions: Batch Queue & AI Topic Generator

**Feature Branch**: `005-batch-queue-topics`  
**Date**: 2026-10-13  
**Status**: Completed  

---

## 1. Topic Ideation Strategy (Single & Batch)

### Context & Problem
Creators producing daily TikTok / YouTube Shorts quizzes face cognitive fatigue inventing viral trivia topics. Furthermore, generating topics one-by-one for a 10-video batch wastes API quota and risks repetitive themes.

### Decision
1. **Single Topic Ideation (`/api/v1/quiz/topics/suggest-single`)**:
   - Invokes Gemini with a specialized high-curiosity prompt tuned for viral TikTok Open-Recall formats.
   - Output schema: `TopicSuggestion` with `topic` (concise <= 60 chars), `category`, and `curiosity_hook`.
   - Supports an optional `category_hint` (e.g., "Наука", "Игры", "История", or blank for random chaos).
2. **Batch Topic Ideation (`/api/v1/quiz/topics/suggest-batch`)**:
   - In a **SINGLE Gemini API call**, requests $N$ (2 to 20) distinct, non-overlapping topics spanning varied niches (bizarre biology, historical paradoxes, cognitive illusions, gaming trivia, everyday mysteries).
   - Consumes **exactly 1 request** from the provider's 15 RPM quota.
   - Output schema: `BatchTopicList` containing an ordered list of `TopicSuggestion` items.

### Alternatives Considered
- *Separate API call per topic in batch*: Rejected because requesting 10 topics in separate calls would consume 10 requests out of the 15 RPM quota in seconds, leaving zero room for question generation.
- *Hardcoded topic dictionary*: Rejected because AI generation offers infinite variety, trending angles, and adaptability to optional user hints.

---

## 2. Gemini 15 RPM Rate Limiting & Progressive Generation

### Context & Problem
The user's Gemini model quota is **15 RPM** (Requests Per Minute) and **250K TPM**. Generating 9-question scripts for 10 videos requires 10 script generation calls. If fired concurrently, HTTP 429 `RESOURCE_EXHAUSTED` errors will crash the pipeline.

### Decision
1. **Async Rate Limiter (`PacedLimiter`)**:
   - Enforces a minimum interval of $\ge 5.0$ seconds between consecutive calls to the Gemini API ($60 / 5.0 = 12$ RPM max), guaranteeing a 20% safety margin under the 15 RPM ceiling.
2. **Progressive Background Generation Pipeline**:
   - When a batch is launched, Video 1 questions are generated first so the user can immediately begin review.
   - Questions for Videos 2..$N$ are enqueued into a background worker paced by the `PacedLimiter` (5-second spacing).
   - While the user inspects, edits, and verifies Video 1 (typically 20–45 seconds), Videos 2 and 3 finish in the background. By the time the user clicks "Одобрить и далее", the next video's questions are already cached.
3. **Resilient Retry & Exponential Backoff**:
   - On transient HTTP 429 / 503 errors, retry with exponential backoff ($5s, 10s, 20s$) up to 4 attempts.
   - Queue exposes `rate_limit_waiting: bool` and seconds remaining so the UI displays an informative status badge ("Ожидание квоты ИИ (15 RPM)...").

### Alternatives Considered
- *Wait for all 10 scripts to generate before opening review*: Would require $10 \times 5s = 50$ seconds of blank screen waiting for the user. Progressive background generation reduces initial perceived wait time to only ~3–4 seconds.
- *Unthrottled concurrent `asyncio.gather`*: Guaranteed to trigger 429 quota exhaustion immediately.

---

## 3. Sequential Background Render Queue (Hardware Safety)

### Context & Problem
Remotion video encoding utilizes Chromium/Puppeteer for 60fps frame capture and FFmpeg for video/audio muxing, consuming significant GPU/CPU/VRAM resources. Concurrent rendering crashes graphics drivers or triggers Node pipe EOF errors on consumer desktop hardware.

### Decision
1. **Strict Concurrency = 1 via `asyncio.Semaphore(1)`**:
   - The queue worker picks and renders only **one** approved video at any given moment.
   - Subsequent approved videos wait in `queued` status.
2. **Fault Isolation**:
   - If Video $k$ fails during rendering (e.g. invalid asset or timeout), that video is marked `failed` with its error message, and the queue worker automatically proceeds to Video $k+1$. The entire batch is not aborted.
3. **State & Progress Tracking**:
   - Each item tracks: `pending_approval`, `queued`, `rendering`, `completed`, `failed`, plus `progress_percent` (0–100%) and current `stage`.
   - Polling endpoint `GET /api/v1/quiz/batch/queue/status` returns full queue state.
4. **Result Access**:
   - Completed videos offer individual "Скачать MP4" buttons and video previews, plus a batch ZIP export endpoint (`GET /api/v1/quiz/batch/queue/download-all`).

---

## 4. Sequential Question Approval Wizard UI/UX

### Context & Problem
Users must be able to review and adjust questions for each video in the batch without losing edits when switching steps.

### Decision
1. **Interactive Step Wizard**:
   - Top progress bar / pill selector: "Видео 1 из N", "Видео 2 из N", etc.
   - Users can move forward ("Одобрить и далее") or backward ("Назад") or click any completed step index to re-inspect.
2. **Full Editing Capabilities**:
   - Inline editing of question text, correct answer, fun fact.
   - Image search and thumbnail selection per question.
   - Selective question regeneration via checkboxes + "Перегенерировать выбранные".
3. **Draft Preservation**:
   - Batch review state is kept in frontend memory / `sessionStorage`. If the user accidentally navigates away, draft questions and approvals remain intact.

---

## 5. Technology Stack Mapping

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Pydantic Schemas** | Pydantic v2 (`BaseModel`) | Constitution Principle I compliance: strict contracts for topics, batches, items. |
| **AI Topic Ideation** | Gemini REST API (`google-genai` / `types.GenerateContentConfig`) | Structured JSON outputs, single-call batch prompt. |
| **Pacing / Rate Limiter** | `asyncio.Lock` + timestamp token tracking | Precise $\ge 5.0$s interval enforcement without third-party Redis dependencies. |
| **Queue Orchestrator** | In-memory `BatchQueueManager` | Lightweight, zero-config, persistent across requests during server runtime. |
| **Motion Rendering** | Remotion CLI via `QuizOrchestrator` | Sequential FIFO execution via semaphore lock. |
| **Frontend UI** | Tailwind CSS + Vanilla JS in `quiz.html` | Seamless integration with existing dark glassmorphic styling. |

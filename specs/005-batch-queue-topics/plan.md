# Implementation Plan: Batch Queue & AI Topic Generator

**Branch**: `005-batch-queue-topics` | **Date**: 2026-10-13 | **Spec**: [specs/005-batch-queue-topics/spec.md](file:///C:/Users/User/Desktop/videoanalizer/specs/005-batch-queue-topics/spec.md)

**Input**: Feature specification from `specs/005-batch-queue-topics/spec.md` with strict Gemini 15 RPM / 250K TPM quota constraints.

---

## Summary

This feature implements:
1. **Single-Video AI Topic Suggestion**: Instant viral topic generation via Gemini REST API ("🎲 Придумать тему").
2. **Batch Topic Ideation**: Single API call creating $N$ (2–20) diverse, non-overlapping topics to conserve provider quotas.
3. **15 RPM Pacing & Progressive Script Generation**: Safe token bucket / timestamp pacing ($\ge 5.0$ seconds between consecutive calls, $\le 12$ RPM) with exponential backoff on HTTP 429. Progressive background generation caches upcoming scripts while the user reviews current items.
4. **Sequential Multi-Video Approval Wizard**: Step-by-step review interface ("Видео k из N") supporting inline editing, image search, and selective regeneration.
5. **Sequential Background Render Queue**: Strict single-concurrency execution (`asyncio.Semaphore(1)`) for Remotion renders to protect host hardware from VRAM/RAM crashes, with real-time status polling, failure isolation, and bulk download.

---

## Technical Context

**Language/Version**: Python 3.11+, JavaScript (ES2022 / HTML5), TypeScript (Remotion template)  
**Primary Dependencies**: FastAPI, Uvicorn, Pydantic v2, `google-genai`, `edge-tts`, Remotion CLI  
**Storage**: In-memory state with browser `sessionStorage` draft persistence; local disk for rendered MP4 and temporary job folders  
**Testing**: `pytest`, `pytest-asyncio`, isolated contract/unit tests with synthetic fixtures  
**Target Platform**: Windows 10/11 desktop, cross-platform Python  
**Project Type**: Web service + interactive browser GUI + CLI orchestrator  
**Performance Goals**:
- Single topic generation: $\le 3.5$s
- Batch topic generation ($N \le 20$): $\le 6.0$s in a single request
- Strict provider quota adherence: 0 unhandled 429 errors ($\le 12$ RPM)
- Video rendering: 1 concurrent render job, 60fps 1080x1920  
**Constraints**: Provider rate limit of 15 RPM / 250K TPM; strict concurrency = 1 during Remotion rendering  
**Scale/Scope**: Batches up to 20 videos per queue run  

---

## Constitution Check

*GATE: All principles from VideoAnalyzer Constitution v1.1.0 evaluated.*

| Constitution Principle | Status | Compliance Details |
| :--- | :--- | :--- |
| **I. Strict Type Safety & Pydantic Data Contracts** | PASS | All new endpoints and queue objects strictly adhere to Pydantic v2 schemas (`TopicSuggestion`, `BatchTopicList`, `BatchQueueItem`, `BatchQueueState`, `BatchRenderStartRequest`). No untyped dictionaries across boundaries. |
| **II. Declarative Motion Rendering (Remotion & FFmpeg)** | PASS | Remotion rendering invoked via `QuizOrchestrator` using CLI and typed JSON props. Concurrency locked to 1 (`asyncio.Semaphore(1)`) to avoid process crashes. Temporary assets cleaned up deterministically per job ID. |
| **III. Asynchronous & Resilient AI Engine (Gemini REST API)** | PASS | All topic and script generation uses Gemini REST API via `google-genai` SDK with structured outputs (`response_schema`). Live WebSocket API is strictly avoided. Rate limiter enforces $\ge 5.0$s intervals with exponential backoff on 429. |
| **IV. Isolated Testing & Contract Verification** | PASS | Unit and contract test suites cover rate limiting, batch topic parsing, queue state transitions, and API routes with synthetic mocks without live API calls. |
| **V. Decoupled Sub-Service Boundaries** | PASS | Topic generation resides in `@script-service` (`ScriptService`), queue management in `@orchestrator` / `BatchQueueManager`, and UI presentation in FastAPI routes and `quiz.html`. |

---

## Project Structure

### Documentation (this feature)

```text
specs/005-batch-queue-topics/
├── plan.md              # Implementation plan (this file)
├── research.md          # Research findings & architectural decisions
├── data-model.md        # Pydantic schemas and state transition diagrams
├── quickstart.md        # Runnable verification and testing scenarios
├── contracts/
│   ├── api_topics.json       # OpenAPI contract for topic ideation
│   └── api_batch_queue.json  # OpenAPI contract for batch queue
├── checklists/
│   └── requirements.md  # Quality checklist
└── tasks.md             # Actionable task list (/speckit-tasks output)
```

### Source Code Impact

```text
videoanalizer/
├── quiz/
│   ├── models.py            # [MODIFY] Add TopicSuggestion, BatchTopicList, BatchQueueItem, BatchQueueState
│   ├── script_service.py    # [MODIFY] Add suggest_topic(), suggest_batch_topics()
│   ├── rate_limiter.py      # [NEW] Async rate limiter enforcing <= 12 RPM (5.0s delay) & backoff
│   └── batch_queue.py       # [NEW] BatchQueueManager with asyncio.Semaphore(1) worker
├── api/
│   └── routes_quiz.py       # [MODIFY] Add topic endpoints & batch queue REST endpoints
└── ui/
    └── templates/
        └── quiz.html        # [MODIFY] "🎲 Придумать тему" button, Batch tab, approval wizard, queue monitor
tests/
└── unit/
    ├── test_rate_limiter.py # [NEW] Test 5s pacing and exponential backoff
    ├── test_topic_generator.py # [NEW] Test single & batch topic suggestions
    └── test_batch_queue.py  # [NEW] Test sequential queue execution & fault isolation
```

---

## Complexity Tracking

*No constitutional violations; no additional complex third-party infrastructure (e.g. Redis, Celery) required.*

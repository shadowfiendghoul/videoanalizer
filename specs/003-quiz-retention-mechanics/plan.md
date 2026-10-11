# Implementation Plan: Quiz Retention Mechanics & Viral Features

**Branch**: `003-quiz-retention-mechanics` | **Date**: 2026-10-11 | **Spec**: [specs/003-quiz-retention-mechanics/spec.md](file:///c:/Users/User/Desktop/videoanalizer/specs/003-quiz-retention-mechanics/spec.md)

**Input**: Feature specification from `/specs/003-quiz-retention-mechanics/spec.md` and detailed viral retention mechanics from `/specs/retention-features.md`.

---

## Summary

Реализация полного комплекса из 8 вирусных механик удержания внимания (Retention Rate) и виральности (Share & Comment Velocity) для вертикальных викторин формата 9:16 (TikTok, YouTube Shorts, Instagram Reels). Включает психологическую шкалу статуса (IQ/Rank Bar), ускоряющийся стресс-таймер (3.0с $\rightarrow$ 2.5с $\rightarrow$ 1.8с) с панической виньеткой, счетчик комбо-стрика огня с ультра-режимом, ловушку для споров в комментариях (Comment Trap Outro), защиту верстки от переполнения текстом (clamp), динамическую синхронизацию аудио/кадров и архитектурную защиту от падения памяти (OOM Guard с `Semaphore(1)` и `concurrency=3`).

---

## Technical Context

**Language/Version**: Python 3.11+ (Backend) | TypeScript 5.3+ / Node.js 18+ (Remotion Video Engine)  
**Primary Dependencies**: FastAPI, Pydantic v2 (`BaseModel`, `Settings`), Remotion v4, React 18, Tailwind CSS v3, `edge-tts`, `google-genai` SDK  
**Storage**: Filesystem workspaces (`assets/backgrounds`, `assets/sfx`, `temp/quiz_<id>`, `outputs/`)  
**Testing**: `pytest` (22 unit & contract tests), `ruff`  
**Target Platform**: Windows 11 / PowerShell (AMD Ryzen 7 8845H c Radeon 780M iGPU)  
**Project Type**: Asynchronous Web Service (FastAPI) + Declarative Motion Graphics Renderer (Remotion)  
**Performance Goals**:
- Общий хронометраж ролика: строго **45–50 секунд** (Блиц-формат под TikTok/Shorts).
- Скорость и стабильность рендера: 1080x1920 60fps без падений по OOM; пиковый расход RAM $\le 4$ ГБ.  
**Constraints**:
- Строгая последовательная очередь рендеринга `asyncio.Semaphore(1)` на стороне FastAPI.
- Ограничение пула рендера кадров Chromium: `--concurrency=3`.
- Максимальная длина текста: вопрос $\le 65$ симв., ответ $\le 25$ симв., CSS `clamp(26px, ..., 44px)` для удержания в 840px зоне.  
**Scale/Scope**: 9 вопросов на ролик (3 уровня сложности по 3 вопроса), 8 компонентов удержания.

---

## Constitution Check

*GATE: Evaluation against VideoAnalyzer Constitution v1.1.0*

| Principle | Status | Evaluation |
|---|---|---|
| **I. Strict Type Safety & Pydantic Data Contracts** | **PASS** | Все новые сущности (`RankTierConfig`, `StressTimerTier`, `ComboStreakConfig`, `CommentTrapConfig`, `QuizRetentionConfig`) строго валидируются через Pydantic v2 с fail-fast гарантией. |
| **II. Declarative Motion Rendering (Remotion & FFmpeg)** | **PASS** | Визуальные слои удержания строятся на декларативных React/Remotion компонентах с анимацией через `spring()`/`interpolate()`. Передача данных строго через typed props. Фоновые видео зацикливаются через `<Loop>`. |
| **III. Asynchronous & Resilient AI Engine (Gemini REST)** | **PASS** | Генерация сценариев использует официальный Gemini REST API со структурированным выводом и строгими ограничениями на длину текста. WebSocket Live API не используется. |
| **IV. Isolated Testing & Contract Verification** | **PASS** | Все модули сопровождаются изолированными mock-тестами; контракты Pydantic и Remotion проверяются автоматизированными тестами до сборки. |
| **V. Decoupled Sub-Service Boundaries** | **PASS** | Роли строго изолированы: `@script-service` генерирует текст, `@audio-service` синтезирует речь и SFX, `@template-engine` верстает компоненты, `@orchestrator` запускает Remotion CLI. |

---

## Project Structure

### Documentation (this feature)

```text
specs/003-quiz-retention-mechanics/
├── spec.md              # Feature specification & clarification log
├── plan.md              # This implementation plan
├── research.md          # Phase 0 research decisions & architecture choices
├── data-model.md        # Phase 1 domain entities & TypeScript definitions
├── quickstart.md        # Phase 1 runnable validation scenarios
├── contracts/           # Phase 1 schema contracts
│   ├── remotion_render_props.json
│   └── api_generate_request.json
└── checklists/
    └── requirements.md  # Specification quality checklist (14/14 passing)
```

### Source Code Layout

```text
videoanalizer/
├── quiz/
│   ├── models.py                  # Pydantic v2 schemas (+ QuizRetentionConfig, RankTier, StressTimer)
│   ├── config.py                  # QuizConfig settings
│   ├── script_service.py          # Gemini AI generation with <=65 and <=25 char limits
│   ├── audio_service.py           # Edge-TTS timing, dynamic duration calculation & SFX synthesis
│   ├── workspace.py               # Isolated temp workspaces with auto-cleanup
│   ├── orchestrator.py            # Queue management (Semaphore(1)), props preparation & Remotion CLI
│   └── cli.py                     # CLI entrypoint
├── api/
│   └── routes_quiz.py             # FastAPI REST endpoints (/preview, /generate, /jobs)
└── ui/
    └── templates/
        └── quiz.html              # Web dashboard with retention toggles & live progress

templates/quiz-remotion/
├── src/
│   ├── types.ts                   # TypeScript interfaces matching Pydantic schemas
│   ├── Root.tsx                   # Remotion Root composition
│   ├── QuizChallenge.tsx          # Master composition with dynamic sequence timing
│   └── components/
│       ├── RankStatusBar.tsx      # [NEW] Top IQ/Rank bar (NPC -> 1% Geniuses at Y=160px)
│       ├── StressTimer.tsx        # [NEW] Accelerating countdown (3.0s -> 2.5s -> 1.8s)
│       ├── PanicVignette.tsx      # [NEW] Pulsing red edge vignette on Hard tier
│       ├── StreakFire.tsx         # [NEW] Combo streak fire counter (Ultra blue mode at >=7)
│       ├── CommentTrapOutro.tsx   # [NEW] Controversy hook outro banner on last 1.5s
│       ├── DecoyFakeOut.tsx       # [NEW] 0.3s fake answer tease on Q4/Q7
│       ├── AntiCheatCallout.tsx   # [NEW] HUD sticker on Q9
│       ├── LevelHeader.tsx        # Tier level header
│       ├── QuestionLadder.tsx     # Left-side 1-9 ladder
│       ├── KaraokeCaptions.tsx    # Responsive dynamic text captions
│       ├── CenterBanner.tsx       # Central video banner overlay
│       └── BackgroundLayer.tsx    # Looped video background with gradients

tests/
├── unit/
│   └── quiz/
│       ├── test_api_routes.py
│       ├── test_audio_service.py
│       ├── test_image_service.py
│       ├── test_orchestrator.py
│       ├── test_script_service.py
│       └── test_retention_mechanics.py  # [NEW] Unit tests for retention logic
└── contract/
    └── quiz/
        └── test_quiz_schema_contract.py # Contract tests for QuizRetentionConfig
```

---

## Complexity Tracking

*Constitution violations: NONE. All gates PASS without exceptions.*

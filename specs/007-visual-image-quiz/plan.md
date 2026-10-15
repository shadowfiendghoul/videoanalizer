# Implementation Plan: 007-visual-image-quiz

**Branch**: `007-visual-image-quiz` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-visual-image-quiz/spec.md`

---

## Summary

Реализация нового режима вирусных видеовикторин **"Visual Image Quiz"** (быстрая смена предметов в одной точке + прогрессивная 4-уровневая лестница) для произвольных динамических тем (бренды, авто, игры, кино, флаги, животные и др.).
1. **Интро-хук (0:00–0:03.5s)**: Циклический быстрый флип всех 10 картинок в едином боксе `x: 780, y: 450` (380x380 px) с интервалом 100–120 мс на кадр под Rapid Flip SFX и интригующую реплику диктора; левая панель уровней скрыта.
2. **Последовательный геймплей**: 4 блока лестницы («Лёгкий уровень» — зелёный, «Средний уровень» — жёлтый, «Эксперт» — красный, «Мастер / Финал» — пурпурный). Появление картинок с пружинящим эффектом (`scale 0 -> 1.1 -> 1.0`), синхронный быстрый таймер (1.5–2.0 с), звуковые сигналы Ding и плавное открытие ответов.
3. **Хуки вовлечения**: Байт на комментарии после Q3, байт на репост после Q6, финальная «коммент-ловушка» на Q10 со скрытием ответа («10. Пиши в коммы») и призывом угадать в комментариях под клиффхэнгер.
4. **Подбор картинок с утверждением**: Автоматический поиск картинок через `/api/v1/quiz/search-image` с интерактивным предпросмотром и подтверждением (approval) пользователем в UI.
5. **Пословные караоке-субтитры**: Выводятся для всех реплик диктора в слоте `y: 1420..1500` над безопасной зоной TikTok.

---

## Technical Context

**Language/Version**: Python 3.11+ (Backend), TypeScript / React 18+ (Remotion).  
**Primary Dependencies**:
- Backend: `pydantic` v2, `google-genai` / `httpx` (Gemini REST API), `edge-tts`, `fastapi`, `ffmpeg`.
- Frontend/Rendering: Remotion (CLI & React runtime), Tailwind CSS, Lucide icons.

**Storage**:
- Кэш изображений: `assets/quizzes/<theme_slug>/`.
- Временная рабочая область: изолированные каталоги под управлением `QuizWorkspace`.
- Результаты: `output/`.

**Testing**: `pytest`, `pytest-asyncio` с синтетическими моками для Gemini и Edge-TTS.  
**Target Platform**: Windows 10/11, Linux, macOS; с поддержкой аппаратного ускорения NVENC/CPU.  
**Project Type**: Модульное расширение десктопного веб-приложения VideoAnalyzer.  
**Performance Goals**:
- Генерация полного сценария через Gemini REST API: < 5.0 сек.
- Точность флипа интро: строго 100–120 мс на кадр (с точностью до 1 кадра при 60 fps).
- Суммарная длительность ролика: ровно 45–55 секунд.
- Рендер Remotion 1080x1920 60fps без утечек памяти.

**Constraints**:
- Полное соблюдение безопасных зон вертикального видео 9:16 (снизу >= 400px, справа >= 120px).
- Нумерация реплик: на Q1 диктор сразу называет вопрос без вводных слов «Вопрос номер один».

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I: Strict Type Safety & Pydantic Data Contracts**  
  *Status*: **PASS**  
  Все сущности строго типизированы: `VisualQuizItem`, `VisualQuizDataset`, `VisualQuizRenderProps`, `VisualDifficulty`. Валидация происходит на входе и выходе.
- **Principle II: Declarative Motion Rendering & Media Processing**  
  *Status*: **PASS**  
  Создается независимая Remotion-композиция `VisualImageQuiz` (1080x1920 60fps). Координаты и тайминги передаются через типизированные пропсы без мутации кода компонентов. Временные медиафайлы очищаются контекстным менеджером.
- **Principle III: Asynchronous & Resilient AI Engine**  
  *Status*: **PASS**  
  Генерация сценария взаимодействует исключительно с Gemini REST API с экспоненциальным бэкоффом и структурированным выводом Pydantic. WebSockets не используются.
- **Principle IV: Isolated Testing & Contract Verification**  
  *Status*: **PASS**  
  Все компоненты покрываются изолированными тестами с синтетическими моками без внешних сетевых вызовов в CI.
- **Principle V: Decoupled Sub-Service Boundaries**  
  *Status*: **PASS**  
  Четкое разделение ответственности: `@script-service` (сценарий и подбор картинок), `@audio-service` (синтез и SFX микс), `@template-engine` (Remotion-компоненты), `@orchestrator` (сборка и запуск рендера).

---

## Project Structure

### Documentation (this feature)

```text
specs/007-visual-image-quiz/
├── spec.md              # Спецификация требований и пользовательских историй
├── plan.md              # Настоящий план реализации архитектуры
├── research.md          # Исследования и технические обоснования (Phase 0)
├── data-model.md        # Pydantic v2 модели и схемы данных (Phase 1)
├── quickstart.md        # Пошаговое руководство по сквозному тестированию (Phase 1)
├── contracts/           # Спецификации интерфейсов API и JSON-схемы Remotion
│   ├── visual_quiz_api.json
│   └── remotion_props_schema.json
├── checklists/
│   └── requirements.md  # Чеклист качества требований (20/20 passing)
└── tasks.md             # Пошаговый граф задач реализации (Phase 2, /speckit-tasks)
```

### Source Code (repository root)

```text
videoanalizer/
├── quiz/
│   ├── models.py                   # [EXTEND] Добавление VisualQuizItem, VisualQuizDataset, VisualQuizRenderProps
│   ├── script_service.py            # [EXTEND] Генерация визуального сценария VisualQuizDataset через Gemini REST
│   ├── audio_service.py            # [EXTEND] Сборка AudioCueSheet для VisualImageQuiz с SFX и синхронным таймером
│   └── orchestrator.py             # [EXTEND] Поддержка режима visual_image_quiz в QuizOrchestrator
├── api/
│   └── routes_quiz.py              # [EXTEND] REST эндпоинты /api/v1/quiz/visual/generate и /render
└── ui/
    └── templates/
        └── quiz.html               # [EXTEND] UI селектор режима, плитка 10 карточек с модерацией картинок

templates/quiz-remotion/src/
├── Root.tsx                        # [EXTEND] Регистрация композиции VisualImageQuiz
├── VisualImageQuiz.tsx             # [NEW] Главная композиция Visual Image Quiz (1080x1920 60fps)
├── components/
│   ├── RapidCenterFlip.tsx         # [NEW] Компонент быстрого флипа 10 картинок в интро (120 мс/кадр)
│   ├── SpringImageCard.tsx         # [NEW] Пружинящее появление загаданного предмета (scale 0 -> 1.1 -> 1.0)
│   ├── ProgressiveLadder.tsx       # [NEW] Левая панель 4 уровней с заголовками и отложенным открытием
│   ├── SyncHorizontalTimer.tsx     # [NEW] Синхронный таймер (1.5-2.0s) с цветовым переходом
│   └── EngagementOverlay.tsx       # [NEW] Анимированные стикеры комментариев (Q3) и стрелки репоста (Q6)
└── types.ts                        # [EXTEND] TypeScript типы для VisualQuizRenderProps

tests/
├── unit/quiz/
│   ├── test_visual_quiz_script.py  # [NEW] Тесты генерации сценария и валидации схемы
│   └── test_visual_quiz_audio.py   # [NEW] Тесты сборщика аудиоряда и таймингов
└── integration/quiz/
    └── test_visual_quiz_orchestrator.py # [NEW] Интеграционный тест рендера через Remotion
```

---

## Complexity Tracking

*Нарушений Конституции нет. Все проектные решения строго соответствуют принципам Pydantic v2, Remotion 9:16 и изолированных сервисов.*

# Implementation Plan: Профиль GPU-ускорения рендеринга ('gpu_fast')

**Branch**: `004-gpu-fast-rendering` | **Date**: 2026-10-12 | **Spec**: [specs/004-gpu-fast-rendering/spec.md](file:///C:/Users/User/Desktop/videoanalizer/specs/004-gpu-fast-rendering/spec.md)

---

## Summary

Реализация двухуровневого профиля рендеринга (`gpu_fast` и `cpu_safe`) для кардинального ускорения создания Shorts-видео:
1. Автоматический кроссплатформенный зонд оборудования `videoanalizer/utils/hardware.py` (AMD AMF, NVIDIA NVENC, Intel QSV, Windows MediaFoundation MFT) с валидацией через 1-кадровый тест.
2. Подключение аппаратной растеризации Chromium ANGLE/DirectX (`--gl=angle`) и постоянного кэша Webpack-бандлов (`--bundle-cache`) в оркестраторе Remotion.
3. Инъекция аппаратного видеокодека в `remotion.config.ts` через официальный перехват `Config.overrideFfmpegCommand`.
4. Перевод финального уникализатора `uniquifier.py` на аппаратный энкодер (ускорение в 6–10 раз).
5. Веб-интерфейс в `quiz.html` с элегантным переключателем режимов `⚡ GPU Fast` / `🖥️ CPU Safe`, бейджем обнаруженной видеокарты и сохранением настроек в `localStorage`.

---

## Technical Context

**Language/Version**: Python 3.11+, TypeScript 5.0+, React 18+  
**Primary Dependencies**: Remotion 4.0+, Chromium (Puppeteer), FFmpeg 9.0+, FastAPI, Pydantic v2  
**Storage**: Временные директории рендера (`temp/quiz_*`) с детерминированной автоочисткой, persistent webpack cache  
**Testing**: `pytest`, `pytest-asyncio`, isolated synthetic FFmpeg mocks & fixtures  
**Target Platform**: Windows 11 (AMD Radeon 780M / NVIDIA RTX / Intel), Linux, macOS  
**Performance Goals**:
- Сокращение времени рендеринга видео в 3–5 раз.
- Сокращение фазы Webpack сборки с ~12 сек до < 1 сек.
- Сокращение пост-обработки `uniquifier.py` с ~20 сек до ~2 сек.
- Снижение нагрузки на CPU во время рендера с 100% до < 25%.  
**Constraints**:
- Нулевые падения (Fail-Safe): при недоступности или ошибке GPU происходит бесшовный откат на `cpu_safe` (`libx264`).
- Никаких регрессий в существующих 65 тестах.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Strict Type Safety & Pydantic Data Contracts**: Все новые параметры (`RenderProfile`, `HardwareCapabilities`, `QuizGenerateRequest.render_profile`) строго типизированы в Pydantic v2 моделях.
- [x] **II. Declarative Motion Rendering & Media Processing (Remotion & FFmpeg)**: Remotion вызывается строго декларативно через CLI (`--gl=angle`, `--bundle-cache`), а кодеки кастомизируются через стандартный интерфейс `remotion.config.ts` без хаков внутренних компонентов.
- [x] **III. Asynchronous & Resilient AI Engine**: Не затрагивает контуры Gemini REST API.
- [x] **IV. Isolated Testing & Contract Verification**: Модуль оборудования тестируется изолированно синтетическими mock-командами FFmpeg и тестами на реальном железе.
- [x] **V. Decoupled Sub-Service Boundaries**: Четкое разделение ответственности: `videoanalizer/utils/hardware.py` зондирует железо; `routes_quiz.py` передает параметры; `orchestrator.py` собирает CLI-команды; `quiz.html` отображает UI.

---

## Project Structure

```text
specs/004-gpu-fast-rendering/
├── spec.md                  # Feature Specification
├── plan.md                  # Implementation Plan
├── research.md              # Research & Benchmarks
├── data-model.md            # Pydantic Schemas & Data Contracts
├── quickstart.md            # Quickstart & Verification Guide
├── contracts/
│   └── hardware-contract.json # JSON Schema for Hardware API
└── tasks.md                 # Isolated Task Breakdown
```

### Модифицируемые и создаваемые файлы кодовой базы

#### [NEW] `videoanalizer/utils/hardware.py`
Зонд аппаратного оборудования, вендора GPU и валидация аппаратных энкодеров FFmpeg (`h264_amf`, `h264_nvenc`, `h264_qsv`, `h264_mf`, `libx264`).

#### [NEW] `tests/unit/test_hardware.py`
Набор модульных тестов для зонда оборудования с моками и проверкой fallback на CPU.

#### [MODIFY] `videoanalizer/quiz/config.py`
Добавление параметров `render_profile`, `enable_bundle_cache`, `gl_backend` в `QuizOrchestratorConfig`.

#### [MODIFY] `videoanalizer/quiz/models.py`
Добавление перечисления `RenderProfile` и моделей аппаратного статуса.

#### [MODIFY] `videoanalizer/api/routes_quiz.py`
Добавление `render_profile` в `QuizGenerateRequest` и нового эндпоинта `GET /api/v1/hardware/status`.

#### [MODIFY] `templates/quiz-remotion/remotion.config.ts`
Добавление хука `Config.overrideFfmpegCommand` для подстановки аппаратного видеоэнкодера по переменным окружения.

#### [MODIFY] `videoanalizer/quiz/orchestrator.py`
Обновление построения команды Remotion CLI: передача `--gl=angle`, `--bundle-cache`, переменных окружения `VIDEOANALIZER_RENDER_PROFILE` и `VIDEOANALIZER_HW_ENCODER`.

#### [MODIFY] `videoanalizer/media/uniquifier.py`
Перевод кодирования видеопотока на активный аппаратный энкодер при профиле `gpu_fast`.

#### [MODIFY] `videoanalizer/ui/templates/quiz.html`
Интеграция переключателя режимов рендеринга `⚡ GPU Fast` / `🖥️ CPU Safe` с авто-определением GPU и сохранением в `localStorage`.

---

## ⚡ Max Hardware Utilization (Режим максимальной производительности)

### 1. Архитектура автомасштабирования под CPU и RAM
- **Динамический Concurrency**:
  - `videoanalizer/utils/hardware.py`: функция `calculate_optimal_concurrency(profile: RenderProfile, safety_margin: float = 0.75) -> int`.
  - Задействование 75–80% доступных логических ядер процессора (`os.cpu_count() * 0.75`).
  - Предотвращение OOM (Out Of Memory): проверка доступной оперативной памяти (`get_system_memory_mb()`) с расчетом квоты ~450 МБ на поток Remotion Chromium.
  - Итоговый concurrency масштабируется в диапазоне от 2 до 24+ потоков без риска падения по памяти.

### 2. Кэширование сборки Remotion (Build Reuse)
- **Менеджер бандла (`videoanalizer/quiz/build_cache.py`)**:
  - Вычисление хэша исходных кодов React-компонентов в `templates/quiz-remotion/src/`.
  - Однократная сборка бандла `npx remotion bundle src/index.ts --out-dir=build` при первом старте или изменении шаблона.
  - При всех последующих рендерах Remotion CLI вызывается напрямую с указанием готовой директории бандла `build` вместо `src/index.ts`.
  - Время старта рендеринга сокращается до **0.1 секунды**, полностью устраняя задержку на компиляцию Webpack.

### 3. Автоопределение и ультраскоростные пресеты аппаратного кодирования
- **Расширенный каскад энкодеров**:
  - NVIDIA (`h264_nvenc`) -> AMD (`h264_amf`) -> Intel (`h264_qsv`) -> Apple (`h264_videotoolbox`) -> Windows MediaFoundation (`h264_mf`).
- **Ультраскоростные профили**:
  - `h264_nvenc`: `-preset p1 -tune ull -rc cbr -b:v 12M` (быстрейший профиль с ультранизкой задержкой).
  - `h264_amf`: `-quality speed -rc cbr -b:v 12M`.
  - `h264_qsv`: `-preset veryfast -b:v 12M`.
  - `h264_videotoolbox`: `-realtime 1 -b:v 12M`.
  - `h264_mf`: `-rate_control cbr -b:v 12M`.
  - `libx264` (fallback): `-preset ultrafast -tune fastdecode -threads 0 -crf 20`.

### 4. Параллельный асинхронный пайплайн данных (Concurrent Data Staging)
- **Асинхронный сбор медиа-ресурсов**:
  - Как только получена структура вопросов квиза, этапы синтеза речи Edge-TTS, поиска и скачивания изображений DuckDuckGo, подготовки фона, музыки, промо-баннера и валидации бандла Remotion запускаются одновременно через `asyncio.gather`.
  - Задержка фазы подготовки сокращается с 25–35 секунд до времени выполнения одного сетевого запроса TTS (~5–7 секунд).

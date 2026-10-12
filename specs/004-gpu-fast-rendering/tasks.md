# Tasks: Профиль GPU-ускорения рендеринга ('gpu_fast')

**Feature**: Профиль GPU-ускорения рендеринга ('gpu_fast')  
**Branch**: `004-gpu-fast-rendering`  
**Plan**: [specs/004-gpu-fast-rendering/plan.md](file:///C:/Users/User/Desktop/videoanalizer/specs/004-gpu-fast-rendering/plan.md)  
**Spec**: [specs/004-gpu-fast-rendering/spec.md](file:///C:/Users/User/Desktop/videoanalizer/specs/004-gpu-fast-rendering/spec.md)  

---

## Phase 1: Setup & Data Contracts (Prerequisites)

**Purpose**: Добавление строгих Pydantic v2 схем и контрактов данных для управления профилями рендеринга и статусом оборудования.

- [x] T001 [P] Implement `RenderProfile` and `GpuVendor` enums in `videoanalizer/quiz/models.py`
- [x] T002 [P] Implement `HardwareCapabilities` Pydantic v2 schema in `videoanalizer/quiz/models.py`
- [x] T003 Update `QuizOrchestratorConfig` in `videoanalizer/quiz/config.py` to add `render_profile`, `enable_bundle_cache`, and `gl_backend`
- [x] T004 Update `QuizGenerateRequest` in `videoanalizer/api/routes_quiz.py` to accept `render_profile: RenderProfile = RenderProfile.GPU_FAST`
- [x] T005 [P] Create unit test contract for hardware schemas in `tests/unit/test_hardware.py`

**Checkpoint**: Все модели данных Pydantic строго валидируются и готовы к использованию.

---

## Phase 2: Foundational Hardware Probe Engine

**Purpose**: Реализация надежного, кэшируемого зонда аппаратного обеспечения для обнаружения видеокарты и валидации доступных кодеков FFmpeg.

- [x] T006 Create `videoanalizer/utils/hardware.py` with GPU vendor detection (AMD, NVIDIA, Intel, Windows MediaFoundation) and FFmpeg encoder verification
- [x] T007 Implement 1-frame dry-run probe method `validate_encoder(encoder_name: str) -> bool` in `videoanalizer/utils/hardware.py` to test encoder driver stability before activation
- [x] T008 Add cached singleton accessor `get_hardware_capabilities() -> HardwareCapabilities` in `videoanalizer/utils/hardware.py`
- [x] T009 Add unit tests in `tests/unit/test_hardware.py` verifying detection logic, encoder prioritization (`h264_amf` on AMD, `h264_nvenc` on NVIDIA, `h264_mf` on generic Windows), and fallback to `libx264`

**Checkpoint**: Зонд оборудования надежно определяет GPU и выбирает оптимальный энкодер без накладных расходов по времени.

---

## Phase 3: User Story 1 - GPU Acceleration in Remotion Engine (Priority: P1) 🎯 MVP

**Purpose**: Активация аппаратной растеризации Chromium через ANGLE/DirectX, кэширования Webpack бандлов и аппаратного кодирования в Remotion.

- [x] T010 [US1] Update `_build_remotion_command` in `videoanalizer/quiz/orchestrator.py` to pass `--gl=angle` and `--bundle-cache` when `render_profile == RenderProfile.GPU_FAST`
- [x] T011 [US1] Inject environment variables `VIDEOANALIZER_RENDER_PROFILE` and `VIDEOANALIZER_HW_ENCODER` into the Remotion subprocess in `videoanalizer/quiz/orchestrator.py`
- [x] T012 [US1] Implement `Config.overrideFfmpegCommand` in `templates/quiz-remotion/remotion.config.ts` to substitute `libx264` with the active hardware encoder (`h264_amf` / `h264_nvenc` / `h264_mf`)
- [x] T013 [US1] Implement fail-safe automatic fallback: if Remotion render with GPU flags fails, log a warning and retry automatically in `cpu_safe` mode
- [x] T014 [US1] Add unit tests in `tests/unit/quiz/test_orchestrator.py` asserting correct CLI flags and environment variables for both `gpu_fast` and `cpu_safe` profiles

**Checkpoint**: Рендеринг Remotion работает с GPU-растеризацией и кэшированием Webpack, экономя до 70% времени генерации.

---

## Phase 4: User Story 2 - GPU Acceleration in Media Pipeline & Uniquifier (Priority: P2)

**Purpose**: Ускорение финальной пост-обработки видео (`uniquifier.py`) и вспомогательных FFmpeg операций через аппаратный энкодер.

- [x] T015 [US2] Update `VideoUniquifierConfig` in `videoanalizer/media/uniquifier.py` to accept `render_profile: RenderProfile`
- [x] T016 [US2] Update `apply_video_uniquifier` in `videoanalizer/media/uniquifier.py` to dynamically use the validated hardware encoder with vendor-optimized preset flags вместо hardcoded `libx264`
- [x] T017 [US2] Add unit test in `tests/unit/test_uniquifier.py` verifying hardware encoder command construction and fallback to `libx264` if hardware encoder throws an error

**Checkpoint**: Пост-обработка видео ускорена с 20 секунд до 1.5–2.5 секунд.

---

## Phase 5: User Story 3 - Web UI & REST API Controls (Priority: P3)

**Purpose**: Добавление пользовательского переключателя в веб-интерфейс и REST эндпоинта для отображения возможностей оборудования.

- [x] T018 [US3] Add `GET /api/v1/hardware/status` route in `videoanalizer/api/routes_quiz.py` returning `HardwareCapabilities`
- [x] T019 [US3] Add sleek glassmorphic "⚡ Режим рендеринга" toggle card in `videoanalizer/ui/templates/quiz.html` with options `[⚡ GPU Fast]` and `[🖥️ CPU Safe]`
- [x] T020 [US3] Add JavaScript auto-probe logic in `videoanalizer/ui/templates/quiz.html` to fetch `/api/v1/hardware/status` on page load and display GPU badge (e.g. `🟢 GPU: AMD Radeon 780M (h264_amf / D3D11)`)
- [x] T021 [US3] Add `localStorage` persistence and payload binding for `render_profile` in `videoanalizer/ui/templates/quiz.html`
- [x] T022 [US3] Add API integration tests in `tests/unit/quiz/test_api_routes.py` verifying `/api/v1/hardware/status` and `render_profile` in generation requests

**Checkpoint**: Пользователь в браузере видит статус своей видеокарты, переключает профиль и запускает генерацию с GPU-ускорением.

---

## Phase 6: Verification & End-to-End Benchmarking

**Purpose**: Сквозная верификация, проверка стабильности и бенчмаркинг прироста скорости.

- [x] T023 Run full automated test suite `python -m pytest tests/` ensuring 100% pass rate
- [x] T024 Run `python -m ruff check videoanalizer/ tests/` ensuring zero linting issues
- [x] T025 Run test render in Remotion and compare execution time between `cpu_safe` and `gpu_fast`

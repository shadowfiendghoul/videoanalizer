# Feature Specification: Batch Queue & AI Topic Generator

**Feature Branch**: `005-batch-queue-topics`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "нужно сделать чтобы видосыможно было ставить в очередь типо вписал 10 штук нажал генерацию и сначало по очереди одобряешь вопросы для каждого и после они делаються по очереди но тогда нужно чтобы тему тоже придумывала нейросеть и сделать отдельно если захочется всего одно видео сделать то была кнопка сгенерировать тему"

---

## Clarifications

### Session 2026-10-13

- Q: Какие квоты и ограничения накладывает модель Gemini? → A: Модель ограничена лимитом 15 RPM (запросов в минуту) и 250K TPM. Пакетная генерация должна строго соблюдать pacing (интервал >= 4.5-5.0 сек между вызовами API), объединять генерацию всех тем в 1 запрос и реализовывать автоматический retry с backoff на случай HTTP 429 (Resource Exhausted).
- Q: Как генерировать вопросы для пачки видео с учетом лимита 15 RPM? → A: Прогрессивная фоновая генерация (Paced Background Pipeline): вопросы для видео 1 готовы сразу для начала проверки, а вопросы для последующих видео генерируются в фоновом потоке с интервалом 5 секунд, пока пользователь изучает и одобряет первое видео. Это гарантирует нулевое ожидание при переключении и 100% соблюдение лимита 15 RPM.
- Q: Запускать ли рендеринг только после того, как проверены и одобрены все видео в пачке? → A: Очередь рендеринга запускается строго после завершения проверки всех N видео (или явного исключения ненужных) единой кнопкой «Запустить очередь рендеринга», не создавая фоновой нагрузки на GPU/CPU в процессе чтения и редактирования вопросов.
- Q: Как настраивать голос диктора и фоновую музыку для пачки видео? → A: Настройки голоса озвучки, фоновой музыки, громкости и профиля рендера задаются один раз на панели управления перед генерацией и единообразно применяются ко всем роликам пачки. Визард проверки сфокусирован исключительно на проверке вопросов, ответов и иллюстраций.
- Q: Что должно происходить с готовыми видео при запуске новой пачки? → A: Завершенные видео сохраняются в очереди до ручной очистки. Дополнительно в интерфейс добавляется постоянный раздел «История генераций», где сохраняются все созданные видео с подписанными темами, датой создания, встроенным плеером и кнопками скачивания MP4.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Single Video AI Topic Suggestion (Priority: P1)

As a content creator creating an individual quiz video, I want an AI button next to the topic input that instantly invents a viral, non-trivial quiz topic so that I don't have to suffer from creative block or manually brainstorm engaging ideas.

**Why this priority**: Immediate everyday convenience for standard single-video workflows; core building block for AI topic ideation.

**Independent Test**: Can be tested directly on the quiz creation screen: click the "🎲 Придумать тему" button without typing anything, verify that a catchy, formatted topic appears in the input field, and proceed to generate questions for it.

**Acceptance Scenarios**:

1. **Given** the user is on the quiz creation dashboard and the topic field is empty (or has placeholder text), **When** the user clicks "🎲 Придумать тему", **Then** the system queries the AI and fills the topic input with an engaging, viral topic (e.g. "Анатомические парадоксы тела", "Забытые законы средневековья").
2. **Given** the topic field already has text, **When** the user clicks "🎲 Придумать тему" again, **Then** the system replaces the topic with a fresh, alternative viral idea.
3. **Given** a user specifies an optional category guidance (or leaves it blank), **When** generating a topic, **Then** the generated topic is concise (under 60 characters), specific, and proven for high viral curiosity.

---

### User Story 2 - Batch Topic Ideation & Review (Priority: P2)

As a creator planning a batch of multiple videos (e.g., 5 or 10 Shorts at once), I want to specify the desired quantity of videos and have the AI generate a list of distinct, diverse topics across different curiosity niches in a SINGLE API request so that 15 RPM quota is preserved and every video covers a unique niche.

**Why this priority**: Essential preparatory step for multi-video generation; allows creators to oversee and adjust the lineup before generating 9-question scripts.

**Independent Test**: Switch to Batch Mode, enter a quantity (e.g., 5), click "Сгенерировать темы для пачки", verify 5 distinct non-overlapping topics are produced in a single API call, and edit or regenerate any individual topic in the list.

**Acceptance Scenarios**:

1. **Given** the user enters a batch size N (between 2 and 20), **When** the user clicks "Сгенерировать темы", **Then** the system issues a single structured prompt and displays a list of N numbered topics covering diverse categories (e.g., gaming paradoxes, world mysteries, human body, bizarre science, inventions).
2. **Given** the generated batch list of topics, **When** the user notices a topic they want to adjust, **Then** the user can edit the topic text directly in place or click a single-item refresh button to replace that specific topic with a new one.
3. **Given** the user is satisfied with the topic list, **When** the user confirms the batch, **Then** the system initiates progressive rate-limited question generation and transitions into the Sequential Question Approval flow.

---

### User Story 3 - Sequential Multi-Video Question Approval Flow (Priority: P1)

As a creator generating a batch of videos, I want to review, edit, and approve the 9 trivia questions for each video sequentially (Video 1 of N, Video 2 of N, etc.) while background question generation paces itself within the 15 RPM ceiling so that I maintain 100% editorial quality control without hitting rate limits.

**Why this priority**: Fulfills the core user requirement ("сначала по очереди одобряешь вопросы для каждого"); prevents rendering inaccurate or low-quality scripts without user consent.

**Independent Test**: Launch a batch with 3 topics. Verify that Video 1 displays its 9 questions with full editing, image selection, and selective question regeneration. Click "Одобрить и перейти к следующему", verify Video 2 is loaded for review, and so on until all 3 are approved and queued for rendering.

**Acceptance Scenarios**:

1. **Given** a batch of N videos has its questions generated progressively, **When** the review wizard opens, **Then** it clearly shows progress (e.g., "Видео 1 из N: [Название темы]") and displays all 9 questions with difficulty tiers, answers, visual clues, and selection checkboxes.
2. **Given** the current video card in the approval wizard, **When** the user makes inline edits or selectively regenerates questions, **Then** all adjustments are preserved for that specific video.
3. **Given** the user clicks "Одобрить и далее" on item k (1 <= k < N), **Then** the wizard saves item k's approved state and smoothly loads item k+1 for review.
4. **Given** the user wants to jump back or forward, **When** using the step navigation (e.g. tabs or step indicator 1..N), **Then** the user can inspect and re-edit any previously approved video in the active batch.
5. **Given** the user completes the approval of the last video (N), **When** clicking "Запустить очередь рендеринга", **Then** all N approved videos are enqueued into the Sequential Background Render Queue.

---

### User Story 4 - Background Sequential Render Queue & Monitoring (Priority: P1)

As a content creator who has approved a batch of videos, I want the system to render the videos sequentially in the background one by one, displaying real-time queue progress and download links for completed videos, so that my computer hardware is not overloaded and I can download all finished videos as they complete.

**Why this priority**: Core execution pipeline for batch processing; safeguards GPU/CPU stability and delivers finished MP4 files.

**Independent Test**: Enqueue 3 approved quiz jobs. Verify that Job 1 begins rendering while Jobs 2 and 3 remain in "В очереди (ожидание)" status. When Job 1 finishes, verify Job 2 immediately starts rendering, Job 1 displays a completed preview and download button, and after Job 3 finishes, all 3 videos are accessible.

**Acceptance Scenarios**:

1. **Given** an approved batch of N videos, **When** the queue starts, **Then** the first video immediately transitions to "Рендеринг" status with a live progress bar, while remaining videos display "В очереди (#2, #3, ...)".
2. **Given** an active rendering task finishes successfully, **When** it transitions to "Готово", **Then** the system automatically picks the next queued task and begins its rendering without manual intervention.
3. **Given** a video finishes rendering, **Then** its queue card displays the video player preview and a direct "Скачать MP4" button.
4. **Given** an unexpected error occurs during one video's rendering, **When** that job fails, **Then** that specific job displays an error badge and message, while the queue continues to process the remaining queued videos without crashing the entire batch.
5. **Given** multiple completed videos in the batch, **When** the user visits the queue panel, **Then** a "Скачать все готовые" action or individual download links are clearly accessible.

---

### Edge Cases

- **Strict 15 RPM Rate Limit Throttling**: When generating questions for a batch of 10 videos, system introduces an intentional delay (>= 4.5–5.0 seconds between consecutive Gemini calls) ensuring the request rate never exceeds 12 requests/minute.
- **HTTP 429 (Resource Exhausted) Handling**: If Gemini reports code 429, the system triggers exponential backoff (e.g. wait 10s, 20s) and displays an informative banner: "Ожидание квоты нейросети (15 RPM)...", resuming automatically without loss of progress.
- **User enters invalid batch size**: If the user inputs 0, negative, or more than 20 videos, the system enforces boundary limits (min 2, max 20) with friendly UI feedback.
- **User abandons batch halfway through review**: If the user closes or refreshes the page during the review step (e.g. at video 4 of 10), the draft batch state is preserved in local session storage so the user can resume review without re-generating from scratch.
- **Queue cancellation**: The user can cancel remaining queued jobs or remove a specific video from the queue before its rendering starts.
- **System crash / server restart during queue**: Jobs that were waiting in queue remain recorded with their approved scripts so the user can restart rendering with a single click.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single-click "🎲 Придумать тему" action in the single-video creation form that generates an engaging, viral quiz topic via Gemini AI.
- **FR-002**: System MUST allow creators to specify an optional topic theme/category hint (or leave it blank for maximum diversity) when requesting AI topic suggestions.
- **FR-003**: System MUST provide a "Пакетная генерация (Очередь)" toggle or mode allowing users to specify a batch count between 2 and 20 videos.
- **FR-004**: System MUST generate N unique, non-overlapping, high-curiosity topics in a SINGLE Gemini API request when initiating a batch, preventing unnecessary RPM consumption.
- **FR-005**: System MUST allow users to view, edit, or regenerate any topic in the generated batch list before proceeding to question generation.
- **FR-006**: System MUST generate 9-question 3-tier trivia challenges for all items in the batch according to the established viral progression rules (Levels 1–3).
- **FR-007**: System MUST provide a sequential review wizard ("Видео 1 из N", "Видео 2 из N") allowing users to approve each video's questions in turn.
- **FR-008**: System MUST support all existing question editing capabilities within the batch review wizard, including inline text edits, custom image search, and selective question regeneration.
- **FR-009**: System MUST permit non-linear navigation between videos in the review wizard (e.g. jump back to video 2 from video 4 to make changes).
- **FR-010**: System MUST allow the user to remove/skip an unwanted video from the batch during the approval stage.
- **FR-011**: System MUST enqueue all approved batch items into a FIFO (First-In, First-Out) sequential rendering queue upon final confirmation.
- **FR-012**: System MUST process rendering queue tasks strictly sequentially (maximum 1 concurrent active Remotion render job) to protect host hardware from VRAM/RAM exhaustion and driver crashes.
- **FR-013**: System MUST assign a random background video from available assets to each video in the batch if "Случайный фон" is selected, ensuring visual diversity across the batch.
- **FR-014**: System MUST maintain real-time status tracking for each item in the queue: `pending_approval`, `queued`, `rendering`, `completed`, `failed`.
- **FR-015**: System MUST automatically advance to the next queued item as soon as the active item completes or fails.
- **FR-016**: System MUST provide direct video download links and inline video player previews for every completed item in the queue.
- **FR-017**: System MUST provide a "Скачать все готовые видео" action when multiple batch jobs are completed.
- **FR-018**: System MUST isolate failures such that a failure in video k does not halt the rendering of remaining videos in the queue.
- **FR-019**: System MUST allow users to cancel or clear remaining items in the queue at any time.
- **FR-020**: System MUST apply batch settings (voice, background music track, music volume, uniquifier, and render profile) uniformly across all items in the batch as selected on the main dashboard before batch initiation.
- **FR-021**: System MUST implement strict rate-limiting / request pacing (<= 12 RPM, minimum 4.5-5.0 seconds delay between API calls) when generating batch questions to prevent exceeding the provider's 15 RPM quota.
- **FR-022**: System MUST implement exponential backoff retry on HTTP 429 (Resource Exhausted) errors, gracefully holding the queue without crashing or discarding batch state.
- **FR-023**: System MUST provide a dedicated "История генераций" section in the UI that displays all rendered videos with their quiz topics, creation dates/times, video players, and individual "Скачать MP4" download buttons, preserving records across browser sessions.
- **FR-024**: System MUST allow users to play, preview, or download any previously generated video directly from the "История генераций" section without clearing the active queue.

---

### Key Entities *(include if feature involves data)*

- **TopicSuggestion**: Represents an individual AI-generated topic with topic title, target niche/category, and viral curiosity hook.
- **BatchTopicList**: Collection of N topics generated for a batch, each with an index, title, and status.
- **BatchQueueItem**: An individual video task in the batch lifecycle:
  - `item_id`: Unique identifier (e.g. `bq_...`).
  - `index`: 1-based order index in the batch.
  - `topic`: Quiz topic string.
  - `challenge`: Approved `QuizChallenge` structure (9 questions, tiers, visual clues).
  - `status`: `pending_approval` | `queued` | `rendering` | `completed` | `failed`.
  - `progress_percent`: 0 to 100%.
  - `stage`: Human-readable stage description.
  - `video_path`: Local path to completed MP4.
  - `download_url`: API URL for downloading the MP4.
  - `error_message`: Optional error details if failed.
- **BatchQueue**: The orchestrator queue manager maintaining the list of `BatchQueueItem` records, active rendering lock, rate-limiting queue, and execution state.
- **GenerationHistoryItem**: Persistent record of a rendered quiz video:
  - `history_id`: Unique identifier.
  - `job_id`: Original generation job/item ID.
  - `topic`: Quiz topic title.
  - `created_at`: Creation timestamp.
  - `video_path`: Path to local MP4.
  - `download_url`: Direct download URL.
  - `duration_seconds`: Video duration.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Single topic generation completes and populates the input in under 3.5 seconds from user click.
- **SC-002**: Batch topic generation creates up to 20 distinct topics in a SINGLE API request within 6.0 seconds, consuming exactly 1 request against the 15 RPM quota.
- **SC-003**: 100% of batch AI requests remain within the 15 RPM limit without unhandled 429 errors due to automated pacing (<= 12 RPM).
- **SC-004**: 100% of approved batch items are rendered without memory exhaustion or crash on host hardware due to strict single-concurrency queue enforcement.
- **SC-005**: Users can review and approve a 10-video batch in under 5 minutes through the streamlined step wizard.
- **SC-006**: If one item in a 10-video batch encounters an asset or encoding failure, 9 out of 10 remaining videos continue and finish successfully without queue abort.
- **SC-007**: All completed batch videos are accessible for preview and download from a single persistent queue panel.

---

## Assumptions

- **Concurrency**: Remotion video encoding is CPU- and GPU-intensive; sequential (concurrency = 1) rendering is optimal for desktop consumer hardware to ensure stability and zero crashes.
- **AI Rate Limits**: The configured Gemini model (`Gemini 2.5 Flash Lite` / `Gemini 3.5 Flash Lite`) enforces a strict quota of 15 RPM and 250K TPM. All batch operations must respect this through single-call batch ideation and progressive 5-second pacing for script generation.
- **Voice and Style Consistency**: By default, all videos in a batch share the user's selected voice, sound effects volume, and render profile, while background videos are dynamically varied per video if "Случайный фон" is selected.
- **Persistence**: Batch and queue state will be maintained in-memory on the backend server with local session persistence in the web browser, so page refreshes do not disrupt ongoing renders or lose completed download links.\n
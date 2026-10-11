# Feature Specification: Automated Quiz & Trivia Shorts Generator (QuizyPeasy Style)

**Feature Branch**: `002-quiz-shorts-generator`

**Created**: 2026-10-10

**Status**: Ready for Planning

**Input**: User description: "Создай модуль генерации вертикальных викторин (Quiz / Trivia Shorts) в стиле TikTok-аккаунта QuizyPeasy. Основные требования: 1. Генерация викторин (Gemini REST API): Генерация пакета вопросов по заданной теме (общие знания, угадай флаг/страну, логотипы, поп-культура). Выходной формат — строгая Pydantic v2 схема: вопрос, 3–4 варианта ответа, правильный индекс, краткий интересный факт. 2. Озвучка и саунд-дизайн: Синтез речи вопроса и вариантов через edge-tts (бесплатные голоса Microsoft). Звуковые эффекты: тикающий таймер (3 секунды на размышление) и победный звук 'ding' при раскрытии ответа. 3. Визуальный рендеринг (9:16, 1080x1920, 60fps): Зацикленный фоновый видеоряд (нейтральный геймплей / абстрактный 3D-фон). Верх: привлекающий баннер темы. Центр: карточка вопроса / картинка. Низ: кнопки с вариантами ответов (A, B, C). Анимированная полоса таймера обратного отсчета (progress bar). Анимация раскрытия: правильный ответ подсвечивается зеленым, неверные темнеют. 4. Вывод: автоматическая сборка через FFmpeg в готовый MP4."

## Clarifications

### Session 2026-10-10
- Q: Как модуль должен упаковывать сгенерированные вопросы в готовые видеофайлы MP4? (FR-015) → A: Единый челлендж-ролик из 9 вопросов, разделенных на 3 уровня сложности: Легкий (3 вопроса, зеленый акцент), Средний (3 вопроса, желтый акцент) и Сложный (3 вопроса, красный акцент).
- Q: Что именно диктор должен озвучивать голосом для каждого из 9 вопросов и как оформлять варианты ответа? (FR-004, FR-011) → A: Озвучивается только вопрос и правильный ответ при раскрытии; варианты ответов (A, B, C) полностью исключены из видеоряда. Викторина проводится в формате прямого угадывания (Open Recall): на экране вопрос/картинка, 3 секунды таймер на размышление, затем по звонку «ding» визуально и голосом раскрывается правильный ответ.
- Q: Как система должна получать графические ассеты для визуальных викторин («угадай флаг», «логотип», «страну»)? (FR-010) → A: Option B — Автоматический динамический поиск и скачивание изображений из интернета на лету через API поиска изображений с кешированием в локальную рабочую директорию и валидацией формата/разрешения.
- Q: Как должен анимироваться текст вопроса и ответа при озвучке диктором? (FR-010, FR-014) → A: Option A — Динамические субтитры караоке. Извлечение пословных таймингов (word-level boundaries) из edge-tts и синхронная подсветка активного слова ярким неоновым цветом в такт голосу диктора.
- Q: Откуда система должна брать фоновые видеоролики (геймплей / абстрактные 3D-лупы)? (FR-008) → A: Option A — Локальная директория assets/backgrounds/ со случайным выбором готового вертикального 9:16 видеоклипа, либо опциональный путь к конкретному локальному файлу из параметров запроса.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 9-Question Open-Recall Trivia Generation & Contract Validation (Priority: P1)

A content creator specifies a quiz topic (such as General Knowledge, Guess the Flag/Country, Famous Logos, Pop Culture, or a custom prompt). The system queries the AI engine to produce a structured 9-question challenge divided into 3 progressive difficulty tiers:
1. Level 1: Easy (3 questions, green theme)
2. Level 2: Medium (3 questions, yellow theme)
3. Level 3: Hard (3 questions, red theme)
The quiz runs in an Open-Recall format: instead of multiple-choice buttons, each item contains concise question text, the single definitive correct answer, and an optional brief fun fact. For visual topics (flags, logos), the system automatically performs an online image search, downloading and verifying the visual asset into local cache. The system strictly validates the dataset against the Pydantic v2 schema before allowing downstream processing.

**Why this priority**: Open-recall trivia maximizes viewer comments and engagement. Without a verified 9-question structured dataset with difficulty tiers and verified image assets, downstream rendering cannot proceed.

**Independent Test**: Can be tested by requesting a quiz challenge on "World Flags", verifying that the output contains exactly 9 complete questions categorized into 3 Easy, 3 Medium, and 3 Hard items conforming to the Pydantic schema with downloaded valid image file paths in local cache.

**Acceptance Scenarios**:

1. **Given** a chosen topic (e.g., "World Geography"), **When** generation runs, **Then** the system outputs a challenge containing 9 questions partitioned into 3 Easy, 3 Medium, and 3 Hard questions with explicit correct answers and fun facts.
2. **Given** a visual topic (e.g., "Guess the Logo"), **When** questions are generated, **Then** the system searches the web for matching high-resolution logos, downloads them to temporary storage, and links verified local image paths in the schema.
3. **Given** an invalid or incomplete model response (e.g. fewer than 9 questions or missing tier labels), **When** validation executes, **Then** the system rejects the payload and re-requests a valid schema structure.

---

### User Story 2 - Voiceover Narration, Word-Level Alignment & Sound Design (Priority: P2)

The system automatically synthesizes natural neural speech narration for each question prompt and its revealed answer, extracting word-level alignment boundaries to drive synchronized dynamic karaoke captions. Across the 9 questions, it orchestrates a high-tension soundscape: spoken question narration with active word highlighting, a 3-second tension-building ticking sound effect during the think phase, an immediate celebratory chime ("ding") upon answer reveal, and spoken answer narration with dynamic highlighting.

**Why this priority**: Word-by-word synchronized captions and precise sound effects are essential for viewer attention retention, maintaining the total video length within the viral 55–65 second window.

**Independent Test**: Can be tested on a single question cycle or full 9-question sequence, verifying that spoken audio, word timestamp events, exactly 3.0s ticking sound, reveal chime, and answer narration trigger in exact sequence without audio clipping or synchronization drift.

**Acceptance Scenarios**:

1. **Given** a validated quiz question, **When** audio synthesis is triggered, **Then** speech audio is generated along with precise word-level boundary timestamps (`start_ms`, `end_ms`, `word`) for both the question prompt and the answer.
2. **Given** speech synthesis output, **When** the audio cue sheet is assembled, **Then** a 3-second countdown ticking sound is placed in the think window, followed immediately by a victory chime ("ding") aligned with the answer reveal.
3. **Given** the transition between difficulty tiers, **When** moving from Easy to Medium or Medium to Hard, **Then** an audio level-up stinger signals the tier escalation.

---

### User Story 3 - 3-Tier Motion Graphics & TikTok Karaoke Typography (Priority: P3)

The system visually renders the 9-question challenge in a 9:16 vertical canvas (1080x1920 at 60 fps). The visual layout consists of a looped neutral background video (randomly selected from `assets/backgrounds/` or custom file), a dynamic top banner showing the current tier and question index ("LEVEL 1: EASY • 1/9", "LEVEL 2: MEDIUM • 4/9", "LEVEL 3: HARD • 7/9"), a centered question card (or dynamically downloaded flag/logo image), dynamic word-by-word karaoke typography, and an animated countdown progress bar. No multiple-choice buttons are shown. Visual accents transition dynamically across tiers:
- Easy Tier: Vivid Neon Green accents (`#22C55E`)
- Medium Tier: Vibrant Neon Amber/Yellow accents (`#F59E0B`)
- Hard Tier: Intense Neon Crimson/Red accents (`#EF4444`)
During speech narration, each spoken word highlights dynamically with bold neon luminescence. During each 3-second thinking window, the progress bar linearly depletes at 60 fps. Upon expiration, an animated Answer Card bursts onto the screen displaying the correct answer with dynamic word highlighting and sound effects.

**Why this priority**: The combination of Open-Recall mechanics and TikTok karaoke-style text animation delivers maximum mobile engagement and retention.

**Independent Test**: Can be tested by rendering a 9-question sequence, verifying that the output strictly adheres to 1080x1920 at 60 fps, words highlight synchronously with speech, tier badges and question counters (1/9 to 9/9) update per question, UI accent colors shift from Green to Yellow to Red, and the answer card animates smoothly upon countdown completion.

**Acceptance Scenarios**:

1. **Given** spoken question narration, **When** audio plays, **Then** each spoken word on screen highlights synchronously in vibrant neon color.
2. **Given** question 1 (Easy) renders, **When** the screen is active, **Then** the header displays "LEVEL 1: EASY (1/9)" with green theme accents.
3. **Given** question 4 (Medium) renders, **When** transitioning from Level 1, **Then** the UI shifts to yellow theme accents and displays "LEVEL 2: MEDIUM (4/9)".
4. **Given** question 7 (Hard) renders, **When** transitioning from Level 2, **Then** the UI shifts to red theme accents and displays "LEVEL 3: HARD (7/9)".
5. **Given** a visual trivia question with a downloaded image, **When** rendered on screen, **Then** the image is centered inside the card using aspect-ratio containment (`object-fit: contain`).
6. **Given** timer expiration, **When** the reveal event fires, **Then** the correct answer card animates onto the screen with bold high-contrast styling and green neon accent glow, highlighting words in sync with narration.

---

### User Story 4 - Automated 9-Question Challenge Assembly & Export (Priority: P4)

The content creator can trigger automated end-to-end rendering of the complete 9-question challenge. The system orchestrates background loops, visual tiers, timer bars, voiceovers, karaoke caption timelines, and SFX into a single polished MP4 video file (~55–65 seconds) ready for publication on TikTok, YouTube Shorts, and Instagram Reels. Temporary frames, downloaded images, and audio slices are cleaned up deterministically.

**Why this priority**: Delivers a ready-to-publish viral quiz challenge in a single output file with optimal viewer completion rates.

**Independent Test**: Can be tested by rendering the full 9-question challenge, verifying that a single valid MP4 video file is produced with all 9 questions in sequence, complete audiovisual sync, and 100% temporary cache cleanup.

**Acceptance Scenarios**:

1. **Given** a 9-question challenge dataset, **When** render is initiated, **Then** the system outputs a single MP4 file containing all 9 questions across the 3 difficulty levels.
2. **Given** the rendered MP4, **When** inspected in a media player, **Then** video streams match 1080x1920 at 60 fps with synchronized stereo audio and zero stutter.
3. **Given** process completion or cancellation, **When** the job terminates, **Then** all temporary frame caches and audio slices are deleted from disk.

---

### Edge Cases

- **Web Search Failure or Broken Image**: When an online image search fails or returns a 404/corrupted file for a visual question, the system falls back to an alternate search result, or gracefully displays a stylized text/emoji card rather than breaking the render pipeline.
- **Word-Boundary Timing Desync**: If speech synthesis word boundaries have slight misalignments on rapid or hyphenated words, the system applies smoothing clamps so word highlighting never trails or precedes audible speech by more than 50ms.
- **Lengthy Question or Answer Text**: When question text or the revealed answer is unusually long, font sizes must automatically scale down or wrap gracefully to prevent text overflowing beyond card boundaries.
- **External Speech Synthesis Outages**: If the remote speech synthesis service is temporarily unavailable or times out, the system implements retry attempts with backoff and reports actionable errors if unrecoverable.
- **Short Background Video Loops**: If the source background video is shorter than the 9-question challenge duration (~60s), the system seamlessly loops the video without audio glitches, black frames, or frozen frames.
- **Aspect Ratio Distortions**: When downloaded question images have varying aspect ratios, they must be scaled with `object-fit: contain` inside a fixed aspect-ratio container to prevent stretching or cutoff.
- **Dynamic Timing Drift Across 9 Questions**: Each question's start, think, and reveal keyframes must be dynamically chained to preceding audio durations to prevent cumulative drift across the 9 questions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support generating structured trivia challenges of exactly 9 questions based on user-selected preset topics ("General Knowledge", "Guess the Flag/Country", "Brand Logos", "Pop Culture") and user-defined custom text prompts.
- **FR-002**: System MUST validate all generated trivia challenges against a strict structured contract containing:
  - 3 progressive difficulty tiers: Level 1 (Easy, 3 questions), Level 2 (Medium, 3 questions), Level 3 (Hard, 3 questions).
  - Each question item containing: question text, definitive correct answer string, brief fun fact, tier index (1 to 3), question index (1 to 9), and optional visual asset path or search query. (Multiple-choice option buttons are omitted from the user-facing format).
- **FR-003**: System MUST reject and re-request or discard any generated trivia items that fail schema validation (such as missing answers, empty question titles, or out-of-bounds indices).
- **FR-004**: System MUST synthesize natural neural speech for the question text and the revealed answer with fun fact for each of the 9 questions, capturing word-level timing boundaries (`start_ms`, `end_ms`, `word`). Multiple-choice options are not read aloud.
- **FR-005**: System MUST provide configurable voice selection supporting multiple languages (at minimum Russian and English) with matching natural neural voices.
- **FR-006**: System MUST generate a continuous synchronized audio composition combining spoken question prompts, 3-second tension-building ticking sound effects per question, celebratory "ding" chimes upon answer reveals, and tier-up stingers between levels.
- **FR-007**: System MUST render vertical video compositions strictly adhering to 9:16 aspect ratio (1080x1920 resolution) at 60 frames per second.
- **FR-008**: System MUST select a neutral background video at random from a local directory (`assets/backgrounds/`), supporting an optional explicit file path override in job parameters, and loop it seamlessly if shorter than total video duration.
- **FR-009**: System MUST display a dynamic thematic banner at the top of the canvas showing the current category, difficulty level badge ("LEVEL 1: EASY", "LEVEL 2: MEDIUM", "LEVEL 3: HARD"), and question counter ("1/9" through "9/9").
- **FR-010**: System MUST render dynamic TikTok karaoke-style animated captions with word-by-word neon highlighting for spoken question prompts, synchronized with audio narration.
- **FR-011**: System MUST support automated on-the-fly image search and download for visual trivia topics ("Guess the Flag/Country", "Logos"), caching verified images locally with fallback to stylized text/emoji cards upon network failure.
- **FR-012**: System MUST omit multiple-choice option buttons (A, B, C, D) from the canvas, operating in an Open-Recall format where viewers mentally formulate the answer during the countdown.
- **FR-013**: System MUST display an animated countdown timer progress bar that smoothly depletes over exactly 3.0 seconds during each question's think phase at 60 fps.
- **FR-014**: System MUST dynamically adapt UI theme accent colors across difficulty tiers:
  - Level 1 (Easy): Neon Green accents (`#22C55E`)
  - Level 2 (Medium): Neon Amber/Yellow accents (`#F59E0B`)
  - Level 3 (Hard): Neon Crimson/Red accents (`#EF4444`)
- **FR-015**: System MUST execute an instantaneous reveal transition when each countdown completes, animating the Answer Card with bold typography, word-by-word synchronized highlighting, and vivid neon accent glow.
- **FR-016**: System MUST assemble the entire 9-question challenge into a single cohesive high-engagement MP4 video (~55–65 seconds) ready for TikTok, YouTube Shorts, and Instagram Reels.
- **FR-017**: System MUST deterministically isolate and delete all temporary files (intermediate audio cuts, frame sequences, temp video slices) upon job completion or termination.

### Key Entities

- **Quiz Challenge Dataset**: Complete challenge containing 9 `QuizItem`s structured into 3 `QuizTier` objects (Easy, Medium, Hard).
- **Quiz Item**: Represents a single open-recall trivia question, containing `topic`, `difficulty` ("easy" | "medium" | "hard"), `question_number` (1-9), `question_text`, `correct_answer`, `fun_fact`, `image_query` (optional), and `local_image_path` (optional).
- **Audio Cue Sheet**: Master timeline mapping timestamps for all 9 questions: question speech intervals, word-level boundary cues, 3.0s think intervals, reveal ding timestamps, answer speech intervals, and tier transition points.
- **Tier Theme Configuration**: Visual styling mapped to difficulty: Easy (Green `#22C55E`), Medium (Yellow `#F59E0B`), Hard (Red `#EF4444`).
- **Background Asset**: Background video resource selected from `assets/backgrounds/` or custom filepath.
- **Quiz Video Render Job**: The execution unit combining the 9-Question Dataset, Master Audio Cue Sheet, Background Asset, and Motion Graphics Template to produce the finalized MP4 file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of trivia challenge datasets conform to the 9-question 3-tier open-recall schema without runtime type or parsing errors.
- **SC-002**: Generated video files strictly conform to 1080x1920 (9:16) resolution, 60.0 fps video stream, and 48kHz AAC stereo audio.
- **SC-003**: Audiovisual synchronization between spoken syllables and visual karaoke word highlights is within 50 milliseconds across all 9 questions.
- **SC-004**: Audiovisual synchronization between each audio reveal chime ("ding") and the visual answer card reveal transition is within 50 milliseconds across all 9 questions.
- **SC-005**: Total challenge video duration remains strictly within 55 to 65 seconds, maintaining optimal completion rates and loop potential on vertical video platforms.
- **SC-006**: All text elements (questions, revealed answers, banners, tier badges) remain 100% legible on standard mobile screens (tested at 360x640 mobile viewport size).
- **SC-007**: 100% of temporary intermediate media files and frame buffers are deleted from disk upon job finish, ensuring zero persistent disk space leakage.

## Assumptions

- **Target Output Format**: A single 9-question vertical challenge video per generation job, lasting between 55 and 65 seconds in Open-Recall format with TikTok karaoke subtitles.
- **Difficulty Tiers**: Standardized as 3 questions per tier: Questions 1–3 Easy (Green), Questions 4–6 Medium (Yellow), Questions 7–9 Hard (Red).
- **Think Time**: Standardized at 3.0 seconds per question with animated countdown bar.
- **Asset Bundling**: Neutral background video loops and sound effects (ticking timer, reveal chime, tier stingers) are supplied from a curated local library (`assets/backgrounds/` and `assets/sfx/`).
- **Image Sourcing**: Visual trivia queries automated online image search API on the fly, with local caching in job workspace and fallback handling.
- **Language & Voice Support**: Both Russian and English supported out-of-the-box with default Microsoft neural voices assigned per language.
- **Execution Environment**: Runs locally with Remotion (Node.js/React/Tailwind) and FFmpeg orchestrated by Python 3.11 backend.

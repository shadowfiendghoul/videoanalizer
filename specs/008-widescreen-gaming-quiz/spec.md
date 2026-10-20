# Feature Specification: 008-widescreen-gaming-quiz

**Feature Branch**: `008-widescreen-gaming-quiz`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Design a complete, modular 16:9 widescreen (1920x1080) gaming trivia quiz video system with multi-round progression, dynamic game mechanics, and strict visual hierarchy inspired by 'Quiz Please'. Overall video & round structure target ~9-10 minutes, 50 questions total across 5 rounds, 4s splash screens, intro hook, outro score tier evaluation. Canvas & layout coordinates 1920x1080. Timing & audio rules 9.0s per question (6.0s guess + 3.0s reveal). All texts, themes, rounds, and games are examples and must be configurable by users."

## Clarifications

### Session 2026-10-20
- Q: Каким основным способом пользователи будут задавать и формировать датасет для 50 вопросов викторины 16:9? → A: ИИ-генерация по промту через Gemini с автоматическим поиском ассетов и последующим обязательным этапом верификации/ручной правки вопросов, ответов и медиа перед рендерингом (согласовано с существующими режимами VideoAnalyzer).
- Q: Будет ли использоваться голос диктора (TTS-озвучка) для зачитывания самих вопросов и ответов во время 9-секундного цикла вопроса? → A: Вариант A — только SFX/звуковое оформление в раундах (тиканье, аудио-фрагменты, победный джингл); голос диктора озвучивает только Интро (0–8 с) и Аутро (15 с), обеспечивая строго фиксированный 9.0-секундный тайминг каждого вопроса без рассинхрона речи.
- Q: Как система должна получать звуковые ассеты для Раунда 2 («Звуки оружия / предметов») при автоматической генерации викторины через ИИ-промт? → A: Вариант B с контролем пользователя — автоматический поиск и загрузка звукового фрагмента из веб-источников/API по ключевым словам из промта с обязательным предпрослушиванием, ручной проверкой и возможностью загрузить/заменить файл в окне верификации перед рендерингом.
- Q: Должна ли система автоматически накладывать визуальные маски и фильтры (круглый радар, темный силуэт) через Remotion/CSS к обычным картинкам, или ожидать уже заранее подготовленные/отфотошопленные ассеты? → A: Вариант C — процедурные маски в Remotion по умолчанию (для Раунда 4 круглая маска радара с HUD-сеткой, для Раунда 5 высококонтрастный силуэт), с возможностью отключения фильтра или загрузки готового файла в окне верификации UI.
- Q: Должна ли присутствовать постоянная фоновая музыка (BGM) на протяжении всей викторины, и как она должна вести себя в аудио-раунде со звуками оружия? → A: Вариант A — единый нагнетающий фоновый саундтрек на протяжении всей викторины с автоматическим приглушением (audio ducking до 15–20% громкости) в момент воспроизведения звуков оружия (Раунд 2, 0.5–4.5 с) и во время речи диктора в Интро/Аутро.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 16:9 Widescreen Question Stage & Timing Synchronization (Priority: P1)

As a YouTube viewer and quiz participant, I want to watch a clean, high-impact 1920x1080 widescreen gaming trivia stage where questions, asset media, an animated countdown bar, and answer reveals appear with exact, rhythmic predictability, so that I can participate in the quiz in real time without cognitive clutter.

**Why this priority**: The core value of a long-form trivia show lies in the presentation stage and timing rhythm of individual questions. Without a responsive, visually balanced 16:9 canvas and synchronized 9-second question cycle (6s guessing + 3s reveal hold), the video system cannot function as an engaging quiz.

**Independent Test**: Can be verified by rendering a standalone 1-round sequence of questions and testing that each question strictly abides by the 6.0s countdown bar depletion, positive reveal chime at 6.0s, and 3.0s answer hold before transitioning.

**Acceptance Scenarios**:

1. **Given** a question with an image asset, **When** the question starts, **Then** the top status bar displays the current round title and question counter ("QUESTION 01 / 10"), the asset container displays the image fitted inside 1140x540 px, and the countdown timer linearly shrinks from 100% to 0% over 6.0 seconds with synchronized ticking audio.
2. **Given** the timer reaches 0.0 seconds (frame equivalent at 60 fps), **When** 6.0 seconds elapse, **Then** the answer reveal panel snaps into view with an instant bounce animation and chime sound, displaying the correct answer in uppercase for exactly 3.0 seconds.
3. **Given** an answer has been displayed for 3.0 seconds, **When** 9.0 seconds total per question elapse, **Then** the stage immediately transitions to the subsequent question without dead air.

---

### User Story 2 - Multi-Round Progression & Multi-Modal Asset Mechanics (Priority: P2)

As a video creator, I want to configure multi-round quizzes (such as 5 rounds of 10 questions, or custom round counts) where each round can employ distinct gameplay mechanics (screenshots, audio SFX with animated waveforms, masked game-over screens, cropped HUD minimaps, and character silhouettes), so that viewer fatigue is prevented over long 9–10 minute videos.

**Why this priority**: Long-form trivia retention depends on variety. Switching mechanics between rounds (e.g. from visual screenshots to audio sound identification to radar recognition) refreshes viewer interest across a 50-question marathon.

**Independent Test**: Can be tested by configuring a dataset containing at least one image round and one audio SFX round, verifying that image rounds render fitted graphics and audio rounds render the glowing animated waveform icon while playing the cue audio between 0.5s and 4.5s.

**Acceptance Scenarios**:

1. **Given** a round configured for audio identification (e.g., weapon or item sound), **When** a question in this round is active, **Then** the asset container renders an animated glowing cyan waveform / speaker icon and plays the specific game audio snippet during 0.5s–4.5s of the guessing phase.
2. **Given** a round configured for HUD/minimap or game-over recognition, **When** the question is rendered, **Then** the asset container displays the cropped graphic without revealing masked titles or spoiler details.
3. **Given** a question transitions from one round to another, **When** the round number increments, **Then** the top-left round badge updates its title and styling according to the new round's metadata.

---

### User Story 3 - Cinematic Round Splash Transitions & Gamified Outro (Priority: P3)

As a viewer, I want to experience distinct 4-second cinematic splash screens between rounds (with round titles, pass rates, and sound stingers) and a gamified score evaluation outro card (Noob to God Tier) at the end, so that the quiz feels like a polished broadcast gameshow ("Quiz Please").

**Why this priority**: Broadcast polish and competitive benchmarking give viewers a clear sense of progression, build anticipation for harder rounds, and drive comments for YouTube algorithmic distribution.

**Independent Test**: Can be tested by running a transition between Round 1 and Round 2 to verify the 4-second splash screen with zoom and audio stinger, followed by rendering the final outro card at the conclusion of all rounds.

**Acceptance Scenarios**:

1. **Given** the final question of a round finishes its 3.0s answer hold, **When** transitioning to the next round, **Then** a 4.0-second splash screen displays the upcoming round title, pass rate statistic, and audio sub-bass stinger before question 1 of the new round begins.
2. **Given** all 50 questions have concluded, **When** entering the outro phase, **Then** a 15-second outro card displays the tier bracket breakdown (0–20: Noob, 21–35: Gamer, 36–45: Pro, 46–50: God Tier) and prompts viewers to comment their final score and subscribe.
3. **Given** the video starts at 0:00, **When** the intro hook plays, **Then** an 8.0-second dynamic challenge teaser announces the 50-question structure and kicks off Round 1 without stalling.

---

### User Story 4 - Modular & Fully Customizable Content Configuration (Priority: P4)

As a content producer, I want to supply my own custom quiz themes, round definitions, media asset links, difficulty curves, question quantities, and text strings via a structured configuration dataset, so that the engine is not hardcoded to a single gaming topic and can generate any 16:9 trivia show.

**Why this priority**: Creators need to produce diverse series (e.g. Anime Trivia, Retro 90s Gaming, Movie Quotes, General Esports) using the same high-production 16:9 widescreen layout without modifying rendering code.

**Independent Test**: Can be tested by supplying an alternate non-gaming dataset (e.g. Cinema Trivia) with 3 rounds of 6 questions and verifying that the system successfully parses, lays out, and renders the video according to the provided dataset.

**Acceptance Scenarios**:

1. **Given** a custom dataset with custom round names, question counts, and asset URLs, **When** validated by the system, **Then** all layout coordinates, badge titles, question totals ("QUESTION X / Y"), and timers adapt dynamically.
2. **Given** a creator modifies the guessing timer duration (e.g. from 6.0s to 5.0s or 7.0s) or answer hold duration (e.g. from 3.0s to 2.5s), **When** rendered, **Then** the countdown bar, audio events, and reveal transitions calibrate automatically to the configured values.
3. **Given** a draft dataset generated from an AI prompt, **When** the creator inspects the batch before rendering, **Then** the interface allows reviewing, editing question/answer texts, swapping media assets, and approving the batch before initiating the final Remotion render.

---

### Edge Cases

- **Asset aspect ratio mismatch**: When a provided screenshot or image does not match the 1140x540 container (e.g. 4:3 retro screenshot or ultra-wide HUD crop), the system preserves the original aspect ratio with centered placement and uniform letterboxing without stretching or pixel distortion.
- **Audio asset duration exceeds guessing window**: When an audio SFX snippet is longer than 4.0 seconds (exceeding the 0.5s–4.5s window), the audio is cleanly truncated with a 0.25-second fade-out before the reveal chime fires at 6.0 seconds.
- **Long answer text overflow**: When an answer title contains unusually long text (e.g., > 35 characters such as "THE CHRONICLES OF RIDDICK: ASSAULT ON DARK ATHENA"), the text container automatically reduces font scale or wraps cleanly within the 1000px answer panel without clipping outside container bounds.
- **Missing or corrupted asset file**: If an image or audio file fails validation or cannot be resolved, the system renders a clean branded placeholder (with asset name and question prompt) rather than crashing the rendering pipeline.
- **Audio asset search failure or invalid format**: When an automated web search for an audio snippet fails to find a suitable clip, the system flags the question item in the verification interface with a visual warning badge and allows the creator to upload a local audio file or accept a fallback neutral SFX stinger.
- **Variable round size**: If a creator configures an uneven number of questions per round (e.g. 8 questions in Round 1 and 12 in Round 2), the question tracker ("QUESTION 08 / 08") accurately reflects the specific round's capacity.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render all video output strictly in 16:9 widescreen format (1920x1080 resolution) at 60.0 frames per second.
- **FR-002**: System MUST structure the trivia video into an Intro Hook (0:00–0:08), N configurable Rounds (default: 5 rounds of 10 questions each for 50 questions total), 4.0-second Round Splash Screens between rounds, and a 15-second Gamified Outro Card.
- **FR-003**: System MUST execute each question in a strict, two-phase timed cycle: a Guessing Phase (default: 6.0 seconds) and an Answer Reveal Hold Phase (default: 3.0 seconds), yielding a strict 9.0-second base question duration.
- **FR-004**: System MUST position a Top Status Bar containing a Top-Left Round Badge (X: 120px, Y: 50px, W: 480px, H: 60px) and a Top-Right Question Tracker (X: 1480px, Y: 50px, W: 320px, H: 60px).
- **FR-005**: System MUST position a Central Asset Container (X: 360px, Y: 170px, W: 1200px, H: 600px) that supports multiple asset display modes:
  - *Image / Screen mode*: Centered image, max fit 1140x540 px, 12px corner radius, preserved aspect ratio.
  - *Minimap / Radar mode*: Centered image with procedural circular crop (`clip-path: circle()`) and subtle tactical radar HUD grid overlay by default, with per-item toggle to bypass for pre-cut radar assets.
  - *Silhouette mode*: Character graphic with procedural high-contrast silhouette mask (`filter: brightness(0)`) by default, with per-item toggle to bypass for pre-rendered silhouettes.
  - *Audio SFX mode*: Dark container displaying a centered, animated glowing cyan (#00E5FF) pulse / waveform graphic while cue audio plays.
- **FR-006**: System MUST position a Countdown Timer Bar (X: 360px, Y: 800px, W: 1200px, H: 16px) that linearly depletes from 100% width to 0px over the Guessing Phase (6.0s), transitioning from amber (#F59E0B) to red (#EF4444) during the final 1.5 seconds.
- **FR-007**: System MUST position an Answer Reveal Panel (X: 460px, Y: 860px, W: 1000px, H: 90px) that remains hidden or displays an unobtrusive guessing prompt during 0.0s–6.0s, and snaps into view at 6.0s with an instant scale-up bounce animation, holding until 9.0s.
- **FR-008**: System MUST assemble a multi-track audio mix per question strictly using non-verbal audio elements (no spoken question/answer narration):
  - Rhythmic ticking audio during the 0.0s–6.0s Guessing Phase.
  - Question-specific audio cue playback during 0.5s–4.5s for audio rounds.
  - A positive reveal chime stinger at exactly 6.0s when the answer panel appears.
  - Voiceover narration is strictly confined to the Intro Hook (0:00–0:08) and Outro Card (15s).
- **FR-009**: System MUST render a 4.0-second Round Splash Screen between consecutive rounds displaying the upcoming Round Number, Round Title, a difficulty / pass rate callout, accompanied by a cinematic sub-bass audio stinger.
- **FR-010**: System MUST render a 15-second Outro Card presenting a 4-tier score breakdown (0–20: Noob, 21–35: Gamer, 36–45: Pro, 46–50: God Tier) and a subscriber call-to-action.
- **FR-011**: System MUST render a deep carbon slate (#0D1117 with radial vignette to #07090D) background layer overlaid with a darkened (50% opacity), heavily blurred (80% blur) looping ambient background video.
- **FR-012**: System MUST ingest and validate all rounds, question items, media paths, timers, texts, and score tiers via a declarative, strictly typed data model without hardcoding gaming trivia content.
- **FR-013**: System MUST provide an interactive review and editing stage for AI-prompt-generated datasets, allowing creators to inspect, modify question/answer texts, verify or replace media assets, and approve the batch prior to initiating final video rendering.
- **FR-014**: System MUST support an automated audio asset retrieval pipeline for audio-based rounds (e.g. Round 2 weapon/item sounds) that queries web audio sources/APIs by game/item keywords, automatically caches preview clips, and enables playback audition and file replacement/upload in the verification UI before final rendering.
- **FR-015**: System MUST mix a continuous ambient background music (BGM) track beneath the soundscape across all rounds, with automated audio ducking (reducing BGM to 15–20% volume) during Round 2 audio cue playback (0.5s–4.5s) and speech narration in Intro/Outro.

### Key Entities *(include if feature involves data)*

- **WidescreenQuizDataset**: Root dataset defining the entire 16:9 quiz show, including title, intro hook, outro configuration, background styling, global timing defaults, background music track (`bgm_track_path: Optional[str]`, `bgm_ducking_volume: float = 0.2`), and an ordered list of rounds.
- **WidescreenQuizRound**: Specification for an individual round, containing round index, round name, visual badge theme, asset display mode (screenshot, audio_sfx, game_over, minimap, silhouette, custom), pass rate statistic, and an ordered list of questions.
- **WidescreenQuizItem**: Individual question data unit containing question index within the round, global question number (e.g. 1–50), prompt text, answer text, asset media path/URL (image or audio), procedural mask toggle (`apply_procedural_mask: bool = True`), and optional difficulty tag.
- **WidescreenTimingSlot**: Calculated timeline coordinates per question (guessing phase start/duration, reveal trigger frame, hold duration, total question duration in frames).
- **WidescreenOutroConfig**: Definition of score evaluation tiers (point ranges, tier names, badge colors) and call-to-action text for the outro sequence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of generated video output is strictly 1920x1080 resolution at 60.0 fps without visual distortion or letterbox stretching.
- **SC-002**: A complete 50-question, 5-round trivia video renders with a total duration between 8 minutes 45 seconds and 10 minutes 00 seconds (including intro, 4 interstitial splashes, and outro).
- **SC-003**: The countdown timer bar depletes at a steady 60 fps without frame drops, and the answer reveal snaps into view within 1 video frame (16.6ms) of the 6.0-second reveal trigger mark.
- **SC-004**: System supports configuring 1 to 10 distinct rounds with variable question counts (1 to 20 questions per round) without requiring any layout or styling code alterations.
- **SC-005**: All text elements (answers up to 45 characters, round titles up to 40 characters) fit within designated bounding boxes without clipping or overflowing outside safe canvas margins.

## Assumptions

- **Target platform**: YouTube desktop and TV long-form landscape viewing (16:9 aspect ratio at 1080p60), distinct from vertical short-form (9:16) platforms.
- **Asset preparation**: Image assets for screenshots, game-over screens, and minimaps are sourced or cropped to approximately landscape orientation before rendering; audio snippets are clean SFX clips between 1.0s and 4.0s in length.
- **Voiceover narration**: Spoken speech narration is strictly confined to the Intro Hook and Outro Card. The in-round 9.0s question cycles operate strictly on procedural sound effects (ticking, game cue, reveal chime), eliminating speech length variance and guaranteeing zero timing drift across all 50 questions.
- **Existing architecture compatibility**: Reuses the core VideoAnalyzer decoupled architecture (@script-service for content models, @audio-service for audio mixing, @orchestrator for coordination, and Remotion CLI for rendering).

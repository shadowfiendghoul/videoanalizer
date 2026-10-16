"""AudioService: Generates voiceover narration via edge-tts and master AudioCueSheet."""

import asyncio
import logging
import math
import re
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts

from videoanalizer.quiz.config import QuizConfig, get_quiz_config
from videoanalizer.quiz.models import (
    AudioCueSheet,
    QuestionAudioCue,
    QuizChallenge,
    QuizRetentionConfig,
    SfxPaths,
    VisualQuizDataset,
    VisualQuizTimingSlot,
    VisualQuizWordTiming,
    VoiceConfig,
    WordCue,
)
from videoanalizer.quiz.workspace import QuizWorkspace

logger = logging.getLogger(__name__)


def ensure_latest_edge_tts() -> None:
    """Ensure edge_tts is upgraded to >=7.3.1 in sys.modules to prevent 403 handshake errors."""
    global edge_tts
    if getattr(edge_tts, "__version__", "") < "7.3.1":
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("edge_tts"):
                del sys.modules[mod_name]
        import edge_tts as _reloaded_edge_tts

        edge_tts = _reloaded_edge_tts


def probe_audio_duration_ms(audio_path: Path) -> int:
    """Probe audio duration in milliseconds using ffprobe or fallback calculation."""
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        # Check ffmpeg dir for ffprobe
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            candidate = Path(ffmpeg_bin).parent / "ffprobe.exe"
            if candidate.exists():
                ffprobe_bin = str(candidate)

    if ffprobe_bin and audio_path.exists():
        try:
            cmd = [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)  # noqa: S603
            sec = float(res.stdout.strip())
            return int(sec * 1000)
        except Exception as e:
            logger.debug(f"ffprobe failed for {audio_path}: {e}")

    # Fallback to file size estimation for 128kbps mp3 if probe unavailable
    if audio_path.exists() and audio_path.suffix.lower() == ".mp3":
        size = audio_path.stat().st_size
        # 128kbps = 16000 bytes/sec
        return max(500, int((size / 16000) * 1000))
    return 2000


def ensure_default_sfx(sfx_dir: Path) -> None:
    """Ensure standard sound effects exist, generating synthetic WAVs if missing."""
    sfx_dir.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100

    tick_mp3 = sfx_dir / "timer_tick.mp3"
    tick_path = sfx_dir / "timer_tick.wav"
    if not tick_path.exists() and not tick_mp3.exists():
        n_samples = int(sample_rate * 0.1)
        with wave.open(str(tick_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                env = math.exp(-i / (sample_rate * 0.015))
                val = math.sin(2 * math.pi * 1800 * t) * env * 28000
                data.extend(struct.pack("<h", int(val)))
            f.writeframes(data)

    chosen_tick = tick_mp3 if tick_mp3.exists() else tick_path

    ding_path = sfx_dir / "reveal_ding.wav"
    if not ding_path.exists():
        n_samples = int(sample_rate * 1.2)
        with wave.open(str(ding_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                env = math.exp(-i / (sample_rate * 0.25))
                val = (
                    (
                        0.7 * math.sin(2 * math.pi * 1046.5 * t)
                        + 0.3 * math.sin(2 * math.pi * 2093.0 * t)
                    )
                    * env
                    * 28000
                )
                data.extend(struct.pack("<h", int(val)))
            f.writeframes(data)

    level_up_path = sfx_dir / "level_up.wav"
    if not level_up_path.exists():
        n_samples = int(sample_rate * 1.2)
        notes = [523.25, 659.25, 783.99, 1046.5]
        with wave.open(str(level_up_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                note_idx = min(int(t / 0.15), len(notes) - 1)
                freq = notes[note_idx]
                note_t = t - (note_idx * 0.15)
                env = math.exp(-note_t * 3.0) if note_idx < 3 else math.exp(-note_t * 2.0)
                val = math.sin(2 * math.pi * freq * t) * env * 26000
                data.extend(struct.pack("<h", int(val)))
            f.writeframes(data)

    heartbeat_path = sfx_dir / "heartbeat_panic.wav"
    if not heartbeat_path.exists():
        # Double-pulse heartbeat sound (0.6s)
        n_samples = int(sample_rate * 0.6)
        with wave.open(str(heartbeat_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                # First thump at 0.0s, second thump at 0.22s
                env1 = math.exp(-t * 25.0) if t < 0.22 else 0.0
                t2 = t - 0.22
                env2 = math.exp(-t2 * 20.0) if t >= 0.22 else 0.0
                val = (
                    math.sin(2 * math.pi * 65.0 * t) * env1 * 28000
                    + math.sin(2 * math.pi * 55.0 * t) * env2 * 30000
                )
                data.extend(struct.pack("<h", int(max(-32767, min(32767, val)))))
            f.writeframes(data)

    streak_fire_path = sfx_dir / "streak_fire.wav"
    if not streak_fire_path.exists():
        # Fire whoosh burst (0.5s)
        n_samples = int(sample_rate * 0.5)
        with wave.open(str(streak_fire_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                env = math.sin(math.pi * (i / n_samples))
                # Frequency glide from 300Hz to 900Hz
                freq = 300.0 + 600.0 * (t / 0.5)
                val = math.sin(2 * math.pi * freq * t) * env * 25000
                data.extend(struct.pack("<h", int(max(-32767, min(32767, val)))))
            f.writeframes(data)

    rank_levelup_path = sfx_dir / "rank_levelup.wav"
    if not rank_levelup_path.exists():
        # Soaring cosmic arpeggio (1.4s)
        n_samples = int(sample_rate * 1.4)
        cosmic_notes = [440.0, 554.37, 659.25, 880.0, 1108.73]
        with wave.open(str(rank_levelup_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                idx = min(int(t / 0.12), len(cosmic_notes) - 1)
                freq = cosmic_notes[idx]
                note_t = t - (idx * 0.12)
                env = math.exp(-note_t * 2.5)
                val = (
                    0.7 * math.sin(2 * math.pi * freq * t)
                    + 0.3 * math.sin(2 * math.pi * (freq * 2) * t)
                ) * env * 27000
                data.extend(struct.pack("<h", int(max(-32767, min(32767, val)))))
            f.writeframes(data)

    comment_buzzer_path = sfx_dir / "comment_buzzer.wav"
    if not comment_buzzer_path.exists():
        # Dramatic deep brass / vine boom impact (1.0s)
        n_samples = int(sample_rate * 1.0)
        with wave.open(str(comment_buzzer_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                env = math.exp(-t * 4.0)
                # Pitch drop from 120Hz to 45Hz
                freq = max(45.0, 120.0 - 75.0 * t)
                val = (
                    0.8 * math.sin(2 * math.pi * freq * t)
                    + 0.2 * math.sin(2 * math.pi * (freq * 3) * t)
                ) * env * 31000
                data.extend(struct.pack("<h", int(max(-32767, min(32767, val)))))
            f.writeframes(data)

    card_flip_path = sfx_dir / "card_flip_rapid.wav"
    if not card_flip_path.exists():
        # Rapid clicking card flip sound (3.5s)
        n_samples = int(sample_rate * 3.5)
        with wave.open(str(card_flip_path), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                phase = (t % 0.12)
                click_env = math.exp(-phase * 120.0) if phase < 0.04 else 0.0
                val = math.sin(2 * math.pi * 1800.0 * t) * click_env * 24000
                data.extend(struct.pack("<h", int(max(-32767, min(32767, val)))))
            f.writeframes(data)

    return SfxPaths(
        timer_tick=str(chosen_tick),
        reveal_ding=str(ding_path),
        level_up=str(level_up_path),
        heartbeat_panic=str(heartbeat_path),
        streak_fire=str(streak_fire_path),
        rank_levelup=str(rank_levelup_path),
        comment_buzzer=str(comment_buzzer_path),
    )



class AudioService:
    """Synthesizes speech and compiles master synchronized AudioCueSheet."""

    def __init__(self, config: QuizConfig | None = None) -> None:
        self.config = config or get_quiz_config()

    def ensure_default_sfx(self, sfx_dir: Path) -> SfxPaths:
        """Ensure standard sound effects exist, returning SfxPaths."""
        return ensure_default_sfx(sfx_dir)

    def _synthesize_offline_fallback(
        self, text: str, output_path: Path, voice: str = ""
    ) -> None:
        """Offline fallback using pyttsx3 or synthetic audio when edge-tts is unavailable."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import pyttsx3

            wav_path = output_path.with_suffix(".wav")
            engine = pyttsx3.init()
            if "irina" in voice.lower() or "ru" in voice.lower():
                for v in engine.getProperty("voices"):
                    if "irina" in v.id.lower():
                        engine.setProperty("voice", v.id)
                        break
            engine.save_to_file(text, str(wav_path))
            engine.runAndWait()

            if output_path.suffix.lower() == ".mp3":
                ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
                subprocess.run(  # noqa: S603
                    [ffmpeg_bin, "-y", "-i", str(wav_path), "-b:a", "192k", str(output_path)],
                    check=True,
                    capture_output=True,
                )
                if wav_path.exists():
                    wav_path.unlink()
            elif wav_path != output_path:
                shutil.move(str(wav_path), str(output_path))
            return
        except Exception as e:
            logger.warning("pyttsx3 offline fallback failed: %s. Generating tone fallback.", e)

        # Final safety fallback: synthetic tone file
        sample_rate = 44100
        n_samples = int(sample_rate * 1.5)
        wav_target = (
            output_path.with_suffix(".wav")
            if output_path.suffix.lower() == ".mp3"
            else output_path
        )
        with wave.open(str(wav_target), "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            data = bytearray()
            for i in range(n_samples):
                t = i / sample_rate
                val = math.sin(2 * math.pi * 440.0 * t) * 16000
                data.extend(struct.pack("<h", int(val)))
            f.writeframes(data)

        if output_path.suffix.lower() == ".mp3":
            ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
            subprocess.run(  # noqa: S603
                [ffmpeg_bin, "-y", "-i", str(wav_target), "-b:a", "192k", str(output_path)],
                check=False,
                capture_output=True,
            )
            if wav_target.exists():
                wav_target.unlink()

    async def synthesize_speech_with_cues(
        self,
        text: str,
        voice: str,
        output_path: Path,
        voice_config: VoiceConfig | None = None,
        allow_fallback: bool = False,
    ) -> tuple[int, list[WordCue]]:
        """Synthesize text via edge-tts or VoiceService, capturing audio and word-level timestamps.

        Includes multiple fallback voices, exponential retry backoff, and strict voice consistency.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if voice_config is not None:
            from videoanalizer.quiz.voice_service import VoiceService

            if not hasattr(self, "_voice_service") or self._voice_service is None:
                self._voice_service = VoiceService(config=voice_config)
            res = await self._voice_service.synthesize(text, output_path, voice_config)
            cues = [
                WordCue(word=w.word, start_ms=w.start_ms, end_ms=w.end_ms) for w in res.words
            ]
            return res.duration_ms, cues

        if "sapi" in voice.lower() or "irina" in voice.lower():
            self._synthesize_offline_fallback(text, output_path, voice=voice)
            duration_ms = probe_audio_duration_ms(output_path)
            words: list[WordCue] = []
            tokens = text.split()
            if tokens and duration_ms > 0:
                step = duration_ms // len(tokens)
                for i, tok in enumerate(tokens):
                    words.append(WordCue(word=tok, start_ms=i * step, end_ms=(i + 1) * step))
            return duration_ms, words

        rate_arg = "+0%"
        af_filter: str | None = None
        base_voice = voice

        if voice == "ru-RU-SvetlanaEnergetic":
            base_voice = "ru-RU-SvetlanaNeural"
            rate_arg = "+15%"
        elif voice == "ru-RU-MaleBaritone":
            base_voice = "ru-RU-SvetlanaNeural"
            af_filter = (
                "asetrate=44100*0.82,atempo=1/0.82,"
                "equalizer=f=150:t=q:w=1:g=4,equalizer=f=2500:t=q:w=1:g=2"
            )
        elif voice == "ru-RU-EpicAnnouncer":
            base_voice = "ru-RU-SvetlanaNeural"
            af_filter = (
                "asetrate=44100*0.74,atempo=1/0.74,"
                "equalizer=f=100:t=q:w=1.2:g=7,aecho=0.8:0.7:40:0.25"
            )
        elif voice == "ru-RU-ChibiCartoon":
            base_voice = "ru-RU-SvetlanaNeural"
            af_filter = "asetrate=44100*1.28,atempo=1/1.28,equalizer=f=3000:t=q:w=1:g=3"

        voices_to_try = [base_voice]

        if "ru-" in base_voice.lower():
            for ru_voice in ("ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"):
                if ru_voice not in voices_to_try:
                    voices_to_try.append(ru_voice)
        elif "en-" in base_voice.lower():
            for en_voice in (
                "en-US-GuyNeural",
                "en-US-JennyNeural",
                "en-US-ChristopherNeural",
            ):
                if en_voice not in voices_to_try:
                    voices_to_try.append(en_voice)

        audio_bytes = bytearray()
        words: list[WordCue] = []
        synthesized_successfully = False
        detected_speech_start_ms: int | None = None
        detected_speech_duration_ms: int | None = None

        # Pre-sanitize text: colons and hyphens cause DmitryNeural to fail
        # with 'No audio was received'
        tts_text = text.replace(":", " ").replace("—", " ").replace("-", " ")
        tts_text = " ".join(tts_text.split())

        ensure_latest_edge_tts()

        for v in voices_to_try:
            max_attempts = 2 if len(voices_to_try) > 1 else 3
            for attempt in range(max_attempts):
                try:
                    communicate = edge_tts.Communicate(tts_text, v, rate=rate_arg)
                    audio_bytes.clear()
                    words.clear()
                    detected_speech_start_ms = None
                    detected_speech_duration_ms = None
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_bytes.extend(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            start_ms = chunk["offset"] // 10000
                            dur_ms = chunk["duration"] // 10000
                            word_text = chunk["text"]
                            words.append(
                                WordCue(
                                    word=word_text,
                                    start_ms=start_ms,
                                    end_ms=start_ms + dur_ms,
                                )
                            )
                        elif chunk["type"] == "SentenceBoundary":
                            detected_speech_start_ms = chunk["offset"] // 10000
                            detected_speech_duration_ms = chunk["duration"] // 10000
                    if audio_bytes:
                        synthesized_successfully = True
                        break
                except Exception as e:
                    if "403" in str(e) or "Handshake" in str(e):
                        ensure_latest_edge_tts()
                    logger.info(
                        "Voice %s attempt %d/%d note for '%s': %s (retrying)",
                        v,
                        attempt + 1,
                        max_attempts,
                        text[:30],
                        e,
                    )
                    await asyncio.sleep(0.3 * (attempt + 1))
            if synthesized_successfully:
                break

        if not synthesized_successfully or not audio_bytes:
            effective_allow_fallback = (
                voice_config.allow_fallback if voice_config is not None else allow_fallback
            )
            is_offline_voice = any(
                term in voice.lower() for term in ("sapi", "offline", "irina")
            )
            if effective_allow_fallback or is_offline_voice:
                logger.warning(
                    "All edge-tts voices failed for '%s'. Engaging offline TTS fallback.",
                    text[:40],
                )
                self._synthesize_offline_fallback(text, output_path, voice=voice)
                duration_ms = probe_audio_duration_ms(output_path)
                tokens = text.split()
                if tokens and duration_ms > 0:
                    step = duration_ms // len(tokens)
                    for i, tok in enumerate(tokens):
                        words.append(WordCue(word=tok, start_ms=i * step, end_ms=(i + 1) * step))
                return duration_ms, words
            else:
                raise RuntimeError(
                    f"Speech synthesis failed for voice '{voice}' on cue text: '{text[:50]}...'. "
                    "Mid-session degradation to offline robotic voice is disabled "
                    "to guarantee voice consistency."
                )

        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        if af_filter:
            ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
            filtered_target = output_path.with_name(f"flt_{output_path.name}")
            try:
                subprocess.run(  # noqa: S603
                    [
                        ffmpeg_bin,
                        "-y",
                        "-i",
                        str(output_path),
                        "-af",
                        af_filter,
                        str(filtered_target),
                    ],
                    check=True,
                    capture_output=True,
                )
                if filtered_target.exists():
                    shutil.move(str(filtered_target), str(output_path))
            except Exception as flt_err:
                logger.warning("Failed to apply voice audio filter (%s): %s", af_filter, flt_err)

        duration_ms = probe_audio_duration_ms(output_path)
        if not words:
            # Fallback high-precision cues using SentenceBoundary and character length weights
            tokens = text.split()
            if tokens and duration_ms > 0:
                start_offset = (
                    detected_speech_start_ms
                    if detected_speech_start_ms is not None
                    else 80  # Default leading priming offset
                )
                effective_duration = (
                    detected_speech_duration_ms
                    if detected_speech_duration_ms is not None
                    else max(200, duration_ms - start_offset - 250)
                )

                token_weights = [max(1, len(tok)) for tok in tokens]
                total_weight = sum(token_weights) or 1

                curr_ms = start_offset
                for i, tok in enumerate(tokens):
                    w_dur = int((token_weights[i] / total_weight) * effective_duration)
                    words.append(
                        WordCue(
                            word=tok,
                            start_ms=curr_ms,
                            end_ms=curr_ms + max(120, w_dur),
                        )
                    )
                    curr_ms += w_dur

        # Pacing pause to prevent edge-tts WebSocket rate limits on rapid calls
        await asyncio.sleep(0.12)
        return duration_ms, words

    async def generate_challenge_audio(
        self,
        challenge: QuizChallenge,
        workspace: QuizWorkspace | None = None,
        output_dir: Path | None = None,
        voice: str | None = None,
        retention_config: QuizRetentionConfig | None = None,
        intro_hook: str | None = None,
        voice_config: VoiceConfig | None = None,
    ) -> AudioCueSheet:
        """Synthesize all 9 questions and assemble the master AudioCueSheet."""
        ensure_default_sfx(self.config.sfx_dir)
        selected_voice = voice or self.config.default_voices.get(
            challenge.language, "ru-RU-SvetlanaNeural"
        )
        fps = self.config.fps

        cues: list[QuestionAudioCue] = []
        current_frame = 0

        intro_text: str | None = None
        intro_audio_path: Path | None = None
        intro_dur_ms: int = 0
        intro_words: list[WordCue] = []
        intro_frames: int = 0

        # Synthesize optional viral intro hook greeting if provided
        if intro_hook and intro_hook.strip():
            intro_text = intro_hook.strip()
            if output_dir:
                intro_audio_path = output_dir / "intro_hook.mp3"
            elif workspace:
                intro_audio_path = workspace.get_audio_path("intro_hook.mp3")
            else:
                raise ValueError("Either output_dir or workspace must be provided.")

            intro_dur_ms, intro_words = await self.synthesize_speech_with_cues(
                intro_text,
                selected_voice,
                intro_audio_path,
                voice_config=voice_config,
            )
            # Add a 6-frame pacing buffer between intro hook and question 1
            intro_frames = max(1, int(intro_dur_ms * fps / 1000)) + 6
            current_frame = intro_frames

        # Process each question in sequence
        for q in challenge.all_questions():
            q_num = q.question_number

            # Determine progressive blitz think duration for current difficulty tier
            think_sec = self.config.think_duration_sec
            if retention_config and retention_config.stress_timer_enabled:
                tier_name = "easy" if q_num <= 3 else ("medium" if q_num <= 6 else "hard")
                for tier_cfg in retention_config.stress_tiers:
                    if tier_cfg.tier_level == tier_name:
                        think_sec = tier_cfg.think_duration_sec
                        break
            elif not retention_config:
                # Default blitz progression: 3.0s (Easy), 2.5s (Medium), 1.8s (Hard)
                think_sec = 3.0 if q_num <= 3 else (2.5 if q_num <= 6 else 1.8)

            think_duration_ms = int(think_sec * 1000)
            think_frames = int(think_sec * fps)

            if output_dir:
                q_audio_path = output_dir / f"q_{q_num}_prompt.mp3"
                ans_audio_path = output_dir / f"q_{q_num}_answer.mp3"
            elif workspace:
                q_audio_path = workspace.get_audio_path(f"q_{q_num}_prompt.mp3")
                ans_audio_path = workspace.get_audio_path(f"q_{q_num}_answer.mp3")
            else:
                raise ValueError("Either output_dir or workspace must be provided.")

            # Format spoken question text matching viral quiz pacing
            # First question starts immediately without prefix ("вопрос номер 1"),
            # while subsequent questions (2-9) are announced explicitly.
            if challenge.language == "ru":
                num_words_ru = {
                    1: "один",
                    2: "два",
                    3: "три",
                    4: "четыре",
                    5: "пять",
                    6: "шесть",
                    7: "семь",
                    8: "восемь",
                    9: "девять",
                }
                n_str = num_words_ru.get(q_num, str(q_num))
                if q_num == 1:
                    clean_text = re.sub(
                        r"^(?:вопрос\s*(?:номер)?\s*(?:1|один)[\s,:—–-]+)",
                        "",
                        q.question_text,
                        flags=re.IGNORECASE,
                    ).strip()
                    if clean_text:
                        clean_text = clean_text[0].upper() + clean_text[1:]
                    q_speech = clean_text or q.question_text
                else:
                    q_speech = (
                        q.question_text
                        if q.question_text.lower().startswith("вопрос")
                        else f"Вопрос номер {n_str}, {q.question_text}"
                    )
                a_speech = (
                    q.correct_answer
                    if q.correct_answer.lower().startswith("ответ")
                    else f"Ответ: {q.correct_answer}"
                )
            else:
                num_words_en = {
                    1: "one",
                    2: "two",
                    3: "three",
                    4: "four",
                    5: "five",
                    6: "six",
                    7: "seven",
                    8: "eight",
                    9: "nine",
                }
                n_str = num_words_en.get(q_num, str(q_num))
                if q_num == 1:
                    clean_text = re.sub(
                        r"^(?:question\s*(?:number)?\s*(?:1|one)[\s,:—–-]+)",
                        "",
                        q.question_text,
                        flags=re.IGNORECASE,
                    ).strip()
                    if clean_text:
                        clean_text = clean_text[0].upper() + clean_text[1:]
                    q_speech = clean_text or q.question_text
                else:
                    q_speech = (
                        q.question_text
                        if q.question_text.lower().startswith("question")
                        else f"Question number {n_str}, {q.question_text}"
                    )
                a_speech = (
                    q.correct_answer
                    if q.correct_answer.lower().startswith("answer")
                    else f"Answer: {q.correct_answer}"
                )

            # Synthesize question prompt
            q_dur_ms, q_words = await self.synthesize_speech_with_cues(
                q_speech,
                selected_voice,
                q_audio_path,
                voice_config=voice_config,
            )

            # Synthesize answer text (punchy answer on reveal ding)
            ans_dur_ms, ans_words = await self.synthesize_speech_with_cues(
                a_speech,
                selected_voice,
                ans_audio_path,
                voice_config=voice_config,
            )

            start_frame = current_frame
            q_frames = max(1, int(q_dur_ms * fps / 1000))
            think_start_frame = start_frame + q_frames
            reveal_frame = think_start_frame + think_frames
            ans_frames = max(1, int(ans_dur_ms * fps / 1000))

            # Snappy reveal hold duration: comfortable to see the answer and visual illustration
            # without sluggish dead air before the next question begins (0.4s padding, min 1.25s)
            min_reveal_frames = int(1.25 * fps)
            hold_padding_frames = int(0.4 * fps)
            reveal_duration_frames = max(min_reveal_frames, ans_frames + hold_padding_frames)
            end_frame = reveal_frame + reveal_duration_frames
            current_frame = end_frame


            cues.append(
                QuestionAudioCue(
                    question_number=q_num,
                    start_frame=start_frame,
                    question_audio_file=str(q_audio_path),
                    question_duration_ms=q_dur_ms,
                    question_words=q_words,
                    think_start_frame=think_start_frame,
                    think_duration_ms=think_duration_ms,
                    reveal_frame=reveal_frame,
                    answer_audio_file=str(ans_audio_path),
                    answer_duration_ms=ans_dur_ms,
                    answer_words=ans_words,
                    end_frame=end_frame,
                )
            )

        total_duration_frames = current_frame
        total_duration_ms = int(total_duration_frames * 1000 / fps)

        logger.info(
            f"Compiled AudioCueSheet: {len(cues)} questions, "
            f"total duration: {total_duration_ms}ms ({total_duration_frames} frames @ {fps}fps)"
        )

        return AudioCueSheet(
            total_duration_ms=total_duration_ms,
            total_duration_frames=total_duration_frames,
            cues=cues,
            intro_hook_text=intro_text,
            intro_hook_audio_file=str(intro_audio_path) if intro_audio_path else None,
            intro_hook_duration_ms=intro_dur_ms,
            intro_hook_words=intro_words,
            intro_hook_duration_frames=intro_frames,
        )

    # Alias for orchestrator interface
    synthesize_cue_sheet = generate_challenge_audio

    async def generate_visual_quiz_audio(
        self,
        dataset: VisualQuizDataset,
        workspace: QuizWorkspace,
        voice: str | None = None,
        voice_config: VoiceConfig | None = None,
        banner_duration_frames: int | None = None,
    ) -> tuple[Path, list[VisualQuizTimingSlot], list[dict], int, int, int | None]:
        """Synthesize all speech cues and assemble master AudioCueSheet & timing slots for VisualImageQuiz.

        Returns:
            (master_audio_path, timing_slots, subtitles, total_duration_frames, hook_end_frame, banner_start_frame)
        """
        ensure_default_sfx(self.config.sfx_dir)
        selected_voice = voice or "ru-RU-DmitryNeural"
        fps = self.config.fps

        timing_slots: list[VisualQuizTimingSlot] = []
        subtitles: list[dict] = []
        audio_events: list[tuple[Path, float, float]] = []  # (path, start_time_sec, volume_db)

        # 1. Synthesize Intro Hook (Strictly 3.0–3.2 seconds duration)
        hook_audio_path = workspace.get_audio_path("visual_hook.mp3")
        hook_text = dataset.hook_tts
        cleaned_hook = re.sub(r'[, -]*\b(погнали[, -]*)?что это(\s+за\s+[^.!?]+)?\??', '', hook_text, flags=re.IGNORECASE).strip()
        if cleaned_hook:
            if not cleaned_hook.endswith(('.', '!', '?')):
                cleaned_hook += '!'
            hook_text = cleaned_hook

        hook_dur_ms, hook_words = await self.synthesize_speech_with_cues(
            hook_text,
            selected_voice,
            hook_audio_path,
            voice_config=voice_config,
        )

        # Ensure hook audio finishes cleanly within ~2.9-3.0s using FFmpeg atempo if needed
        target_hook_ms = 3000
        if hook_dur_ms > target_hook_ms and hook_audio_path.exists():
            speed_ratio = hook_dur_ms / target_hook_ms
            speed_ratio = min(2.2, max(1.05, speed_ratio))
            sped_up_path = workspace.get_audio_path("visual_hook_fast.mp3")
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", str(hook_audio_path),
                "-filter:a", f"atempo={speed_ratio:.3f}",
                "-vn", str(sped_up_path),
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await proc.wait()
                if sped_up_path.exists() and proc.returncode == 0:
                    shutil.move(str(sped_up_path), str(hook_audio_path))
                    hook_dur_ms = probe_audio_duration_ms(hook_audio_path)
                    scale = 1.0 / speed_ratio
                    for w in hook_words:
                        w.start_ms = int(w.start_ms * scale)
                        w.end_ms = int(w.end_ms * scale)
            except Exception as err:
                logger.warning("Failed to accelerate hook audio: %s", err)

        hook_end_frame = int(round(3.2 * fps))  # Strictly 3.2s transition
        audio_events.append((hook_audio_path, 0.0, 0.0))

        # Add Rapid Card Flip SFX during intro
        card_flip_sfx = self.config.sfx_dir / "card_flip_rapid.wav"
        if card_flip_sfx.exists():
            audio_events.append((card_flip_sfx, 0.0, -4.0))

        # Add transition sound effect at 3.2s transition point
        level_up_sfx = self.config.sfx_dir / "level_up.wav"
        ding_sfx = self.config.sfx_dir / "reveal_ding.wav"
        if level_up_sfx.exists():
            audio_events.append((level_up_sfx, hook_end_frame / fps, -2.0))
        elif ding_sfx.exists():
            audio_events.append((ding_sfx, hook_end_frame / fps, -3.0))

        # Add hook words to subtitles
        for w in hook_words:
            subtitles.append({
                "word": w.word,
                "start_frame": max(0, int(w.start_ms * fps / 1000)),
                "end_frame": max(1, int(w.end_ms * fps / 1000)),
            })

        current_frame = hook_end_frame
        timer_sfx = self.config.sfx_dir / "timer_tick.wav"
        cliff_sfx = self.config.sfx_dir / "heartbeat_panic.wav"

        # Interstitial lookup by question number
        interstitials_map = {
            it.after_question: it for it in (dataset.interstitials or [])
        }

        insert_idx = max(1, len(dataset.items) // 2)
        banner_start_frame: int | None = None

        # 2. Iterate Questions 1..10
        for item_idx, item in enumerate(dataset.items):
            # Pause video & gameplay timeline for optional promo banner mid-quiz
            if (
                item_idx == insert_idx
                and banner_duration_frames
                and banner_duration_frames > 0
            ):
                banner_start_frame = current_frame
                current_frame += banner_duration_frames

            q_id = item.id
            q_prompt_path = workspace.get_audio_path(f"visual_q_{q_id}_prompt.mp3")
            q_ans_path = workspace.get_audio_path(f"visual_q_{q_id}_answer.mp3")

            p_dur_ms, p_words = await self.synthesize_speech_with_cues(
                item.prompt_tts,
                selected_voice,
                q_prompt_path,
                voice_config=voice_config,
            )
            a_dur_ms, a_words = await self.synthesize_speech_with_cues(
                item.answer_tts,
                selected_voice,
                q_ans_path,
                voice_config=voice_config,
            )

            start_frame = current_frame
            p_frames = max(0, int(p_dur_ms * fps / 1000)) if item.prompt_tts and item.prompt_tts.strip() else 0

            # Timer starts strictly after prompt audio finishes (plus 6 frames breathing room)
            timer_start_frame = start_frame + p_frames + (6 if p_frames > 0 else 0)
            timer_duration_frames = int(dataset.timer_duration_sec * fps)
            reveal_frame = timer_start_frame + timer_duration_frames
            answer_audio_start_frame = reveal_frame

            ans_frames = max(1, int(a_dur_ms * fps / 1000))
            end_frame = reveal_frame + ans_frames + 16

            slot = VisualQuizTimingSlot(
                question_id=q_id,
                start_frame=start_frame,
                prompt_audio_start_frame=start_frame,
                timer_start_frame=timer_start_frame,
                timer_duration_frames=timer_duration_frames,
                answer_audio_start_frame=answer_audio_start_frame,
                reveal_frame=reveal_frame,
                end_frame=end_frame,
            )
            timing_slots.append(slot)

            audio_events.append((q_prompt_path, start_frame / fps, 0.0))
            if timer_sfx.exists():
                audio_events.append((timer_sfx, timer_start_frame / fps, -6.0))

            if q_id == 10 and cliff_sfx.exists():
                audio_events.append((cliff_sfx, reveal_frame / fps, -3.0))
            elif ding_sfx.exists():
                audio_events.append((ding_sfx, reveal_frame / fps, -4.0))

            audio_events.append((q_ans_path, answer_audio_start_frame / fps, 0.0))

            for w in p_words:
                subtitles.append({
                    "word": w.word,
                    "start_frame": start_frame + int(w.start_ms * fps / 1000),
                    "end_frame": start_frame + int(w.end_ms * fps / 1000),
                })
            for w in a_words:
                subtitles.append({
                    "word": w.word,
                    "start_frame": answer_audio_start_frame + int(w.start_ms * fps / 1000),
                    "end_frame": answer_audio_start_frame + int(w.end_ms * fps / 1000),
                })

            current_frame = end_frame + 6

            # Check interstitial
            if q_id in interstitials_map:
                inter = interstitials_map[q_id]
                inter_path = workspace.get_audio_path(f"visual_interstitial_{q_id}.mp3")
                i_dur_ms, i_words = await self.synthesize_speech_with_cues(
                    inter.tts_text,
                    selected_voice,
                    inter_path,
                    voice_config=voice_config,
                )
                inter_start_frame = current_frame
                audio_events.append((inter_path, inter_start_frame / fps, 0.0))
                for w in i_words:
                    subtitles.append({
                        "word": w.word,
                        "start_frame": inter_start_frame + int(w.start_ms * fps / 1000),
                        "end_frame": inter_start_frame + int(w.end_ms * fps / 1000),
                    })
                inter_frames = max(int(inter.duration_sec * fps), int(i_dur_ms * fps / 1000) + 12)
                current_frame += inter_frames

        total_duration_frames = current_frame
        master_audio_path = workspace.get_audio_path("visual_quiz_master_mix.wav")

        await self._render_audio_events_mix(audio_events, master_audio_path, total_duration_frames / fps)

        return (
            master_audio_path,
            timing_slots,
            subtitles,
            total_duration_frames,
            hook_end_frame,
            banner_start_frame,
        )

    async def _render_audio_events_mix(
        self,
        events: list[tuple[Path, float, float]],
        output_path: Path,
        total_duration_sec: float,
    ) -> None:
        """Mix multiple audio files at given timestamps and volumes into a single WAV via FFmpeg."""
        valid_events = [(p, t, vol) for p, t, vol in events if p.exists()]
        if not valid_events:
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi",
                "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(max(1.0, total_duration_sec)),
                str(output_path),
            ]
            await asyncio.to_thread(subprocess.run, cmd, capture_output=True, check=True)
            return

        inputs = []
        filter_parts = []
        for idx, (path, start_sec, vol_db) in enumerate(valid_events):
            inputs.extend(["-i", str(path)])
            delay_ms = int(max(0.0, start_sec) * 1000)
            vol_factor = 10.0 ** (vol_db / 20.0)
            filter_parts.append(
                f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume={vol_factor:.2f}[a{idx}];"
            )

        amix_inputs = "".join(f"[a{i}]" for i in range(len(valid_events)))
        filter_complex = (
            "".join(filter_parts)
            + f"{amix_inputs}amix=inputs={len(valid_events)}:dropout_transition=0:normalize=0,alimiter=limit=0.95[outa]"
        )

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-ac", "2",
            "-ar", "44100",
            "-t", str(total_duration_sec),
            str(output_path),
        ]

        def _run_ffmpeg():
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                logger.warning("FFmpeg audio mix failed: %s. Using simple copy fallback.", res.stderr)
                if valid_events:
                    shutil.copy2(valid_events[0][0], output_path)

        await asyncio.to_thread(_run_ffmpeg)


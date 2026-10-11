"""AudioService: Generates voiceover narration via edge-tts and master AudioCueSheet."""

import logging
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

import edge_tts

from videoanalizer.quiz.config import QuizConfig, get_quiz_config
from videoanalizer.quiz.models import (
    AudioCueSheet,
    QuestionAudioCue,
    QuizChallenge,
    SfxPaths,
    WordCue,
)
from videoanalizer.quiz.workspace import QuizWorkspace

logger = logging.getLogger(__name__)


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

    tick_path = sfx_dir / "timer_tick.wav"
    if not tick_path.exists():
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

    return SfxPaths(
        timer_tick=str(tick_path),
        reveal_ding=str(ding_path),
        level_up=str(level_up_path),
    )


class AudioService:
    """Synthesizes speech and compiles master synchronized AudioCueSheet."""

    def __init__(self, config: QuizConfig | None = None) -> None:
        self.config = config or get_quiz_config()

    def ensure_default_sfx(self, sfx_dir: Path) -> SfxPaths:
        """Ensure standard sound effects exist, returning SfxPaths."""
        return ensure_default_sfx(sfx_dir)

    async def synthesize_speech_with_cues(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> tuple[int, list[WordCue]]:
        """Synthesize text via edge-tts, capturing audio and word-level timestamps.

        Returns:
            Tuple of (duration_ms, list of WordCue).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        voices_to_try = [voice]
        if "ru-" in voice.lower() and voice != "ru-RU-SvetlanaNeural":
            voices_to_try.append("ru-RU-SvetlanaNeural")
        elif "en-" in voice.lower() and voice != "en-US-GuyNeural":
            voices_to_try.append("en-US-GuyNeural")

        audio_bytes = bytearray()
        words: list[WordCue] = []

        for v in voices_to_try:
            try:
                communicate = edge_tts.Communicate(text, v, rate="+20%")
                audio_bytes.clear()
                words.clear()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes.extend(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start_ms = chunk["offset"] // 10000
                        dur_ms = chunk["duration"] // 10000
                        word_text = chunk["text"]
                        words.append(
                            WordCue(word=word_text, start_ms=start_ms, end_ms=start_ms + dur_ms)
                        )
                if audio_bytes:
                    break
            except Exception as e:
                logger.warning(f"Voice {v} failed for speech synthesis: {e}")
                if v == voices_to_try[-1]:
                    raise

        with open(output_path, "wb") as f:
            f.write(audio_bytes)

        duration_ms = probe_audio_duration_ms(output_path)
        if not words:
            # Fallback approximate cues if engine emitted none
            tokens = text.split()
            if tokens and duration_ms > 0:
                step = duration_ms // len(tokens)
                for i, tok in enumerate(tokens):
                    words.append(WordCue(word=tok, start_ms=i * step, end_ms=(i + 1) * step))

        return duration_ms, words

    async def generate_challenge_audio(
        self,
        challenge: QuizChallenge,
        workspace: QuizWorkspace | None = None,
        output_dir: Path | None = None,
        voice: str | None = None,
    ) -> AudioCueSheet:
        """Synthesize all 9 questions and assemble the master AudioCueSheet."""
        ensure_default_sfx(self.config.sfx_dir)
        selected_voice = voice or self.config.default_voices.get(
            challenge.language, "ru-RU-SvetlanaNeural"
        )
        fps = self.config.fps
        think_duration_ms = int(self.config.think_duration_sec * 1000)
        think_frames = int(self.config.think_duration_sec * fps)

        cues: list[QuestionAudioCue] = []
        current_frame = 0

        # Process each question in sequence
        for q in challenge.all_questions():
            q_num = q.question_number
            if output_dir:
                q_audio_path = output_dir / f"q_{q_num}_prompt.mp3"
                ans_audio_path = output_dir / f"q_{q_num}_answer.mp3"
            elif workspace:
                q_audio_path = workspace.get_audio_path(f"q_{q_num}_prompt.mp3")
                ans_audio_path = workspace.get_audio_path(f"q_{q_num}_answer.mp3")
            else:
                raise ValueError("Either output_dir or workspace must be provided.")

            # Format spoken question text matching viral quiz pacing
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
                q_speech = (
                    q.question_text
                    if q.question_text.lower().startswith("вопрос")
                    else f"Вопрос номер {n_str}. {q.question_text}"
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
                q_speech = (
                    q.question_text
                    if q.question_text.lower().startswith("question")
                    else f"Question number {n_str}. {q.question_text}"
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
            )

            # Synthesize answer text (punchy answer on reveal ding)
            ans_dur_ms, ans_words = await self.synthesize_speech_with_cues(
                a_speech,
                selected_voice,
                ans_audio_path,
            )

            start_frame = current_frame
            q_frames = max(1, int(q_dur_ms * fps / 1000))
            think_start_frame = start_frame + q_frames
            reveal_frame = think_start_frame + think_frames
            ans_frames = max(1, int(ans_dur_ms * fps / 1000))

            # Add a 15-frame breathing buffer before next question
            pause_frames = 15
            end_frame = reveal_frame + ans_frames + pause_frames
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
        )

    # Alias for orchestrator interface
    synthesize_cue_sheet = generate_challenge_audio

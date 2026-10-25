"""VoiceService: Hybrid speech synthesis and voice cloning pipeline."""

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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from qwen_tts import Qwen3TTSModel

import aiohttp
import edge_tts
import numpy as np
import soundfile as sf

from videoanalizer.quiz.audio_service import ensure_latest_edge_tts, probe_audio_duration_ms
from videoanalizer.quiz.models import (
    RvcModelInfo,
    SynthesizedSpeechResult,
    VoiceConfig,
    VoiceMode,
    WordTiming,
)
from videoanalizer.quiz.rvc_engine import RvcInferenceEngine

logger = logging.getLogger(__name__)

VIRTUAL_VOICE_PRESETS: dict[str, dict[str, Any]] = {
    "ru-RU-SvetlanaEnergetic": {
        "base_voice": "ru-RU-SvetlanaNeural",
        "rate_multiplier": 1.15,
        "af_filter": None,
    },
    "ru-RU-MaleBaritone": {
        "base_voice": "ru-RU-SvetlanaNeural",
        "rate_multiplier": 1.0,
        "af_filter": (
            "asetrate=44100*0.82,atempo=1/0.82,"
            "equalizer=f=150:t=q:w=1:g=4,equalizer=f=2500:t=q:w=1:g=2"
        ),
    },
    "ru-RU-EpicAnnouncer": {
        "base_voice": "ru-RU-SvetlanaNeural",
        "rate_multiplier": 1.0,
        "af_filter": (
            "asetrate=44100*0.74,atempo=1/0.74,"
            "equalizer=f=100:t=q:w=1.2:g=7,aecho=0.8:0.7:40:0.25"
        ),
    },
    "ru-RU-ChibiCartoon": {
        "base_voice": "ru-RU-SvetlanaNeural",
        "rate_multiplier": 1.0,
        "af_filter": "asetrate=44100*1.28,atempo=1/1.28,equalizer=f=3000:t=q:w=1:g=3",
    },
}


def compress_speech_pauses(
    audio: np.ndarray,
    sr: int,
    max_pause_sec: float = 0.13,
    min_silence_to_trim_sec: float = 0.18,
    silence_threshold: float = 0.015,
) -> np.ndarray:
    """Detect and compress silences longer than min_silence_to_trim_sec down to max_pause_sec.

    Uses root-mean-square energy over 20ms frames with 10ms hops.
    Preserves natural prosody while cutting dead pauses between words.
    """
    if len(audio) == 0:
        return audio

    frame_len = int(sr * 0.02)
    hop = int(sr * 0.01)
    if len(audio) < frame_len:
        return audio

    mono_audio = np.mean(audio, axis=1) if audio.ndim > 1 else audio

    n_frames = (len(mono_audio) - frame_len) // hop
    energy = np.array([
        np.sqrt(np.mean(mono_audio[i * hop : i * hop + frame_len] ** 2))
        for i in range(n_frames)
    ])

    is_silent = energy < silence_threshold

    silence_blocks: list[tuple[int, int]] = []
    start_idx: int | None = None
    for i, s in enumerate(is_silent):
        if s and start_idx is None:
            start_idx = i
        elif not s and start_idx is not None:
            silence_blocks.append((start_idx, i))
            start_idx = None
    if start_idx is not None:
        silence_blocks.append((start_idx, len(is_silent)))

    keep_mask = np.ones(len(audio), dtype=bool)

    for s_start, s_end in silence_blocks:
        dur = (s_end - s_start) * 0.01
        if dur > min_silence_to_trim_sec:
            if s_start == 0:
                keep_sec = 0.03
            elif s_end == len(is_silent):
                keep_sec = 0.04
            else:
                keep_sec = max_pause_sec

            cut_start = int((s_start * hop) + (keep_sec * sr))
            cut_end = int(s_end * hop)
            if cut_start < cut_end and cut_end <= len(audio):
                keep_mask[cut_start:cut_end] = False

    return audio[keep_mask]


class RvcModelRegistry:
    """Discovers and catalogs local pre-trained RVC model checkpoints."""

    def __init__(self, models_dir: Path | str | None = None) -> None:
        self.models_dir = Path(models_dir) if models_dir else Path("assets/models/rvc")

    def discover_models(self, models_dir: Path | str | None = None) -> list[RvcModelInfo]:
        """Scan target directory for *.pth checkpoint files and matching *.index files."""
        search_dir = Path(models_dir) if models_dir else self.models_dir
        if not search_dir.exists() or not search_dir.is_dir():
            return []

        models: list[RvcModelInfo] = []
        for pth_path in sorted(search_dir.glob("*.pth")):
            if not pth_path.is_file():
                continue
            model_id = pth_path.stem
            human_name = model_id.replace("_", " ").replace("-", " ").title()

            index_path: Path | None = None
            candidate_index = pth_path.with_suffix(".index")
            if candidate_index.exists():
                index_path = candidate_index
            else:
                for idx_candidate in search_dir.glob(f"{model_id}*.index"):
                    index_path = idx_candidate
                    break

            try:
                size_bytes = pth_path.stat().st_size
                is_valid = size_bytes > 0
            except OSError:
                size_bytes = 0
                is_valid = False

            models.append(
                RvcModelInfo(
                    model_id=model_id,
                    name=human_name,
                    file_path=str(pth_path.as_posix()),
                    index_path=str(index_path.as_posix()) if index_path else None,
                    file_size_bytes=size_bytes,
                    is_valid=is_valid,
                )
            )

        return models

    def get_model(
        self,
        model_id_or_path: str,
        models_dir: Path | str | None = None,
    ) -> RvcModelInfo | None:
        """Find a model info record by model_id, stem name, or relative path."""
        models = self.discover_models(models_dir)
        p = Path(model_id_or_path)
        lookup_id = p.stem.lower()

        for m in models:
            matches_id = m.model_id.lower() == lookup_id
            matches_path = m.file_path.lower() == str(model_id_or_path).lower()
            if matches_id or matches_path:
                return m
        return None


class VoiceService:
    """Coordinates multi-modal speech generation and RVC voice cloning with resilient fallback."""

    def __init__(
        self,
        config: VoiceConfig | None = None,
        models_dir: Path | str | None = None,
        rvc_engine: RvcInferenceEngine | None = None,
    ) -> None:
        self.config = config or VoiceConfig()
        self.models_dir = Path(models_dir) if models_dir else Path("assets/models/rvc")
        self.registry = RvcModelRegistry(models_dir=self.models_dir)
        self.rvc_engine = rvc_engine or RvcInferenceEngine(
            device=self.config.device,
            pitch_method=self.config.pitch_method,
        )
        self._ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    _qwen3_model_instance = None

    @classmethod
    def _get_qwen3_model(cls, model_dir: Path | str) -> "Qwen3TTSModel":
        """Lazy load and cache Qwen3TTSModel across multiple question calls."""
        if cls._qwen3_model_instance is None:
            from qwen_tts import Qwen3TTSModel

            logger.info("Loading Qwen3-TTS model into memory from %s...", model_dir)
            cls._qwen3_model_instance = Qwen3TTSModel.from_pretrained(
                str(model_dir),
                device_map="cpu",
            )
        return cls._qwen3_model_instance

    async def synthesize(
        self,
        text: str,
        output_path: Path | str | None = None,
        config: VoiceConfig | None = None,
    ) -> SynthesizedSpeechResult:
        """Synthesize text using configured mode, automatically applying graceful degradation."""
        cfg = config or self.config
        target_path = Path(output_path) if output_path else Path("output_speech.wav")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        mode = cfg.voice_mode

        if not cfg.allow_fallback:
            if mode == VoiceMode.QWEN3_RVC:
                return await self._synthesize_qwen3_rvc(text, target_path, cfg)
            elif mode == VoiceMode.CUSTOM_RVC:
                return await self._synthesize_rvc(text, target_path, cfg)
            elif mode == VoiceMode.EDGE_TTS:
                return await self._synthesize_edge_tts(text, target_path, cfg)
            elif mode == VoiceMode.OFFLINE_FALLBACK:
                return self._synthesize_offline_fallback(text, target_path, cfg)
            else:
                raise ValueError(f"Unknown voice mode: {mode}")

        # 0. Tier 0: Qwen3-TTS + RVC voice conversion (degradation ladder enabled)
        if mode == VoiceMode.QWEN3_RVC:
            try:
                return await self._synthesize_qwen3_rvc(text, target_path, cfg)
            except Exception as e:
                logger.warning(
                    "Qwen3-TTS + RVC synthesis failed (%s). Degrading to custom_rvc mode.", e
                )
                mode = VoiceMode.CUSTOM_RVC

        # 1. Tier 1: Custom RVC voice conversion
        if mode == VoiceMode.CUSTOM_RVC:
            try:
                return await self._synthesize_rvc(text, target_path, cfg)
            except Exception as e:
                logger.warning(
                    "Custom RVC voice synthesis failed (%s). Degrading to edge_tts mode.", e
                )
                mode = VoiceMode.EDGE_TTS

        # 2. Tier 2: Standard Edge-TTS synthesis
        if mode == VoiceMode.EDGE_TTS:
            try:
                return await self._synthesize_edge_tts(text, target_path, cfg)
            except Exception as e:
                logger.warning(
                    "Edge-TTS synthesis failed (%s). Degrading to offline_fallback mode.", e
                )
                mode = VoiceMode.OFFLINE_FALLBACK

        # 3. Tier 3: Offline fallback
        return self._synthesize_offline_fallback(text, target_path, cfg)

    async def _synthesize_edge_tts(
        self,
        text: str,
        output_path: Path,
        cfg: VoiceConfig,
    ) -> SynthesizedSpeechResult:
        """Synthesize pristine narration via edge-tts and capture millisecond WordBoundary cues."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Sanitize punctuation that can crash edge-tts DmitryNeural
        # Replace em-dashes, en-dashes and word hyphens with spaces (e.g. 'Кока-Кола' -> 'Кока Кола')
        clean_text = text.replace("—", " ").replace("–", " ").replace("-", " ")
        clean_text = clean_text.replace(":", ", ").replace(";", ", ")
        clean_text = clean_text.replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ")
        words_tokens = clean_text.split()
        # Edge-TTS DmitryNeural frequently crashes on short 1-3 word answers with trailing '!' or '?'
        if len(words_tokens) <= 3:
            clean_text = clean_text.replace("!", "").replace("?", "").strip()
        clean_text = " ".join(clean_text.split()).strip()
        if clean_text and not clean_text.endswith((".", "!", "?")):
            clean_text += "."

        # Resolve virtual voice presets (e.g. ru-RU-ChibiCartoon, ru-RU-MaleBaritone)
        raw_voice = cfg.base_voice
        af_filter: str | None = None
        effective_rate = cfg.speech_rate
        if raw_voice in VIRTUAL_VOICE_PRESETS:
            preset = VIRTUAL_VOICE_PRESETS[raw_voice]
            candidate_voice = preset["base_voice"]
            af_filter = preset.get("af_filter")
            effective_rate *= preset.get("rate_multiplier", 1.0)
        else:
            candidate_voice = raw_voice

        # Voice consistency: use base_voice. If Dmitry is selected but text contains Latin words
        # (e.g. game or brand names like 'Minecraft', 'Portal'), Azure Speech has no Latin vocab for Dmitry
        # and returns NoAudioReceived. We use ru-RU-SvetlanaNeural which natively speaks Latin/English phrases.
        has_latin = bool(re.search(r"[a-zA-Z]", clean_text))
        active_voice = (
            "ru-RU-SvetlanaNeural"
            if (has_latin and "dmitry" in candidate_voice.lower())
            else candidate_voice
        )

        # Rate handling:
        # ru-RU-DmitryNeural rejects any custom rate (!= +0%) on Microsoft Azure with NoAudioReceived.
        # To preserve Dmitry's voice and speed, we synthesize Dmitry at +0% and apply atempo in FFmpeg.
        # Svetlana and other voices support native SSML rate directly.
        if "dmitry" in active_voice.lower():
            rate_arg = "+0%"
            if abs(effective_rate - 1.0) >= 0.02:
                tempo_str = f"atempo={effective_rate:.3f}"
                af_filter = f"{af_filter},{tempo_str}" if af_filter else tempo_str
        else:
            pct = int(round((effective_rate - 1.0) * 100))
            rate_arg = f"{pct:+d}%"

        audio_bytes = bytearray()
        words: list[WordTiming] = []
        last_err: Exception | None = None

        ensure_latest_edge_tts()

        # Retry persistently to handle transient network hiccups
        max_attempts = 25
        for attempt in range(max_attempts):
            try:
                audio_bytes.clear()
                words.clear()
                connector = aiohttp.TCPConnector(resolver=aiohttp.ThreadedResolver())
                communicate = edge_tts.Communicate(
                    clean_text, active_voice, rate=rate_arg, connector=connector
                )
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes.extend(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        start_ms = chunk["offset"] // 10000
                        dur_ms = chunk["duration"] // 10000
                        words.append(
                            WordTiming(
                                word=chunk["text"],
                                start_ms=start_ms,
                                end_ms=start_ms + dur_ms,
                            )
                        )
                if audio_bytes:
                    break
            except Exception as e:
                last_err = e
                if "403" in str(e) or "Handshake" in str(e):
                    ensure_latest_edge_tts()
                # Invalid voice name: fall back immediately without wasting 25 attempts
                if "Invalid voice" in str(e):
                    logger.warning(
                        "Voice %s is invalid in Edge-TTS. Falling back immediately to ru-RU-SvetlanaNeural.",
                        active_voice,
                    )
                    active_voice = "ru-RU-SvetlanaNeural"
                    pct = int(round((effective_rate - 1.0) * 100))
                    rate_arg = f"{pct:+d}%"
                    continue
                # DmitryNeural lacks Latin vocab and throws NoAudioReceived on English names/terms
                if (
                    "NoAudioReceived" in type(e).__name__
                    or "No audio was received" in str(e)
                ) and "dmitry" in active_voice.lower():
                    logger.warning(
                        "Voice %s failed with NoAudioReceived on '%s'. Switching to ru-RU-SvetlanaNeural.",
                        active_voice,
                        clean_text[:40],
                    )
                    active_voice = "ru-RU-SvetlanaNeural"
                    pct = int(round((effective_rate - 1.0) * 100))
                    rate_arg = f"{pct:+d}%"
                    continue
                logger.warning(
                    "Edge-TTS voice %s attempt %d/%d failed: %s. Retrying...",
                    active_voice,
                    attempt + 1,
                    max_attempts,
                    e,
                )
                sleep_dur = 0.01 if "pytest" in sys.modules else min(0.3 * (attempt + 1), 2.0)
                await asyncio.sleep(sleep_dur)

        if not audio_bytes:
            if not cfg.allow_fallback:
                raise RuntimeError(
                    f"Edge-TTS synthesis failed for '{clean_text}': {last_err}. "
                    "Mid-session degradation to offline robotic voice is disabled "
                    "to guarantee voice consistency."
                )
            logger.warning(
                "Edge-TTS returned no audio data for '%s' (%s). Falling back to offline fallback.",
                clean_text,
                last_err,
            )
            return self._synthesize_offline_fallback(text, output_path, cfg)

        # Save raw output (edge-tts generates MP3)
        temp_mp3 = output_path.with_suffix(".temp.mp3")
        temp_mp3.write_bytes(audio_bytes)

        # Apply acoustic filters (virtual presets or Dmitry atempo tempo scaling)
        if af_filter:
            flt_mp3 = output_path.with_suffix(".flt.mp3")
            cmd = [
                self._ffmpeg_bin,
                "-y",
                "-i",
                str(temp_mp3),
                "-af",
                af_filter,
                str(flt_mp3),
            ]
            subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
            if temp_mp3.exists():
                temp_mp3.unlink()
            temp_mp3 = flt_mp3

        # If target is WAV, transcode to normalized PCM WAV
        if output_path.suffix.lower() == ".wav":
            cmd = [
                self._ffmpeg_bin,
                "-y",
                "-i",
                str(temp_mp3),
                "-ar",
                "44100",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ]
            subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
            if temp_mp3.exists():
                temp_mp3.unlink()
        else:
            if temp_mp3 != output_path:
                shutil.move(str(temp_mp3), str(output_path))

        duration_ms = probe_audio_duration_ms(output_path)
        # If atempo was applied via FFmpeg to Dmitry, adjust word timings proportionally
        if "dmitry" in active_voice.lower() and abs(effective_rate - 1.0) >= 0.02 and effective_rate > 0:
            tempo_ratio = 1.0 / effective_rate
            for w in words:
                w.start_ms = int(round(w.start_ms * tempo_ratio))
                w.end_ms = int(round(w.end_ms * tempo_ratio))

        if not words and duration_ms > 0:
            tokens = text.split()
            if tokens:
                step = duration_ms // len(tokens)
                for i, tok in enumerate(tokens):
                    words.append(
                        WordTiming(
                            word=tok,
                            start_ms=i * step,
                            end_ms=(i + 1) * step,
                        )
                    )

        return SynthesizedSpeechResult(
            audio_path=str(output_path),
            duration_ms=duration_ms,
            words=words,
            voice_mode_used=VoiceMode.EDGE_TTS,
        )

    async def _synthesize_rvc(
        self,
        text: str,
        output_path: Path,
        cfg: VoiceConfig,
    ) -> SynthesizedSpeechResult:
        """Execute hybrid pipeline: synthesize base narration, then transform vocal timbre."""
        # 1. Resolve RVC model checkpoint
        if not cfg.rvc_model_path:
            raise ValueError("No RVC model path specified in VoiceConfig.")

        model_path = Path(cfg.rvc_model_path)
        if not model_path.exists():
            # Check if model is inside models_dir
            candidate = self.models_dir / cfg.rvc_model_path
            if candidate.exists():
                model_path = candidate
            else:
                candidate_pth = self.models_dir / f"{cfg.rvc_model_path}.pth"
                if candidate_pth.exists():
                    model_path = candidate_pth
                else:
                    raise FileNotFoundError(f"RVC checkpoint not found: {cfg.rvc_model_path}")

        # 2. Synthesize base speech via Edge-TTS into intermediate WAV
        intermediate_wav = output_path.with_name(f"{output_path.stem}_base.wav")
        base_result = await self._synthesize_edge_tts(text, intermediate_wav, cfg)

        if cfg.tighten_pauses and intermediate_wav.exists():
            base_audio, sr = sf.read(str(intermediate_wav))
            tightened_audio = compress_speech_pauses(
                base_audio, sr, max_pause_sec=cfg.max_pause_sec
            )
            sf.write(str(intermediate_wav), tightened_audio, sr)

        # 3. Apply RVC voice conversion & timbre swap
        try:
            self.rvc_engine.convert_voice(
                input_path=intermediate_wav,
                output_path=output_path,
                model_path=model_path,
                pitch_shift=cfg.pitch_shift,
                index_path=cfg.rvc_index_path,
            )
        except Exception as rvc_err:
            if not cfg.allow_fallback:
                logger.warning(
                    "RVC voice conversion failed in strict custom_rvc mode (%s). "
                    "Preserving intermediate base audio.",
                    rvc_err,
                )
                if output_path.suffix.lower() == intermediate_wav.suffix.lower():
                    shutil.copy2(intermediate_wav, output_path)
                else:
                    cmd = [
                        self._ffmpeg_bin,
                        "-y",
                        "-i",
                        str(intermediate_wav),
                        "-c:a",
                        "libmp3lame" if output_path.suffix.lower() == ".mp3" else "pcm_s16le",
                        str(output_path),
                    ]
                    subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
            else:
                raise
        finally:
            if intermediate_wav.exists() and intermediate_wav != output_path:
                intermediate_wav.unlink(missing_ok=True)

        # 4. Measure converted duration (RVC preserves syllable timing and duration)
        final_dur_ms = probe_audio_duration_ms(output_path)

        return SynthesizedSpeechResult(
            audio_path=str(output_path),
            duration_ms=final_dur_ms or base_result.duration_ms,
            words=base_result.words,
            voice_mode_used=VoiceMode.CUSTOM_RVC,
            model_name=model_path.stem,
        )

    async def _synthesize_qwen3_rvc(
        self,
        text: str,
        output_path: Path,
        cfg: VoiceConfig,
    ) -> SynthesizedSpeechResult:
        """Synthesize expressive speech via Qwen3-TTS, tighten pauses, and convert via RVC."""
        clean_text = text.replace(":", ", ").replace("—", ", ").replace(" - ", ", ")
        clean_text = " ".join(clean_text.split())

        model = await asyncio.to_thread(self._get_qwen3_model, cfg.qwen3_model_path)

        ref_path = Path(cfg.qwen3_ref_audio)
        if not ref_path.exists():
            candidates = [
                Path("assets/voices/mellstroy_ref.wav"),
                Path("output/voice_samples/mellstroy_pitch_0.wav"),
                self.models_dir / "mellstroy_ref.wav",
            ]
            for cand in candidates:
                if cand.exists():
                    ref_path = cand
                    break

        if not ref_path.exists():
            raise FileNotFoundError(
                f"Reference audio not found for Qwen3-TTS: {cfg.qwen3_ref_audio}"
            )

        def _run_qwen3() -> tuple[np.ndarray, int]:
            for attempt in range(3):
                try:
                    wavs, sr = model.generate_voice_clone(
                        text=clean_text,
                        language="russian",
                        ref_audio=str(ref_path),
                        x_vector_only_mode=True,
                        do_sample=False,
                    )
                    return wavs[0], sr
                except Exception as e:
                    if attempt == 2:
                        raise
                    try:
                        import torch

                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()
                    except ImportError:
                        pass
                    logger.warning(
                        "Qwen3 voice clone attempt %d failed (%s). Retrying...",
                        attempt + 1,
                        e,
                    )
            raise RuntimeError(f"Failed to generate Qwen3 voice clone for '{clean_text}'")

        audio_raw, sr = await asyncio.to_thread(_run_qwen3)

        if cfg.tighten_pauses:
            audio_processed = compress_speech_pauses(
                audio_raw,
                sr,
                max_pause_sec=cfg.max_pause_sec,
            )
        else:
            audio_processed = audio_raw

        intermediate_wav = output_path.with_name(f"{output_path.stem}_qwen3_base.wav")
        sf.write(str(intermediate_wav), audio_processed, sr)

        # Resolve RVC model
        target_model = cfg.rvc_model_path or "Mellstroy-strimer.pth"
        model_path = Path(target_model)
        if not model_path.exists():
            cand = self.models_dir / target_model
            if cand.exists():
                model_path = cand
            else:
                cand_pth = self.models_dir / f"{Path(target_model).stem}.pth"
                if cand_pth.exists():
                    model_path = cand_pth
                else:
                    raise FileNotFoundError(f"RVC checkpoint not found: {target_model}")

        index_path = cfg.rvc_index_path
        if not index_path:
            candidate_idx = model_path.with_suffix(".index")
            if candidate_idx.exists():
                index_path = str(candidate_idx)
            else:
                for idx_c in self.models_dir.glob(f"{model_path.stem}*.index"):
                    index_path = str(idx_c)
                    break

        try:
            await asyncio.to_thread(
                self.rvc_engine.convert_voice,
                input_path=intermediate_wav,
                output_path=output_path,
                model_path=model_path,
                pitch_shift=cfg.pitch_shift,
                index_path=index_path,
            )
        except Exception as rvc_err:
            logger.warning(
                "RVC voice conversion failed in Qwen3-RVC mode (%s). "
                "Using direct Qwen3 cloned audio to maintain Mellstroy speaker consistency.",
                rvc_err,
            )
            if output_path.suffix.lower() == intermediate_wav.suffix.lower():
                shutil.copy2(intermediate_wav, output_path)
            else:
                cmd = [
                    self._ffmpeg_bin,
                    "-y",
                    "-i",
                    str(intermediate_wav),
                    "-c:a",
                    "libmp3lame" if output_path.suffix.lower() == ".mp3" else "pcm_s16le",
                    str(output_path),
                ]
                subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
        finally:
            if intermediate_wav.exists() and intermediate_wav != output_path:
                intermediate_wav.unlink(missing_ok=True)

        final_dur_ms = probe_audio_duration_ms(output_path)
        if final_dur_ms <= 0:
            final_dur_ms = int(len(audio_processed) / sr * 1000)

        tokens = clean_text.split()
        words: list[WordTiming] = []
        if tokens and final_dur_ms > 0:
            step = final_dur_ms // len(tokens)
            for i, tok in enumerate(tokens):
                words.append(
                    WordTiming(
                        word=tok,
                        start_ms=i * step,
                        end_ms=(i + 1) * step,
                    )
                )

        return SynthesizedSpeechResult(
            audio_path=str(output_path),
            duration_ms=final_dur_ms,
            words=words,
            voice_mode_used=VoiceMode.QWEN3_RVC,
            model_name=model_path.stem,
        )

    def _synthesize_offline_fallback(
        self,
        text: str,
        output_path: Path,
        cfg: VoiceConfig,
    ) -> SynthesizedSpeechResult:
        """Multi-tier offline fallback: pyttsx3 or synthetic sine wave with WordTiming."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        synthesized_ok = False
        try:
            import pyttsx3

            wav_temp = output_path.with_suffix(".temp.wav")
            engine = pyttsx3.init()
            if "ru" in cfg.base_voice.lower():
                for v in engine.getProperty("voices"):
                    if "irina" in v.id.lower() or "ru" in v.id.lower():
                        engine.setProperty("voice", v.id)
                        break
            engine.save_to_file(text, str(wav_temp))
            engine.runAndWait()

            if output_path.suffix.lower() == ".wav":
                if wav_temp != output_path:
                    shutil.move(str(wav_temp), str(output_path))
            else:
                cmd = [
                    self._ffmpeg_bin,
                    "-y",
                    "-i",
                    str(wav_temp),
                    "-b:a",
                    "192k",
                    str(output_path),
                ]
                subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603
                if wav_temp.exists():
                    wav_temp.unlink()
            synthesized_ok = True
        except Exception as e:
            logger.warning("pyttsx3 offline fallback failed: %s. Using synthetic tone.", e)

        if not synthesized_ok:
            sample_rate = 44100
            n_samples = int(sample_rate * 1.5)
            wav_temp = output_path.with_suffix(".temp.wav")
            with wave.open(str(wav_temp), "w") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(sample_rate)
                data = bytearray()
                for i in range(n_samples):
                    t = i / sample_rate
                    val = math.sin(2 * math.pi * 440.0 * t) * 16000
                    data.extend(struct.pack("<h", int(val)))
                f.writeframes(data)

            if output_path.suffix.lower() == ".wav":
                if wav_temp != output_path:
                    shutil.move(str(wav_temp), str(output_path))
            else:
                cmd = [
                    self._ffmpeg_bin,
                    "-y",
                    "-i",
                    str(wav_temp),
                    "-b:a",
                    "192k",
                    str(output_path),
                ]
                subprocess.run(cmd, check=False, capture_output=True)  # noqa: S603
                if wav_temp.exists():
                    wav_temp.unlink()

        duration_ms = probe_audio_duration_ms(output_path)
        if duration_ms <= 0:
            duration_ms = 1500

        # Create evenly spaced word timings so subtitles render smoothly
        tokens = text.split()
        words: list[WordTiming] = []
        if tokens:
            step = duration_ms // len(tokens)
            for i, tok in enumerate(tokens):
                words.append(
                    WordTiming(
                        word=tok,
                        start_ms=i * step,
                        end_ms=(i + 1) * step,
                    )
                )

        return SynthesizedSpeechResult(
            audio_path=str(output_path),
            duration_ms=duration_ms,
            words=words,
            voice_mode_used=VoiceMode.OFFLINE_FALLBACK,
        )

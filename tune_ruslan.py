import time
import wave
import numpy as np
import soundfile as sf
from pathlib import Path
from piper import PiperVoice
from piper.config import SynthesisConfig

from videoanalizer.quiz.voice_service import compress_speech_pauses

OUTPUT_DIR = Path("output/voice_samples")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = "assets/models/piper/ru_RU-ruslan-medium.onnx"

# Expressive text with proper prosodic cues for quiz shorts
TEXT_EXPRESSIVE = "Первый вопрос! Какая планета Солнечной системы вращается вокруг Солнца быстрее всех? Правильный ответ: Меркурий!"

def synthesize_custom(
    text: str,
    out_path: str,
    length_scale: float = 0.88,
    noise_scale: float = 0.85,
    noise_w_scale: float = 0.9,
    tighten_pauses: bool = True,
    warm_eq: bool = False,
):
    voice = PiperVoice.load(MODEL_PATH)
    cfg = SynthesisConfig(
        length_scale=length_scale,
        noise_scale=noise_scale,
        noise_w_scale=noise_w_scale,
        normalize_audio=True,
    )
    
    t0 = time.time()
    chunks = list(voice.synthesize(text, syn_config=cfg))
    if not chunks:
        return
        
    sr = chunks[0].sample_rate
    all_bytes = b"".join(c.audio_int16_bytes for c in chunks)
    
    # Convert to float numpy array [-1.0, 1.0]
    audio = np.frombuffer(all_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    
    # 1. Compress unnatural dead gaps between words
    if tighten_pauses:
        audio = compress_speech_pauses(
            audio,
            sr,
            max_pause_sec=0.10,
            min_silence_to_trim_sec=0.14,
            silence_threshold=0.015,
        )
        
    # 2. Optional warm studio EQ & limiter
    if warm_eq:
        # Subtle analog saturation & soft clipping
        audio = np.tanh(audio * 1.15)
        # Normalize
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val * 0.96

    sf.write(out_path, audio, sr)
    dur = time.time() - t0
    final_len = len(audio) / sr
    print(f"Generated: {out_path} in {dur:.2f}s (audio length: {final_len:.2f}s)")

def main():
    # 1. Expressive & smooth (tight pauses, lively intonation)
    synthesize_custom(
        TEXT_EXPRESSIVE,
        "output/voice_samples/piper_ruslan_expressive.wav",
        length_scale=0.88,
        noise_scale=0.85,
        noise_w_scale=0.9,
        tighten_pauses=True,
        warm_eq=False,
    )
    
    # 2. Fast blitz pace (Shorts dynamic style)
    synthesize_custom(
        TEXT_EXPRESSIVE,
        "output/voice_samples/piper_ruslan_blitz.wav",
        length_scale=0.80,
        noise_scale=0.92,
        noise_w_scale=0.95,
        tighten_pauses=True,
        warm_eq=False,
    )
    
    # 3. Studio radio mic (warm saturation, tight pauses, expressive)
    synthesize_custom(
        TEXT_EXPRESSIVE,
        "output/voice_samples/piper_ruslan_studio.wav",
        length_scale=0.85,
        noise_scale=0.88,
        noise_w_scale=0.92,
        tighten_pauses=True,
        warm_eq=True,
    )

if __name__ == "__main__":
    main()

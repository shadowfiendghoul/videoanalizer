import time
import wave
from pathlib import Path
from piper import PiperVoice

OUTPUT_DIR = Path("output/voice_samples")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEXT = "Первый вопрос. Какая планета Солнечной системы вращается вокруг Солнца быстрее всех? Правильный ответ — Меркурий."

def synthesize_piper(model_path: str, out_path: str):
    t0 = time.time()
    voice = PiperVoice.load(model_path)
    
    chunks = list(voice.synthesize(TEXT))
    if not chunks:
        print(f"No audio produced for {model_path}")
        return
        
    sr = chunks[0].sample_rate
    channels = chunks[0].sample_channels
    width = chunks[0].sample_width
    
    all_bytes = b"".join(c.audio_int16_bytes for c in chunks)
    
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(sr)
        wf.writeframes(all_bytes)
        
    dur = time.time() - t0
    print(f"Saved: {out_path} in {dur:.2f}s (samplerate: {sr})")

def main():
    synthesize_piper("assets/models/piper/ru_RU-ruslan-medium.onnx", "output/voice_samples/piper_ruslan.wav")
    synthesize_piper("assets/models/piper/ru_RU-dmitri-medium.onnx", "output/voice_samples/piper_dmitri.wav")
    synthesize_piper("assets/models/piper/ru_RU-denis-medium.onnx", "output/voice_samples/piper_denis.wav")
    synthesize_piper("assets/models/piper/ru_RU-irina-medium.onnx", "output/voice_samples/piper_irina.wav")

if __name__ == "__main__":
    main()

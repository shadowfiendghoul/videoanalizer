import os
import time
import soundfile as sf
import torch
import torchaudio

# Robust Windows soundfile fallback for torchaudio.load
def _sf_load(uri, **kwargs):
    data, sr = sf.read(str(uri), dtype="float32")
    tensor = torch.from_numpy(data)
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)
    else:
        tensor = tensor.t()
    return tensor, sr

torchaudio.load = _sf_load

import f5_tts
from f5_tts.api import F5TTS

OUTPUT_DIR = "output/voice_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_TEXT = "Первый вопрос. Какая планета Солнечной системы вращается вокруг Солнца быстрее всех? Правильный ответ — Меркурий."

def main():
    print("Initializing F5TTS on CPU...")
    t0 = time.time()
    f5 = F5TTS(device="cpu")
    print(f"F5TTS loaded in {time.time() - t0:.2f}s")
    
    ref_dir = os.path.join(f5_tts.__path__[0], "infer", "examples", "basic")
    ref_wav = os.path.join(ref_dir, "basic_ref_en.wav")
    ref_text = "Some call me nature, others call me mother nature."
    
    out_wav = os.path.join(OUTPUT_DIR, "f5tts_sample_flowmatching.wav")
    print("\n--- Generating Flow Matching Speech (F5-TTS) ---")
    t_gen = time.time()
    
    f5.infer(
        ref_file=ref_wav,
        ref_text=ref_text,
        gen_text=TEST_TEXT,
        file_wave=out_wav,
        nfe_step=16,
        speed=1.0,
    )
    dur = time.time() - t_gen
    print(f"\nSUCCESS: Generated {out_wav} in {dur:.2f}s")

if __name__ == "__main__":
    main()

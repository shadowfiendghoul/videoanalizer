import os
import time
import torch

os.environ["COQUI_TOS_AGREED"] = "1"
from TTS.api import TTS

OUTPUT_DIR = "output/voice_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_TEXT = "Первый вопрос. Какая планета Солнечной системы вращается вокруг Солнца быстрее всех? Правильный ответ — Меркурий."

def main():
    print("Loading XTTS-v2...")
    t0 = time.time()
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    print(f"XTTS-v2 initialized in {time.time() - t0:.2f}s")
    
    speakers_to_test = [
        "Viktor Eka",
        "Damien Black",
        "Claribel Dervla",
        "Asya Anara",
    ]
    
    available_speakers = tts.speakers or []
    print(f"Total built-in speakers: {len(available_speakers)}")
    
    for spk in speakers_to_test:
        if spk not in available_speakers:
            print(f"Speaker '{spk}' not found in built-in list!")
            continue
            
        out_path = os.path.join(OUTPUT_DIR, f"xtts_{spk.lower().replace(' ', '_')}.wav")
        print(f"\n--- Generating for speaker: {spk} ---")
        t_gen = time.time()
        tts.tts_to_file(
            text=TEST_TEXT,
            speaker=spk,
            language="ru",
            file_path=out_path,
            temperature=0.7,
            repetition_penalty=2.0,
        )
        dur = time.time() - t_gen
        print(f"Saved: {out_path} ({dur:.2f}s)")

if __name__ == "__main__":
    main()

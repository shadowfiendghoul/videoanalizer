import os
import time

os.environ["COQUI_TOS_AGREED"] = "1"
from TTS.api import TTS

OUTPUT_DIR = "output/voice_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_TEXT = "Первый вопрос. Какая планета Солнечной системы вращается вокруг Солнца быстрее всех? Правильный ответ — Меркурий."

def main():
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    
    speakers = [
        "Ludvig Milivoj",
        "Lidiya Szekeres"
    ]
    
    for spk in speakers:
        out_name = f"xtts_{spk.lower().replace(' ', '_')}.wav"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        if os.path.exists(out_path):
            continue
        print(f"Generating for {spk}...")
        t0 = time.time()
        tts.tts_to_file(
            text=TEST_TEXT,
            speaker=spk,
            language="ru",
            file_path=out_path,
            temperature=0.7,
            repetition_penalty=2.0
        )
        print(f"Done in {time.time() - t0:.2f}s: {out_path}")

if __name__ == "__main__":
    main()

import os
import time

os.environ["COQUI_TOS_AGREED"] = "1"
from TTS.api import TTS

OUTPUT_DIR = "output/voice_samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_TEXT = "Первый вопрос. Какая планета Солнечной системы вращается вокруг Солнца быстрее всех? Правильный ответ — Меркурий."

def main():
    print("Loading XTTS-v2...")
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)
    
    # 1. Anti-gurgle with Viktor Eka
    out1 = os.path.join(OUTPUT_DIR, "xtts_viktor_antigurgle.wav")
    print("\n1. Generating Viktor with temperature=0.15, rep_penalty=10.0...")
    t0 = time.time()
    tts.tts_to_file(
        text=TEST_TEXT,
        speaker="Viktor Eka",
        language="ru",
        file_path=out1,
        temperature=0.15,
        repetition_penalty=10.0,
        top_k=50,
        top_p=0.8,
        enable_text_splitting=True,
    )
    print(f"Saved: {out1} in {time.time() - t0:.2f}s")
    
    # 2. Russian speaker clone reference
    ref_audio = "output/voice_samples/dmitry_fast_base.wav"
    if os.path.exists(ref_audio):
        out2 = os.path.join(OUTPUT_DIR, "xtts_cloned_russian_host.wav")
        print("\n2. Generating with Russian reference voice...")
        t0 = time.time()
        tts.tts_to_file(
            text=TEST_TEXT,
            speaker_wav=ref_audio,
            language="ru",
            file_path=out2,
            temperature=0.15,
            repetition_penalty=10.0,
            top_k=50,
            top_p=0.8,
            enable_text_splitting=True,
        )
        print(f"Saved: {out2} in {time.time() - t0:.2f}s")

if __name__ == "__main__":
    main()

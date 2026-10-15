import asyncio
import edge_tts
from pathlib import Path

OUTPUT_DIR = Path("output/voice_samples")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def make_refs():
    # 1. Male reference
    text_male = "Здравствуйте! Сегодня мы проверим вашу эрудицию и кругозор."
    path_male = OUTPUT_DIR / "ref_male_host.wav"
    comm1 = edge_tts.Communicate(text_male, "ru-RU-DmitryNeural", rate="+0%")
    await comm1.save(str(path_male))
    print(f"Created male reference: {path_male}")

    # 2. Female reference
    text_female = "Привет! Готов проверить свои знания в увлекательной викторине?"
    path_female = OUTPUT_DIR / "ref_female_host.wav"
    comm2 = edge_tts.Communicate(text_female, "ru-RU-SvetlanaNeural", rate="+0%")
    await comm2.save(str(path_female))
    print(f"Created female reference: {path_female}")

if __name__ == "__main__":
    asyncio.run(make_refs())

"""Generate full vertical quiz video with Mellstroy voice.

Uses Qwen3-TTS + RVC and random background.
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

from videoanalizer.quiz.config import get_quiz_config
from videoanalizer.quiz.models import RenderProfile, VoiceConfig, VoiceMode
from videoanalizer.quiz.orchestrator import QuizOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("QuizRunner")


async def main() -> None:
    topic = "Странные научные парадоксы"
    logger.info("Starting complete vertical quiz video generation...")
    logger.info("Topic: '%s'", topic)

    voice_cfg = VoiceConfig(
        voice_mode=VoiceMode.QWEN3_RVC,
        rvc_model_path="Mellstroy-strimer.pth",
        rvc_index_path="assets/models/rvc/Mellstroy-strimer_v2.index",
        pitch_shift=0,
        qwen3_model_path="assets/models/qwen3_tts",
        qwen3_ref_audio="assets/voices/mellstroy_ref.wav",
        tighten_pauses=True,
        max_pause_sec=0.13,
    )

    config = get_quiz_config()
    orchestrator = QuizOrchestrator(config=config)

    def progress_callback(pct: int, msg: str) -> None:
        logger.info("[PROGRESS %3d%%] %s", pct, msg)

    start_time = time.time()
    out_path = Path("output/quiz_mellstroy_science_paradoxes.mp4")

    result = await orchestrator.generate(
        topic=topic,
        language="ru",
        background_video="random",
        output_filename=str(out_path),
        intro_hook="Ты гений, если ответишь на все девять вопросов!",
        background_music="assets/music/music_87f02af3_Sneaky_Snitch_chosic_com.mp3",
        background_music_volume=0.15,
        render_profile=RenderProfile.GPU_FAST,
        progress_callback=progress_callback,
        voice_config=voice_cfg,
    )

    elapsed = time.time() - start_time
    logger.info("VIDEO GENERATION COMPLETE!")
    logger.info("Output video: %s (size: %.2f MB)", result, result.stat().st_size / 1024 / 1024)
    logger.info("Total processing time: %.1f seconds (%.2f minutes)", elapsed, elapsed / 60)


if __name__ == "__main__":
    asyncio.run(main())

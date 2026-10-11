"""Standalone CLI entrypoint for Quiz Shorts Generator."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from videoanalizer.quiz.orchestrator import QuizOrchestrator


def setup_logging() -> None:
    """Configure console logging format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate viral vertical Quiz & Trivia shorts "
            "(QuizyPeasy style) in 1080x1920 60fps MP4."
        ),
    )
    parser.add_argument(
        "--topic",
        "-t",
        type=str,
        required=True,
        help="Quiz topic prompt (e.g. 'Мировая география', 'Guess the Flag', 'Brand Logos').",
    )
    parser.add_argument(
        "--language",
        "-l",
        type=str,
        default="ru",
        choices=["ru", "en"],
        help="Language for quiz questions and voiceover narration (default: ru).",
    )
    parser.add_argument(
        "--background",
        "-b",
        type=str,
        default=None,
        help="Optional path to a custom 9:16 background video.",
    )
    parser.add_argument(
        "--voice",
        "-v",
        type=str,
        default=None,
        help="Optional edge-tts neural voice name override.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Target output MP4 filepath (default: outputs/<topic>_<timestamp>.mp4).",
    )
    return parser.parse_args()


async def main_async() -> int:
    """Async main routine."""
    args = parse_args()
    setup_logging()
    logger = logging.getLogger("quiz.cli")

    logger.info("Initializing Quiz Shorts Generator...")
    logger.info("Topic: '%s' | Language: %s", args.topic, args.language)

    orchestrator = QuizOrchestrator()
    try:
        output_file = await orchestrator.generate(
            topic=args.topic,
            language=args.language,
            background_video=Path(args.background) if args.background else None,
            voice=args.voice,
            output_filename=args.output,
        )
        logger.info("Quiz short video successfully generated: %s", output_file)
        print(f"SUCCESS: {output_file}")
        return 0
    except Exception as exc:
        logger.error("Failed to generate quiz short: %s", exc, exc_info=True)
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    """CLI entrypoint."""
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()

"""ScriptService: Generates structured 9-question 3-tier trivia challenges via Gemini REST API."""

import asyncio
import json
import logging
from pathlib import Path

from google import genai
from google.genai import types

from videoanalizer.quiz.config import QuizConfig, get_quiz_config
from videoanalizer.quiz.image_service import ImageService
from videoanalizer.quiz.models import DifficultyTier, QuizChallenge
from videoanalizer.quiz.workspace import QuizWorkspace

logger = logging.getLogger(__name__)


QUIZ_SYSTEM_PROMPT = """You are an elite short-form trivia creator specializing in viral TikTok
and YouTube Shorts quizzes in the signature QuizyPeasy channel style.

RULES & CONSTRAINTS:
1. Format: Open-Recall trivia challenge (NO multiple-choice options).
   The viewer is presented with a question prompt or visual clue, gets 3 seconds to think,
   and then sees the definitive answer.
2. Structure: Exactly 9 questions, strictly organized into 3 progressive tiers:
   - Level 1 (Easy): 3 questions, theme_color '#22C55E', question numbers 1, 2, 3.
   - Level 2 (Medium): 3 questions, theme_color '#F59E0B', question numbers 4, 5, 6.
   - Level 3 (Hard): 3 questions, theme_color '#EF4444', question numbers 7, 8, 9.
3. Content Quality:
   - Question texts must be punchy, direct, and under 120 characters.
   - Correct answers must be crisp (1 to 4 words).
   - Fun facts must be fascinating, educational, and under 150 characters.
   - If the topic is visual (flags, country shapes, brand logos, monuments),
     provide a precise 'image_query' (e.g. 'Flag of Argentina', 'Starbucks Logo')
     for each question. If non-visual, set 'image_query' to null.
4. Output: You MUST strictly return valid JSON adhering to the QuizChallenge schema."""


class ScriptService:
    """Service responsible for generating quiz trivia content using Gemini REST API."""

    def __init__(
        self, image_service: ImageService | None = None, config: QuizConfig | None = None
    ) -> None:
        self.config = config or get_quiz_config()
        self.image_service = image_service or ImageService()

    async def _call_gemini(self, topic: str, language: str) -> QuizChallenge:
        """Execute Gemini REST API call with structured Pydantic v2 schema."""
        api_key = self.config.effective_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        prompt = (
            f"Generate a viral 9-question 3-tier trivia challenge on the topic: '{topic}'.\n"
            f"Language: {language}.\n"
            f"Ensure 3 Easy, 3 Medium, and 3 Hard questions strictly matching the required schema."
        )

        config = types.GenerateContentConfig(
            system_instruction=QUIZ_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=QuizChallenge,
            temperature=0.7,
        )

        # Execute call with retry on 503 temporary demand spikes
        loop = asyncio.get_running_loop()
        max_retries = 4
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.config.gemini_model,
                        contents=prompt,
                        config=config,
                    ),
                )
                raw_text = response.text or "{}"
                data = json.loads(raw_text)
                return QuizChallenge.model_validate(data)
            except Exception as exc:
                last_error = exc
                err_msg = str(exc)
                is_transient = (
                    "503" in err_msg
                    or "UNAVAILABLE" in err_msg
                    or "high demand" in err_msg
                    or "429" in err_msg
                    or "RESOURCE_EXHAUSTED" in err_msg
                )
                if is_transient and attempt < max_retries - 1:
                    delay = 2.5 * (2**attempt)
                    logger.warning(
                        "Transient Gemini API error (attempt %d/%d). Retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise exc

        if last_error:
            raise last_error
        raise RuntimeError("Failed to generate content from Gemini API.")

    async def generate_quiz(
        self,
        topic: str,
        language: str = "ru",
        workspace: QuizWorkspace | None = None,
    ) -> QuizChallenge:
        """Generate 9-question trivia challenge and download visual assets if applicable."""
        logger.info(f"Generating 9-question quiz challenge for topic: '{topic}' (lang={language})")
        challenge = await self._call_gemini(topic, language)

        # Normalize total count and tier colors if needed
        color_map = {
            DifficultyTier.EASY: "#22C55E",
            DifficultyTier.MEDIUM: "#F59E0B",
            DifficultyTier.HARD: "#EF4444",
        }
        for tier in challenge.tiers:
            tier.theme_color = color_map.get(tier.tier_level, tier.theme_color)

        # Resolve image assets concurrently if queries exist
        if workspace:
            image_tasks = []
            target_items = []
            for item in challenge.all_questions():
                if item.image_query:
                    dest = workspace.get_image_path(f"q_{item.question_number}.png")
                    image_tasks.append(
                        self.image_service.search_and_download(item.image_query, dest)
                    )
                    target_items.append(item)

            if image_tasks:
                results = await asyncio.gather(*image_tasks, return_exceptions=True)
                for item, res in zip(target_items, results, strict=False):
                    if isinstance(res, Path) and res.exists():
                        item.local_image_path = str(res)
                    else:
                        item.local_image_path = None

        logger.info(
            "Quiz challenge generated successfully with %d questions.",
            len(challenge.all_questions()),
        )
        return challenge

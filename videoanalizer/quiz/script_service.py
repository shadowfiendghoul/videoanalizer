"""ScriptService: Generates structured 9-question 3-tier trivia challenges via Gemini REST API."""

import asyncio
import io
import json
import logging
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from videoanalizer.quiz.config import QuizConfig, get_quiz_config
from videoanalizer.quiz.image_service import ImageService
from videoanalizer.quiz.models import (
    DifficultyTier,
    QuizChallenge,
    QuizItem,
    RegeneratedQuestionsPayload,
)
from videoanalizer.quiz.workspace import QuizWorkspace

logger = logging.getLogger(__name__)


QUIZ_SYSTEM_PROMPT = """You are an elite short-form trivia creator specializing in viral TikTok
and YouTube Shorts quizzes in the signature QuizyPeasy channel style.

RULES & CONSTRAINTS:
1. Format & Multi-Topic Chaos:
   - Format: Open-Recall trivia challenge (NO multiple-choice options).
     The viewer sees the question number in a vertical ladder, gets 3 seconds to think,
     and then sees the definitive answer pop onto the ladder row.
   - Unless an explicit single topic is specified, every single question MUST come from a
     completely different category (e.g. Gaming, Pop Culture, Food, Bizarre Laws, Body Paradoxes,
     Tech History, Nature/Animals).
   - Zero-cliché filter: Strictly FORBIDDEN to use overused school trivia (no capital cities,
     no "how many planets", no "cheetah is fastest animal", no "how many hearts octopus has").

2. Structure (Strict 9-Question Progressive Ramp):
   - Level 1 (Warmup): 3 questions, theme_color '#22C55E', question numbers 1, 2, 3.
     Non-trivial but quick to answer.
   - Level 2 (Mind Traps): 3 questions, theme_color '#F59E0B', question numbers 4, 5, 6.
     Cognitive traps, counter-intuitive facts, Mandela effects.
   - Level 3 (Hardcore Paradoxes): 3 questions, theme_color '#EF4444', question numbers 7, 8, 9.
     Shocking, debate-provoking paradoxes.

3. Strict Layout & Retention Guard:
   - Question text: Direct, punchy, strictly <= 65 characters (never exceed 80 characters).
   - Correct answer: Crisp, 1 to 4 words, strictly <= 25 characters (never exceed 35 characters).
   - Fun fact / Punchline: Fascinating, educational, strictly <= 90 characters for fast voiceover.
   - Visual Answer Illustrations: Provide a concise, descriptive English search query in
     'image_query' depicting the correct answer (e.g. for 'Золото' -> 'gold bullion bars',
     for 'Бедренная кость' -> 'human femur bone', for '60 минут' -> 'stopwatch clock 60 min').
     The image will be displayed as an illustration card together with the revealed answer.

4. Output:
   - You MUST strictly return valid JSON adhering to the QuizChallenge schema."""


FACT_CHECK_SYSTEM_PROMPT = """You are a rigorous scientific fact-checker and trivia auditor
with encyclopedic precision. Your job is to audit and refine a 9-question trivia challenge.

VERIFICATION RULES:
1. Strict Factual Veracity:
   - Verify questions, answers, and fun facts against verified scientific/historical facts.
   - Banish popular myths, misconceptions, and outdated school trivia (e.g. "taste zones on tongue",
     "Great Wall visible from space with naked eye", "humans use only 10% of brain").
   - If a question or fact is based on a debunked myth, REWRITE it into a true, verified paradox.
2. Unambiguous Answers:
   - Ensure the 'correct_answer' is undeniably accurate and specific.
3. Strict Layout Length Constraints:
   - 'question_text': punchy, direct, strictly <= 65 chars (never exceed 80 chars).
   - 'correct_answer': crisp, 1 to 4 words, strictly <= 25 chars (never exceed 35 chars).
   - 'fun_fact': educational takeaway, strictly <= 90 chars.
   - 'image_query': accurate English search query clearly depicting the verified correct answer.
4. Preserve Structure:
   - Keep exactly 9 questions across 3 tiers (Level 1: 1-3, Level 2: 4-6, Level 3: 7-9).
   - Retain question numbers and tier theme colors.
5. Output:
   - You MUST strictly return valid JSON adhering to the QuizChallenge schema."""


REGENERATE_QUESTIONS_SYSTEM_PROMPT = """You are an elite short-form trivia creator
specializing in viral TikTok and YouTube Shorts quizzes in the signature QuizyPeasy channel style.
You are tasked with regenerating SPECIFIC question numbers in an existing 9-question 3-tier trivia.

RULES & CONSTRAINTS:
1. Format & Progression:
   - Generate NEW questions ONLY for the requested question numbers.
   - For each requested question, adhere strictly to its tier and index:
     * Question 1, 2, 3: Level 1 (Warmup), difficulty 'easy', tier_index 1. Non-trivial.
     * Question 4, 5, 6: Level 2 (Mind Traps), difficulty 'medium', tier_index 2. Cognitive traps.
     * Question 7, 8, 9: Level 3 (Hardcore Paradoxes), difficulty 'hard', tier_index 3.
2. Anti-Duplication:
   - The user has KEPT several questions. You MUST NOT duplicate facts or answers from them.
   - Zero-cliché filter: Strictly avoid overused school trivia.
3. Strict Layout Length Constraints:
   - 'question_text': punchy, direct, strictly <= 65 characters (never exceed 80 chars).
   - 'correct_answer': crisp, 1 to 4 words, strictly <= 25 characters (never exceed 35 chars).
   - 'fun_fact': educational takeaway, strictly <= 90 characters.
   - 'image_query': concise English search query for an illustration of the correct answer.
4. Output:
   - You MUST strictly return valid JSON adhering to the RegeneratedQuestionsPayload schema."""


class ScriptService:
    """Service responsible for generating quiz trivia content using Gemini REST API."""

    def __init__(
        self, image_service: ImageService | None = None, config: QuizConfig | None = None
    ) -> None:
        self.config = config or get_quiz_config()
        self.image_service = image_service or ImageService()

    async def _call_gemini(
        self, topic: str, language: str, temperature: float | None = None
    ) -> QuizChallenge:
        """Execute Gemini REST API call with structured Pydantic v2 schema."""
        api_key = self.config.effective_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        prompt = (
            f"Generate a viral 9-question 3-tier trivia challenge on the topic: '{topic}'.\n"
            f"Language: {language}.\n"
            f"Adhere strictly to the 3-tier progression: Level 1 (Warmup), Level 2 (Mind Traps), "
            f"Level 3 (Hardcore Paradoxes). Zero clichés, non-trivial questions, punchy text."
        )

        eff_temp = (
            temperature if temperature is not None else self.config.creative_temperature
        )

        config = types.GenerateContentConfig(
            system_instruction=QUIZ_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=QuizChallenge,
            temperature=eff_temp,
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

    async def _verify_and_refine_facts(
        self, challenge: QuizChallenge, language: str
    ) -> QuizChallenge:
        """Run strict secondary fact-checking pass to correct inaccuracies and myths."""
        logger.info("Running secondary strict fact-checking pass on 9-question challenge...")
        api_key = self.config.effective_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        prompt = (
            f"Audit and verify this 9-question trivia challenge in language '{language}'.\n"
            f"Verify all questions are unambiguous and all facts are scientifically true.\n"
            f"Debunk any myths and ensure strict character length limits.\n"
            f"Input Challenge JSON:\n{challenge.model_dump_json()}"
        )

        config = types.GenerateContentConfig(
            system_instruction=FACT_CHECK_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=QuizChallenge,
            temperature=self.config.verifier_temperature,
        )

        loop = asyncio.get_running_loop()
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
            verified = QuizChallenge.model_validate(data)
            logger.info("Fact-checking verifier pass completed successfully.")
            return verified
        except Exception as exc:
            logger.warning(
                "Fact-checking verifier pass encountered an error, falling back to original: %s",
                exc,
            )
            return challenge

    async def generate_quiz(
        self,
        topic: str,
        language: str = "ru",
        workspace: QuizWorkspace | None = None,
        creative_temperature: float | None = None,
        fact_check: bool | None = None,
    ) -> QuizChallenge:
        """Generate 9-question trivia challenge and download visual assets if applicable."""
        logger.info(f"Generating 9-question quiz challenge for topic: '{topic}' (lang={language})")
        challenge = await self._call_gemini(topic, language, temperature=creative_temperature)

        # Stage 2: Strict fact-checking pass
        do_fact_check = (
            self.config.fact_check_enabled if fact_check is None else fact_check
        )
        if do_fact_check:
            challenge = await self._verify_and_refine_facts(challenge, language)

        # Normalize total count and tier colors if needed
        color_map = {
            DifficultyTier.EASY: "#22C55E",
            DifficultyTier.MEDIUM: "#F59E0B",
            DifficultyTier.HARD: "#EF4444",
        }
        for tier in challenge.tiers:
            tier.theme_color = color_map.get(tier.tier_level, tier.theme_color)

        # Resolve image preview URLs for visual questions (allowing user approval in UI)
        if workspace is None:
            for item in challenge.all_questions():
                if item.image_query and not item.image_url:
                    try:
                        img_results = await self.image_service._search_image_urls(
                            item.image_query, max_results=2
                        )
                        if img_results:
                            item.image_url = (
                                img_results[0].get("image") or img_results[0].get("thumbnail")
                            )
                    except Exception as e:
                        logger.debug(
                            "Failed to resolve preview image for '%s': %s", item.image_query, e
                        )

        # Resolve local image assets if workspace provided
        if workspace:
            image_tasks = []
            target_items = []
            for item in challenge.all_questions():
                if item.image_url or item.image_query:
                    dest = workspace.get_image_path(f"q_{item.question_number}.png")
                    if item.image_url:
                        image_tasks.append(
                            self._download_and_verify_url(item.image_url, dest)
                        )
                    else:
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

    async def _download_and_verify_url(self, url: str, dest_path: Path) -> Path | None:
        """Download image from direct URL and verify it opens as valid image."""
        raw_bytes = await self.image_service._download_bytes(url)
        if raw_bytes:
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                img = Image.open(io.BytesIO(raw_bytes))
                img = img.convert("RGBA")
                img.save(dest_path, "PNG")
                return dest_path
            except Exception as e:
                logger.warning("Failed to save image from URL %s: %s", url, e)
        return None

    async def _call_gemini_regenerate(
        self,
        challenge: QuizChallenge,
        question_numbers: list[int],
        temperature: float | None = None,
    ) -> list[QuizItem]:
        """Call Gemini to regenerate specifically requested question numbers."""
        api_key = self.config.effective_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        kept_lines = [
            f"- Вопрос {q.question_number}: {q.question_text} (Ответ: {q.correct_answer})"
            for q in challenge.all_questions()
            if q.question_number not in question_numbers
        ]
        requested_lines = [
            f"- Вопрос {q.question_number} (Уровень {q.tier_index}, сложность {q.difficulty.value})"
            for q in challenge.all_questions()
            if q.question_number in question_numbers
        ]

        prompt = (
            f"Тема викторины: '{challenge.topic}'. Язык: '{challenge.language}'.\n"
            f"В викторине ОСТАЮТСЯ следующие вопросы (НЕ ДУБЛИРОВАТЬ их факты, темы и ответы!):\n"
            + ("\n".join(kept_lines) if kept_lines else "(Нет оставшихся вопросов)")
            + "\n\n"
            "Сгенерируй НОВЫЕ вопросы ТОЛЬКО для следующих номеров:\n"
            + "\n".join(requested_lines)
            + "\n\n"
            "Для каждого номера верни question_number, difficulty, tier_index, "
            "punchy question_text (<=65 символов), correct_answer (<=25 символов), "
            "fun_fact (<=90 символов), image_query (поисковый запрос картинки на английском)."
        )

        eff_temp = (
            temperature if temperature is not None else self.config.creative_temperature
        )

        config = types.GenerateContentConfig(
            system_instruction=REGENERATE_QUESTIONS_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=RegeneratedQuestionsPayload,
            temperature=eff_temp,
        )

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
                payload = RegeneratedQuestionsPayload.model_validate(data)
                return payload.questions
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
                        "Transient Gemini error on regen (attempt %d/%d). Retrying in %.1fs: %s",
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
        raise RuntimeError("Failed to regenerate questions from Gemini API.")

    async def regenerate_selected_questions(
        self,
        challenge: QuizChallenge,
        question_numbers: list[int],
        creative_temperature: float | None = None,
        fact_check: bool | None = None,
    ) -> QuizChallenge:
        """Regenerate specific questions while preserving other questions and user edits."""
        target_nums = set(question_numbers)
        if not target_nums:
            return challenge

        logger.info(
            "Regenerating selected questions %s for topic: '%s'",
            sorted(target_nums),
            challenge.topic,
        )

        new_items = await self._call_gemini_regenerate(
            challenge=challenge,
            question_numbers=list(target_nums),
            temperature=creative_temperature,
        )

        # Index new items by question_number
        new_items_by_num: dict[int, QuizItem] = {
            item.question_number: item for item in new_items
        }

        # If any requested question_number was missing from response, assign unmatched sequentially
        unmatched_new = [
            item for item in new_items if item.question_number not in target_nums
        ]
        for q_num in sorted(target_nums):
            if q_num not in new_items_by_num and unmatched_new:
                fallback_item = unmatched_new.pop(0)
                fallback_item.question_number = q_num
                fallback_item.tier_index = 1 if q_num <= 3 else (2 if q_num <= 6 else 3)
                fallback_item.difficulty = (
                    DifficultyTier.EASY
                    if q_num <= 3
                    else (DifficultyTier.MEDIUM if q_num <= 6 else DifficultyTier.HARD)
                )
                new_items_by_num[q_num] = fallback_item

        # Resolve candidate preview image URLs for visual questions
        for item in new_items_by_num.values():
            if item.image_query and not item.image_url:
                try:
                    img_results = await self.image_service._search_image_urls(
                        item.image_query, max_results=2
                    )
                    if img_results:
                        item.image_url = (
                            img_results[0].get("image") or img_results[0].get("thumbnail")
                        )
                except Exception as e:
                    logger.debug(
                        "Failed to resolve preview image for '%s': %s",
                        item.image_query,
                        e,
                    )

        # Update challenge in place, preserving all unselected questions and their edits
        for tier in challenge.tiers:
            updated_questions = []
            for existing_q in tier.questions:
                if existing_q.question_number in new_items_by_num:
                    new_q = new_items_by_num[existing_q.question_number]
                    new_q.tier_index = tier.tier_index
                    new_q.difficulty = tier.tier_level
                    updated_questions.append(new_q)
                else:
                    updated_questions.append(existing_q)
            tier.questions = updated_questions

        logger.info(
            "Successfully regenerated %d questions in challenge.",
            len(new_items_by_num),
        )
        return challenge

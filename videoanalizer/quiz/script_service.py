"""ScriptService: Generates structured 9-question 3-tier trivia challenges via Gemini REST API."""

import asyncio
import io
import json
import logging
import random
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from videoanalizer.quiz.config import QuizConfig, get_quiz_config
from videoanalizer.quiz.image_service import ImageService
from videoanalizer.quiz.models import (
    BatchTopicList,
    DifficultyTier,
    QuizChallenge,
    QuizItem,
    RegeneratedQuestionsPayload,
    TopicSuggestion,
)
from videoanalizer.quiz.rate_limiter import get_gemini_rate_limiter
from videoanalizer.quiz.workspace import QuizWorkspace

logger = logging.getLogger(__name__)


DIVERSE_TOPIC_DOMAINS = [
    "Космос, чёрные дыры и тайны Вселенной",
    "Секреты видеоигр, пасхалки и геймдев",
    "Необъяснимые исторические парадоксы и забытые цивилизации",
    "Психология восприятия, оптические иллюзии и ловушки разума",
    "Экстремальная природа, океанские глубины и необычные животные",
    "Кинематограф, поп-культура и скрытые детали культовых фильмов",
    "Технологии, киберпанк и инженерные загадки",
    "Криминалистика, шифры и нераскрытые тайны прошлого",
    "Странные законы стран мира и исторические казусы",
    "Кулинарные феномены, еда и химия вкуса",
    "Авиация, морские тайны и катастрофы",
    "Городские легенды, мифы и эффекты Манделы",
]


SINGLE_TOPIC_SYSTEM_PROMPT = """Ты — ведущий креативный продюсер вирусных коротких видео
(TikTok, YouTube Shorts, Reels) в фирменном стиле канала QuizyPeasy.
Твоя цель — придумать одну захватывающую тему для викторины-лестницы из 9 вопросов (Open-Recall).

ПРАВИЛА И ТРЕБОВАНИЯ К ТЕМЕ:
1. Парадоксы и высокий уровень любопытства (Curiosity Hook):
   - Тема должна вызывать любопытство или ощущение «Я был уверен, но ошибся».
   - Генерируй темы из самых разных сфер: космос, видеоигры, инженерные загадки,
     забытая история, оптические иллюзии, дикая природа, авиация, странные законы мира.
   - СТРОГИЙ ЗАПРЕТ: Не зацикливайся на анатомии человека или биологии! Не выдавай темы про тело.
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО повторять одни и те же темы. Каждая генерация уникальна и свежа.
2. Строгий фильтр банальности (Anti-Cliché):
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ школьные темы (никаких «Столицы мира», «Таблица умножения»).
3. Ограничения формата:
   - 'topic': Краткое название темы на запрошенном языке (strictly <= 65 characters / символов).
   - 'category': Ниша темы (например: 'Космос', 'Видеоигры', 'История', strictly <= 35 characters).
   - 'curiosity_hook': 1 короткая фраза о вирусном крючке темы (строго <= 100 символов).
4. Формат вывода:
   - Ты ОБЯЗАН вернуть строго валидный JSON в соответствии со схемой TopicSuggestion."""


BATCH_TOPIC_SYSTEM_PROMPT = """Ты — ведущий креативный продюсер вирусных коротких видео
(TikTok, YouTube Shorts, Reels) в фирменном стиле канала QuizyPeasy.
Твоя цель — придумать ровно N УНИКАЛЬНЫХ тем для пакета роликов-викторин из 9 вопросов.

ПРАВИЛА ПАКЕТНОЙ ГЕНЕРАЦИИ:
1. Максимальное разнообразие ниш:
   - Каждая тема ОБЯЗАНА относиться к совершенно ДРУГОЙ нише/категории
     (например: Космос, Видеоигры, Криминалистика, История, Психология, Кино, Технологии, Природа).
   - Запрет на пересечение тем: не более 1 темы по схожей тематике на пачку.
   - Не делай пачку исключительно про анатомию или биологию.
2. Анти-банальность:
   - Категорически запрещены стандартные школьные темы (никаких «Столицы стран», «География»).
3. Ограничения формата:
   - Сгенерируй ровно запрошенное количество тем (count).
   - Для каждой темы заполни:
     * 'topic': Емкое название на запрошенном языке (strictly <= 65 characters / символов).
     * 'category': Название ниши (strictly <= 35 characters / символов).
     * 'curiosity_hook': 1 емкое предложение о вирусной интриге (строго <= 100 символов).
4. Формат вывода:
   - Ты ОБЯЗАН вернуть строго валидный JSON в соответствии со схемой BatchTopicList."""


QUIZ_SYSTEM_PROMPT = """Ты — элитный сценарист и продюсер вирусных викторин для TikTok
и YouTube Shorts в фирменном стиле канала QuizyPeasy.

ПРАВИЛА И ОГРАНИЧЕНИЯ ФОРМАТА:
1. Механика Open-Recall (Без вариантов ответа):
   - Формат викторины — прямой открытый ответ зрителя (БЕЗ вариантов выбора A/B/C/D).
     Зритель видит вопрос в строке вертикальной лестницы, получает 3 секунды на размышление,
     после чего правильный ответ ярко всплывает в ячейке лестницы.
   - Если тема не задана, каждый из 9 вопросов ОБЯЗАН быть из совершенно разной области
     (игры, поп-культура, странные законы, парадоксы анатомии, рекорды, технологии, природа).
   - Фильтр банальности: СТРОЖАЙШЕ ЗАПРЕЩЕНО использовать заезженные школьные вопросы
     (никаких столиц, «сколько планет», «гепард», «сколько сердец у осьминога»).

2. Структура (Строгая прогрессивная лестница из 9 вопросов):
   - Уровень 1 (Разминка): 3 вопроса, theme_color '#22C55E', номера 1, 2, 3.
     Небанальные, но доступные для быстрого ответа за 3 секунды.
   - Уровень 2 (Когнитивные ловушки): 3 вопроса, theme_color '#F59E0B', номера 4, 5, 6.
     Интуитивные ловушки, контринтуитивные факты, эффекты Манделы, где 90% ошибаются.
   - Уровень 3 (Хардкорные парадоксы): 3 вопроса, theme_color '#EF4444', номера 7, 8, 9.
     Шокирующие факты, провоцирующие споры в комментариях.

3. Жесткие лимиты на длину текста (Layout Guard):
   - Question text: Прямой вопрос, strictly <= 65 characters (never exceed 80 characters).
   - Correct answer: Ответ (1-4 слова), strictly <= 25 characters (never exceed 35 characters).
   - Fun fact / Punchline: Увлекательный факт для быстрой озвучки, strictly <= 90 characters.
   - Visual Answer Illustrations: Provide a concise, descriptive English search query in
     'image_query' depicting the correct answer (e.g. for 'Золото' -> 'gold bullion bars',
     for 'Бедренная кость' -> 'human femur bone', for '60 минут' -> 'stopwatch clock 60 min').
     Картинка будет показана зрителю в карточке-иллюстрации вместе с появлением ответа.

4. Формат вывода:
   - Ты ОБЯЗАН вернуть строго валидный JSON в соответствии со схемой QuizChallenge."""


FACT_CHECK_SYSTEM_PROMPT = """Ты — строгий факт-чекер (scientific fact-checker)
и энциклопедический аудитор контента.
Твоя задача — провести детальный аудит и верификацию викторины из 9 вопросов.

ПРАВИЛА ВЕРИФИКАЦИИ:
1. Строгая достоверность (Strict Factual Veracity):
   - Проверь каждый вопрос, ответ и факт по академическим и научным источникам.
   - Безжалостно искореняй популярные мифы, городские легенды и школьные заблуждения
     (например: «вкусовые зоны», «Стену видно из космоса», «человек использует 10% мозга»).
   - Если вопрос построен на развенчанном мифе, ПЕРЕПИШИ его в настоящий парадокс.
2. Однозначность ответа:
   - Убедись, что 'correct_answer' формулируется четко и не допускает двоякого толкования.
3. Строгие ограничения на длину текста:
   - 'question_text': емко и лаконично, strictly <= 65 characters (never exceed 80 characters).
   - 'correct_answer': четко, 1-4 слова, strictly <= 25 characters (never exceed 35 characters).
   - 'fun_fact': полезный факт, strictly <= 90 characters.
   - 'image_query': accurate English search query clearly depicting the verified correct answer.
4. Сохранение структуры:
   - Сохраняй ровно 9 вопросов в 3 уровнях (1-3: Уровень 1, 4-6: Уровень 2, 7-9: Уровень 3).
   - Сохраняй номера вопросов и цвета темы уровней.
5. Формат вывода:
   - Ты ОБЯЗАН вернуть строго валидный JSON в соответствии со схемой QuizChallenge."""


REGENERATE_QUESTIONS_SYSTEM_PROMPT = """Ты — элитный сценарист викторин для TikTok
и YouTube Shorts в фирменном стиле канала QuizyPeasy.
Твоя задача — перегенерировать указанные номера вопросов в уже существующей викторине из 9 вопросов.

ПРАВИЛА И ОГРАНИЧЕНИЯ:
1. Формат и соответствие уровням:
   - Сгенерируй НОВЫЕ вопросы ТОЛЬКО для запрошенных номеров.
   - Для каждого запрошенного вопроса строго соблюдай его уровень и сложность:
     * Вопросы 1, 2, 3: Уровень 1 (Разминка), difficulty 'easy', tier_index 1. Быстрые.
     * Вопросы 4, 5, 6: Уровень 2 (Ловушки), difficulty 'medium', tier_index 2. Ловушки.
     * Вопросы 7, 8, 9: Уровень 3 (Хардкор), difficulty 'hard', tier_index 3. Парадоксы.
2. Anti-Duplication (Анти-дублирование):
   - The user has KEPT questions. Пользователь СОХРАНИЛ часть вопросов (KEPT).
     Ты КАТЕГОРИЧЕСКИ НЕ ДОЛЖЕН дублировать факты, темы и ответы из сохраненных вопросов.
   - Полный фильтр банальности: избегай скучных школьных вопросов.
3. Ограничения длины текста:
   - 'question_text': четкий вопрос, strictly <= 65 characters (never exceed 80 characters).
   - 'correct_answer': 1-4 слова, strictly <= 25 characters (never exceed 35 characters).
   - 'fun_fact': краткий факт, strictly <= 90 characters.
   - 'image_query': concise English search query for an illustration of the correct answer.
4. Формат вывода:
   - Ты ОБЯЗАН вернуть строго валидный JSON по схеме RegeneratedQuestionsPayload."""


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
            f"Сгенерируй вирусную викторину-лестницу из 9 вопросов на тему: '{topic}'.\n"
            f"Язык: {language}.\n"
            f"Строго соблюдай трехуровневую прогрессию сложности: Уровень 1 (Разминка), "
            f"Уровень 2 (Когнитивные ловушки), Уровень 3 (Хардкорные парадоксы). "
            f"Полный отказ от банальностей, нетривиальные вопросы, емкий текст."
        )

        raw_temp = temperature if temperature is not None else self.config.creative_temperature
        eff_temp = min(2.0, max(0.0, float(raw_temp)))

        config = types.GenerateContentConfig(
            system_instruction=QUIZ_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=QuizChallenge,
            temperature=eff_temp,
        )

        # Execute call with retry on 503 temporary demand spikes
        loop = asyncio.get_running_loop()
        limiter = get_gemini_rate_limiter()
        max_retries = 4
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                await limiter.acquire()
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
                is_429 = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
                is_transient = (
                    "503" in err_msg
                    or "UNAVAILABLE" in err_msg
                    or "high demand" in err_msg
                    or is_429
                )
                if is_transient and attempt < max_retries - 1:
                    if is_429:
                        await limiter.record_429_backoff(attempt)
                    else:
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

    async def suggest_topic(
        self,
        category_hint: str | None = None,
        language: str = "ru",
        temperature: float | None = None,
        previous_topic: str | None = None,
    ) -> TopicSuggestion:
        """Suggest a single viral, non-trivial quiz topic using Gemini REST API."""
        api_key = self.config.effective_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        prompt = (
            f"Придумай вирусную, интригующую и небанальную тему "
            f"для викторины-лестницы на языке: '{language}'.\n"
        )
        if category_hint and category_hint.strip():
            prompt += f"Фокусная ниша: '{category_hint.strip()}'.\n"
        else:
            chosen_domain = random.choice(DIVERSE_TOPIC_DOMAINS)  # noqa: S311
            prompt += f"Случайная фокусная ниша для вдохновения: {chosen_domain}.\n"

        if previous_topic and previous_topic.strip():
            prompt += (
                f"КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО повторять или предлагать тему, похожую на предыдущую: "
                f"'{previous_topic.strip()}'. Придумай тему из совершенно другой области!\n"
            )

        prompt += (
            "Обязательное условие: Не ограничивайся анатомией человека или биологией. "
            "Тема должна быть свежей, неожиданной и провоцирующей живой интерес зрителей."
        )

        raw_temp = temperature if temperature is not None else 1.05
        eff_temp = min(2.0, max(0.0, float(raw_temp)))

        config = types.GenerateContentConfig(
            system_instruction=SINGLE_TOPIC_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=TopicSuggestion,
            temperature=eff_temp,
        )

        limiter = get_gemini_rate_limiter()
        loop = asyncio.get_running_loop()
        max_retries = 4

        for attempt in range(max_retries):
            try:
                await limiter.acquire()
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
                return TopicSuggestion.model_validate(data)
            except Exception as exc:
                err_msg = str(exc)
                is_429 = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
                is_transient = is_429 or "503" in err_msg or "UNAVAILABLE" in err_msg
                if is_transient and attempt < max_retries - 1:
                    if is_429:
                        await limiter.record_429_backoff(attempt)
                    else:
                        delay = 2.5 * (2**attempt)
                        await asyncio.sleep(delay)
                else:
                    logger.error("Failed to suggest topic: %s", exc)
                    raise exc

        raise RuntimeError("Failed to suggest topic from Gemini.")

    async def suggest_batch_topics(
        self,
        count: int = 10,
        category_hint: str | None = None,
        language: str = "ru",
        temperature: float | None = None,
    ) -> BatchTopicList:
        """Suggest N distinct, non-overlapping viral topics in a SINGLE Gemini API request."""
        count = max(2, min(20, count))
        api_key = self.config.effective_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        prompt = (
            f"Сгенерируй ровно {count} уникальных, неповторяющихся тем для викторин "
            f"на языке: '{language}'.\n"
            f"Каждая тема ОБЯЗАТЕЛЬНО должна относиться к совершенно другой категории\n"
            f"(например: космос, видеоигры, история, природа, кино, криминалистика, технологии).\n"
            f"Ни в коем случае не делай упор на одну лишь анатомию или медицину!"
        )
        if category_hint and category_hint.strip():
            prompt += (
                f"\nДополнительное пожелание по нише: '{category_hint.strip()}' "
                f"(при этом темы между собой должны сильно различаться)."
            )

        raw_temp = temperature if temperature is not None else 1.05
        eff_temp = min(2.0, max(0.0, float(raw_temp)))

        config = types.GenerateContentConfig(
            system_instruction=BATCH_TOPIC_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=BatchTopicList,
            temperature=eff_temp,
        )

        limiter = get_gemini_rate_limiter()
        loop = asyncio.get_running_loop()
        max_retries = 4

        for attempt in range(max_retries):
            try:
                await limiter.acquire()
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
                return BatchTopicList.model_validate(data)
            except Exception as exc:
                err_msg = str(exc)
                is_429 = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg
                is_transient = is_429 or "503" in err_msg or "UNAVAILABLE" in err_msg
                if is_transient and attempt < max_retries - 1:
                    if is_429:
                        await limiter.record_429_backoff(attempt)
                    else:
                        delay = 2.5 * (2**attempt)
                        await asyncio.sleep(delay)
                else:
                    logger.error("Failed to suggest batch topics: %s", exc)
                    raise exc

        raise RuntimeError("Failed to suggest batch topics from Gemini.")

    async def _verify_and_refine_facts(
        self, challenge: QuizChallenge, language: str
    ) -> QuizChallenge:
        """Run strict secondary fact-checking pass to correct inaccuracies and myths."""
        logger.info("Running secondary strict fact-checking pass on 9-question challenge...")
        api_key = self.config.effective_api_key.get_secret_value()
        client = genai.Client(api_key=api_key)

        prompt = (
            f"Проведи строгий научный аудит этой викторины из 9 вопросов на языке '{language}'.\n"
            f"Убедись, что все вопросы однозначны, а факты строго соответствуют науке и истории.\n"
            f"Искорени любые мифы и обеспечь соблюдение лимитов длины.\n"
            f"Исходный JSON викторины:\n{challenge.model_dump_json()}"
        )

        raw_temp = self.config.verifier_temperature
        eff_temp = min(2.0, max(0.0, float(raw_temp)))

        config = types.GenerateContentConfig(
            system_instruction=FACT_CHECK_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=QuizChallenge,
            temperature=eff_temp,
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
        do_fact_check = self.config.fact_check_enabled if fact_check is None else fact_check
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
                            item.image_url = img_results[0].get("image") or img_results[0].get(
                                "thumbnail"
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
                        image_tasks.append(self._download_and_verify_url(item.image_url, dest))
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
            "question_text (<=65 символов), correct_answer (<=25 символов), "
            "fun_fact (<=90 символов), image_query (поисковый запрос на английском)."
        )

        raw_temp = temperature if temperature is not None else self.config.creative_temperature
        eff_temp = min(2.0, max(0.0, float(raw_temp)))

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
        new_items_by_num: dict[int, QuizItem] = {item.question_number: item for item in new_items}

        # If any requested question_number was missing from response, assign unmatched sequentially
        unmatched_new = [item for item in new_items if item.question_number not in target_nums]
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
                        item.image_url = img_results[0].get("image") or img_results[0].get(
                            "thumbnail"
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

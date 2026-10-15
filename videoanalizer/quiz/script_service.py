"""ScriptService: Generates structured 9-question 3-tier trivia challenges via Gemini REST API."""

import asyncio
import io
import json
import logging
import random
from pathlib import Path
from typing import TypeVar

from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel

from videoanalizer.quiz.config import QuizConfig, get_quiz_config
from videoanalizer.quiz.image_service import ImageService
from videoanalizer.quiz.models import (
    BatchTopicList,
    DifficultyTier,
    QuizChallenge,
    QuizItem,
    RegeneratedQuestionsPayload,
    TopicSuggestion,
    VisualDifficulty,
    VisualQuizDataset,
    VisualQuizInterstitial,
    VisualQuizInterstitialType,
    VisualQuizItem,
)
from videoanalizer.quiz.rate_limiter import get_gemini_rate_limiter
from videoanalizer.quiz.workspace import QuizWorkspace

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

RANDOM_QUIZ_ANGLES = [
    "общая эрудиция и кругозор с вопросами на логику и смекалку",
    "культовые видеоигры разных лет (персонажи, миры, сюжеты, предметы)",
    "мировое кино, культовые сериалы и мультипликация",
    "космос, планеты и устройство Вселенной",
    "необычная география, страны мира, океаны и рекорды планеты",
    "мировая история, древние цивилизации и великие открытия",
    "физика, химия и природные явления вокруг нас",
    "технологии, интернет, компьютеры и культовые гаджеты",
    "еда, напитки, специи и кулинария разных стран",
    "автомобили, авиация и легендарная техника",
    "поп-культура, музыкальная индустрия и мировые хиты",
    "литература, мифология и культовые книжные вселенные",
    "спорт, Олимпийские игры и невероятные мировые рекорды",
    "деньги, мировые бренды и история знаменитых вещей",
    "живая природа, редкие животные и экстремальное выживание",
]

SINGLE_TOPIC_SYSTEM_PROMPT = """Ты — креативный продюсер вирусных вертикальных видео-викторин (Shorts, TikTok, Reels) в формате «лестница из 9 вопросов».
Твоя задача — придумать ОДНУ понятную, широкую и азартную тему для интерактивной текстовой викторины.

ГЛАВНЫЕ ПРАВИЛА ФОРМАТА:
1. ЭТО ИНТЕРАКТИВНЫЙ ТЕСТ НА ЭРУДИЦИЮ, А НЕ СТАТЬЯ С ФАКТАМИ:
   - Зрителю задают 9 открытых вопросов, дают 3 секунды на ответ в уме, после чего показывают правильный ответ.
   - СТРОЖАЙШЕ ЗАПРЕЩЕНЫ заголовки в стиле познавательных роликов или топ-списков:
     ❌ «Сумасшедшие законы разных стран»
     ❌ «10 шокирующих фактов о космосе»
     ❌ «Странные привычки гениев»

2. ПОЛНЫЙ ЗАПРЕТ НА ФОРМАТ «ПРАВДА / ЛОЖЬ» И «ДА / НЕТ»:
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ темы со словами «Правда или ложь», «Факт или вымысел», «Миф или реальность», «Отличи X от Y».
   - Ответ на каждый из 9 вопросов ОБЯЗАН быть конкретным существительным, именем, термином, названием или числом (1-3 слова), а не «Да/Нет» или «Правда/Ложь».

3. ОТКАЗ ОТ УЗКИХ ШАБЛОНОВ И КРИВЫХ КОНСТРУКЦИЙ:
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО заставлять зрителя угадывать объект по одной узкой фишке (❌ «Угадай героя по слабости», ❌ «Угадай машину по скрытой фишке», ❌ «Угадай фильм по детали»).
   - Тема должна задавать ПОНЯТНУЮ И ШИРОКУЮ ТЕМУ/ВСЕЛЕННУЮ, внутри которой легко задать 9 совершенно РАЗНЫХ вопросов (кто, где, какой предмет, в каком году, какое вещество и т.д.).

4. ОБРАЗЦЫ ПРАВИЛЬНЫХ ТЕМ:
   ✓ «Тест на эрудицию: вопросы, где ошибаются 90% людей»
   ✓ «Викторина для геймеров: от простых игр до хардкора»
   ✓ «Тест по географии: знаешь ли ты нашу планету?»
   ✓ «Школьная физика и химия: вспомнишь базу?»
   ✓ «Викторина по культовым фильмам и сериалам»
   ✓ «Тест по космосу: от Солнечной системы до черных дыр»
   ✓ «Викторина по истории: события, изменившие мир»
   ✓ «Тест для киноманов: вселенная Marvel и DC»
   ✓ «Еда и кулинария: знаешь ли ты, что на твоей тарелке?»
   ✓ «Тест на общую эрудицию: пройдешь все 9 уровней?»
   ✓ «Викторина по автомобилям и легендарной технике»
   ✓ «Тест по миру интернета, технологий и гаджетов»

5. ГРАМОТНОСТЬ И ЕСТЕСТВЕННОСТЬ ЯЗЫКА:
   - Пиши на чистом, естественном, грамотном русском языке без кривого сленга (никаких «выживач»), опечаток (никаких «узовешь») и корявых машинных переводов.
   - Заголовок темы должен быть простым, понятным за 1 секунду скролла и охватывать тему, где зритель может проверить свои реальные знания.

6. ТОЛЬКО ТЕКСТОВАЯ МЕХАНИКА ВОПРОСОВ (ВАЖНО!):
   - На этапе вопроса зритель видит ТОЛЬКО текст (без картинок-загадок и без звука треков). Картинка появляется только вместе с готовым ответом!
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО предлагать темы, где для ответа нужно смотреть на картинку или слушать аудио:
     ❌ «Угадай бренд по логотипу / собаку по силуэту / страну по флагу / актера по фото»
     ❌ «Угадай песню по мелодии / группу по риффу / игру по звуку»
   - Запрещены унылые школьные банальности («Столицы мира», «Таблица умножения») и анатомия/медицина (если пользователь явно не попросил).

7. ЛИМИТЫ И СХЕМА:
   - 'topic': Название темы в формате вызова/игры (strictly <= 65 characters).
   - 'category': Краткое название ниши (strictly <= 35 characters).
   - 'curiosity_hook': Короткий вопрос-байт для удержания зрителя (strictly <= 100 characters).
   - Верни строго валидный JSON по схеме TopicSuggestion."""


BATCH_TOPIC_SYSTEM_PROMPT = """Ты — креативный продюсер вирусных вертикальных видео-викторин (Shorts, TikTok, Reels) в формате «лестница из 9 вопросов».
Твоя задача — придумать пакет из N уникальных, неповторяющихся тем для интерактивных текстовых викторин.

ГЛАВНЫЕ ПРАВИЛА ФОРМАТА:
1. КАЖДАЯ ТЕМА — ЭТО ИНТЕРАКТИВНЫЙ ТЕСТ НА ЭРУДИЦИЮ:
   - Запрещены заголовки документалок и статей («Тайны океана...», «Невероятные факты о...», «Странные законы...»).
   - Каждая тема должна звучать как игра или тест на эрудицию с 9 открытыми вопросами.

2. ПОЛНЫЙ ЗАПРЕТ НА ФОРМАТ «ПРАВДА / ЛОЖЬ» И «ДА / НЕТ»:
   - СТРОЖАЙШЕ ЗАПРЕЩЕНЫ темы со словами «Правда или ложь», «Факт или вымысел», «Миф или реальность», «Отличи X от Y».
   - Ответ на каждый вопрос обязан быть конкретным существительным, именем, термином или числом (1-3 слова).

3. ШИРОКИЕ ТЕМЫ ВМЕСТО УЗКИХ ШАБЛОНОВ:
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать узкие шаблоны вроде «Угадай героя по слабости», «Угадай автомобиль по фишке», «Назови фильм по детали».
   - Тема должна задавать ПОНЯТНУЮ И ШИРОКУЮ ТЕМУ/ВСЕЛЕННУЮ, внутри которой легко задать 9 разноплановых вопросов (кто, где, какой предмет, в каком году, какое вещество и т.д.).

4. ОБРАЗЦЫ ПРАВИЛЬНЫХ ТЕМ:
   ✓ «Тест на эрудицию: вопросы, где ошибаются 90% людей»
   ✓ «Викторина для геймеров: от простых игр до хардкора»
   ✓ «Тест по географии: знаешь ли ты нашу планету?»
   ✓ «Школьная физика и химия: вспомнишь базу?»
   ✓ «Викторина по культовым фильмам и сериалам»
   ✓ «Тест по космосу: от Солнечной системы до черных дыр»
   ✓ «Викторина по истории: события, изменившие мир»
   ✓ «Тест для киноманов: вселенная Marvel и DC»
   ✓ «Еда и кулинария: знаешь ли ты, что на твоей тарелке?»
   ✓ «Тест на общую эрудицию: пройдешь все 9 уровней?»
   ✓ «Викторина по автомобилям и легендарной технике»
   ✓ «Тест по миру интернета, технологий и гаджетов»

5. ГРАМОТНОСТЬ И ЕСТЕСТВЕННОСТЬ ЯЗЫКА:
   - Пиши на чистом, естественном, грамотном русском языке без кривого сленга, опечаток и корявых машинных переводов.
   - Заголовок темы должен быть простым и понятным за 1 секунду.

6. ЗАПРЕТ НА ВИЗУАЛЬНЫЕ И АУДИО-ЗАГАДКИ:
   - В викторине вопрос задается ТОЛЬКО текстом, а картинка всплывает лишь при показе ответа.
   - СТРОГО ЗАПРЕЩЕНЫ темы вроде «Угадай по логотипу / фото / силуэту / флагу / кадру» или «Угадай песню по звуку / треку».
   - Запрет на анатомию, медицину и скучные школьные банальности («Столицы стран»).

7. ПРАВИЛО РАЗНООБРАЗИЯ (ЗАВИСИТ ОТ ЗАПРОСА ПОЛЬЗОВАТЕЛЯ):
   - Если пользователь НЕ задал конкретную нишу: каждая из N тем ОБЯЗАНА принадлежать к совершенно разной сфере жизни (не более 1 темы на категорию).
   - Если пользователь ЗАДАЛ конкретную нишу: все N тем должны быть внутри этой ниши, но охватывать разные аспекты (история, персонажи, культовые части, термины, рекорды) без узких шаблонных механик и без самоповторов.

8. ЛИМИТЫ И СХЕМА:
   - Сгенерируй ровно запрошенное количество тем (count).
   - 'topic': strictly <= 65 characters.
   - 'category': strictly <= 35 characters.
   - 'curiosity_hook': strictly <= 100 characters.
   - Верни строго валидный JSON по схеме BatchTopicList."""


QUIZ_SYSTEM_PROMPT = """Ты — элитный сценарист вирусных викторин для TikTok и YouTube Shorts в формате прогрессивной лестницы из 9 вопросов.

ПРАВИЛА И ОГРАНИЧЕНИЯ ФОРМАТА:
1. Механика Open-Recall (Без вариантов ответа A/B/C/D):
   - Зритель читает короткий вопрос, думает 3 секунды и называет ответ вслух, после чего правильный ответ и его иллюстрация всплывают на экране.
   - Каждый вопрос обязан иметь ОДИН четкий, бесспорный и конкретный ответ (1-3 слова).
   - Вопрос должен работать чисто текстом: не пиши «Кто изображен на фото?» или «Чей это логотип?», так как фото появится только вместе с ответом!
   - Фильтр банальности: строжайше запрещены заезженные вопросы («какая планета красная», «самое быстрое животное — гепард», «сколько сердец у осьминога», «столица Франции»).

2. Строгая прогрессивная лестница (3 уровня по 3 вопроса):
   - Уровень 1 (Разминка — вопросы 1, 2, 3, theme_color '#22C55E'):
     Доступные, но интересные вопросы с мгновенным узнаванием, чтобы вовлечь 90% зрителей за первые секунды.
   - Уровень 2 (Когнитивные ловушки — вопросы 4, 5, 6, theme_color '#F59E0B'):
     Контринтуитивные вопросы, частые заблуждения, эффекты Манделы и вопросы с подвохом, где интуитивный ответ оказывается неверным.
   - Уровень 3 (Хардкор — вопросы 7, 8, 9, theme_color '#EF4444'):
     Сложные вопросы для 1% экспертов, парадоксальные детали и редкие факты, провоцирующие жаркие споры в комментариях.

3. Жесткие лимиты длины (Layout Guard):
   - 'question_text': прямой, плотный вопрос без воды, strictly <= 65 characters (never exceed 80 characters).
   - 'correct_answer': точный ответ (1-3 слова), strictly <= 25 characters (never exceed 35 characters).
   - 'fun_fact': панчлайн или удивительное пояснение к ответу для озвучки, strictly <= 90 characters.
   - 'image_query': точный поисковый запрос на АНГЛИЙСКОМ языке (2-5 слов), описывающий конкретный физический объект, персонажа или сцену из правильного ответа для поиска картинки (например: для 'Вольфрам' -> 'glowing tungsten filament bulb', для 'Марио' -> 'Super Mario Nintendo character'). Избегай абстрактных слов.

4. Формат вывода:
   - Верни строго валидный JSON в соответствии со схемой QuizChallenge."""


FACT_CHECK_SYSTEM_PROMPT = """Ты — главный редактор и строгий верификатор контента для викторин.
Твоя задача — проверить и при необходимости исправить викторину из 9 вопросов.

ПРАВИЛА АУДИТА:
1. Проверка достоверности (Наука + Канон поп-культуры):
   - Для научных, исторических и бытовых тем: проверяй факты по энциклопедическим источникам. Безжалостно исправляй развенчанные мифы («человек использует 10% мозга», «Великую стену видно из космоса», «зоны вкуса на языке», «хамелеон меняет цвет для маскировки»).
   - Для тем по видеоиграм, кино, сериалам и книгам: проверяй строгую точность по официальному канону и лору вселенной (имена, механики, даты выхода, сюжетные детали).
   - Если вопрос содержит фактическую ошибку или миф, перепиши его или разверни так, чтобы он разоблачал этот миф.

2. Однозначность и текстовая самодостаточность:
   - Убедись, что на каждый вопрос существует только один точный ответ без двусмысленности.
   - Убедись, что вопрос не требует от зрителя видеть картинку до появления ответа.

3. Сохранение жестких лимитов верстки:
   - 'question_text': strictly <= 65 characters (never exceed 80 characters).
   - 'correct_answer': 1-4 слова, strictly <= 25 characters (never exceed 35 characters).
   - 'fun_fact': strictly <= 90 characters.
   - 'image_query': конкретный англоязычный запрос (2-5 слов), наглядно изображающий правильный ответ.
   - Сохраняй структуру: 3 уровня по 3 вопроса (1-3, 4-6, 7-9) и их цвета.

4. Формат вывода:
   - Верни строго валидный JSON в соответствии со схемой QuizChallenge."""


REGENERATE_QUESTIONS_SYSTEM_PROMPT = """Ты — элитный сценарист вирусных викторин для TikTok и YouTube Shorts.
Твоя задача — сгенерировать замену ТОЛЬКО для указанных номеров вопросов в существующей викторине.

ПРАВИЛА ЗАМЕНЫ:
1. Строгое попадание в уровень сложности:
   - Номера 1, 2, 3 -> Уровень 1 (Разминка), difficulty 'easy', tier_index 1. Быстрые и вовлекающие.
   - Номера 4, 5, 6 -> Уровень 2 (Ловушки), difficulty 'medium', tier_index 2. С подвохом.
   - Номера 7, 8, 9 -> Уровень 3 (Хардкор), difficulty 'hard', tier_index 3. Для настоящих знатоков.

2. Полный запрет на дублирование (Anti-Duplication):
   - В запросе передан список СОХРАНЕННЫХ вопросов (KEPT). Категорически запрещено повторять их ответы, объекты, персонажей или смежные факты.
   - Вопрос должен быть полностью понятен из текста (без опоры на картинку до ответа) и не содержать школьных банальностей.

3. Жесткие лимиты длины:
   - 'question_text': strictly <= 65 characters (never exceed 80 characters).
   - 'correct_answer': 1-3 слова, strictly <= 25 characters (never exceed 35 characters).
   - 'fun_fact': strictly <= 90 characters.
   - 'image_query': конкретный запрос на английском языке (2-5 слов), иллюстрирующий правильный ответ."""


RANDOM_VISUAL_QUIZ_THEMES = [
    "Суперкары и легендарные автомобили",
    "Культовые логотипы мировых брендов",
    "Флаги необычных стран и территорий",
    "Оружие и предметы из культовых видеоигр",
    "Породы собак и редкие животные",
    "Архитектурные шедевры и памятники мира",
    "Космические корабли и техника из кино",
    "Персонажи ретро-игр 90-х и 2000-х",
    "Музыкальные инструменты народов мира",
    "Эмблемы мировых футбольных клубов",
    "Символы супергероев Marvel и DC",
    "Культовые кроссовки в истории сникер-культуры",
]

VISUAL_QUIZ_SYSTEM_PROMPT = """Ты — креативный сценарист вирусных вертикальных викторин в формате «Visual Image Quiz» (Shorts, TikTok, Reels).
Зритель смотрит на быстро сменяющиеся картинки, а затем последовательно угадывает 10 предметов по фото/логотипам с нарастающей сложностью.

СТРУКТУРА СЦЕНАРИЯ:
1. Ровно 10 предметов:
   - Предметы 1..3: difficulty="easy" (максимально узнаваемые предметы или силуэты).
   - Предметы 4..6: difficulty="medium" (предметы, знакомые любителям темы).
   - Предметы 7..9: difficulty="hard" (сложные предметы для экспертов).
   - Предмет 10: difficulty="master" (редкий или спорный предмет — коммент-ловушка).

2. ТРЕБОВАНИЯ К ОЗВУЧКЕ ДИКТОРА (TTS):
   - Вопрос 1: диктор СРАЗУ задает вопрос БЕЗ слов «Вопрос номер один» (например: «Что это?», «Узнаешь модель?», «Что за логотип?»).
   - Вопросы 2..9: диктор объявляет номер (например: «Номер два, что это?», «Вопрос три, как называется?»).
   - Вопрос 10: правильный ответ намеренно скрывается. В поле 'answer_text' строго пиши: "Пиши в коммы". В поле 'answer_tts' диктор интригующе призывает зрителей писать свои догадки в комментариях (например: «А это самый сложный! Напиши свой ответ в комментариях!»).
   - Все реплики диктора должны быть краткими, энергичными и без лишней воды (до 15 слов на реплику).

3. ПОИСКОВЫЕ ЗАПРОСЫ КАРТИНОК ('image_query'):
   - Для каждого предмета составь точный поисковый запрос (лучше на английском с ключевыми словами isolated, transparent logo, front view, icon) для нахождения четкого изображения без фона или на чистом фоне.

4. ИНТРО-ХУК ('hook_tts'):
   - Энергичная интригующая фраза на 3-3.5 секунды, представляющая тему и бросающая вызов зрителю (например: «Угадай все эти суперкары! На десятый ответят только настоящие знатоки. Погнали, что это?»).

5. ВСТАВКИ ('interstitials'):
   - после вопроса 3: type="comment_bait", tts_text="Зажми кнопку комментариев и отправь свой смайлик!"
   - после вопроса 6: type="share_bait", tts_text="Перешли это видео другу, который шарит так же!"

Верни строго валидный JSON по схеме VisualQuizDataset."""


class ScriptService:
    """Service responsible for generating quiz trivia content using Gemini REST API."""

    def __init__(
        self,
        image_service: ImageService | None = None,
        config: QuizConfig | None = None,
        client: genai.Client | None = None,
    ) -> None:
        self.config = config or get_quiz_config()
        self.image_service = image_service or ImageService()
        if client is not None:
            self._client = client
        else:
            api_key = self.config.effective_api_key.get_secret_value()
            self._client = genai.Client(api_key=api_key)

    async def _generate_structured(
        self,
        prompt: str,
        system_instruction: str,
        response_schema: type[T],
        temperature: float | None = None,
    ) -> T:
        """Unified structured generation method using native async Client.aio with retries and rate limiter."""
        raw_temp = temperature if temperature is not None else self.config.creative_temperature
        eff_temp = min(2.0, max(0.0, float(raw_temp)))

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=eff_temp,
        )

        limiter = get_gemini_rate_limiter()
        max_retries = 4
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                await limiter.acquire()
                response = await self._client.aio.models.generate_content(
                    model=self.config.gemini_model,
                    contents=prompt,
                    config=config,
                )
                raw_text = response.text or "{}"
                data = json.loads(raw_text)
                return response_schema.model_validate(data)
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

    async def _call_gemini(
        self, topic: str, language: str, temperature: float | None = None
    ) -> QuizChallenge:
        """Execute Gemini API call with structured Pydantic v2 schema."""
        prompt = (
            f"Тема викторины: «{topic}».\n"
            f"Язык: {language}.\n"
            f"Сгенерируй викторину-лестницу из 9 открытых вопросов (Уровень 1: Разминка, Уровень 2: Ловушки, Уровень 3: Хардкор). "
            f"Вопросы должны быть строго текстовыми, нетривиальными и иметь однозначный краткий ответ (1-3 слова)."
        )
        return await self._generate_structured(
            prompt=prompt,
            system_instruction=QUIZ_SYSTEM_PROMPT,
            response_schema=QuizChallenge,
            temperature=temperature,
        )

    async def suggest_topic(
        self,
        category_hint: str | None = None,
        language: str = "ru",
        temperature: float | None = None,
        previous_topic: str | None = None,
    ) -> TopicSuggestion:
        """Suggest a single viral, non-trivial quiz topic using Gemini REST API."""
        prompt_lines = [
            f"Язык: {language}.",
            "Придумай 1 широкую, понятную и увлекательную тему для интерактивной текстовой викторины из 9 вопросов.",
        ]
        if category_hint and category_hint.strip():
            prompt_lines.append(
                f"Обязательное направление от пользователя: «{category_hint.strip()}». "
                f"Сделай из него широкую тему для теста на эрудицию (без узких шаблонов и без 'правда/ложь')."
            )
        else:
            angle = random.choice(RANDOM_QUIZ_ANGLES)  # noqa: S311
            prompt_lines.append(
                f"Вектор для вдохновения (придумай широкую тему в этой сфере): «{angle}»."
            )

        if previous_topic and previous_topic.strip():
            prompt_lines.append(
                f"КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО повторять или брать тему, смежную с предыдущей: «{previous_topic.strip()}»."
            )

        prompt = "\n".join(prompt_lines)
        temp = temperature if temperature is not None else 1.05
        return await self._generate_structured(
            prompt=prompt,
            system_instruction=SINGLE_TOPIC_SYSTEM_PROMPT,
            response_schema=TopicSuggestion,
            temperature=temp,
        )

    async def suggest_batch_topics(
        self,
        count: int = 10,
        category_hint: str | None = None,
        language: str = "ru",
        temperature: float | None = None,
    ) -> BatchTopicList:
        """Suggest N distinct, non-overlapping viral topics in a SINGLE Gemini API request."""
        count = max(2, min(20, count))
        prompt_lines = [
            f"Язык: {language}.",
            f"Сгенерируй ровно {count} уникальных тем для интерактивных текстовых викторин из 9 вопросов.",
        ]
        if category_hint and category_hint.strip():
            prompt_lines.append(
                f"Все {count} тем должны быть внутри ниши «{category_hint.strip()}», "
                f"но каждая обязана охватывать разные аспекты темы (история, персонажи, культовые части, термины, рекорды) "
                f"без узких шаблонов и без самоповторов."
            )
        else:
            prompt_lines.append(
                "Каждая из тем обязана относиться к совершенно разной жизненной, научной или поп-культурной категории (максимальный разброс ниш)."
            )

        prompt = "\n".join(prompt_lines)
        temp = temperature if temperature is not None else 1.05
        return await self._generate_structured(
            prompt=prompt,
            system_instruction=BATCH_TOPIC_SYSTEM_PROMPT,
            response_schema=BatchTopicList,
            temperature=temp,
        )

    async def _verify_and_refine_facts(
        self, challenge: QuizChallenge, language: str
    ) -> QuizChallenge:
        """Run strict secondary fact-checking pass to correct inaccuracies and myths."""
        logger.info("Running secondary strict fact-checking pass on 9-question challenge...")
        prompt = (
            f"Язык викторины: {language}.\n"
            f"Проведи строгий аудит достоверности (по науке или официальному канону/лору), однозначности ответов и лимитов длины символов.\n"
            f"Исходный JSON:\n{challenge.model_dump_json()}"
        )
        try:
            verified = await self._generate_structured(
                prompt=prompt,
                system_instruction=FACT_CHECK_SYSTEM_PROMPT,
                response_schema=QuizChallenge,
                temperature=self.config.verifier_temperature,
            )
            logger.info("Fact-checking verifier pass completed successfully.")
            return verified
        except Exception as exc:
            logger.warning(
                "Fact-checking verifier pass encountered an error, falling back to original: %s",
                exc,
            )
            return challenge

    async def _resolve_preview_images(self, questions: list[QuizItem]) -> None:
        """Resolve candidate preview image URLs in parallel for items that have image_query and no image_url."""
        candidates = [q for q in questions if q.image_query and not q.image_url]
        if not candidates:
            return

        async def _fetch(item: QuizItem) -> None:
            try:
                img_results = await self.image_service._search_image_urls(
                    item.image_query, max_results=2
                )
                if img_results:
                    item.image_url = img_results[0].get("image") or img_results[0].get("thumbnail")
            except Exception as e:
                logger.debug("Failed to resolve preview image for '%s': %s", item.image_query, e)

        await asyncio.gather(*[_fetch(item) for item in candidates], return_exceptions=True)

    async def generate_quiz(
        self,
        topic: str,
        language: str = "ru",
        workspace: QuizWorkspace | None = None,
        creative_temperature: float | None = None,
        fact_check: bool | None = None,
    ) -> QuizChallenge:
        """Generate 9-question trivia challenge and download visual assets if applicable."""
        logger.info("Generating 9-question quiz challenge for topic: '%s' (lang=%s)", topic, language)
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

        # Resolve image preview URLs in parallel for visual questions (allowing user approval in UI)
        if workspace is None:
            await self._resolve_preview_images(challenge.all_questions())

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

    def _save_image_thread(self, raw_bytes: bytes, dest_path: Path) -> Path | None:
        """Synchronous helper running in worker thread to process and save PIL image."""
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img = img.convert("RGBA")
                img.save(dest_path, "PNG")
            return dest_path
        except Exception as e:
            logger.warning("Failed to save image from URL to %s: %s", dest_path, e)
            return None

    async def _download_and_verify_url(self, url: str, dest_path: Path) -> Path | None:
        """Download image from direct URL and verify/save it in a background thread."""
        raw_bytes = await self.image_service._download_bytes(url)
        if raw_bytes:
            return await asyncio.to_thread(self._save_image_thread, raw_bytes, dest_path)
        return None

    async def _call_gemini_regenerate(
        self,
        challenge: QuizChallenge,
        question_numbers: list[int],
        temperature: float | None = None,
    ) -> list[QuizItem]:
        """Call Gemini to regenerate specifically requested question numbers."""
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
            f"Тема викторины: «{challenge.topic}». Язык: {challenge.language}.\n"
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

        payload = await self._generate_structured(
            prompt=prompt,
            system_instruction=REGENERATE_QUESTIONS_SYSTEM_PROMPT,
            response_schema=RegeneratedQuestionsPayload,
            temperature=temperature,
        )
        return payload.questions

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

        # Resolve candidate preview image URLs in parallel for visual questions
        await self._resolve_preview_images(list(new_items_by_num.values()))

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

        # Secondary fact-checking pass if requested
        do_fact_check = self.config.fact_check_enabled if fact_check is None else fact_check
        if do_fact_check:
            challenge = await self._verify_and_refine_facts(challenge, challenge.language)

        logger.info(
            "Successfully regenerated %d questions in challenge.",
            len(new_items_by_num),
        )
        return challenge

    async def generate_visual_quiz_dataset(
        self,
        theme: str | None = None,
        language: str = "ru",
        auto_search_images: bool = True,
        temperature: float | None = None,
    ) -> VisualQuizDataset:
        """Generate a complete Visual Image Quiz dataset with 10 questions and optional image search."""
        chosen_theme = theme.strip() if theme and theme.strip() else random.choice(RANDOM_VISUAL_QUIZ_THEMES)

        prompt = (
            f"Тема визуальной викторины: «{chosen_theme}».\n"
            f"Язык озвучки и интерфейса: {language}.\n"
            f"Сгенерируй вирусный сценарий из 10 предметов с нарастающей сложностью (3 easy, 3 medium, 3 hard, 1 master-ловушка). "
            f"Для вопроса 1 диктор сразу задает вопрос без фразы 'Вопрос 1'. Для вопроса 10 ответ скрыт с призывом писать в комментарии."
        )

        dataset = await self._generate_structured(
            prompt=prompt,
            system_instruction=VISUAL_QUIZ_SYSTEM_PROMPT,
            response_schema=VisualQuizDataset,
            temperature=temperature,
        )

        # Force structural integrity
        dataset.theme = chosen_theme
        dataset.mode = "visual_image_quiz"

        # Sanitize question 1 to ensure no "Вопрос номер один" prefix
        if dataset.items:
            q1_prompt = dataset.items[0].prompt_tts
            for prefix in ("Вопрос номер один,", "Вопрос номер 1,", "Вопрос 1,", "Вопрос один,"):
                if q1_prompt.startswith(prefix):
                    dataset.items[0].prompt_tts = q1_prompt[len(prefix):].strip()

        # Sanitize question 10 cliffhanger
        if len(dataset.items) >= 10:
            dataset.items[9].answer_text = "Пиши в коммы"
            dataset.items[9].difficulty = VisualDifficulty.MASTER

        # Search candidate images if requested
        if auto_search_images:
            await self._resolve_visual_quiz_images(dataset)

        logger.info(
            "Successfully generated VisualQuizDataset for theme '%s' with %d items.",
            chosen_theme,
            len(dataset.items),
        )
        return dataset

    async def _resolve_visual_quiz_images(self, dataset: VisualQuizDataset) -> None:
        """Find candidate image URLs for visual quiz items via ImageService."""
        async def _fetch_item_image(item: VisualQuizItem) -> None:
            if item.image_url:
                return
            try:
                candidates = await self.image_service._search_image_urls(item.image_query, max_results=3)
                if candidates:
                    for cand in candidates:
                        url = cand.get("image") or cand.get("thumbnail")
                        if url:
                            item.image_url = url
                            break
            except Exception as err:
                logger.warning("Failed to auto-search image for '%s': %s", item.image_query, err)

        await asyncio.gather(*[_fetch_item_image(it) for it in dataset.items])


"""ScriptService: Generates structured 9-question 3-tier trivia challenges via Gemini REST API."""

import asyncio
import io
import json
import logging
import random
import re
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
    VisualTopicSuggestion,
    AssetDisplayMode,
    WidescreenIntroConfig,
    WidescreenOutroConfig,
    WidescreenQuizDataset,
    WidescreenQuizItem,
    WidescreenQuizRound,
    WidescreenScoreTier,
)
from videoanalizer.quiz.exclusions_service import QuizExclusionsManager
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

RANDOM_VISUAL_QUIZ_THEMES_EN = [
    "World's Most Iconic Brand Logos",
    "Supercars and Legendary Sports Cars",
    "World Flags and Famous Emblems",
    "Iconic Video Game Weapons and Items",
    "Rare Dog Breeds and Exotic Animals",
    "World Architectural Landmarks and Wonders",
    "Legendary Spaceships and Sci-Fi Tech",
    "Classic 90s and 2000s Retro Game Heroes",
    "Premier League and World Football Badges",
    "Iconic Marvel and DC Superhero Emblems",
    "Legendary Sneakers in Streetwear History",
]

VISUAL_QUIZ_SYSTEM_PROMPT = """Ты — креативный сценарист вирусных вертикальных викторин в формате «Visual Image Quiz» (Shorts, TikTok, Reels).
Зритель смотрит на быстро сменяющиеся картинки в интро (rapid center flip), а затем последовательно угадывает 10 предметов/вопросов по визуальному материалу с нарастающей сложностью.

СТРУКТУРА СЦЕНАРИЯ (СТРОГО 10 ПРЕДМЕТОВ):
- Предметы 1..3: difficulty="easy" (максимально узнаваемые, доступные 95% зрителей).
- Предметы 4..6: difficulty="medium" (знакомые любителям и фанатам темы).
- Предметы 7..9: difficulty="hard" (сложные для экспертов, редкие или культовые детали).
- Предмет 10: difficulty="master" (кульминация/клиффхэнгер: ответ скрыт в комменты).

ОСНОВНЫЕ ПРАВИЛА:

1. СТРОГОЕ СОБЛЮДЕНИЕ ПОЛЬЗОВАТЕЛЬСКОГО СПИСКА (USER-PROVIDED ITEMS):
   - Если пользователь в описании темы перечислил конкретные предметы/вопросы по уровням (например: Easy: A, B, C; Medium: D, E, F; Hard: G, H, I; Master: J):
     ТЫ ОБЯЗАН СТРОГО И ТОЧНО ИСПОЛЬЗОВАТЬ ИМЕННО ЭТИ ПРЕДМЕТЫ для соответствующих позиций 1..10!
   - Если для позиции указан выбор (например: «Energy Sword (Halo) или AWP Dragon Lore (CS2)»), выбери один из них.
   - Запрещено заменять предметы пользователя своими или игнорировать предложенные примеры.

2. РАЗЛИЧЕНИЕ ВИЗУАЛЬНОГО ОБЪЕКТА И ПРАВИЛЬНОГО ОТВЕТА («УГАДАЙ X ПО Y»):
   - Если викторина устроена по принципу косвенного угадывания (например: «Угадай игру по оружию», «Угадай фильм по кадру/предмету», «Угадай персонажа по силуэту/атрибуту»):
     - В поле 'image_query': пиши точный англоязычный поисковый запрос ПОКАЗЫВАЕМОГО ВИЗУАЛЬНОГО ОБЪЕКТА с названием игры/вселенной (например: "Minecraft diamond sword", "Portal gun", "Pokeball", "God of War Blades of Chaos", "Assassin's Creed Hidden Blade", "Half-Life crowbar", "CoD Zombies Ray Gun", "Doom BFG 9000", "Final Fantasy VII Buster Sword", "Halo Energy Sword").
     - В поле 'answer_text': пиши то, ЧТО именно зритель должен угадать — ЦЕЛЕВОЙ ОТВЕТ (название игры или фильма) КАПСОМ (например: 'MINECRAFT', 'PORTAL', 'POKÉMON', 'GOD OF WAR', 'ASSASSIN\'S CREED', 'HALF-LIFE', 'CALL OF DUTY', 'DOOM', 'FINAL FANTASY VII', 'HALO').
       НЕ пиши в answer_text название самого оружия, если тема — угадать игру!
     - В поле 'prompt_tts': диктор спрашивает именно о целевом ответе (например: «Что за игра?», «Номер два, какая игра?», «Номер три, узнаешь игру?»).
     - В поле 'answer_tts': диктор четко называет правильный ответ (например: «Это Minecraft!», «Это God of War!»).
   - Если викторина устроена напрямую (например, «Логотипы брендов», «Суперкары», «Флаги стран»):
     - 'image_query': сам объект или логотип (например: "Apple logo", "Ferrari F40", "Flag of Brazil").
     - 'answer_text': название самого объекта/бренда.
     - 'prompt_tts': «Что за бренд?», «Узнаешь модель?», «Что это?».

3. ПРАВИЛО 10-ГО ПРЕДМЕТА (MASTER-ЛОФУШКА):
   - difficulty: строго "master".
   - 'answer_text': строго "Пиши в коммы" (для русского языка) или "Write in comments" (для английского языка).
   - 'image_query': поисковый запрос 10-го предмета из задания пользователя (например: "Halo Energy Sword" или "CS2 AWP Dragon Lore").
   - 'answer_tts': диктор интригующе призывает писать свои догадки в комментариях (например: «А это самый сложный! Напиши игру в комментариях!» или «And this is the final level! Drop your guess in the comments!»).

4. РЕПЛИКИ ДИКТОРА (TTS):
   - Вопрос 1: диктор СРАЗУ задает вопрос по сути БЕЗ вводных слов «Вопрос номер один» (например: «Что за игра?», «Узнаешь модель?», «Что за бренд?»).
   - Вопросы 2..9: диктор обязательно называет номер и кратко спрашивает (например: «Номер два, что за игра?», «Вопрос три, как называется?», «Номер четыре, откуда это?»).
   - Все реплики диктора должны быть краткими и динамичными (до 10-12 слов).

5. ИНТРО-ХУК ('hook_tts'):
   - КРАТКАЯ энергичная фраза СТРОГО до 5–7 слов (длительность звучания максимум 2.5–2.7 секунды).
   - Хук обязан ТОЧНО соответствовать теме:
     - Для темы «Угадай игру по оружию»: «Угадай игру по оружию! Погнали!» или "Guess the game by weapon! Let's go!".
     - Для темы про фильмы: «Угадай все фильмы по кадру!».
     - Для темы про автомобили: «Узнаешь все 10 автомобилей? Попробуй!».
     - Для темы про логотипы: «Угадай все эти логотипы! Погнали!».
   - ВНИМАНИЕ: Запрещено говорить слово «логотипы», если викторина не про логотипы!

6. ПОИСКОВЫЕ ЗАПРОСЫ КАРТИНОК ('image_query'):
   - Составь точный, емкий поисковый запрос строго на английском языке (название предмета, персонажа, логотипа или модели).
   - Всегда добавляй в конец запроса 'white background png' (например: "Minecraft diamond sword white background png", "Portal gun white background png", "Apple logo white background png") — на белом фоне алгоритм идеально вырезает чистый контур!
   - Запрещено использовать длинный мусор вроде 'vector logo transparent png isolated without background'.

Верни строго валидный JSON по схеме VisualQuizDataset."""


VISUAL_TOPIC_SYSTEM_PROMPT = """Ты — креативный продюсер вирусных визуальных видео-викторин для TikTok, YouTube Shorts и Reels.
Формат: зритель видит картинку/логотип/объект и за 3 секунды угадывает ответ, а в первые 3 секунды диктор произносит интригующий хук пока в центре быстро мелькают карточки (rapid center flip).

Твоя цель: придумать вирусную тему для ВИЗУАЛЬНОЙ викторины из 10 картинок и цепляющий флип-хук.

Требования:
1. Тема ДОЛЖНА быть чисто визуальной (логотипы, суперкары, флаги, персонажи аниме/кино, бренды, животные, ретро-игры, достопримечательности).
2. flip_hook должен содержать интригу или вызов (например: "Угадай все 10 логотипов! На 9-м ошибаются 98% людей!", "Назови 10 суперкаров по фарам! На последнем споткнется даже эксперт!").
3. sample_items: укажи 3-5 узнаваемых предметов по этой теме.
Верни строго валидный JSON по схеме VisualTopicSuggestion."""


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
        self.exclusions_manager = QuizExclusionsManager()
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

    async def suggest_visual_topic(
        self,
        category_hint: str | None = None,
        language: str = "ru",
        temperature: float | None = None,
    ) -> VisualTopicSuggestion:
        """Suggest a viral visual quiz topic with catchy rapid-flip hook using Gemini."""
        is_en = (language or "ru").lower().startswith("en")
        if is_en:
            prompt_lines = [
                "Language: English (en).",
                "Invent 1 viral visual quiz topic with image cards and an engaging rapid-flip hook strictly in English.",
            ]
            if category_hint and category_hint.strip():
                prompt_lines.append(f"User category direction: '{category_hint.strip()}'.")
            else:
                angles = [
                    "World iconic brand logos and secret details",
                    "Supercars and hypercars by headlights or silhouette",
                    "Famous movie landmarks by a single shot",
                    "Popular video game icons and weapons",
                    "World flags with optical illusions or traps",
                    "Architectural wonders and famous monuments",
                ]
                prompt_lines.append(f"Inspiration angle: '{random.choice(angles)}'.")
        else:
            prompt_lines = [
                f"Язык: {language}.",
                "Придумай 1 вирусную тему для визуальной викторины с карточками-картинками и флип-хуком.",
            ]
            if category_hint and category_hint.strip():
                prompt_lines.append(f"Пожелание/направление от пользователя: «{category_hint.strip()}».")
            else:
                angles = [
                    "Логотипы культовых брендов и тайные детали",
                    "Суперкары и спорткары по оптике/силуэту",
                    "Угадай популярный фильм по одному кадру",
                    "Персонажи аниме по силуэтам или глазам",
                    "Флаги государств мира с подвохом",
                    "Известные мировые достопримечательности",
                    "Культовые видеоигры 2000-х по скриншоту",
                    "Породы собак и редкие кошачьи",
                    "Символы супергероев Marvel и DC",
                    "Культовые кроссовки в истории сникер-культуры",
                ]
                prompt_lines.append(f"Вектор для вдохновения: «{random.choice(angles)}».")

        exclusions = self.exclusions_manager.load()
        if exclusions.get("topics"):
            recent_topics = exclusions["topics"][-25:]
            prompt_lines.append(
                f"СТРОГО ЗАПРЕЩЕНО повторять или дублировать ранее использованные темы: {', '.join(f'«{t}»' for t in recent_topics)}."
            )

        prompt = "\n".join(prompt_lines)
        temp = temperature if temperature is not None else 1.05
        return await self._generate_structured(
            prompt=prompt,
            system_instruction=VISUAL_TOPIC_SYSTEM_PROMPT,
            response_schema=VisualTopicSuggestion,
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

        # Record topic into persistent exclusions
        self.exclusions_manager.add_exclusions(topic=topic)

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
        is_en = (language or "ru").lower().startswith("en")
        if not theme or not theme.strip():
            chosen_theme = random.choice(RANDOM_VISUAL_QUIZ_THEMES_EN if is_en else RANDOM_VISUAL_QUIZ_THEMES)
            clean_title = chosen_theme
        else:
            chosen_theme = theme.strip()
            first_line = chosen_theme.split("\n")[0].strip()
            if ":" in first_line:
                clean_title = first_line.split(":")[0].strip()
            else:
                clean_title = first_line or chosen_theme
            clean_title = clean_title.strip("«»\"' ")

        exclusion_clause = self.exclusions_manager.get_prompt_exclusion_clause(max_items=80)
        if is_en:
            prompt_parts = [
                f"Visual Quiz Theme & Requirements:\n{chosen_theme}",
                "Language of voiceover and UI: English (en).",
                "Generate a viral script with exactly 10 items of increasing difficulty (3 easy, 3 medium, 3 hard, 1 master cliffhanger).",
                "CRITICAL INSTRUCTIONS:",
                "- If specific items, questions, or tiers (Easy, Medium, Hard, Master) are listed in the user prompt, YOU MUST STRICTLY USE THOSE EXACT ITEMS for the corresponding levels 1..10!",
                "- Understand what is shown in 'image_query' vs what is answered in 'answer_text'. For example, in 'Guess the game by weapon', image_query is the weapon with game context and 'white background png' (e.g. 'Minecraft Diamond Sword white background png') and answer_text is the game title (e.g. 'MINECRAFT')!",
                "- For Question 1: narrator immediately asks the question without saying 'Question 1' (e.g. 'What game is this?' or 'Guess the game!').",
                "- For Questions 2-9: narrator announces question number (e.g. 'Number two, what game is this?').",
                "- For Question 10: set answer_text strictly to 'Write in comments', difficulty='master'. For answer_tts, narrator intriguingly challenges viewer to guess in comments.",
                "- In hook_tts: energetic short challenge matching the exact theme, STRICTLY 5-7 words, under 3.0 seconds (e.g. 'Guess the game by weapon! Let's go!'). Do NOT use the word 'logos' unless the theme is actually about brand logos.",
            ]
        else:
            prompt_parts = [
                f"Тема и требования к визуальной викторине:\n{chosen_theme}",
                f"Язык озвучки и интерфейса: {language}.",
                "Сгенерируй вирусный сценарий из 10 предметов с нарастающей сложностью (3 easy, 3 medium, 3 hard, 1 master-ловушка).",
                "КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА:",
                "- Если в описании темы выше перечислены конкретные предметы/вопросы по уровням (Easy, Medium, Hard, Master) — ТЫ ОБЯЗАН СТРОГО ИСПОЛЬЗОВАТЬ ИМЕННО ЭТИ ПРЕДМЕТЫ для соответствующих позиций 1..10!",
                "- Различай показываемый объект и правильный ответ: если тема «Угадай игру по оружию», в 'image_query' ищи само оружие на английском с добавлением 'white background png' (например: 'Minecraft diamond sword white background png', 'Portal gun white background png', 'God of War Blades of Chaos white background png'), а в 'answer_text' пиши правильный ответ — название самой игры (например: 'MINECRAFT', 'PORTAL', 'GOD OF WAR', 'HALF-LIFE') капсом!",
                "- В репликах диктора ('prompt_tts'): спрашивай именно о целевом ответе (например: 'Что за игра?', 'Номер два, какая игра?', 'Номер три, узнаешь игру?').",
                "- Для вопроса 1 диктор сразу задает вопрос без фразы 'Вопрос 1'. Для вопроса 10 ответ скрыт ('Пиши в коммы', difficulty='master') с интригующим призывом писать догадки в комментарии.",
                "- В интро hook_tts напиши краткий энергичный вызов СТРОГО до 5-7 слов, строго соответствующий теме (например: 'Угадай игру по оружию! Погнали!'). Запрещено говорить 'логотипы', если тема не про логотипы!",
            ]
        if exclusion_clause:
            prompt_parts.append(exclusion_clause)

        prompt = "\n".join(prompt_parts)

        dataset = await self._generate_structured(
            prompt=prompt,
            system_instruction=VISUAL_QUIZ_SYSTEM_PROMPT,
            response_schema=VisualQuizDataset,
            temperature=temperature,
        )

        # Force structural integrity
        dataset.theme = clean_title or dataset.theme or chosen_theme
        dataset.mode = "visual_image_quiz"
        dataset.language = "en" if is_en else "ru"
        dataset.interstitials = []
        dataset.timer_duration_sec = 1.75

        # Sanitize hook_tts: forbid "What is this?" and enforce strict 5-7 words budget for <= 3.0s intro
        if dataset.hook_tts:
            cleaned_hook = dataset.hook_tts
            if is_en:
                cleaned_hook = re.sub(r'[, -]*\b(let\'?s go[, -]*)?what is (this|that|it)(\s+brand)?\??', '', cleaned_hook, flags=re.IGNORECASE).strip()
                if not cleaned_hook or ("logo" in cleaned_hook.lower() and "logo" not in clean_title.lower()):
                    cleaned_hook = f"Guess all {clean_title}! Let's go!" if len(clean_title.split()) <= 4 else "Guess them all! Let's go!"
            else:
                cleaned_hook = re.sub(r'[, -]*\b(погнали[, -]*)?что это(\s+за\s+[^.!?]+)?\??', '', cleaned_hook, flags=re.IGNORECASE).strip()
                if not cleaned_hook or ("логотип" in cleaned_hook.lower() and "логотип" not in clean_title.lower()):
                    cleaned_hook = f"Угадай {clean_title}! Погнали!" if len(clean_title.split()) <= 4 else "Угадай всё! Погнали!"

            # Enforce max 6-7 words budget so speech finishes cleanly under 3.0s
            words = cleaned_hook.split()
            if len(words) > 7:
                sentences = [s.strip() for s in re.split(r'[.!?]+', cleaned_hook) if s.strip()]
                if sentences and 3 <= len(sentences[0].split()) <= 7:
                    cleaned_hook = sentences[0]
                else:
                    cleaned_hook = " ".join(words[:6]).rstrip(",;:- ")
            if not cleaned_hook.endswith(('.', '!', '?')):
                cleaned_hook += '!'
            dataset.hook_tts = cleaned_hook

        # Sanitize question 1 to ensure no "Question 1" / "Вопрос номер один" prefix
        if dataset.items:
            q1_prompt = dataset.items[0].prompt_tts
            prefixes = (
                ("Question number one,", "Question number 1,", "Question 1,", "Question one,")
                if is_en
                else ("Вопрос номер один,", "Вопрос номер 1,", "Вопрос 1,", "Вопрос один,")
            )
            for prefix in prefixes:
                if q1_prompt.lower().startswith(prefix.lower()):
                    dataset.items[0].prompt_tts = q1_prompt[len(prefix):].strip()

        # Sanitize question 10 cliffhanger
        if len(dataset.items) >= 10:
            dataset.items[9].answer_text = "Write in comments" if is_en else "Пиши в коммы"
            dataset.items[9].difficulty = VisualDifficulty.MASTER

        # Search candidate images if requested
        if auto_search_images:
            await self._resolve_visual_quiz_images(dataset)

        # Record newly generated items and theme to exclusions file to prevent future repetition
        cliff_labels = {"Пиши в коммы", "Write in comments"}
        new_items = [
            it.answer_text
            for it in dataset.items
            if it.answer_text and it.answer_text not in cliff_labels
        ]
        self.exclusions_manager.add_exclusions(topic=chosen_theme, items=new_items)

        logger.info(
            "Successfully generated VisualQuizDataset for theme '%s' with %d items (saved to exclusions).",
            chosen_theme,
            len(dataset.items),
        )
        return dataset

    async def _resolve_visual_quiz_images(self, dataset: VisualQuizDataset) -> None:
        """Find candidate image URLs for visual quiz items via ImageService, strictly prioritizing transparent PNGs."""
        async def _fetch_item_image(item: VisualQuizItem) -> None:
            if item.image_url:
                return
            try:
                query_to_search = ImageService.format_transparent_query(
                    item.image_query or item.answer_text
                )
                candidates = await self.image_service._search_image_urls(query_to_search, max_results=8)
                if candidates:
                    sorted_candidates = ImageService.sort_transparent_candidates(candidates)
                    for cand in sorted_candidates:
                        url = cand.get("image") or cand.get("thumbnail")
                        if url:
                            item.image_url = url
                            break
            except Exception as err:
                logger.warning("Failed to auto-search image for '%s': %s", item.image_query, err)

        await asyncio.gather(*[_fetch_item_image(it) for it in dataset.items])

    async def generate_widescreen_quiz_dataset(
        self,
        topic_prompt: str = "Культовые видеоигры всех времен",
        language: str = "ru",
        num_rounds: int = 5,
        questions_per_round: int = 10,
    ) -> WidescreenQuizDataset:
        """Generate a complete modular 16:9 widescreen multi-round trivia quiz dataset."""
        logger.info(
            "Generating WidescreenQuizDataset: prompt='%s', language=%s, rounds=%d, q_per_round=%d",
            topic_prompt,
            language,
            num_rounds,
            questions_per_round,
        )

        # 1. Check if Gemini client is configured
        client = self._client
        has_key = bool(self.config.effective_api_key.get_secret_value())
        if client and has_key:
            system_instruction = (
                "Ты — главный сценарист и геймдизайнер масштабной 16:9 widescreen телевикторины "
                "по видеоиграм в стиле 'Quiz Please' на 50 вопросов (5 уникальных раундов по 10 вопросов). "
                "Раунды должны прогрессировать по сложности и механикам:\n"
                "1. Скриншоты игр (asset_mode='screenshot') — массовые популярные игры.\n"
                "2. Звуки оружия и предметов (asset_mode='audio_sfx') — культовые игровые звуки с поисковыми запросами.\n"
                "3. Экраны гибели Game Over (asset_mode='game_over') — узнаваемые экраны смерти с замазанным названием.\n"
                "4. Миникарты и радары (asset_mode='minimap') — узнаваемые радары из HUD.\n"
                "5. Силуэты персонажей (asset_mode='silhouette') — культовые герои в виде силуэтов.\n"
                "Ответ на каждый вопрос должен быть четким названием игры или предмета/персонажа капсом (1-4 слова). "
                "Тайминг: guessing_duration_sec=6.0, reveal_hold_duration_sec=3.0."
            )
            user_prompt = f"Тема викторины: {topic_prompt}. Язык: {language}. Сгенерируй {num_rounds} раундов по {questions_per_round} вопросов."

            try:
                rate_limiter = get_gemini_rate_limiter()
                async with rate_limiter:
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=self.config.gemini_model,
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json",
                            response_schema=WidescreenQuizDataset,
                            temperature=0.7,
                        ),
                    )
                if response and response.text:
                    parsed = json.loads(response.text)
                    dataset = WidescreenQuizDataset.model_validate(parsed)
                    logger.info("Successfully generated WidescreenQuizDataset via Gemini API.")
                    return dataset
            except Exception as err:
                logger.warning("Gemini generation failed: %s. Using default gaming quiz template.", err)

        # 2. Deterministic Fallback Dataset (5 Rounds x 10 Questions = 50 Questions Total)
        logger.info("Building curated default 50-question 16:9 gaming quiz dataset.")
        rounds: list[WidescreenQuizRound] = []

        is_en = language == "en"

        round_definitions = [
            (
                1,
                "ROUND 01: GAME SCREENSHOTS" if is_en else "РАУНД 01: СКРИНШОТЫ ИГР",
                AssetDisplayMode.SCREENSHOT,
                "94% OF PLAYERS PASS THIS ROUND" if is_en else "94% ИГРОКОВ ПРОХОДЯТ ЭТОТ РАУНД",
                "#58A6FF",
                [
                    ("Grand Theft Auto V", "GTA V gameplay screenshot Los Santos"),
                    ("Minecraft", "Minecraft survival house screenshot"),
                    ("The Elder Scrolls V: Skyrim", "Skyrim Bleak Falls Barrow screenshot"),
                    ("Fortnite", "Fortnite battle royale gameplay screenshot"),
                    ("The Witcher 3: Wild Hunt", "Witcher 3 White Orchard landscape screenshot"),
                    ("DOOM Eternal", "Doom Eternal slayer combat screenshot"),
                    ("Portal 2", "Portal 2 aperture science test chamber"),
                    ("Cyberpunk 2077", "Cyberpunk 2077 Night City neon street"),
                    ("Half-Life 2", "Half-Life 2 City 17 trainstation screenshot"),
                    ("Elden Ring", "Elden Ring Erdtree Limgrave panorama"),
                ],
            ),
            (
                2,
                "ROUND 02: WEAPON & ITEM SOUNDS" if is_en else "РАУНД 02: ЗВУКИ ОРУЖИЯ И ПРЕДМЕТОВ",
                AssetDisplayMode.AUDIO_SFX,
                "78% OF PLAYERS PASS THIS ROUND" if is_en else "78% ИГРОКОВ ПРОХОДЯТ ЭТОТ РАУНД",
                "#00E5FF",
                [
                    ("AWP (CS:GO / CS2)", "CS AWP sniper rifle gunshot sound"),
                    ("AK-47 (COUNTER-STRIKE)", "CS AK-47 assault rifle gunshot sound"),
                    ("MINECRAFT (EATING SOUND)" if is_en else "MINECRAFT (ЗВУК ЕДЫ)", "Minecraft eating apple food sound"),
                    ("HALF-LIFE (MEDKIT HEAL)" if is_en else "HALF-LIFE (АПТЕЧКА)", "Half-Life wall health station medkit sound"),
                    ("DARK SOULS (YOU DIED)", "Dark Souls death sound you died chime"),
                    ("GTA (WASTED)", "GTA San Andreas wasted sound effect"),
                    ("PAC-MAN (DEATH SOUND)" if is_en else "PAC-MAN (ГИБЕЛЬ)", "Pacman retro arcade death sound"),
                    ("SUPER MARIO (COIN PICKUP)" if is_en else "SUPER MARIO (МОНЕТКА)", "Super Mario Bros coin pickup sound"),
                    ("SONIC (GOLD RING)" if is_en else "SONIC (КОЛЬЦО)", "Sonic the Hedgehog gold ring sound"),
                    ("PORTAL (PORTAL GUN)" if is_en else "PORTAL (ПОРТАЛЬНАЯ ПУШКА)", "Portal gun shot blue orange sound"),
                ],
            ),
            (
                3,
                "ROUND 03: GAME OVER SCREENS" if is_en else "РАУНД 03: ЭКРАНЫ СМЕРТИ (GAME OVER)",
                AssetDisplayMode.GAME_OVER,
                "58% OF PLAYERS PASS THIS ROUND" if is_en else "58% ИГРОКОВ ПРОХОДЯТ ЭТОТ РАУНД",
                "#EF4444",
                [
                    ("DARK SOULS III", "Dark Souls 3 YOU DIED screen clean"),
                    ("FALLOUT: NEW VEGAS", "Fallout New Vegas death camera spinning screen"),
                    ("GRAND THEFT AUTO: SAN ANDREAS", "GTA San Andreas wasted screen black white"),
                    ("CUPHEAD", "Cuphead YOU DIED run and gun progress card"),
                    ("DEAD SPACE", "Dead Space Isaac Clarke death stomp screen"),
                    ("SEKIRO: SHADOWS DIE TWICE", "Sekiro death kanji red symbol screen"),
                    ("RESIDENT EVIL 4", "Resident Evil 4 YOU ARE DEAD blood text"),
                    ("CALL OF DUTY: MODERN WARFARE 2", "Call of Duty death quote screen MW2"),
                    ("UNDERTALE", "Undertale heart broken Game Over screen"),
                    ("HOLLOW KNIGHT", "Hollow Knight shade death crack mask screen"),
                ],
            ),
            (
                4,
                "ROUND 04: RADAR MINIMAPS" if is_en else "РАУНД 04: МИНИКАРТЫ И РАДАРЫ",
                AssetDisplayMode.MINIMAP,
                "42% OF PLAYERS PASS THIS ROUND" if is_en else "42% ИГРОКОВ ПРОХОДЯТ ЭТОТ РАУНД",
                "#F59E0B",
                [
                    ("THE WITCHER 3", "Witcher 3 circular compass minimap radar hud"),
                    ("GTA V", "GTA 5 rectangular gps minimap hud"),
                    ("CYBERPUNK 2077", "Cyberpunk 2077 circular red scanner radar minimap"),
                    ("ASSASSIN'S CREED II", "Assassins Creed 2 eagle round minimap hud"),
                    ("RED DEAD REDEMPTION 2", "RDR2 circular old west compass minimap hud"),
                    ("WORLD OF WARCRAFT", "World of Warcraft circular tracking minimap hud"),
                    ("FALLOUT 4", "Fallout 4 bottom pip boy compass bar hud"),
                    ("CS2 / CS:GO", "Counter Strike radar circle bomb defusal minimap"),
                    ("GENSHIN IMPACT", "Genshin Impact circular elemental minimap hud"),
                    ("FAR CRY 3", "Far Cry 3 circular island jungle radar hud"),
                ],
            ),
            (
                5,
                "ROUND 05: CHARACTER SILHOUETTES" if is_en else "РАУНД 05: СИЛУЭТЫ ГЕРОЕВ (БОЖЕСТВЕННЫЙ РАНГ)",
                AssetDisplayMode.SILHOUETTE,
                "18% OF PLAYERS PASS THIS ROUND" if is_en else "18% ИГРОКОВ ПРОХОДЯТ ЭТОТ РАУНД",
                "#8B5CF6",
                [
                    ("KRATOS (GOD OF WAR)" if is_en else "КРАТОС (GOD OF WAR)", "Kratos Leviathan axe God of War silhouette character render"),
                    ("MASTER CHIEF (HALO)" if is_en else "МАСТЕР ЧИФ (HALO)", "Master Chief Spartan helmet Halo silhouette"),
                    ("GERALT OF RIVIA (THE WITCHER)" if is_en else "ГЕРАЛЬТ (ВЕДЬМАК)", "Geralt of Rivia dual swords Witcher silhouette"),
                    ("GORDON FREEMAN (HALF-LIFE)" if is_en else "ГОРДОН ФРИМЕН (HALF-LIFE)", "Gordon Freeman HEV suit crowbar silhouette"),
                    ("ARTHUR MORGAN (RDR2)" if is_en else "АРТУР МОРГАН (RDR2)", "Arthur Morgan cowboy hat revolver silhouette"),
                    ("LARA CROFT (TOMB RAIDER)" if is_en else "ЛАРА КРОФТ (TOMB RAIDER)", "Lara Croft dual pistols Tomb Raider silhouette"),
                    ("DOOM SLAYER (DOOM)" if is_en else "ДУМГАЙ (DOOM)", "Doom Slayer Praetor suit shotgun silhouette"),
                    ("SOLID SNAKE (METAL GEAR SOLID)" if is_en else "СОЛИД СНЕЙК (MGS)", "Solid Snake headband Metal Gear Solid silhouette"),
                    ("STEVE (MINECRAFT)" if is_en else "СТИВ (MINECRAFT)", "Steve Minecraft diamond pickaxe cube silhouette"),
                    ("SANS (UNDERTALE)" if is_en else "СЭНС (UNDERTALE)", "Sans the skeleton blue eye Undertale silhouette"),
                ],
            ),
        ]

        global_q_counter = 1
        for r_num, r_title, r_mode, r_pass, r_color, items_data in round_definitions[:num_rounds]:
            q_items: list[WidescreenQuizItem] = []
            for item_idx, (answer, query) in enumerate(items_data[:questions_per_round], start=1):
                if is_en:
                    prompt = "Guess the video game from screenshot"
                    if r_mode == AssetDisplayMode.AUDIO_SFX:
                        prompt = "Identify the weapon or item from sound"
                    elif r_mode == AssetDisplayMode.GAME_OVER:
                        prompt = "Which game has this Game Over screen?"
                    elif r_mode == AssetDisplayMode.MINIMAP:
                        prompt = "Recognize the game from this radar minimap"
                    elif r_mode == AssetDisplayMode.SILHOUETTE:
                        prompt = "Name the iconic character from silhouette"
                else:
                    prompt = "Угадайте игру по скриншоту"
                    if r_mode == AssetDisplayMode.AUDIO_SFX:
                        prompt = "Угадайте оружие или предмет по звуку"
                    elif r_mode == AssetDisplayMode.GAME_OVER:
                        prompt = "Из какой игры этот экран смерти?"
                    elif r_mode == AssetDisplayMode.MINIMAP:
                        prompt = "Назовите игру по миникарте"
                    elif r_mode == AssetDisplayMode.SILHOUETTE:
                        prompt = "Назовите культового персонажа по силуэту"

                q_items.append(
                    WidescreenQuizItem(
                        item_index=item_idx,
                        global_question_number=global_q_counter,
                        prompt_text=prompt,
                        answer_text=answer.upper(),
                        asset_search_query=query,
                        apply_procedural_mask=True,
                        audio_cue_duration_sec=4.0,
                    )
                )
                global_q_counter += 1

            rounds.append(
                WidescreenQuizRound(
                    round_number=r_num,
                    round_title=r_title,
                    asset_mode=r_mode,
                    pass_rate_statistic=r_pass,
                    badge_theme_color=r_color,
                    splash_duration_sec=4.0,
                    questions=q_items,
                )
            )

        intro_hook = (
            "50 Gaming Questions. 5 Unique Rounds. Can you reach the God Tier rank? Round one starts right now!"
            if is_en
            else "50 игровых вопросов. 5 уникальных раундов. Сможешь ли ты дойти до ранга God Tier? Раунд один начинается прямо сейчас!"
        )
        outro_speech = (
            "Comment your final score down below and subscribe to the channel for part two!"
            if is_en
            else "Напиши свой итоговый балл в комментариях под этим видео и подпишись на канал, чтобы не пропустить вторую часть!"
        )
        cta = (
            "COMMENT YOUR SCORE & SUBSCRIBE!"
            if is_en
            else "НАПИШИ СВОЙ СЧЕТ В КОММЕНТАРИЯХ & ПОДПИШИСЬ!"
        )

        return WidescreenQuizDataset(
            mode="widescreen_gaming_quiz",
            title="50 GAMING QUESTIONS CHALLENGE",
            language=language,
            guessing_duration_sec=6.0,
            reveal_hold_duration_sec=3.0,
            intro=WidescreenIntroConfig(
                hook_tts=intro_hook,
                duration_sec=8.0,
                challenge_title="50 GAMING QUESTIONS CHALLENGE",
            ),
            outro=WidescreenOutroConfig(
                duration_sec=15.0,
                outro_tts=outro_speech,
                call_to_action=cta,
                score_tiers=[
                    WidescreenScoreTier(tier_name="Noob", min_score=0, max_score=20, badge_color="#94A3B8"),
                    WidescreenScoreTier(tier_name="Gamer", min_score=21, max_score=35, badge_color="#3B82F6"),
                    WidescreenScoreTier(tier_name="Pro", min_score=36, max_score=45, badge_color="#8B5CF6"),
                    WidescreenScoreTier(tier_name="God Tier", min_score=46, max_score=50, badge_color="#F59E0B"),
                ],
            ),
            rounds=rounds,
        )



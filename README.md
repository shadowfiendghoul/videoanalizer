# VideoAnalyzer 🎬

**AI-генератор вирусных вертикальных Shorts / TikTok / Reels роликов**  
Работает на базе **Google Gemini Flash**, **Edge-TTS**, **Remotion (React/TypeScript 9:16)** и **FFmpeg**.

---

## ⚡ Быстрый старт на Windows (В 1 клик)

Для запуска на Windows не требуется сложная ручная настройка:

1. **Установка зависимостей:**
   Дважды кликните по **`install.bat`** (или выполните `.\install.ps1` в PowerShell).
   * Автоматически проверит Python 3.11+, Node.js и FFmpeg (предложит установить через WinGet при отсутствии).
   * Создаст изолированное виртуальное окружение (`.venv`).
   * Установит все Python-библиотеки и Remotion NPM-пакеты.
   * Настроит конфигурационный файл `.env` и запросит ключ Gemini API.

2. **Запуск программы:**
   Дважды кликните по **`start.bat`**.
   * Автоматически откроет браузер по адресу: **`http://localhost:7860`**.

---

## 🚀 Основные возможности

### 1. Генератор викторин и квизов (Quiz Shorts Generator)
* 🧠 **9-вопросный блиц-формат** (3 уровня: Легкий $\rightarrow$ Средний $\rightarrow$ Тяжелый).
* 🔬 **Двухэтапный ИИ-пайплайн**:
  * *Этап 1 ($T=0.95$)*: Креативная генерация оригинальных парадоксов и нетривиальных фактов.
  * *Этап 2 ($T=0.1$)*: Строгий факт-чекинг для отсеивания мифов и проверки достоверности.
* 🔥 **Вирусные механики удержания (Retention Mechanics)**:
  * **Шкала статуса и IQ**: NPC $\rightarrow$ Нормис $\rightarrow$ Эрудит $\rightarrow$ 1% Гениев.
  * **Прогрессирующий стресс-таймер**: 3.0с $\rightarrow$ 2.5с $\rightarrow$ 1.8с с нарастающим пульсом сердца и виньеткой тревоги.
  * **Счетчик комбо-стрика**: Нарастающее пламя огня с синим ультра-режимом при стрике $\ge 7$.
  * **Decoy Fake-Out**: 0.3с обманка ложного ответа перед показом правильного (`❌ НЕ ПАРИЖ` $\rightarrow$ `✅ ЛИОН`).
  * **Аутро-ловушка для комментариев**: Призыв к спорам в финале для взрывного роста комментариев.
* 🖼️ **Визуальные подсказки (Visual Clues)**: Автоматический поиск и ручной выбор фото по ответу вопроса через DuckDuckGo, стильное анимированное отображение в Remotion.
* 📢 **Промо-баннеры**: Интеграция центрального видео-баннера с автоматической паузой фонового видео и адаптацией субтитров.

### 2. Анализатор смешных моментов (Funny Moments Ingestion)
* 📥 **Загрузка видео**: Вставка ссылки на YouTube или загрузка локального файла (`.mp4`, `.mov`, `.webm`, `.mkv`).
* 🤖 **ИИ-поиск панчлайнов**: Распознавание смешных моментов, криков, реакций стримера и ключевых фраз через аудиовизуальный анализ Gemini.
* 📐 **Умный кроп 9:16**:
  * Центрированный кроп (`1080x1920`).
  * **Разделенный экран (Streamer Split-Screen)**: Веб-камера сверху + геймплей снизу с интерактивным выбором зон.
* ✂️ **Удаление тишины**: Мягкое вырезание пауз с кроссфейдами без аудиощелчков.
* 💬 **Караоке-субтитры**: Динамические всплывающие слова в стиле TikTok.

---

## 🛠 Архитектура

```text
videoanalizer/
├── config.py             # Глобальная конфигурация Pydantic Settings
├── api/                  # FastAPI асинхронные REST-эндпоинты
│   ├── routes_quiz.py    # Эндпоинты генерации квизов, факт-чекинга и поиска картинок
│   └── routes.py         # Эндпоинты анализа видео и нарезки
├── quiz/                 # Ядро викторин
│   ├── models.py         # Строгие Pydantic v2 схемы данных и контракты
│   ├── config.py         # Настройки темпа, голосов и температур Gemini
│   ├── script_service.py # Двухэтапная генерация (Креатив + Факт-чекер)
│   ├── image_service.py  # Асинхронный поиск и кэширование картинок (DuckDuckGo/Pillow)
│   ├── audio_service.py  # Edge-TTS озвучка, тайминги слов и SFX
│   └── orchestrator.py   # Оркестратор FIFO-очереди и запуск Remotion CLI
├── media/                # Модули FFmpeg медиа-обработки
├── ui/                   # Веб-панель (HTML/JS + Gradio)
└── templates/
    └── quiz-remotion/    # 1080x1920 60fps Remotion React/TypeScript композиция
```

---

## 💻 Ручная установка (Cross-Platform: Linux / macOS / Windows)

### 1. Системные требования
* **Python 3.11+**
* **Node.js 18+ & npm**
* **FFmpeg** (должен быть доступен в PATH)
  * Windows: `winget install Gyan.FFmpeg`
  * macOS: `brew install ffmpeg node`
  * Ubuntu/Debian: `sudo apt install ffmpeg nodejs npm`

### 2. Клонирование и настройка Python
```bash
git clone https://github.com/zxcyuiiop/videoanalizer.git
cd videoanalizer

python -m venv .venv
# Активация окружения:
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install --upgrade pip setuptools wheel
pip install -e .
```

### 3. Установка Remotion (Шаблон видео)
```bash
cd templates/quiz-remotion
npm install
cd ../..
```

### 4. Конфигурация API ключа
Скопируйте пример настроек и укажите ваш ключ Gemini API:
```bash
cp .env.example .env
```
В файле `.env`:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Запуск
```bash
python -m videoanalizer
```
Перейдите в браузере по адресу `http://localhost:7860`.

---

## 🧪 Запуск автоматических тестов

```bash
# Все юнит- и контрактные тесты Python (38 тестов):
python -m pytest tests/unit/quiz tests/contract/quiz -v

# Проверка типов TypeScript в Remotion:
cd templates/quiz-remotion && npm run typecheck
```

---

## 📄 Лицензия

MIT License

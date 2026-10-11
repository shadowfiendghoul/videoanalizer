# Quickstart Validation Guide: Quiz Retention Mechanics

**Feature ID**: `003-quiz-retention-mechanics`  
**Target Platform**: Windows / PowerShell (AMD Ryzen 7 8845H, Radeon 780M)  

---

## 1. Prerequisites & Environment Setup

Убедитесь, что активировано виртуальное окружение и установлены зависимости:
```powershell
# Проверка Python и установленных пакетов
python --version
python -c "import fastapi, pydantic, remotion; print('Core dependencies present')"

# Проверка Remotion и Node.js в templates/quiz-remotion
cd templates/quiz-remotion
npm --version
npm run build --if-present
cd ../..
```

---

## 2. Test Execution & Automated Verification

Запуск автоматизированных тестов для проверки контрактов данных, сервиса генерации и рендеринга:

```powershell
# 1. Запуск всех unit и contract тестов модуля Quiz
python -m pytest tests/unit/quiz tests/contract/quiz -v

# 2. Проверка строгого форматирования и типов (Ruff)
python -m ruff check videoanalizer/quiz tests/
```

---

## 3. End-to-End Validation Scenarios

### Сценарий 1: Предпросмотр вопросов с проверкой лимитов текста
Отправьте запрос на генерацию черновика вопросов с проверкой ограничений длины (вопрос $\le 65$ симв., ответ $\le 25$ симв.):
```powershell
curl -X POST "http://localhost:7860/api/v1/quiz/preview-questions" `
  -H "Content-Type: application/json" `
  -d '{"topic": "Космос и планеты", "language": "ru"}'
```
**Ожидаемый результат**:
- Возвращается JSON `QuizChallenge` с 9 вопросами.
- Длина каждого поля `question_text` $\le 65$ символов.
- Длина `correct_answer` $\le 25$ символов.

---

### Сценарий 2: Запуск рендеринга с вирусными механиками удержания
Запустите генерацию полного ролика с включенными тумблерами удержания:
```powershell
curl -X POST "http://localhost:7860/api/v1/quiz/generate" `
  -H "Content-Type: application/json" `
  -d '{
    "topic": "Тайны океана",
    "language": "ru",
    "retention_enabled": true,
    "rank_bar_enabled": true,
    "stress_timer_enabled": true,
    "streak_fire_enabled": true,
    "comment_trap_enabled": true
  }'
```
**Ожидаемый результат**:
- Ответ `202 Accepted` с `job_id` и статусом `queued` / `generating_script`.
- В процессе рендеринга потребление оперативной памяти не превышает 4 ГБ благодаря `--concurrency=3`.
- Итоговый MP4 сохраняется в `outputs/` с общей длительностью строго в пределах **45–50 секунд**.

---

### Сценарий 3: Визуальная верификация в Remotion Preview
Для быстрой отладки анимаций и верстки без полного рендеринга:
```powershell
cd templates/quiz-remotion
npx remotion preview src/index.ts
```
В открывшемся браузере `http://localhost:3000`:
- Проверить наличие `RankStatusBar` в верхней зоне ($Y=160\text{px}$) со сменой рангов: NPC $\rightarrow$ Нормис $\rightarrow$ Эрудит $\rightarrow$ 1% Гениев.
- Проверить шкалу `StressTimer`: уменьшение интервалов 3.0с $\rightarrow$ 2.5с $\rightarrow$ 1.8с и смену цвета (синий $\rightarrow$ оранжевый $\rightarrow$ алый).
- Проверить появление пульсирующей виньетки паники на 3 уровне.
- Проверить счетчик огня `🔥 x1` ... `🔥 x9` в правом верхнем углу и синее пламя при стрике $\ge 7$.
- Проверить финальный оверлей ловушки комментариев на последних 1.5 секундах.

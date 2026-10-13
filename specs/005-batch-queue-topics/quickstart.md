# Quickstart & Verification Guide: Batch Queue & AI Topic Generator

**Feature Branch**: `005-batch-queue-topics`  
**Date**: 2026-10-13  
**Status**: Ready  

---

## 1. Prerequisites

1. Active Python virtual environment with dependencies installed:
   ```bash
   pip install -e .
   ```
2. Valid Gemini API key in `.env` (`GEMINI_API_KEY` or `GOOGLE_API_KEY`).
3. Remotion bundle ready:
   ```bash
   cd videoanalizer/remotion/quiz-ladder
   npm install
   ```

---

## 2. Validation Scenarios

### Scenario 1: Single AI Topic Ideation
Test that the AI generates a catchy, high-curiosity topic in a single click without user input.

```bash
# Automated API verification
python -c "
import asyncio, httpx
async def test():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000') as client:
        resp = await client.post('/api/v1/quiz/topics/suggest-single', json={'language': 'ru'})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        print('Generated single topic:', data['topic'], '| Category:', data['category'])
        assert len(data['topic']) > 3
asyncio.run(test())
"
```
**Expected Outcome**: Returns HTTP 200 with `topic`, `category`, and `curiosity_hook`.

---

### Scenario 2: Batch Topic Generation (1 API Request for N Topics)
Verify that generating 10 topics executes in a single Gemini request to preserve the 15 RPM quota.

```bash
python -c "
import asyncio, httpx
async def test():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000') as client:
        resp = await client.post('/api/v1/quiz/topics/suggest-batch', json={'count': 5, 'language': 'ru'})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        print(f'Generated {len(data[\"topics\"])} batch topics:')
        for idx, t in enumerate(data['topics'], 1):
            print(f' {idx}. {t[\"topic\"]} ({t[\"category\"]})')
        assert len(data['topics']) == 5
asyncio.run(test())
"
```
**Expected Outcome**: Returns exactly 5 distinct topics in a single response within 4–6 seconds.

---

### Scenario 3: 15 RPM Pacing & Progressive Script Generation
Verify that background generation paces calls with $\ge 5.0$ seconds between requests.

```bash
python -m pytest tests/unit/test_rate_limiter.py -v
```
**Expected Outcome**: Tests confirm timestamps between consecutive requests are spaced by $\ge 4.5$–$5.0$s and transient 429s trigger exponential backoff.

---

### Scenario 4: Sequential Queue Worker Execution (Concurrency = 1)
Verify that Remotion render jobs execute strictly one at a time to prevent GPU crashes.

```bash
python -m pytest tests/unit/test_batch_queue.py -v
```
**Expected Outcome**: Tests verify that while Job 1 is rendering, Job 2 remains in `queued` status until Job 1 finishes, and failures in Job 1 do not stop Job 2.

---

### Scenario 5: End-to-End UI Verification
1. Start the web application:
   ```bash
   python -m videoanalizer.ui.app
   ```
2. Open browser at `http://127.0.0.1:8000/quiz`.
3. Click "🎲 Придумать тему" in Single Mode — verify the input fills with an engaging topic.
4. Toggle to "Пакетная генерация (Очередь)", set count to 3.
5. Click "Сгенерировать темы для пачки" — review 3 generated topics.
6. Click "Создать вопросы и открыть проверку" — verify Wizard displays "Видео 1 из 3".
7. Edit questions or pick images for Video 1, click "Одобрить и далее".
8. Review Videos 2 and 3, then click "Запустить очередь рендеринга".
9. Observe live queue: Video 1 renders while Videos 2 and 3 wait in queue.
10. Download completed videos via individual buttons or "Скачать все (ZIP)".

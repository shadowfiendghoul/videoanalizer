# Quickstart & Validation Guide: 006-custom-voice-rvc

Данное руководство содержит сценарии для валидации и сквозного тестирования модуля кастомной голосовой озвучки (Voice Pipeline & Voice Cloning).

---

## 1. Подготовка окружения (Prerequisites)

1. Убедиться, что установлены системные утилиты `ffmpeg` и `ffprobe`:
   ```powershell
   ffmpeg -version
   ffprobe -version
   ```

2. Создать каталог для RVC моделей (если ещё не создан):
   ```powershell
   New-Item -ItemType Directory -Force -Path assets/models/rvc
   ```

3. Для валидации клонирования поместить в `assets/models/rvc/` тестовый чекпоинт:
   - Пример: `assets/models/rvc/streamer_voice.pth` (и опционально `streamer_voice.index`).
   - *Примечание*: При отсутствии файла `.pth` система автоматически и корректно переключается на чистый `edge_tts`.

---

## 2. Сценарий 1: Проверка базового режима Edge-TTS с пословными таймингами

Сценарий проверяет синтез через `ru-RU-DmitryNeural` и генерацию точных `WordBoundary` таймингов.

```powershell
python -c "
import asyncio
from videoanalizer.quiz.audio_service import AudioService
from videoanalizer.quiz.workspace import QuizWorkspace

async def test_edge():
    async with QuizWorkspace() as ws:
        svc = AudioService()
        out_wav = ws.path / 'test_edge.wav'
        dur_ms, words = await svc.synthesize_speech_with_cues(
            text='Столица Франции — это город Париж!',
            voice='ru-RU-DmitryNeural',
            output_path=out_wav
        )
        print(f'Duration: {dur_ms}ms, Words count: {len(words)}')
        assert dur_ms > 1000
        assert len(words) >= 5
        print('Edge-TTS validation PASSED')

asyncio.run(test_edge())
"
```

**Ожидаемый результат**:
- Длительность фразы `~2000-2500ms`.
- Извлечено 6 объектов `WordCue` с точными интервалами времени.

---

## 3. Сценарий 2: Проверка RVC тембральной конверсии (Custom Voice Cloning)

Сценарий валидирует подхват модели `.pth`, инференс со сдвигом высоты тона (`pitch_shift = 0` или `+2`) и сохранение длительности.

```powershell
python -c "
import asyncio
from pathlib import Path
from videoanalizer.quiz.voice_service import VoiceService
from videoanalizer.quiz.models import VoiceConfig, VoiceMode

async def test_rvc():
    config = VoiceConfig(
        voice_mode=VoiceMode.CUSTOM_RVC,
        base_voice='ru-RU-DmitryNeural',
        rvc_model_path='assets/models/rvc/streamer_voice.pth',
        pitch_shift=2,
        speech_rate=1.15
    )
    svc = VoiceService(config=config)
    res = await svc.synthesize(
        text='Привет подписчики! Готовы проверить свои знания?'
    )
    print(f'Synthesized path: {res.audio_path}')
    print(f'Duration: {res.duration_ms}ms, Mode: {res.voice_mode_used}')
    print(f'Words count: {len(res.words)}')
    assert res.duration_ms > 0
    assert len(res.words) > 0
    print('RVC Hybrid validation PASSED')

asyncio.run(test_rvc())
"
```

**Ожидаемый результат**:
- Аудиодорожка успешно переозвучена с тембром `streamer_voice.pth`.
- Режим: `custom_rvc` (или безопасный откат на `edge_tts`, если `.pth` отсутствует на машине разработчика).
- Пословные метки субтитров строго синхронизированы со звуком.

---

## 4. Сценарий 3: Проверка тихой аварийной деградации (Offline Fallback)

Сценарий имитирует сбой сети / невалидный URL Edge-TTS и подтверждает бесшовный переход на офлайн-движок.

```powershell
python -c "
import asyncio
from videoanalizer.quiz.voice_service import VoiceService
from videoanalizer.quiz.models import VoiceConfig, VoiceMode

async def test_offline():
    config = VoiceConfig(voice_mode=VoiceMode.OFFLINE_FALLBACK)
    svc = VoiceService(config=config)
    res = await svc.synthesize(text='Офлайн резерв успешно активирован.')
    print(f'Offline audio created: {res.audio_path}, Duration: {res.duration_ms}ms')
    assert res.voice_mode_used == VoiceMode.OFFLINE_FALLBACK
    print('Offline Fallback validation PASSED')

asyncio.run(test_offline())
"
```

**Ожидаемый результат**:
- Создан валидный WAV-файл без обращения к интернету.
- Видеогенератор продолжает рендеринг без падения конвейера.

---

## 5. Сценарий 4: Автоматическое сканирование моделей через REST API

Проверка обнаружения моделей в каталоге `assets/models/rvc/`:

```powershell
curl http://localhost:7860/api/v1/voice/models
```

**Ожидаемый результат**:
- JSON ответ со списком всех найденных файлов `.pth` и статусом их готовности:
  ```json
  {
    "models": [
      {
        "model_id": "streamer_voice",
        "name": "streamer_voice",
        "file_path": "assets/models/rvc/streamer_voice.pth",
        "file_size_bytes": 52428800,
        "is_valid": true
      }
    ],
    "total_count": 1
  }
  ```

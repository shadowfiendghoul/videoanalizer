# Quickstart: Профиль GPU-ускорения 'gpu_fast'

**Feature**: `004-gpu-fast-rendering`  
**Date**: 2026-10-12  

---

## 🚀 1. Быстрый старт через Веб-Интерфейс

1. Запустите приложение:
   ```powershell
   python -m videoanalizer
   ```
2. Откройте в браузере: `http://localhost:8000/quiz`
3. В верхней части панели настроек обратите внимание на плашку **⚡ Профиль рендеринга**:
   - По умолчанию активна опция `[⚡ GPU Fast (AMD/NVIDIA/Intel HW)]`.
   - Система автоматически отобразит вашу видеокарту, например: `🟢 GPU: AMD Radeon 780M Graphics | Энкодер: h264_amf`.
4. Введите тему квиза и нажмите кнопку **Создать видео**.
5. Наблюдайте прогресс-бар:
   - Фаза сборки бандла Remotion с `--bundle-cache` занимает менее 1 секунды.
   - Рендеринг Remotion с `--gl=angle` выполняется плавно и разгружает CPU.
   - Пост-обработка `uniquifier.py` через `h264_amf` / `h264_mf` завершается за ~1.5 секунды.

---

## 🛠️ 2. Проверка через Python CLI или API

### Проверка статуса оборудования через curl / PowerShell:
```powershell
curl http://localhost:8000/api/v1/hardware/status
```
Ответ:
```json
{
  "gpu_available": true,
  "gpu_name": "AMD Radeon 780M Graphics",
  "gpu_vendor": "amd",
  "active_hw_encoder": "h264_amf",
  "supported_encoders": ["h264_amf", "h264_mf", "libx264"],
  "gl_backend": "angle",
  "recommended_profile": "gpu_fast"
}
```

### Запуск тестов проверки аппаратного ускорения:
```powershell
python -m pytest tests/unit/test_hardware.py
```

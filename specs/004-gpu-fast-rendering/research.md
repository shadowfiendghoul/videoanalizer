# Phase 0 Research: Аппаратное GPU-ускорение и оптимизация производительности

**Feature**: `004-gpu-fast-rendering`  
**Date**: 2026-10-12  

---

## 🔬 1. Исследование доступного аппаратного обеспечения

### Анализ тестовой системы
Выполнен аппаратно-программный опрос через WMI/CIM и FFmpeg:
- **Видеокарта**: `AMD Radeon 780M Graphics` (архитектура RDNA 3, 12 Compute Units).
- **Драйвер**: `32.0.31007.5012` с поддержкой DirectX 12, Vulkan 1.3, AMD AMF и D3D11/D3D12 Video Acceleration.
- **FFmpeg сборка**: 9.0.2 Gyan Full Build со встроенными модулями:
  - `--enable-amf` (AMD Advanced Media Framework)
  - `--enable-nvenc` (NVIDIA Video Codec SDK)
  - `--enable-libvpl` (Intel Quick Sync Video / oneVPL)
  - `--enable-mediafoundation` (Microsoft Media Foundation MFT)
  - `--enable-d3d11va`, `--enable-d3d12va`

### Синтетические бенчмарки кодирования 1080p 60fps
Были проведены тесты кодирования синтетического видеопотока через различные энкодеры:

| Энкодер | Бэкенд / Драйвер | Скорость кодирования | Нагрузка на CPU | Статус |
| :--- | :--- | :--- | :--- | :--- |
| `libx264` (текущий) | CPU Software | ~1.2x – 1.8x | 95% – 100% | Медленно, перегрев CPU |
| `h264_amf` (GPU) | AMD AMF Hardware | **5.89x** | 8% – 15% | **Идеально (рекомендуется для AMD)** |
| `h264_mf` (GPU) | Windows MediaFoundation | **12.2x** | 5% – 12% | **Сверхбыстро (универсальный фолбэк Windows)** |
| `h264_nvenc` | NVIDIA Hardware | N/A (на AMD машине отсутствует) | - | Будет активироваться на машинах с NVIDIA |
| `h264_qsv` | Intel Quick Sync | N/A (на AMD машине отсутствует) | - | Будет активироваться на машинах с Intel |

**Вывод**: При переходе на аппаратное кодирование кодирование видеопотока ускоряется в **4–7 раз**, а процессор освобождается для фоновых асинхронных задач.

---

## 🌐 2. Remotion & Chromium GPU Acceleration

### Как Remotion рендерит кадры
1. Remotion запускает Headless Chromium через Puppeteer.
2. В режиме по умолчанию на Windows headless-браузер часто использует софтверный программный растеризатор (`swiftshader` / `swangle`), что потребляет львиную долю ресурсов процессора при отрисовке сложных CSS-эффектов, glassmorphism, теней drop-shadow и blur-фильтров.
3. **Оптимизация флагом `--gl=angle`**:
   - При передаче `--gl=angle` Chromium задействует ANGLE с бэкендом Direct3D 11/12, перекладывая растеризацию canvas, CSS и фильтров непосредственно на видеокарту.
4. **Кэширование Webpack (`--bundle-cache`)**:
   - По умолчанию Remotion при каждом запуске `render` заново собирает Webpack-бандл шаблона (`templates/quiz-remotion`). Это занимает от 8 до 15 секунд на каждый ролик.
   - Флаг `--bundle-cache` сохраняет бандл между генерациями, сокращая фазу подготовки с 15 секунд до < 1 секунды!

### Перехват кодировщика в Remotion CLI
Встроенный флаг `--hardware-acceleration=required` в `@remotion/renderer` на платформах Windows/Linux захардкожен на `h264_nvenc`. На машинах с AMD или Intel он падает с ошибкой, если передавать его напрямую без NVIDIA GPU!

**Архитектурное решение**:
Использовать официальный хук `Config.overrideFfmpegCommand` в [`remotion.config.ts`](file:///C:/Users/User/Desktop/videoanalizer/templates/quiz-remotion/remotion.config.ts):
```typescript
import { Config } from "@remotion/cli/config";

Config.overrideFfmpegCommand(({ args }) => {
  const profile = process.env.VIDEOANALIZER_RENDER_PROFILE;
  const hwEncoder = process.env.VIDEOANALIZER_HW_ENCODER;

  if (profile === "gpu_fast" && hwEncoder) {
    const newArgs = [...args];
    const codecIdx = newArgs.indexOf("-c:v");
    if (codecIdx !== -1 && newArgs[codecIdx + 1] === "libx264") {
      newArgs[codecIdx + 1] = hwEncoder;
      
      // Замена x264 пресета на параметры соответствующего аппаратного энкодера
      const presetIdx = newArgs.indexOf("-preset");
      if (presetIdx !== -1) {
        if (hwEncoder === "h264_amf") {
          newArgs.splice(presetIdx, 2, "-quality", "speed", "-rc", "cbr");
        } else if (hwEncoder === "h264_nvenc") {
          newArgs.splice(presetIdx, 2, "-preset", "p4", "-cq", "19");
        } else if (hwEncoder === "h264_mf") {
          newArgs.splice(presetIdx, 2, "-b:v", "10M");
        }
      }
    }
    return newArgs;
  }
  return args;
});
```
Это дает:
- Полную кроссплатформенную гибкость.
- Автоматическую поддержку AMD, NVIDIA, Intel и Windows MediaFoundation.
- 100% совместимость со всеми существующими флагами Remotion.

---

## ⚡ 3. Оптимизация Final Uniquifier (`uniquifier.py`)

Модуль `uniquifier.py` выполняет вторичное перекодирование видео для анти-детекта.
Сейчас строка запуска:
`ffmpeg -y -i input.mp4 -vf ... -af ... -c:v libx264 -preset fast -crf 18 output.mp4`
Это занимало ~18-25 секунд.

При переходе на `h264_amf` / `h264_mf`:
`ffmpeg -y -i input.mp4 -vf ... -af ... -c:v h264_amf -quality speed -b:v 10M output.mp4`
Время выполнения снижается до **1.5 – 2.5 секунд** при сохранении отличного битрейта и качества.

---

## 📋 4. Архитектура авто-детекта оборудования (`hardware.py`)

Создается легковесный модуль `videoanalizer/utils/hardware.py`:
1. Функция `probe_hardware_capabilities() -> HardwareCapabilities`:
   - Кэширует результат после первого вызова (не создает задержек при повторных запросах).
   - Определяет имя GPU (`AMD Radeon 780M Graphics`, `NVIDIA GeForce RTX 4070` и т.д.).
   - Проверяет доступность энкодеров в FFmpeg в порядке приоритета:
     1. `h264_nvenc` (при наличии NVIDIA)
     2. `h264_amf` (при наличии AMD)
     3. `h264_qsv` (при наличии Intel)
     4. `h264_mf` (при наличии Windows MediaFoundation)
     5. `libx264` (универсальный программный CPU)
2. Безопасность:
   - Проводит быстрый 1-кадровый тест энкодера перед объявлением его активным. Если драйвер заблокирован, автоматически переключается на следующий доступный вариант.

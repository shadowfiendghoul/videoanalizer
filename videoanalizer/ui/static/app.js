/**
 * VideoAnalyzer Frontend Logic
 * Modern Linear/Vercel single-page client with SSE real-time tracking
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- State ---
  let activeSourceType = 'youtube';
  let selectedFile = null;
  let sourceVideo = null;
  let highlights = [];
  let selectedHighlight = null;
  let sseSource = null;

  // --- DOM Elements ---
  // Tabs & Ingest
  const tabYoutube = document.getElementById('tab-youtube');
  const tabFile = document.getElementById('tab-file');
  const youtubeBox = document.getElementById('youtube-box');
  const fileBox = document.getElementById('file-box');
  const inputYoutubeUrl = document.getElementById('input-youtube-url');
  const btnClearUrl = document.getElementById('btn-clear-url');
  const dropZone = document.getElementById('drop-zone');
  const inputFile = document.getElementById('input-file');
  const fileSelectedName = document.getElementById('file-selected-name');

  // Sliders
  const sliderClipCount = document.getElementById('slider-clip-count');
  const labelClipCount = document.getElementById('label-clip-count');
  const sliderMinDur = document.getElementById('slider-min-dur');
  const labelMinDur = document.getElementById('label-min-dur');
  const sliderMaxDur = document.getElementById('slider-max-dur');
  const labelMaxDur = document.getElementById('label-max-dur');
  const sliderSilenceThresh = document.getElementById('slider-silence-thresh');
  const labelSilenceThresh = document.getElementById('label-silence-thresh');

  // Actions
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnAnalyzeText = document.getElementById('btn-analyze-text');
  const btnPreviewFrame = document.getElementById('btn-preview-frame');
  const btnRender = document.getElementById('btn-render');
  const btnRenderText = document.getElementById('btn-render-text');
  const btnDownload = document.getElementById('btn-download');
  const btnRegenHook = document.getElementById('btn-regen-hook');

  // Layout mode & split screen inputs
  const splitScreenParams = document.getElementById('split-screen-params');
  const webcamX = document.getElementById('webcam-x');
  const webcamY = document.getElementById('webcam-y');
  const webcamW = document.getElementById('webcam-w');
  const webcamH = document.getElementById('webcam-h');
  const gameplayX = document.getElementById('gameplay-x');
  const gameplayY = document.getElementById('gameplay-y');
  const gameplayW = document.getElementById('gameplay-w');
  const gameplayH = document.getElementById('gameplay-h');
  const btnPresetStandard = document.getElementById('btn-preset-standard');
  const btnPresetReset = document.getElementById('btn-preset-reset');

  // Effects & Subtitles
  const checkSilence = document.getElementById('check-silence');
  const silenceOptions = document.getElementById('silence-options');
  const checkSubtitles = document.getElementById('check-subtitles');
  const subtitlesOptions = document.getElementById('subtitles-options');
  const subFontSize = document.getElementById('sub-font-size');
  const subActiveColor = document.getElementById('sub-active-color');
  const subInactiveColor = document.getElementById('sub-inactive-color');
  const checkBanner = document.getElementById('check-banner');
  const bannerOptions = document.getElementById('banner-options');
  const inputBannerText = document.getElementById('input-banner-text');

  // Highlights & Timing
  const highlightsContainer = document.getElementById('highlights-container');
  const highlightsCountBadge = document.getElementById('highlights-count-badge');
  const currentStartSec = document.getElementById('current-start-sec');
  const currentEndSec = document.getElementById('current-end-sec');
  const currentDurationText = document.getElementById('current-duration-text');

  // Player / Canvas
  const previewPlaceholder = document.getElementById('preview-placeholder');
  const previewFrameImg = document.getElementById('preview-frame-img');
  const renderedVideoPlayer = document.getElementById('rendered-video-player');

  // Progress & SSE
  const progressStageTitle = document.getElementById('progress-stage-title');
  const progressPercentBadge = document.getElementById('progress-percent-badge');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const sseIndicator = document.getElementById('sse-indicator');
  const sseStatusText = document.getElementById('sse-status-text');

  // --- 1. Real-Time SSE Setup ---
  function connectSSE() {
    if (sseSource) {
      sseSource.close();
    }

    sseSource = new EventSource('/api/progress');

    sseSource.onopen = () => {
      sseIndicator.className = 'flex items-center space-x-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full';
      sseStatusText.textContent = 'Онлайн';
    };

    sseSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        updateProgressUI(data);
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    sseSource.onerror = () => {
      sseIndicator.className = 'flex items-center space-x-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-full';
      sseStatusText.textContent = 'Переподключение...';
    };
  }

  function updateProgressUI(data) {
    if (!data) return;

    const percent = Math.min(100, Math.max(0, data.percent || 0));
    const stage = data.stage || 'Ожидание задач';

    progressStageTitle.textContent = stage;
    progressPercentBadge.textContent = `${percent}%`;
    progressBarFill.style.width = `${percent}%`;

    // Highlight 5 milestone stages
    updateMilestones(percent, stage);
  }

  function updateMilestones(percent, stage) {
    const steps = [
      { id: 'stage-step-1', threshold: 10, key: 'Скачивание' },
      { id: 'stage-step-2', threshold: 35, key: 'Анализ' },
      { id: 'stage-step-3', threshold: 50, key: 'Кадрирование' },
      { id: 'stage-step-4', threshold: 75, key: 'Караоке' },
      { id: 'stage-step-5', threshold: 100, key: 'Готово' },
    ];

    steps.forEach((step, idx) => {
      const el = document.getElementById(step.id);
      if (!el) return;

      const isCurrent = (stage && stage.toLowerCase().includes(step.key.toLowerCase())) || 
                        (percent >= step.threshold && (idx === steps.length - 1 || percent < steps[idx + 1].threshold));
      const isPassed = percent >= step.threshold;

      if (isPassed || percent === 100) {
        el.className = 'flex items-center space-x-1.5 text-emerald-400 font-medium truncate';
        el.innerHTML = `<i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-emerald-400"></i><span class="truncate">${el.textContent.trim()}</span>`;
      } else if (isCurrent) {
        el.className = 'flex items-center space-x-1.5 text-purple-400 font-semibold truncate animate-pulse';
        el.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 text-purple-400 animate-spin"></i><span class="truncate">${el.textContent.trim()}</span>`;
      } else {
        el.className = 'flex items-center space-x-1.5 text-slate-500 truncate';
        el.innerHTML = `<i data-lucide="circle" class="w-3.5 h-3.5 text-slate-600"></i><span class="truncate">${el.textContent.trim()}</span>`;
      }
    });

    if (window.lucide) {
      lucide.createIcons();
    }
  }

  connectSSE();

  // --- 2. Sliders Synchronization ---
  sliderClipCount.addEventListener('input', () => {
    labelClipCount.textContent = sliderClipCount.value;
  });

  sliderMinDur.addEventListener('input', () => {
    const minVal = parseInt(sliderMinDur.value);
    const maxVal = parseInt(sliderMaxDur.value);
    if (minVal > maxVal) {
      sliderMaxDur.value = minVal;
      labelMaxDur.textContent = `${minVal}с`;
    }
    labelMinDur.textContent = `${minVal}с`;
  });

  sliderMaxDur.addEventListener('input', () => {
    const minVal = parseInt(sliderMinDur.value);
    const maxVal = parseInt(sliderMaxDur.value);
    if (maxVal < minVal) {
      sliderMinDur.value = maxVal;
      labelMinDur.textContent = `${maxVal}с`;
    }
    labelMaxDur.textContent = `${maxVal}с`;
  });

  sliderSilenceThresh.addEventListener('input', () => {
    labelSilenceThresh.textContent = `${parseFloat(sliderSilenceThresh.value).toFixed(1)}с`;
  });

  // --- 3. Source Tabs & File Upload ---
  tabYoutube.addEventListener('click', () => {
    activeSourceType = 'youtube';
    tabYoutube.classList.add('active', 'text-white');
    tabYoutube.classList.remove('text-slate-400');
    tabFile.classList.remove('active', 'text-white');
    tabFile.classList.add('text-slate-400');
    youtubeBox.classList.remove('hidden');
    fileBox.classList.add('hidden');
  });

  tabFile.addEventListener('click', () => {
    activeSourceType = 'file';
    tabFile.classList.add('active', 'text-white');
    tabFile.classList.remove('text-slate-400');
    tabYoutube.classList.remove('active', 'text-white');
    tabYoutube.classList.add('text-slate-400');
    fileBox.classList.remove('hidden');
    youtubeBox.classList.add('hidden');
  });

  btnClearUrl.addEventListener('click', () => {
    inputYoutubeUrl.value = '';
    inputYoutubeUrl.focus();
  });

  dropZone.addEventListener('click', () => inputFile.click());

  inputFile.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('border-purple-500', 'bg-purple-950/20');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('border-purple-500', 'bg-purple-950/20');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-purple-500', 'bg-purple-950/20');
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  function handleFileSelected(file) {
    selectedFile = file;
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
    fileSelectedName.textContent = `✓ ${file.name} (${sizeMb} MB)`;
    fileSelectedName.classList.remove('text-slate-500');
    fileSelectedName.classList.add('text-emerald-400', 'font-medium');
  }

  // --- 4. Reframing & Layout Mode Toggles ---
  document.querySelectorAll('input[name="layout-mode"]').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      if (e.target.value === 'split_screen') {
        splitScreenParams.classList.remove('hidden');
      } else {
        splitScreenParams.classList.add('hidden');
      }
    });
  });

  btnPresetStandard.addEventListener('click', () => {
    webcamX.value = 0;
    webcamY.value = 0;
    webcamW.value = 400;
    webcamH.value = 400;
    gameplayX.value = 0;
    gameplayY.value = 0;
    gameplayW.value = 1920;
    gameplayH.value = 1080;
  });

  btnPresetReset.addEventListener('click', () => {
    webcamX.value = 0;
    webcamY.value = 0;
    webcamW.value = 0;
    webcamH.value = 0;
    gameplayX.value = 0;
    gameplayY.value = 0;
    gameplayW.value = 0;
    gameplayH.value = 0;
  });

  // Effects toggles visibility
  checkSilence.addEventListener('change', (e) => {
    silenceOptions.style.opacity = e.target.checked ? '1' : '0.4';
    sliderSilenceThresh.disabled = !e.target.checked;
  });

  checkSubtitles.addEventListener('change', (e) => {
    subtitlesOptions.style.opacity = e.target.checked ? '1' : '0.4';
    subFontSize.disabled = !e.target.checked;
    subActiveColor.disabled = !e.target.checked;
    subInactiveColor.disabled = !e.target.checked;
  });

  checkBanner.addEventListener('change', (e) => {
    bannerOptions.style.opacity = e.target.checked ? '1' : '0.4';
    inputBannerText.disabled = !e.target.checked;
  });

  // --- 5. Action: Analyze Video (Ingest & Gemini) ---
  btnAnalyze.addEventListener('click', async () => {
    const isUrl = activeSourceType === 'youtube';
    const url = inputYoutubeUrl.value.trim();

    if (isUrl && !url) {
      alert('Пожалуйста, введите корректную ссылку на YouTube.');
      inputYoutubeUrl.focus();
      return;
    }

    if (!isUrl && !selectedFile) {
      alert('Пожалуйста, выберите видеофайл для анализа.');
      return;
    }

    // Set UI loading state
    btnAnalyze.disabled = true;
    btnAnalyzeText.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span> Обработка...';

    const formData = new FormData();
    if (isUrl) {
      formData.append('url', url);
    } else {
      formData.append('file', selectedFile);
    }
    formData.append('clip_count', sliderClipCount.value);
    formData.append('min_duration', sliderMinDur.value);
    formData.append('max_duration', sliderMaxDur.value);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.detail || result.error || 'Ошибка анализа видео');
      }

      sourceVideo = result.video;
      highlights = result.highlights || [];

      renderHighlights(highlights);

      if (highlights.length > 0) {
        selectHighlight(highlights[0]);
      }
    } catch (err) {
      console.error('Analysis error:', err);
      alert(`Ошибка: ${err.message}`);
    } finally {
      btnAnalyze.disabled = false;
      btnAnalyzeText.innerHTML = 'Найти смешные моменты (Gemini AI)';
    }
  });

  // --- 6. Render Highlights List ---
  function renderHighlights(items) {
    highlightsCountBadge.textContent = `${items.length} ${getNoun(items.length, 'момент', 'момента', 'моментов')}`;

    if (!items || items.length === 0) {
      highlightsContainer.innerHTML = `
        <div class="text-center py-8 text-slate-500">
          <p class="text-xs">Смешных моментов по заданным критериям не найдено.</p>
        </div>
      `;
      return;
    }

    highlightsContainer.innerHTML = '';

    items.forEach((item, index) => {
      const card = document.createElement('div');
      card.className = `highlight-card p-3.5 rounded-xl cursor-pointer relative ${selectedHighlight && selectedHighlight.id === item.id ? 'selected' : ''}`;
      card.dataset.id = item.id;

      const duration = (item.end_sec - item.start_sec).toFixed(1);
      const startFormatted = formatTime(item.start_sec);
      const endFormatted = formatTime(item.end_sec);

      card.innerHTML = `
        <div class="flex items-start justify-between gap-2 mb-2">
          <div class="flex items-center space-x-2">
            <span class="w-5 h-5 rounded-md bg-purple-500/20 text-purple-300 flex items-center justify-center text-[10px] font-bold">
              #${index + 1}
            </span>
            <span class="text-xs font-semibold text-white tracking-wide">
              ${escapeHtml(item.suggested_headline || 'Смешной момент')}
            </span>
          </div>
          <div class="flex items-center space-x-1.5 shrink-0">
            <span class="text-xs px-2 py-0.5 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-300 font-mono font-bold flex items-center gap-1">
              <span>🔥</span> ${item.humor_score.toFixed(1)}/10
            </span>
          </div>
        </div>

        <p class="text-xs text-slate-300 mb-2 line-clamp-2 leading-relaxed">
          ${escapeHtml(item.summary || item.transcript || '')}
        </p>

        <div class="flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-white/[0.04]">
          <span class="font-mono text-purple-300">${startFormatted} &rarr; ${endFormatted}</span>
          <span class="text-slate-500">${duration} сек</span>
        </div>
      `;

      card.addEventListener('click', () => {
        selectHighlight(item);
      });

      highlightsContainer.appendChild(card);
    });

    if (window.lucide) {
      lucide.createIcons();
    }
  }

  function selectHighlight(item) {
    selectedHighlight = item;

    // Update active highlight card styles
    document.querySelectorAll('.highlight-card').forEach((card) => {
      if (card.dataset.id === item.id) {
        card.classList.add('selected');
      } else {
        card.classList.remove('selected');
      }
    });

    // Populate timing inputs
    currentStartSec.value = item.start_sec.toFixed(1);
    currentEndSec.value = item.end_sec.toFixed(1);
    updateCurrentDuration();

    // Fill suggested hook headline
    if (item.suggested_headline) {
      inputBannerText.value = item.suggested_headline;
    }

    // Enable render button
    btnRender.disabled = false;

    // Trigger preview frame automatically
    loadPreviewFrame(item.start_sec);
  }

  function updateCurrentDuration() {
    const start = parseFloat(currentStartSec.value) || 0;
    const end = parseFloat(currentEndSec.value) || 0;
    const dur = Math.max(0, end - start).toFixed(1);
    currentDurationText.textContent = `${dur}с`;
  }

  currentStartSec.addEventListener('input', updateCurrentDuration);
  currentEndSec.addEventListener('input', updateCurrentDuration);

  // --- 7. Action: Preview Frame 9:16 ---
  btnPreviewFrame.addEventListener('click', () => {
    const timestamp = parseFloat(currentStartSec.value) || 0;
    loadPreviewFrame(timestamp);
  });

  async function loadPreviewFrame(timestamp) {
    if (!sourceVideo) return;

    btnPreviewFrame.disabled = true;

    const layoutMode = document.querySelector('input[name="layout-mode"]:checked').value;
    const webcamPos = document.querySelector('input[name="webcam-pos"]:checked').value;

    const payload = {
      timestamp_sec: timestamp,
      mode: layoutMode,
      webcam_position: webcamPos,
      webcam_box: {
        x: parseInt(webcamX.value) || 0,
        y: parseInt(webcamY.value) || 0,
        width: parseInt(webcamW.value) || 400,
        height: parseInt(webcamH.value) || 400,
      },
      gameplay_box: {
        x: parseInt(gameplayX.value) || 0,
        y: parseInt(gameplayY.value) || 0,
        width: parseInt(gameplayW.value) || 1920,
        height: parseInt(gameplayH.value) || 1080,
      },
    };

    try {
      const response = await fetch('/api/preview-frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error('Не удалось сгенерировать превью кадра');
      }

      const blob = await response.blob();
      const imageUrl = URL.createObjectURL(blob);

      previewPlaceholder.classList.add('hidden');
      renderedVideoPlayer.classList.add('hidden');
      previewFrameImg.src = imageUrl;
      previewFrameImg.classList.remove('hidden');
    } catch (err) {
      console.error('Preview error:', err);
    } finally {
      btnPreviewFrame.disabled = false;
    }
  }

  // --- 8. Action: Render Short ---
  btnRender.addEventListener('click', async () => {
    if (!selectedHighlight || !sourceVideo) {
      alert('Сначала выберите момент для рендера.');
      return;
    }

    const startSec = parseFloat(currentStartSec.value);
    const endSec = parseFloat(currentEndSec.value);

    if (endSec <= startSec) {
      alert('Время конца должно быть больше времени старта.');
      return;
    }

    btnRender.disabled = true;
    btnRenderText.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span> Рендеринг short...';
    btnDownload.classList.add('hidden');

    const layoutMode = document.querySelector('input[name="layout-mode"]:checked').value;
    const webcamPos = document.querySelector('input[name="webcam-pos"]:checked').value;
    const bannerPos = document.querySelector('input[name="banner-pos"]:checked').value;

    const payload = {
      highlight_id: selectedHighlight.id,
      start_sec: startSec,
      end_sec: endSec,
      layout: {
        mode: layoutMode,
        webcam_position: webcamPos,
        webcam_box: {
          x: parseInt(webcamX.value) || 0,
          y: parseInt(webcamY.value) || 0,
          width: parseInt(webcamW.value) || 400,
          height: parseInt(webcamH.value) || 400,
        },
        gameplay_box: {
          x: parseInt(gameplayX.value) || 0,
          y: parseInt(gameplayY.value) || 0,
          width: parseInt(gameplayW.value) || 1920,
          height: parseInt(gameplayH.value) || 1080,
        },
      },
      silence: {
        enabled: checkSilence.checked,
        threshold_sec: parseFloat(sliderSilenceThresh.value) || 1.0,
      },
      subtitles: {
        enabled: checkSubtitles.checked,
        font_size: parseInt(subFontSize.value) || 42,
        active_color: subActiveColor.value,
        inactive_color: subInactiveColor.value,
      },
      banner: {
        enabled: checkBanner.checked,
        text: inputBannerText.value.trim(),
        position: bannerPos,
      },
    };

    try {
      const response = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (!response.ok || !result.success) {
        throw new Error(result.detail || result.error || 'Ошибка рендеринга');
      }

      // Display rendered MP4 in vertical video player
      previewPlaceholder.classList.add('hidden');
      previewFrameImg.classList.add('hidden');
      renderedVideoPlayer.src = result.download_url;
      renderedVideoPlayer.classList.remove('hidden');
      renderedVideoPlayer.load();
      renderedVideoPlayer.play().catch(() => {});

      // Activate download button
      btnDownload.href = result.download_url;
      btnDownload.download = result.filename;
      btnDownload.classList.remove('hidden');

    } catch (err) {
      console.error('Render error:', err);
      alert(`Ошибка рендера: ${err.message}`);
    } finally {
      btnRender.disabled = false;
      btnRenderText.textContent = 'Сгенерировать вертикальный Short';
    }
  });

  // --- 9. Action: Regenerate Hook Headline ---
  btnRegenHook.addEventListener('click', async () => {
    if (!selectedHighlight) return;

    btnRegenHook.classList.add('animate-spin');
    try {
      const response = await fetch('/api/regenerate-headline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ highlight_id: selectedHighlight.id }),
      });
      const data = await response.json();
      if (data.headline) {
        inputBannerText.value = data.headline;
      }
    } catch (err) {
      console.error('Headline regen error:', err);
    } finally {
      btnRegenHook.classList.remove('animate-spin');
    }
  });

  // --- Helper Functions ---
  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function getNoun(number, one, two, five) {
    let n = Math.abs(number);
    n %= 100;
    if (n >= 5 && n <= 20) return five;
    n %= 10;
    if (n === 1) return one;
    if (n >= 2 && n <= 4) return two;
    return five;
  }

  // --- Auto-restore state on page load/refresh ---
  fetch('/api/state')
    .then((res) => res.json())
    .then((data) => {
      if (data && data.has_video && data.highlights && data.highlights.length > 0) {
        sourceVideo = data.video;
        highlights = data.highlights;
        renderHighlights(highlights);
        selectHighlight(highlights[0]);
      }
    })
    .catch((e) => console.log('State restore skipped:', e));
});

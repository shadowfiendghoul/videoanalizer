# VideoAnalyzer 🎬

**AI-powered funny moments detection and TikTok/Shorts vertical video generator**  
Powered by **Google Gemini 2.5 Flash Native Audio Dialog** and **FFmpeg**.

---

## Features

- 📥 **Video Ingestion**: Paste a public YouTube link or upload a local video file (`.mp4`, `.mkv`, `.mov`, `.webm`).
- 🤖 **AI Humor & Punchline Analysis**: Identifies the funniest moments, comedic timing, voice reactions, and punchlines using Gemini 2.5 Flash.
- ⏱️ **Configurable Clips**: Configure target clip count (1–10) and duration window (15–90s) with manual boundary adjustment.
- 📐 **Vertical 9:16 Reframing**:
  - Simple centered crop (`1080x1920`).
  - **Streamer Split-Screen**: stack webcam/reaction on top and gameplay/content on bottom with custom coordinate boxes and live frame preview.
- ✂️ **Smart Silence Removal**: Cut dead air with 100ms safety padding and 25ms audio micro-crossfades to preserve natural comedic cadence without audio clicks.
- 💬 **TikTok Karaoke Subtitles**: Dynamic word-by-word highlighted captions in the lower third using ASS subtitle styles.
- 🏷️ **AI Hook Headlines**: Automatic viral hook headlines with manual editing capability for the top banner.
- 💾 **Export & Batch Render**: Built-in video preview player and local MP4 downloads.

---

## Architecture

```text
videoanalizer/
├── config.py             # Pydantic Settings (API keys, defaults, paths)
├── exceptions.py         # Custom domain exception hierarchy
├── models/               # Strict Pydantic v2 data models
├── services/             # Domain logic (ingestion, Gemini analysis, silence, transcriber, headlines)
├── media/                # FFmpeg isolated media pipeline (clipper, reframer, subtitler, overlay, renderer)
├── ui/                   # Decoupled Gradio web interface (5 workflow tabs)
└── utils/                # Temp workspace lifecycle and diagnostics
```

---

## Quickstart

### 1. Prerequisites

- **Python 3.11+**
- **FFmpeg** installed and added to `PATH`
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`

### 2. Installation

```bash
# Clone repository and navigate to directory
cd videoanalizer

# Install dependencies
pip install -e .
```

### 3. Configure API Key

Copy `.env.example` to `.env` and set your Google Gemini API key:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
OUTPUT_DIR=./output
```

### 4. Run Application

**Windows (One-Click):**
Просто дважды кликните по файлу **`start.bat`**. Он сам проверит окружение, библиотеки, наличие FFmpeg, откроет браузер и запустит сервер!

**Либо вручную через консоль:**
```bash
python -m videoanalizer
```

Open your browser at `http://localhost:7860`.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT

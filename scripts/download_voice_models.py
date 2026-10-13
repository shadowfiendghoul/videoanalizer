"""Download and verify AI voice models for VideoAnalyzer.

Supports:
- Qwen3-TTS (Qwen/Qwen3-TTS-12Hz-0.6B-Base) for expressive speech generation
- ContentVec / HuBERT (lengyue233/content-vec-best) for RVC phonetic features
- Piper TTS Russian models (Denis, Dmitri)
- RVC model directory structure setup
"""

import argparse
import logging
import sys
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("VoiceModelDownloader")

ROOT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT_DIR / "assets" / "models"
QWEN_DIR = MODELS_DIR / "qwen3_tts"
RVC_DIR = MODELS_DIR / "rvc"
PIPER_DIR = MODELS_DIR / "piper"
VOICES_DIR = ROOT_DIR / "assets" / "voices"

PIPER_MODELS = {
    "denis": {
        "onnx": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main"
            "/ru/ru_RU/denis/medium/ru_RU-denis-medium.onnx"
        ),
        "json": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main"
            "/ru/ru_RU/denis/medium/ru_RU-denis-medium.onnx.json"
        ),
        "file_prefix": "ru_RU-denis-medium",
    },
    "dmitri": {
        "onnx": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main"
            "/ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx"
        ),
        "json": (
            "https://huggingface.co/rhasspy/piper-voices/resolve/main"
            "/ru/ru_RU/dmitri/medium/ru_RU-dmitri-medium.onnx.json"
        ),
        "file_prefix": "ru_RU-dmitri-medium",
    },
}


def ensure_directories() -> None:
    """Ensure all model and voice asset directories exist."""
    for d in [QWEN_DIR, RVC_DIR, PIPER_DIR, VOICES_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    gitkeep = RVC_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()


def download_qwen3_tts(force: bool = False) -> bool:
    """Download Qwen3-TTS 12Hz 0.6B Base model via huggingface_hub."""
    logger.info("--- Checking Qwen3-TTS Base Model ---")
    weights_file = QWEN_DIR / "model.safetensors"

    if not force and weights_file.exists() and weights_file.stat().st_size > 1_000_000_000:
        size_gb = weights_file.stat().st_size / (1024**3)
        logger.info("[OK] Qwen3-TTS model weights already present (%.2f GB)", size_gb)
        return True

    try:
        from huggingface_hub import snapshot_download

        logger.info("Downloading 'Qwen/Qwen3-TTS-12Hz-0.6B-Base' to %s...", QWEN_DIR)
        snapshot_download(
            repo_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            local_dir=str(QWEN_DIR),
            local_dir_use_symlinks=False,
        )
        logger.info("[SUCCESS] Qwen3-TTS weights successfully downloaded!")
        return True
    except ImportError:
        logger.error("[ERROR] 'huggingface_hub' is required. Run: pip install huggingface_hub")
        return False
    except Exception as exc:
        logger.error("[ERROR] Failed to download Qwen3-TTS model: %s", exc)
        return False


def download_contentvec(force: bool = False) -> bool:
    """Pre-cache ContentVec / HuBERT speech representation model."""
    logger.info("--- Checking ContentVec / HuBERT Model ---")
    try:
        from transformers import HubertModel

        logger.info("Pre-caching 'lengyue233/content-vec-best' from Hugging Face...")
        HubertModel.from_pretrained("lengyue233/content-vec-best")
        logger.info("[SUCCESS] ContentVec / HuBERT model cached and ready!")
        return True
    except ImportError:
        logger.error("[ERROR] 'transformers' is required. Run: pip install transformers")
        return False
    except Exception as exc:
        logger.error("[ERROR] Failed to pre-cache ContentVec model: %s", exc)
        return False


def download_piper_voices(force: bool = False) -> bool:
    """Download Russian Piper voice models (Denis & Dmitri)."""
    logger.info("--- Checking Russian Piper Voice Models ---")
    all_ok = True
    for name, urls in PIPER_MODELS.items():
        onnx_dest = PIPER_DIR / f"{urls['file_prefix']}.onnx"
        json_dest = PIPER_DIR / f"{urls['file_prefix']}.onnx.json"

        # Download ONNX
        if force or not onnx_dest.exists() or onnx_dest.stat().st_size < 1_000_000:
            logger.info("Downloading Piper [%s] ONNX model...", name)
            try:
                urllib.request.urlretrieve(urls["onnx"], onnx_dest)  # noqa: S310
                size_mb = onnx_dest.stat().st_size / (1024**2)
                logger.info("[OK] Downloaded %s (%.2f MB)", onnx_dest.name, size_mb)
            except Exception as e:
                logger.error("[ERROR] Failed to download %s: %s", onnx_dest.name, e)
                all_ok = False
        else:
            logger.info("[OK] Piper [%s] ONNX model already present.", name)

        # Download JSON
        if force or not json_dest.exists():
            logger.info("Downloading Piper [%s] config JSON...", name)
            try:
                urllib.request.urlretrieve(urls["json"], json_dest)  # noqa: S310
                logger.info("[OK] Downloaded %s", json_dest.name)
            except Exception as e:
                logger.error("[ERROR] Failed to download %s: %s", json_dest.name, e)
                all_ok = False
        else:
            logger.info("[OK] Piper [%s] config JSON already present.", name)

    return all_ok


def check_rvc_models() -> None:
    """Check local RVC models directory and report available checkpoints."""
    logger.info("--- Checking RVC Voice Models ---")
    models = list(RVC_DIR.glob("*.pth"))
    if models:
        logger.info("[OK] Found %d RVC model checkpoint(s):", len(models))
        for m in models:
            idx = m.with_suffix(".index")
            has_idx = " (with .index)" if idx.exists() else " (no .index)"
            logger.info("  - %s (%.2f MB)%s", m.name, m.stat().st_size / (1024**2), has_idx)
    else:
        logger.warning(
            "[NOTICE] No .pth checkpoints in %s.\n"
            "         Place custom RVC models (.pth and .index) there.",
            RVC_DIR,
        )


def check_reference_voices() -> None:
    """Check available voice reference samples for cloning."""
    logger.info("--- Checking Reference Voice Samples ---")
    refs = list(VOICES_DIR.glob("*.wav")) + list(VOICES_DIR.glob("*.mp3"))
    if refs:
        logger.info("[OK] Found %d reference voice sample(s):", len(refs))
        for r in refs:
            logger.info("  - %s (%.2f KB)", r.name, r.stat().st_size / 1024)
    else:
        logger.warning(
            "[NOTICE] No reference audio in %s. Add reference .wav files for speaker cloning.",
            VOICES_DIR,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Download AI voice models for VideoAnalyzer.")
    parser.add_argument("--qwen", action="store_true", help="Download Qwen3-TTS model")
    parser.add_argument("--contentvec", action="store_true", help="Pre-cache ContentVec / HuBERT")
    parser.add_argument("--piper", action="store_true", help="Download Piper Russian voices")
    parser.add_argument("--all", action="store_true", help="Download all voice models")
    parser.add_argument("--force", action="store_true", help="Force re-download files")
    parser.add_argument(
        "--check-only", action="store_true", help="Only verify existing models without downloading"
    )
    args = parser.parse_args()

    ensure_directories()

    if args.check_only:
        logger.info("Checking voice model files...")
        download_qwen3_tts(force=False)
        check_rvc_models()
        check_reference_voices()
        download_piper_voices(force=False)
        return 0

    download_all = args.all or (not args.qwen and not args.contentvec and not args.piper)

    success = True
    if download_all or args.qwen:
        success = download_qwen3_tts(force=args.force) and success

    if download_all or args.contentvec:
        success = download_contentvec(force=args.force) and success

    if download_all or args.piper:
        success = download_piper_voices(force=args.force) and success

    check_rvc_models()
    check_reference_voices()

    if success:
        logger.info("=====================================================")
        logger.info("   [SUCCESS] All requested voice models are ready!   ")
        logger.info("=====================================================")
        return 0
    else:
        logger.warning("=====================================================")
        logger.warning("   [WARN] Some models could not be downloaded.       ")
        logger.warning("=====================================================")
        return 1


if __name__ == "__main__":
    sys.exit(main())

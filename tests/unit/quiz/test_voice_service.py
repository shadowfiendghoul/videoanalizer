"""Unit tests for VoiceService, RvcModelRegistry, and multi-tier speech fallback."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from videoanalizer.quiz.models import (
    VoiceConfig,
    VoiceMode,
)
from videoanalizer.quiz.voice_service import RvcModelRegistry, VoiceService


class MockAsyncStream:
    """Mock edge_tts stream generating synthetic audio and WordBoundary events."""

    def __init__(self, words: list[str]) -> None:
        self.words = words

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        yield {"type": "audio", "data": b"RIFFmockaudiodata"}
        offset = 0
        dur = 3000000  # 300ms in 100ns units
        for w in self.words:
            yield {
                "type": "WordBoundary",
                "text": w,
                "offset": offset,
                "duration": dur,
            }
            offset += dur


def test_rvc_model_registry_discovery(tmp_path: Path) -> None:
    """Test model scanning in assets/models/rvc/ finding .pth and .index."""
    models_dir = tmp_path / "models" / "rvc"
    models_dir.mkdir(parents=True)

    # Empty directory
    registry = RvcModelRegistry(models_dir=models_dir)
    assert registry.discover_models() == []

    # Create dummy models
    m1_pth = models_dir / "streamer_alpha.pth"
    m1_pth.write_bytes(b"dummy weights 1")
    m1_idx = models_dir / "streamer_alpha.index"
    m1_idx.write_bytes(b"dummy index 1")

    m2_pth = models_dir / "narrator_deep.pth"
    m2_pth.write_bytes(b"dummy weights 2")

    discovered = registry.discover_models()
    assert len(discovered) == 2

    # Check streamer_alpha
    model_alpha = registry.get_model("streamer_alpha")
    assert model_alpha is not None
    assert model_alpha.model_id == "streamer_alpha"
    assert model_alpha.index_path is not None
    assert model_alpha.file_size_bytes > 0
    assert model_alpha.is_valid is True

    # Check narrator_deep (without index)
    model_deep = registry.get_model("narrator_deep")
    assert model_deep is not None
    assert model_deep.index_path is None
    assert model_deep.file_size_bytes > 0


@pytest.mark.asyncio
async def test_voice_service_edge_tts_mode(tmp_path: Path) -> None:
    """Test Edge-TTS synthesis with rate scaling and WordBoundary extraction."""
    svc = VoiceService()
    out_file = tmp_path / "test_edge.wav"
    config = VoiceConfig(
        voice_mode=VoiceMode.EDGE_TTS,
        base_voice="ru-RU-DmitryNeural",
        speech_rate=1.15,
    )

    mock_words = ["Привет", "мир", "викторина"]
    mock_stream = MockAsyncStream(mock_words)

    with patch("edge_tts.Communicate") as mock_comm, patch(
        "videoanalizer.quiz.voice_service.probe_audio_duration_ms", return_value=1200
    ), patch("subprocess.run"):
        instance = MagicMock()
        instance.stream = MagicMock(return_value=mock_stream)
        mock_comm.return_value = instance

        result = await svc.synthesize(
            text="Привет, мир! Викторина",
            output_path=out_file,
            config=config,
        )

        assert result.voice_mode_used == VoiceMode.EDGE_TTS
        assert result.duration_ms == 1200
        assert len(result.words) == 3
        assert result.words[0].word == "Привет"
        assert result.words[0].start_ms == 0
        assert result.words[0].end_ms == 300
        mock_comm.assert_called_once()
        # Verify rate_arg "+15%" was supplied for 1.15 rate
        args, kwargs = mock_comm.call_args
        assert kwargs.get("rate") == "+15%"


@pytest.mark.asyncio
async def test_voice_service_offline_fallback(tmp_path: Path) -> None:
    """Test direct offline fallback generating valid audio and synthetic WordTimings."""
    svc = VoiceService()
    out_file = tmp_path / "test_offline.wav"
    config = VoiceConfig(voice_mode=VoiceMode.OFFLINE_FALLBACK)

    with patch(
        "videoanalizer.quiz.voice_service.probe_audio_duration_ms", return_value=1500
    ):
        result = await svc.synthesize(
            text="Это оффлайн синтез речи",
            output_path=out_file,
            config=config,
        )

        assert result.voice_mode_used == VoiceMode.OFFLINE_FALLBACK
        assert result.duration_ms == 1500
        assert len(result.words) == 4
        assert result.words[0].word == "Это"
        assert Path(result.audio_path).exists()


@pytest.mark.asyncio
async def test_voice_service_degradation_ladder(tmp_path: Path) -> None:
    """Test automatic degradation from CUSTOM_RVC to EDGE_TTS, and EDGE_TTS to OFFLINE_FALLBACK."""
    svc = VoiceService()
    out_file = tmp_path / "test_degrade.wav"

    # 1. Custom RVC fails because model is missing -> degrades to Edge-TTS when allow_fallback=True
    config_rvc = VoiceConfig(
        voice_mode=VoiceMode.CUSTOM_RVC,
        rvc_model_path="non_existent_voice.pth",
        allow_fallback=True,
    )

    mock_stream = MockAsyncStream(["тест"])
    with patch("edge_tts.Communicate") as mock_comm, patch(
        "videoanalizer.quiz.voice_service.probe_audio_duration_ms", return_value=800
    ), patch("subprocess.run"):
        instance = MagicMock()
        instance.stream = MagicMock(return_value=mock_stream)
        mock_comm.return_value = instance

        result = await svc.synthesize(
            text="тест деградации",
            output_path=out_file,
            config=config_rvc,
        )

        # Degraded to EDGE_TTS
        assert result.voice_mode_used == VoiceMode.EDGE_TTS

    # 2. Edge-TTS network exception -> degrades to OFFLINE_FALLBACK when allow_fallback=True
    config_edge = VoiceConfig(voice_mode=VoiceMode.EDGE_TTS, allow_fallback=True)
    with patch("edge_tts.Communicate", side_effect=ConnectionError("Network down")), patch(
        "videoanalizer.quiz.voice_service.probe_audio_duration_ms", return_value=1000
    ):
        result = await svc.synthesize(
            text="один два три четыре",
            output_path=out_file,
            config=config_edge,
        )

        assert result.voice_mode_used == VoiceMode.OFFLINE_FALLBACK
        assert len(result.words) == 4


@pytest.mark.asyncio
async def test_voice_service_strict_consistency_disallows_offline_fallback(
    tmp_path: Path,
) -> None:
    """Verify that with allow_fallback=False (default), errors raise instead of robot voice."""
    svc = VoiceService()
    out_file = tmp_path / "test_strict.wav"
    config_edge = VoiceConfig(voice_mode=VoiceMode.EDGE_TTS, allow_fallback=False)

    with (
        patch("edge_tts.Communicate", side_effect=ConnectionError("Network down")),
        pytest.raises(RuntimeError),
    ):
        await svc.synthesize(
            text="строгий режим без робота",
            output_path=out_file,
            config=config_edge,
        )


def test_compress_speech_pauses() -> None:
    """Test pause compression cuts excessive silences while preserving short natural gaps."""
    import numpy as np

    from videoanalizer.quiz.voice_service import compress_speech_pauses

    sr = 24000
    # 0.5s audio tone + 1.5s silence + 0.5s audio tone
    tone = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, int(sr * 0.5))) * 0.5
    silence = np.zeros(int(sr * 1.5))
    signal = np.concatenate([tone, silence, tone])

    orig_dur = len(signal) / sr
    tightened = compress_speech_pauses(signal, sr, max_pause_sec=0.13, min_silence_to_trim_sec=0.18)
    new_dur = len(tightened) / sr

    assert orig_dur >= 2.5
    # Silence (1.5s) was compressed to ~0.13s, so total duration should be ~1.13s (well under 1.5s)
    assert new_dur < 1.4
    assert new_dur >= 1.0


@pytest.mark.asyncio
async def test_voice_service_qwen3_rvc_mode(tmp_path: Path) -> None:
    """Test QWEN3_RVC synthesis calling Qwen3 model and RVC engine with pause compression."""
    import numpy as np

    from videoanalizer.quiz.voice_service import VoiceService

    svc = VoiceService()
    out_file = tmp_path / "test_qwen_rvc.wav"
    config = VoiceConfig(
        voice_mode=VoiceMode.QWEN3_RVC,
        rvc_model_path="Mellstroy-strimer.pth",
        tighten_pauses=True,
    )

    dummy_raw_wav = np.zeros(24000, dtype=np.float32)
    mock_model = MagicMock()
    mock_model.generate_voice_clone.return_value = ([dummy_raw_wav], 24000)

    with patch.object(VoiceService, "_get_qwen3_model", return_value=mock_model), patch.object(
        svc.rvc_engine, "convert_voice"
    ) as mock_rvc, patch(
        "videoanalizer.quiz.voice_service.probe_audio_duration_ms", return_value=1000
    ), patch(
        "pathlib.Path.exists", return_value=True
    ):
        result = await svc.synthesize(
            text="Тестовый вопрос викторины",
            output_path=out_file,
            config=config,
        )

        assert result.voice_mode_used == VoiceMode.QWEN3_RVC
        assert result.duration_ms == 1000
        assert len(result.words) == 3
        mock_model.generate_voice_clone.assert_called_once()
        mock_rvc.assert_called_once()

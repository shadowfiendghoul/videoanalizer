"""Unit tests for RvcInferenceEngine."""

import wave
from pathlib import Path

import pytest

from videoanalizer.quiz.models import RvcPitchMethod
from videoanalizer.quiz.rvc_engine import RvcInferenceEngine


def _create_dummy_wav(path: Path, duration_sec: float = 0.5) -> None:
    """Helper to generate a minimal valid 16-bit PCM WAV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    n_samples = int(sample_rate * duration_sec)
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(b"\x00\x00" * n_samples)


def test_rvc_engine_initialization() -> None:
    """Verify engine defaults and device selection."""
    engine = RvcInferenceEngine(device="cpu", pitch_method=RvcPitchMethod.RMVPE)
    assert engine.device == "cpu"
    assert engine.pitch_method == RvcPitchMethod.RMVPE
    assert engine.is_cuda_available is False


def test_rvc_engine_missing_files(tmp_path: Path) -> None:
    """Verify FileNotFoundError on missing input or model file."""
    engine = RvcInferenceEngine(device="cpu")
    in_wav = tmp_path / "input.wav"
    out_wav = tmp_path / "output.wav"
    model_pth = tmp_path / "model.pth"

    # Input missing
    with pytest.raises(FileNotFoundError, match="Input audio file not found"):
        engine.convert_voice(in_wav, out_wav, model_pth)

    _create_dummy_wav(in_wav)

    # Model missing
    with pytest.raises(FileNotFoundError, match="RVC model checkpoint not found"):
        engine.convert_voice(in_wav, out_wav, model_pth)


def test_rvc_engine_conversion_and_pitch_shift(tmp_path: Path) -> None:
    """Verify audio conversion with pitch shift within -12..+12 range."""
    engine = RvcInferenceEngine(device="cpu")
    in_wav = tmp_path / "speech.wav"
    out_wav = tmp_path / "converted.wav"
    model_pth = tmp_path / "dummy_voice.pth"

    _create_dummy_wav(in_wav, duration_sec=0.4)
    model_pth.write_bytes(b"dummy weights checkpoint")

    # Test conversion with pitch shift +3
    result_path = engine.convert_voice(
        input_path=in_wav,
        output_path=out_wav,
        model_path=model_pth,
        pitch_shift=3,
    )

    assert result_path.exists()
    assert result_path.stat().st_size > 0

    # Test conversion with extreme pitch shift (clamped)
    out_wav_clamped = tmp_path / "converted_clamped.wav"
    result_clamped = engine.convert_voice(
        input_path=in_wav,
        output_path=out_wav_clamped,
        model_path=model_pth,
        pitch_shift=25,  # should be clamped to 12
    )
    assert result_clamped.exists()


def test_rvc_engine_normalization(tmp_path: Path) -> None:
    """Verify audio normalization generates standard 16-bit PCM WAV."""
    engine = RvcInferenceEngine(device="cpu")
    in_wav = tmp_path / "raw.wav"
    out_wav = tmp_path / "norm.wav"
    _create_dummy_wav(in_wav, duration_sec=0.2)

    norm_path = engine.normalize_audio(in_wav, out_wav, sample_rate=44100, channels=1)
    assert norm_path.exists()
    assert norm_path.stat().st_size > 0

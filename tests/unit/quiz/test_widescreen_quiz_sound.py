"""Unit tests for SoundService (audio retrieval and trimming)."""

import pytest
from pathlib import Path
from videoanalizer.quiz.sound_service import SoundService, synthesize_procedural_sound


def test_synthesize_procedural_sound(tmp_path: Path):
    out_file = tmp_path / "procedural_awp.wav"
    synthesize_procedural_sound("awp shot", out_file, duration_sec=1.5)
    assert out_file.exists()
    assert out_file.stat().st_size > 1000


@pytest.mark.asyncio
async def test_sound_service_fallback_search(tmp_path: Path):
    service = SoundService(sfx_dir=tmp_path / "sfx")
    target_path = tmp_path / "minecraft_eating.wav"

    res = await service.search_and_download_sound("minecraft eating", target_path, max_duration_sec=3.0)
    assert res.exists()
    assert res.stat().st_size > 500

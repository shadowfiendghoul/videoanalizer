"""Unit tests for ImageService gaming asset query formatting and downloading."""

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from videoanalizer.quiz.image_service import ImageService


def test_format_gaming_query():
    # 1. Screenshot mode
    q1 = ImageService.format_gaming_query("Skyrim", "screenshot")
    assert "Skyrim" in q1
    assert "gameplay screenshot" in q1

    # 2. Game over mode
    q2 = ImageService.format_gaming_query("Dark Souls 3", "game_over")
    assert "Dark Souls 3" in q2
    assert "game over screen" in q2

    # 3. Minimap mode
    q3 = ImageService.format_gaming_query("The Witcher 3", "minimap")
    assert "The Witcher 3" in q3
    assert "minimap radar hud" in q3

    # 4. Silhouette mode
    q4 = ImageService.format_gaming_query("Mario", "silhouette")
    assert "Mario" in q4
    assert "transparent png" in q4


@pytest.mark.asyncio
async def test_search_and_download_gaming_asset(tmp_path: Path):
    service = ImageService()
    dest = tmp_path / "test_asset.png"

    # Create dummy PNG image bytes
    img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    dummy_bytes = buf.getvalue()

    with patch.object(service, "_search_image_urls", new=AsyncMock(return_value=[{"image": "http://mock/img.png"}])), \
         patch.object(service, "_download_bytes", new=AsyncMock(return_value=dummy_bytes)):
        result = await service.search_and_download_gaming_asset("DOOM Eternal", "screenshot", dest)
        assert result == dest
        assert dest.exists()
        loaded = Image.open(dest)
        assert loaded.size == (100, 100)


@pytest.mark.asyncio
async def test_search_and_download_gaming_asset_fallback_placeholder(tmp_path: Path):
    service = ImageService()
    dest = tmp_path / "fallback.png"

    # When search fails, it falls back to creating a placeholder PNG
    with patch.object(service, "_search_image_urls", new=AsyncMock(return_value=[])):
        result = await service.search_and_download_gaming_asset("Unknown Game", "minimap", dest)
        assert result == dest
        assert dest.exists()
        loaded = Image.open(dest)
        assert loaded.size == (512, 512)

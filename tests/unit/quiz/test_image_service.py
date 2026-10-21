"""Unit tests for ImageService web image retrieval and local caching."""

import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image

from videoanalizer.quiz.image_service import ImageService


@pytest.mark.asyncio
async def test_search_and_download_success(tmp_path: Path) -> None:
    """Verify ImageService successfully downloads and validates an image."""
    service = ImageService()
    target_path = tmp_path / "test_flag.png"

    # Create real valid 10x10 PNG bytes
    buf = io.BytesIO()
    img = Image.new("RGBA", (10, 10), (0, 255, 0, 255))
    img.save(buf, format="PNG")
    dummy_png = buf.getvalue()

    mock_search_results = [{"image": "https://example.com/flag.png"}]

    with (
        patch.object(
            service, "_search_image_urls", new=AsyncMock(return_value=mock_search_results)
        ),
        patch.object(service, "_download_bytes", new=AsyncMock(return_value=dummy_png)),
    ):
        result = await service.search_and_download("Flag of Brazil", target_path)
        assert result == target_path
        assert target_path.exists()
        assert target_path.stat().st_size > 0


@pytest.mark.asyncio
async def test_search_and_download_failure_fallback(tmp_path: Path) -> None:
    """Verify ImageService gracefully returns None on search or download failure."""
    service = ImageService()
    target_path = tmp_path / "failed_flag.png"

    with patch.object(service, "_search_image_urls", new=AsyncMock(return_value=[])):
        result = await service.search_and_download("NonExistentXYZ123456", target_path)
        assert result is None
        assert not target_path.exists()


def test_format_transparent_query_strips_redundant_keywords() -> None:
    """Verify format_transparent_query does not add redundant background keywords and cleans them if present."""
    # 1. Plain query is preserved without junk appended
    assert ImageService.format_transparent_query("Apple logo") == "Apple logo"
    assert ImageService.format_transparent_query("Ferrari F40") == "Ferrari F40"

    # 2. Boilerplate noise keywords are stripped
    noisy_query = "Apple vector logo transparent png isolated without background"
    assert ImageService.format_transparent_query(noisy_query) == "Apple"

    noisy_query2 = "Nike swoosh logo without background"
    assert ImageService.format_transparent_query(noisy_query2) == "Nike swoosh logo"

    noisy_query3 = "McDonald's isolated without background"
    assert ImageService.format_transparent_query(noisy_query3) == "McDonald's"

    # 3. Empty query returns default fallback
    assert ImageService.format_transparent_query("") == "logo"


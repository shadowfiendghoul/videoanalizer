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
    """Verify format_transparent_query cleans cluttered noise and appends 'white background png'."""
    # 1. Plain query has 'white background png' appended
    assert ImageService.format_transparent_query("Apple logo") == "Apple logo white background png"
    assert ImageService.format_transparent_query("Ferrari F40") == "Ferrari F40 white background png"

    # 2. Boilerplate noise keywords are stripped and replaced with 'white background png'
    noisy_query = "Apple vector logo transparent png isolated without background"
    assert ImageService.format_transparent_query(noisy_query) == "Apple white background png"

    noisy_query2 = "Nike swoosh logo without background"
    assert ImageService.format_transparent_query(noisy_query2) == "Nike swoosh logo white background png"

    # 3. If white background png is already present, it is not duplicated
    already_clean = "Minecraft diamond sword white background png"
    assert ImageService.format_transparent_query(already_clean) == "Minecraft diamond sword white background png"

    # 4. Empty query returns default fallback
    assert ImageService.format_transparent_query("") == "logo white background png"


def test_clean_fake_background_preserves_white_object_parts() -> None:
    """Verify that solid white background is removed while white/light parts of objects are preserved."""
    import numpy as np
    from PIL import ImageDraw

    # 1. Pokeball on pure white background
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # White bottom (245) and red top (220, 20, 20) with pure white center button (255)
    draw.pieslice([20, 20, 80, 80], 0, 180, fill=(245, 245, 245))
    draw.pieslice([20, 20, 80, 80], 180, 360, fill=(220, 20, 20))
    draw.ellipse([45, 45, 55, 55], fill=(255, 255, 255), outline=(20, 20, 20))

    cleaned = ImageService.clean_fake_background(img)
    arr = np.array(cleaned)

    # Background at corners must be transparent
    assert arr[5, 5, 3] == 0
    assert arr[95, 95, 3] == 0
    # White bottom of Pokeball must be opaque (preserved)
    assert arr[65, 50, 3] == 255
    # Red top of Pokeball must be opaque
    assert arr[35, 50, 3] == 255
    # Center pure white button must be opaque
    assert arr[50, 50, 3] == 255

    # 2. Portal Gun on solid white with white highlight
    pg = Image.new("RGB", (100, 100), (255, 255, 255))
    draw_pg = ImageDraw.Draw(pg)
    draw_pg.rectangle([30, 40, 70, 60], fill=(242, 242, 242), outline=(100, 100, 100))
    draw_pg.ellipse([40, 45, 60, 55], fill=(255, 255, 255))

    cleaned_pg = ImageService.clean_fake_background(pg)
    arr_pg = np.array(cleaned_pg)
    assert arr_pg[5, 5, 3] == 0
    assert arr_pg[50, 35, 3] == 255
    assert arr_pg[50, 50, 3] == 255



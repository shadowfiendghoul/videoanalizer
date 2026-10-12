"""Image search and download service with caching and graceful fallback."""

import asyncio
import io
import logging
import warnings
from pathlib import Path

import httpx
from PIL import Image

# Suppress transitional package rename warnings from legacy duckduckgo_search
warnings.filterwarnings("ignore", message=".*duckduckgo_search.*")
warnings.filterwarnings("ignore", message=".*renamed to.*")

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ImageService:
    """Asynchronous service to search and download high-resolution images for visual trivia."""

    def __init__(self, timeout_sec: float = 8.0) -> None:
        self.timeout_sec = timeout_sec

    async def _search_image_urls(self, query: str, max_results: int = 3) -> list[dict[str, str]]:
        """Search image URLs using ddgs / duckduckgo_search or search API."""
        if DDGS is None:
            return []

        try:
            # Small delay between consecutive image queries to prevent DDG 202 Ratelimit
            await asyncio.sleep(0.35)

            loop = asyncio.get_running_loop()

            def _search() -> list[dict[str, str]]:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    with DDGS() as ddgs:
                        return list(ddgs.images(query, max_results=max_results))

            return await loop.run_in_executor(None, _search)
        except Exception as e:
            err_str = str(e)
            if "202" in err_str or "Ratelimit" in err_str:
                logger.info(f"Image search rate-limited for '{query}', using layout fallback.")
            else:
                logger.warning(f"Image search query failed for '{query}': {e}")
            return []

    async def _download_bytes(self, url: str) -> bytes | None:
        """Download raw image bytes via HTTP GET."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.content
        except Exception as e:
            logger.warning(f"Failed to download image from {url}: {e}")
        return None

    async def search_and_download(self, query: str, dest_path: Path) -> Path | None:
        """Search image by query, validate and save to dest_path.

        Returns:
            Path if download & verification succeeded, otherwise None (fallback).
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        results = await self._search_image_urls(query)

        for item in results:
            url = item.get("image") or item.get("thumbnail")
            if not url:
                continue

            content = await self._download_bytes(url)
            if not content:
                continue

            # Verify image content integrity with Pillow
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()
                # Re-open for saving if valid
                img = Image.open(io.BytesIO(content))
                # Ensure RGBA or RGB
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGBA")
                img.save(dest_path)
                logger.info(f"Successfully cached visual asset for '{query}' at {dest_path}")
                return dest_path
            except Exception as e:
                logger.warning(f"Image verification failed for {url}: {e}")
                continue

        logger.info(
            f"No valid image could be downloaded for '{query}'; falling back to text/emoji."
        )
        return None

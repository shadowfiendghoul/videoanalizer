"""Image search and download service with caching and graceful fallback."""

import asyncio
import io
import logging
import warnings
from pathlib import Path

import httpx
from PIL import Image

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS  # type: ignore[no-redef]

        # Neutralize forced warnings.simplefilter("always") inside legacy duckduckgo_search.__init__
        _orig_ddgs_init = getattr(DDGS, "__init__", None)
        if _orig_ddgs_init is not None:

            def _silent_ddgs_init(
                self: object, *args: object, **kwargs: object
            ) -> None:
                orig_warn = warnings.warn
                warnings.warn = lambda *a, **k: None  # type: ignore[assignment]
                try:
                    _orig_ddgs_init(self, *args, **kwargs)
                finally:
                    warnings.warn = orig_warn

            DDGS.__init__ = _silent_ddgs_init  # type: ignore[method-assign]
    except ImportError:
        DDGS = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ImageService:
    """Asynchronous service to search and download high-resolution images for visual trivia."""

    def __init__(self, timeout_sec: float = 8.0) -> None:
        self.timeout_sec = timeout_sec

    @staticmethod
    def format_transparent_query(query: str) -> str:
        """Format and enforce transparent PNG search keywords for logo and icon queries."""
        q = (query or "").strip()
        lower = q.lower()
        parts = [q] if q else ["logo"]
        if "transparent" not in lower:
            parts.append("transparent")
        if "png" not in lower:
            parts.append("png")
        if "without background" not in lower and "no background" not in lower:
            parts.append("without background")
        return " ".join(parts)

    @staticmethod
    def sort_transparent_candidates(results: list[dict[str, str]]) -> list[dict[str, str]]:
        """Sort search candidate URLs prioritizing verified .png extensions and transparent PNG repositories."""
        trusted_png_domains = (
            "pngimg.com",
            "freepnglogos.com",
            "cleanpng.com",
            "stickpng.com",
            "pngall.com",
            "pngplay.com",
            "citypng.com",
            "pngwing.com",
            "pngtree.com",
            "wikimedia.org",
            "wikipedia.org",
        )

        def _score(item: dict[str, str]) -> int:
            url = (item.get("image") or item.get("thumbnail") or "").lower()
            title = (item.get("title") or "").lower()
            score = 0
            if ".png" in url:
                score += 50
            if any(dom in url for dom in trusted_png_domains):
                score += 30
            if "transparent" in url or "transparent" in title:
                score += 20
            if "logo" in url or "logo" in title:
                score += 10
            # Penalize raster photos and formats without transparency
            if url.endswith(".jpg") or url.endswith(".jpeg") or ".jpg?" in url or ".jpeg?" in url:
                score -= 40
            if "vecteezy.com" in url:
                score -= 25
            return score

        return sorted(results, key=_score, reverse=True)

    @staticmethod
    def is_transparent_image(img: Image.Image) -> bool:
        """Check if image has genuine alpha transparency."""
        if img.mode != "RGBA":
            return False
        try:
            import numpy as np

            arr = np.array(img)
            # More than 3% of pixels are transparent or semi-transparent (alpha < 220)
            return bool(np.mean(arr[:, :, 3] < 220) > 0.03)
        except Exception:
            return False

    def is_transparent_file(self, image_path: Path) -> bool:
        """Check if an image file on disk has alpha transparency."""
        try:
            with Image.open(image_path) as img:
                return self.is_transparent_image(img.convert("RGBA"))
        except Exception:
            return False

    async def _search_image_urls(self, query: str, max_results: int = 8) -> list[dict[str, str]]:
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

    @staticmethod
    def clean_fake_background(img: Image.Image) -> Image.Image:
        """Automatically detect and remove fake checkerboard, solid white, and dark backgrounds from logos."""
        try:
            import numpy as np
            import scipy.ndimage as ndi
        except ImportError:
            return img

        img_rgba = img.convert("RGBA")
        arr = np.array(img_rgba)

        # If already has alpha transparency (more than 5% transparent pixels), keep as is
        if np.mean(arr[:, :, 3] < 200) > 0.05:
            return img_rgba

        r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
        max_c = np.maximum(np.maximum(r, g), b)
        min_c = np.minimum(np.minimum(r, g), b)

        h, w = arr.shape[:2]
        if h < 10 or w < 10:
            return img_rgba

        # Neutral light pixels (white or light-grey checkerboard)
        is_neutral_light = (min_c >= 150) & ((max_c - min_c) <= 30)
        # Neutral dark pixels (solid black or dark grey border)
        is_neutral_dark = (max_c <= 40) & ((max_c - min_c) <= 20)

        corners = [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]
        corner_count_light = sum(is_neutral_light[y, x] for y, x in corners)
        corner_count_dark = sum(is_neutral_dark[y, x] for y, x in corners)

        if corner_count_light >= 2:
            target_bg = is_neutral_light
        elif corner_count_dark >= 2:
            target_bg = is_neutral_dark
        else:
            return img_rgba

        labeled, num_features = ndi.label(target_bg)
        if num_features == 0:
            return img_rgba

        # Background labels touching outer border
        border_labels = np.unique(
            np.concatenate([labeled[0, :], labeled[-1, :], labeled[:, 0], labeled[:, -1]])
        )
        border_labels = border_labels[border_labels > 0]
        if len(border_labels) == 0:
            return img_rgba

        mask = np.isin(labeled, border_labels)
        # Safety check: if mask would erase more than 96% of the image, abort and keep original
        if np.mean(mask) > 0.96:
            return img_rgba

        arr[mask, 3] = 0
        return Image.fromarray(arr)

    def clean_image_file(self, image_path: Path, dest_path: Path | None = None) -> Path:
        """Clean fake background from an image file on disk and save as PNG."""
        target = dest_path or image_path
        try:
            with Image.open(image_path) as img:
                cleaned = self.clean_fake_background(img)
                target.parent.mkdir(parents=True, exist_ok=True)
                cleaned.save(target, "PNG")
                return target
        except Exception as e:
            logger.warning("Failed to clean background for %s: %s", image_path, e)
            return image_path

    async def download_from_url(self, url: str, dest_path: Path) -> Path | None:
        """Download image from direct URL, validate with Pillow, clean fake background, and save as PNG."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        content = await self._download_bytes(url)
        if not content:
            return None
        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            img = Image.open(io.BytesIO(content))
            img = self.clean_fake_background(img)
            img.save(dest_path, "PNG")
            logger.info("Successfully downloaded, cleaned and cached image from URL at %s", dest_path)
            return dest_path
        except Exception as e:
            logger.warning("Image verification failed for direct URL %s: %s", url, e)
            return None

    def create_placeholder(self, dest_path: Path, label: str = "?") -> Path:
        """Create a clean placeholder PNG when no image is available, ensuring Remotion never crashes."""
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import ImageDraw

            img = Image.new("RGBA", (512, 512), (15, 23, 42, 240))
            draw = ImageDraw.Draw(img)
            draw.rectangle([12, 12, 499, 499], outline=(56, 189, 248, 220), width=6)
            display_text = label[:20] if label else "?"
            draw.text((256, 256), display_text, fill=(255, 255, 255, 240), anchor="mm")
            img.save(dest_path, "PNG")
            return dest_path
        except Exception as e:
            logger.warning("Failed to create placeholder image: %s", e)
            img = Image.new("RGBA", (64, 64), (20, 20, 30, 255))
            img.save(dest_path, "PNG")
            return dest_path

    async def search_and_download(self, query: str, dest_path: Path) -> Path | None:
        """Search image by query, validate, clean fake background, and save to dest_path.

        Prioritizes verified transparent PNG candidates across search results.
        """
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        sanitized_query = self.format_transparent_query(query)
        results = await self._search_image_urls(sanitized_query, max_results=8)
        sorted_results = self.sort_transparent_candidates(results)

        fallback_candidate_img: Image.Image | None = None

        for item in sorted_results:
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
                img = Image.open(io.BytesIO(content))
                img = self.clean_fake_background(img)

                # If this candidate is genuinely transparent (or cleaned to transparent), accept immediately
                if self.is_transparent_image(img):
                    img.save(dest_path, "PNG")
                    logger.info("Successfully cached transparent PNG asset for '%s' from %s at %s", query, url, dest_path)
                    return dest_path

                # If not transparent, save as fallback candidate in case no transparent candidate is found
                if fallback_candidate_img is None:
                    fallback_candidate_img = img
            except Exception as e:
                logger.warning("Image verification failed for %s: %s", url, e)
                continue

        # If no strictly transparent image was found among all candidates, use best cleaned fallback
        if fallback_candidate_img is not None:
            fallback_candidate_img.save(dest_path, "PNG")
            logger.info("Saved fallback cleaned visual asset for '%s' at %s", query, dest_path)
            return dest_path

        logger.info(
            "No valid image could be downloaded for '%s'; falling back to text/emoji.",
            query,
        )
        return None

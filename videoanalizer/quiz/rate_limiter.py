"""Async rate limiter and request pacer enforcing <= 12 RPM (5.0s spacing) for Gemini API."""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class PacedLimiter:
    """Token/timestamp based rate limiter ensuring calls are spaced by >= min_interval_sec.

    Designed specifically to guard against exceeding Gemini Flash Lite's 15 RPM quota
    by enforcing a safe floor of 5.0 seconds between consecutive requests (max 12 RPM).
    """

    def __init__(self, min_interval_sec: float = 5.0) -> None:
        self.min_interval_sec = min_interval_sec
        self._last_call_time: float = 0.0
        self._lock = asyncio.Lock()
        self.is_waiting: bool = False
        self.current_delay_sec: float = 0.0

    async def acquire(self) -> float:
        """Wait if necessary to satisfy min_interval_sec spacing, then return actual wait time."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call_time
            wait_time = max(0.0, self.min_interval_sec - elapsed)

            if wait_time > 0.0:
                self.is_waiting = True
                self.current_delay_sec = wait_time
                logger.info(
                    "PacedLimiter: Holding for %.2fs to respect 15 RPM quota (interval=%.1fs)",
                    wait_time,
                    self.min_interval_sec,
                )
                try:
                    await asyncio.sleep(wait_time)
                finally:
                    self.is_waiting = False
                    self.current_delay_sec = 0.0

            self._last_call_time = time.monotonic()
            return wait_time

    async def record_429_backoff(self, attempt: int, base_delay: float = 5.0) -> float:
        """Trigger exponential backoff on HTTP 429 Resource Exhausted errors."""
        async with self._lock:
            delay = base_delay * (2**attempt)
            self.is_waiting = True
            self.current_delay_sec = delay
            logger.warning(
                "PacedLimiter: Received HTTP 429 quota exhaustion. Backing off for %.1fs (attempt %d)",
                delay,
                attempt + 1,
            )
            try:
                await asyncio.sleep(delay)
            finally:
                self.is_waiting = False
                self.current_delay_sec = 0.0
            self._last_call_time = time.monotonic()
            return delay

    def get_remaining_wait(self) -> float:
        """Return remaining seconds until next request can be made without waiting."""
        now = time.monotonic()
        elapsed = now - self._last_call_time
        return max(0.0, self.min_interval_sec - elapsed)

    async def __aenter__(self) -> "PacedLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass


_global_gemini_limiter: PacedLimiter | None = None


def get_gemini_rate_limiter() -> PacedLimiter:
    """Return application-wide shared PacedLimiter instance for Gemini calls."""
    global _global_gemini_limiter
    if _global_gemini_limiter is None:
        _global_gemini_limiter = PacedLimiter(min_interval_sec=5.0)
    return _global_gemini_limiter

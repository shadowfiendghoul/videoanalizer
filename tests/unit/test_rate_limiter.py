"""Unit tests for PacedLimiter rate limiter."""

import asyncio
import time
import pytest

from videoanalizer.quiz.rate_limiter import PacedLimiter, get_gemini_rate_limiter


@pytest.mark.asyncio
async def test_paced_limiter_initial_acquire_has_no_delay():
    limiter = PacedLimiter(min_interval_sec=0.1)
    wait_time = await limiter.acquire()
    assert wait_time == 0.0
    assert not limiter.is_waiting


@pytest.mark.asyncio
async def test_paced_limiter_spaces_consecutive_calls():
    limiter = PacedLimiter(min_interval_sec=0.1)

    t0 = time.monotonic()
    await limiter.acquire()
    t1 = time.monotonic()
    await limiter.acquire()
    t2 = time.monotonic()

    # Second acquire must have waited around 0.1s
    elapsed = t2 - t1
    assert elapsed >= 0.09, f"Elapsed {elapsed}s was less than minimum 0.09s"


@pytest.mark.asyncio
async def test_paced_limiter_context_manager():
    limiter = PacedLimiter(min_interval_sec=0.08)

    t0 = time.monotonic()
    async with limiter:
        pass
    t1 = time.monotonic()
    async with limiter:
        pass
    t2 = time.monotonic()

    elapsed = t2 - t1
    assert elapsed >= 0.07


@pytest.mark.asyncio
async def test_paced_limiter_429_backoff():
    limiter = PacedLimiter(min_interval_sec=0.05)

    t0 = time.monotonic()
    delay = await limiter.record_429_backoff(attempt=0, base_delay=0.05)
    t1 = time.monotonic()

    assert delay == 0.05
    assert (t1 - t0) >= 0.045

    # Attempt 1 should double base delay
    delay_2 = await limiter.record_429_backoff(attempt=1, base_delay=0.05)
    assert delay_2 == 0.10


def test_get_gemini_rate_limiter_singleton():
    l1 = get_gemini_rate_limiter()
    l2 = get_gemini_rate_limiter()
    assert l1 is l2
    assert l1.min_interval_sec >= 4.5

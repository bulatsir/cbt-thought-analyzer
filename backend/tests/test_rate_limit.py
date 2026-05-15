import time

from app.rate_limit import InMemoryRateLimiter


async def test_allows_up_to_max_then_rejects():
    rl = InMemoryRateLimiter(max_per_minute=3, window_seconds=60)
    assert [await rl.allow("dev") for _ in range(3)] == [True, True, True]
    assert await rl.allow("dev") is False  # 4th in the window


async def test_devices_are_independent():
    rl = InMemoryRateLimiter(max_per_minute=1, window_seconds=60)
    assert await rl.allow("a") is True
    assert await rl.allow("a") is False
    assert await rl.allow("b") is True  # different device, own bucket


async def test_window_expiry_lets_requests_through_again():
    rl = InMemoryRateLimiter(max_per_minute=1, window_seconds=60)
    assert await rl.allow("dev") is True
    assert await rl.allow("dev") is False
    # Backdate the recorded timestamp so it falls outside the window.
    rl._buckets["dev"][0] = time.monotonic() - 61
    assert await rl.allow("dev") is True


async def test_sweep_evicts_stale_buckets():
    rl = InMemoryRateLimiter(max_per_minute=5, window_seconds=60)
    for dev in ("a", "b", "c"):
        await rl.allow(dev)
    assert set(rl._buckets) == {"a", "b", "c"}

    # Make every recorded hit older than the window and force the next call
    # to run the periodic sweep.
    for bucket in rl._buckets.values():
        bucket[0] = time.monotonic() - 120
    rl._last_sweep = time.monotonic() - 120

    await rl.allow("d")  # triggers sweep
    # a/b/c had only expired hits → evicted; d is the only live bucket.
    assert set(rl._buckets) == {"d"}

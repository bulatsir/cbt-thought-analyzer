import asyncio
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """Sliding-window rate limiter, keyed by device id.

    In-memory only — не переживает рестарт пода, не шарится между репликами.
    Для MVP с одной репликой — ок. Для масштабирования заменить на Redis.
    """

    def __init__(self, max_per_minute: int = 30, window_seconds: int = 60) -> None:
        self._max = max_per_minute
        self._window = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            bucket = self._buckets[key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._max:
                return False
            bucket.append(now)
            return True

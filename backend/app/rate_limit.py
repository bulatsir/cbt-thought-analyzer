import asyncio
import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    """Sliding-window rate limiter, keyed by device id.

    In-memory only — не переживает рестарт пода, не шарится между репликами.
    Для MVP с одной репликой — ок. Для масштабирования заменить на Redis.

    Самоочищается: раз в окно ленивым sweep'ом выкидывает протухшие метки и
    пустые бакеты, иначе словарь рос бы неограниченно от уникальных device-id
    (утечка памяти + вектор DoS на RAM при прокрутке id).
    """

    def __init__(self, max_per_minute: int = 30, window_seconds: int = 60) -> None:
        self._max = max_per_minute
        self._window = window_seconds
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._last_sweep = time.monotonic()

    def _sweep(self, now: float) -> None:
        """Drop expired timestamps and empty buckets. Caller holds the lock."""
        stale: list[str] = []
        for key, bucket in self._buckets.items():
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if not bucket:
                stale.append(key)
        for key in stale:
            del self._buckets[key]
        self._last_sweep = now

    async def allow(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            if now - self._last_sweep > self._window:
                self._sweep(now)
            bucket = self._buckets[key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._max:
                return False
            bucket.append(now)
            return True

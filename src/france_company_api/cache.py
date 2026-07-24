import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 3600, max_entries: int = 1024) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[tuple[Any, ...], tuple[float, dict[str, Any]]] = OrderedDict()
        self._locks: dict[tuple[Any, ...], asyncio.Lock] = {}

    def _get(self, key: tuple[Any, ...]) -> dict[str, Any] | None:
        cached = self._entries.get(key)
        if cached is None:
            return None
        expires_at, value = cached
        if expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return None
        self._entries.move_to_end(key)
        return value

    async def get_or_load(
        self,
        key: tuple[Any, ...],
        loader: Callable[[], Awaitable[dict[str, Any]]],
    ) -> tuple[dict[str, Any], bool]:
        cached = self._get(key)
        if cached is not None:
            return cached, True

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._get(key)
            if cached is not None:
                return cached, True
            value = await loader()
            self._entries[key] = (time.monotonic() + self._ttl, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                evicted_key, _ = self._entries.popitem(last=False)
                self._locks.pop(evicted_key, None)
            return value, False

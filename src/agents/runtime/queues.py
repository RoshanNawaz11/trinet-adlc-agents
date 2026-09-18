"""In-memory queue. Stand-in for a real arq/redis queue — worker.py's
`run_task` doesn't care which backend is behind `enqueue`/`dequeue`, so
swapping this out later shouldn't touch worker.py's logic.
"""

from __future__ import annotations

import asyncio
from typing import Any


class InMemoryQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def enqueue(self, message: dict[str, Any]) -> None:
        await self._queue.put(message)

    async def dequeue(self) -> dict[str, Any]:
        return await self._queue.get()

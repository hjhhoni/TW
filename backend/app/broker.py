"""运行事件分发（用于 SSE 实时推送节点进度）。"""
from __future__ import annotations

import asyncio
from typing import Any


class RunBroker:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def register(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues[run_id] = q
        return q

    def get(self, run_id: str) -> asyncio.Queue | None:
        return self._queues.get(run_id)

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        q = self._queues.get(run_id)
        if q is not None:
            await q.put(event)

    def drop(self, run_id: str) -> None:
        self._queues.pop(run_id, None)


broker = RunBroker()

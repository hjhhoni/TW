"""运行事件分发（SSE 实时进度）。

支持：事件缓冲（订阅时可回放）+ 多订阅者 + 后台运行。
运行结束后缓冲保留一段时间，便于迟到的订阅者拿到最终结果。
"""
from __future__ import annotations

import asyncio
from typing import Any


class RunBroker:
    def __init__(self) -> None:
        self._buffers: dict[str, list[dict[str, Any]]] = {}
        self._subs: dict[str, set[asyncio.Queue]] = {}

    def register(self, run_id: str) -> None:
        self._buffers.setdefault(run_id, [])
        self._subs.setdefault(run_id, set())

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        self._buffers.setdefault(run_id, []).append(event)
        for q in list(self._subs.get(run_id, set())):
            await q.put(event)

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        """订阅某次运行：先回放已缓冲事件，再收实时事件。"""
        self._subs.setdefault(run_id, set())
        q: asyncio.Queue = asyncio.Queue()
        self._subs[run_id].add(q)
        for ev in self._buffers.get(run_id, []):
            await q.put(ev)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        self._subs.get(run_id, set()).discard(q)

    def is_done(self, run_id: str) -> bool:
        buf = self._buffers.get(run_id, [])
        return bool(buf) and buf[-1].get("node") == "__run__"

    def buffer(self, run_id: str) -> list[dict[str, Any]]:
        return list(self._buffers.get(run_id, []))

    def drop(self, run_id: str) -> None:
        self._buffers.pop(run_id, None)
        self._subs.pop(run_id, None)

    def sweep(self, max_keep: int = 50) -> None:
        """保留最近 max_keep 个已结束运行的缓冲，防止内存无限增长。"""
        done = [rid for rid, buf in self._buffers.items()
                if buf and buf[-1].get("node") == "__run__"]
        for rid in done[:-max_keep]:
            self.drop(rid)


broker = RunBroker()

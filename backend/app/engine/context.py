"""运行上下文与进度回调。"""
from __future__ import annotations

from typing import Any, Awaitable, Callable


class RunContext:
    def __init__(
        self,
        run_id: str,
        inputs: dict[str, Any],
        on_event: Callable[[str, str, dict | None], Awaitable[None]] | None = None,
    ) -> None:
        self.run_id = run_id
        self.inputs = inputs or {}
        self.on_event = on_event

    async def emit(self, node_id: str, status: str, data: dict | None = None) -> None:
        if self.on_event:
            try:
                await self.on_event(node_id, status, data or {})
            except Exception:
                pass

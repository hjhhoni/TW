"""工作流运行服务：加载工作流 → 记录运行 → 执行 → 落库。"""
from __future__ import annotations

import json
import uuid
from typing import Any, Awaitable, Callable

from app import storage

from .context import RunContext
from .executor import execute
from .schema import WorkflowGraph

EventCb = Callable[[str, str, dict | None], Awaitable[None]]


async def run_workflow(
    workflow_id: str,
    inputs: dict[str, Any] | None = None,
    run_id: str | None = None,
    source: str = "manual",
    on_event: EventCb | None = None,
) -> dict[str, Any]:
    wf = storage.get_workflow(workflow_id)
    if not wf:
        raise ValueError(f"工作流不存在: {workflow_id}")

    run_id = run_id or uuid.uuid4().hex[:12]
    inputs = inputs or {}
    storage.create_run(run_id, workflow_id, wf["name"], inputs, source)

    graph = WorkflowGraph(**json.loads(wf["graph"]))
    ctx = RunContext(run_id, inputs, on_event)

    try:
        result = await execute(graph, ctx)
        has_out = bool(result["outputs"])
        status = "success" if not result["errors"] else ("partial" if has_out else "error")
        storage.finish_run(
            run_id, status, result["outputs"], result["node_outputs"],
            error=None if not result["errors"] else "; ".join(f"{n}:{e}" for n, e in result["errors"]),
        )
        result["run_id"] = run_id
        result["status"] = status
        return result
    except Exception as e:
        storage.finish_run(run_id, "error", {}, {}, error=str(e))
        return {"run_id": run_id, "status": "error", "error": str(e)}

"""运行工作流 + 运行历史。支持 SSE 实时进度。"""
from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import storage
from app.broker import broker
from app.engine.runner import run_workflow

router = APIRouter(prefix="/api", tags=["runs"])


class RunReq(BaseModel):
    inputs: dict = {}
    stream: bool = False


async def _runner_with_broker(workflow_id: str, run_id: str, inputs: dict, source: str = "manual"):
    async def on_event(node_id: str, status: str, data: dict | None):
        await broker.publish(run_id, {"node": node_id, "status": status, "data": data or {}})

    res = await run_workflow(workflow_id, inputs, run_id=run_id, source=source, on_event=on_event)
    await broker.publish(run_id, {"node": "__run__", "status": res.get("status", "error"), "data": res})
    return res


@router.post("/workflows/{wid}/run")
async def run(wid: str, body: RunReq):
    if not storage.get_workflow(wid):
        raise HTTPException(404, "工作流不存在")
    run_id = uuid.uuid4().hex[:12]

    if not body.stream:
        res = await _runner_with_broker(wid, run_id, body.inputs)
        broker.drop(run_id)
        return res

    broker.register(run_id)
    task = asyncio.create_task(_runner_with_broker(wid, run_id, body.inputs))

    async def event_stream():
        q = broker.get(run_id)
        try:
            while True:
                ev = await q.get()
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                if ev.get("node") == "__run__":
                    break
            await task
        finally:
            broker.drop(run_id)

    return StreamingResponse(event_stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Run-Id": run_id})


@router.get("/runs")
async def list_runs(limit: int = 50):
    items = storage.list_runs(limit)
    for it in items:
        for k in ("inputs", "outputs", "node_outputs"):
            try:
                it[k] = json.loads(it[k])
            except Exception:
                it[k] = {}
    return {"runs": items}


@router.get("/runs/{rid}")
async def get_run(rid: str):
    run = storage.get_run(rid)
    if not run:
        raise HTTPException(404, "运行不存在")
    for k in ("inputs", "outputs", "node_outputs"):
        try:
            run[k] = json.loads(run[k])
        except Exception:
            run[k] = {}
    return run

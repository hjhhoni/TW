"""运行工作流（后台、非阻塞）+ 运行历史 + 实时进度 + 资产落地。

关键：POST /run 立即返回 run_id，真正执行放在后台任务里，
客户端通过 GET /runs/{id}/events 订阅进度，可随时断开/重连，不影响运行。
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import storage
from app.broker import broker
from app.engine.runner import run_workflow

router = APIRouter(prefix="/api", tags=["runs"])

# 进行中的后台任务（用于取消）
_bg_tasks: dict[str, asyncio.Task] = {}


class RunReq(BaseModel):
    inputs: dict = {}


async def _runner(workflow_id: str, run_id: str, inputs: dict):
    async def on_event(node_id: str, status: str, data: dict | None):
        await broker.publish(run_id, {"node": node_id, "status": status, "data": data or {}})

    try:
        res = await run_workflow(workflow_id, inputs, run_id=run_id, source="manual", on_event=on_event)
        await broker.publish(run_id, {"node": "__run__", "status": res.get("status", "error"), "data": res})
        # 把每个输出节点结果存为资产
        wf = storage.get_workflow(workflow_id)
        wf_name = wf["name"] if wf else "工作流"
        for key, text in (res.get("outputs") or {}).items():
            if text and isinstance(text, str):
                storage.create_asset(
                    uuid.uuid4().hex[:12], run_id, workflow_id, wf_name,
                    f"{wf_name} · {key}", text, kind="text",
                )
    except asyncio.CancelledError:
        storage.finish_run(run_id, "cancelled", {}, {}, error="用户取消")
        await broker.publish(run_id, {"node": "__run__", "status": "cancelled",
                                      "data": {"run_id": run_id, "cancelled": True}})
        raise
    except Exception as e:
        storage.finish_run(run_id, "error", {}, {}, error=str(e))
        await broker.publish(run_id, {"node": "__run__", "status": "error",
                                      "data": {"error": str(e), "run_id": run_id}})
    finally:
        _bg_tasks.pop(run_id, None)
        broker.sweep()


@router.post("/workflows/{wid}/run")
async def run(wid: str, body: RunReq):
    if not storage.get_workflow(wid):
        raise HTTPException(404, "工作流不存在")
    run_id = uuid.uuid4().hex[:12]
    broker.register(run_id)
    task = asyncio.create_task(_runner(wid, run_id, body.inputs))
    _bg_tasks[run_id] = task
    return {"run_id": run_id, "status": "running"}


@router.post("/runs/{rid}/cancel")
async def cancel_run(rid: str):
    task = _bg_tasks.get(rid)
    if task and not task.done():
        task.cancel()  # _runner 会捕获并落库 + 发 cancelled 事件
        return {"ok": True, "cancelled": True}
    return {"ok": False, "msg": "运行已结束或不存在"}


@router.get("/runs/{rid}/events")
async def run_events(rid: str):
    async def stream():
        q = await broker.subscribe(rid)
        try:
            while True:
                ev = await q.get()
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                if ev.get("node") == "__run__":
                    break
        finally:
            broker.unsubscribe(rid, q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Run-Id": rid})


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

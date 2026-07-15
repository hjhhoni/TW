"""工作流 CRUD。"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import storage
from app.engine.schema import NODE_TYPES, WorkflowGraph

router = APIRouter(prefix="/api", tags=["workflows"])


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    graph: dict


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    graph: dict | None = None


@router.get("/workflows")
async def list_workflows():
    items = storage.list_workflows()
    # 解析 graph 以便前端直接用
    for it in items:
        try:
            it["graph"] = json.loads(it["graph"])
        except Exception:
            it["graph"] = {"nodes": [], "edges": []}
    return {"workflows": items}


@router.get("/workflows/{wid}")
async def get_workflow(wid: str):
    wf = storage.get_workflow(wid)
    if not wf:
        raise HTTPException(404, "工作流不存在")
    try:
        wf["graph"] = json.loads(wf["graph"])
    except Exception:
        wf["graph"] = {"nodes": [], "edges": []}
    return wf


@router.post("/workflows")
async def create_workflow(body: WorkflowCreate):
    wid = uuid.uuid4().hex[:12]
    # 校验图
    WorkflowGraph(**body.graph)
    wf = storage.upsert_workflow(wid, body.name, body.description, body.graph)
    wf["graph"] = json.loads(wf["graph"])
    return wf


@router.put("/workflows/{wid}")
async def update_workflow(wid: str, body: WorkflowUpdate):
    existing = storage.get_workflow(wid)
    if not existing:
        raise HTTPException(404, "工作流不存在")
    name = body.name if body.name is not None else existing["name"]
    desc = body.description if body.description is not None else existing["description"]
    graph = body.graph if body.graph is not None else json.loads(existing["graph"])
    WorkflowGraph(**graph)
    wf = storage.upsert_workflow(wid, name, desc, graph)
    wf["graph"] = json.loads(wf["graph"])
    return wf


@router.delete("/workflows/{wid}")
async def delete_workflow(wid: str):
    storage.delete_workflow(wid)
    return {"ok": True}


class ImportReq(BaseModel):
    name: str
    description: str = ""
    graph: dict


@router.post("/workflows/import")
async def import_workflow(body: ImportReq):
    """从 JSON 导入工作流（粘贴或上传）。"""
    WorkflowGraph(**body.graph)
    wid = uuid.uuid4().hex[:12]
    wf = storage.upsert_workflow(wid, body.name, body.description, body.graph)
    wf["graph"] = json.loads(wf["graph"])
    return wf


@router.post("/workflows/{wid}/duplicate")
async def duplicate_workflow(wid: str):
    existing = storage.get_workflow(wid)
    if not existing:
        raise HTTPException(404, "工作流不存在")
    new_id = uuid.uuid4().hex[:12]
    wf = storage.upsert_workflow(
        new_id, existing["name"] + " (副本)", existing["description"],
        json.loads(existing["graph"]),
    )
    wf["graph"] = json.loads(wf["graph"])
    return wf


@router.get("/node-types")
async def node_types():
    return {"types": NODE_TYPES}

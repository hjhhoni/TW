"""定时任务接口。"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import storage
from app.scheduler import remove_scheduled, schedule_job, sync_all

router = APIRouter(prefix="/api", tags=["jobs"])


class JobCreate(BaseModel):
    workflow_id: str
    trigger_type: str                # cron | interval
    trigger_config: dict             # cron 字段 或 {seconds|minutes|hours}
    inputs: dict = {}
    enabled: bool = True
    name: str | None = None          # 仅展示用


@router.get("/jobs")
async def list_jobs():
    return {"jobs": storage.list_jobs()}


@router.post("/jobs")
async def create_job(body: JobCreate):
    wf = storage.get_workflow(body.workflow_id)
    if not wf:
        raise HTTPException(404, "工作流不存在")
    job_id = uuid.uuid4().hex[:10]
    job = storage.upsert_job(
        job_id, body.workflow_id, wf["name"],
        body.trigger_type, body.trigger_config, body.inputs, body.enabled,
    )
    schedule_job(job)
    return job


@router.put("/jobs/{jid}")
async def update_job(jid: str, body: JobCreate):
    existing = storage.get_job(jid)
    if not existing:
        raise HTTPException(404, "任务不存在")
    wf = storage.get_workflow(body.workflow_id)
    wf_name = wf["name"] if wf else existing["workflow_name"]
    job = storage.upsert_job(
        jid, body.workflow_id, wf_name,
        body.trigger_type, body.trigger_config, body.inputs, body.enabled,
    )
    schedule_job(job)
    return job


@router.post("/jobs/{jid}/toggle")
async def toggle_job(jid: str):
    job = storage.get_job(jid)
    if not job:
        raise HTTPException(404, "任务不存在")
    job = storage.upsert_job(
        jid, job["workflow_id"], job["workflow_name"],
        job["trigger_type"], json.loads(job["trigger_config"]),
        json.loads(job["inputs"] or "{}"), enabled=not job["enabled"],
    )
    schedule_job(job)
    return job


@router.delete("/jobs/{jid}")
async def delete_job(jid: str):
    remove_scheduled(jid)
    storage.delete_job(jid)
    return {"ok": True}


@router.post("/jobs/sync")
async def sync_jobs():
    sync_all()
    return {"ok": True}

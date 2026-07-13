"""定时任务调度（APScheduler）。

trigger_type:
  - "cron"     : trigger_config = cron 字段 dict（month/day/day_of_week/hour/minute/second）
  - "interval" : trigger_config = {seconds|minutes|hours}
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app import storage
from app.engine.runner import run_workflow

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai", misfire_grace_time=3600, coalesce=True)


def _make_trigger(trigger_type: str, cfg: dict[str, Any]):
    if trigger_type == "cron":
        clean = {k: v for k, v in cfg.items() if v not in (None, "", "*")}
        return CronTrigger(**clean)
    if trigger_type == "interval":
        clean = {k: int(v) for k, v in cfg.items() if str(v).strip()}
        return IntervalTrigger(**clean)
    raise ValueError(f"未知 trigger_type: {trigger_type}")


def _aps_id(job_id: str) -> str:
    return f"wf_{job_id}"


async def _run_job(job_id: str, workflow_id: str, inputs: dict) -> None:
    try:
        await run_workflow(workflow_id, inputs, source="schedule")
    except Exception as e:
        print(f"[scheduler] 任务 {job_id} 执行失败: {e}")
    finally:
        nxt = next_run_time(job_id)
        storage.touch_job_run(job_id, time.time(), nxt)


def next_run_time(job_id: str) -> float | None:
    try:
        job = scheduler.get_job(_aps_id(job_id))
        if job and job.next_run_time:
            return job.next_run_time.timestamp()
    except Exception:
        pass
    return None


def schedule_job(job: dict[str, Any]) -> None:
    if not job.get("enabled"):
        remove_scheduled(job["id"])
        return
    trigger = _make_trigger(job["trigger_type"], json.loads(job["trigger_config"]))
    inputs = json.loads(job.get("inputs") or "{}")
    scheduler.add_job(
        _run_job, trigger,
        args=[job["id"], job["workflow_id"], inputs],
        id=_aps_id(job["id"]), replace_existing=True,
    )
    nxt = next_run_time(job["id"])
    storage.touch_job_run(job["id"], job.get("last_run_at") or 0, nxt)


def remove_scheduled(job_id: str) -> None:
    try:
        scheduler.remove_job(_aps_id(job_id))
    except Exception:
        pass


def sync_all() -> None:
    """根据 storage 重建所有调度（启动或配置变更时调用）。"""
    existing = {j.id for j in scheduler.get_jobs()}
    for job in storage.list_jobs():
        schedule_job(job)
        existing.discard(_aps_id(job["id"]))
    for jid in existing:  # 已删除的
        try:
            scheduler.remove_job(jid)
        except Exception:
            pass


async def start() -> None:
    if not scheduler.running:
        scheduler.start()
    sync_all()


async def shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

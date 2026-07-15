"""sqlite 持久化：工作流、运行记录、定时任务。

单用户本地平台，用同步 sqlite3 + 全局锁即可。
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.config import DB_PATH

_lock = threading.Lock()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _lock, get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                graph TEXT NOT NULL DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                workflow_name TEXT DEFAULT '',
                status TEXT NOT NULL,            -- running | success | error
                inputs TEXT DEFAULT '{}',
                outputs TEXT DEFAULT '{}',
                node_outputs TEXT DEFAULT '{}',
                started_at REAL NOT NULL,
                finished_at REAL,
                error TEXT,
                source TEXT DEFAULT 'manual'     -- manual | schedule
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                workflow_name TEXT DEFAULT '',
                trigger_type TEXT NOT NULL,      -- cron | interval
                trigger_config TEXT NOT NULL,    -- JSON
                inputs TEXT DEFAULT '{}',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at REAL NOT NULL,
                last_run_at REAL,
                next_run_at REAL
            );

            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                run_id TEXT,
                workflow_id TEXT,
                workflow_name TEXT DEFAULT '',
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                kind TEXT DEFAULT 'text',
                created_at REAL NOT NULL
            );
            """
        )


# ---------- workflows ----------
def list_workflows() -> list[dict[str, Any]]:
    with _lock, get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM workflows ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_workflow(wid: str) -> dict[str, Any] | None:
    with _lock, get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM workflows WHERE id=?", (wid,)
        ).fetchone()
        return dict(row) if row else None


def upsert_workflow(wid: str, name: str, description: str, graph: dict) -> dict:
    now = time.time()
    g = json.dumps(graph, ensure_ascii=False)
    with _lock, get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM workflows WHERE id=?", (wid,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE workflows SET name=?, description=?, graph=?, updated_at=? WHERE id=?",
                (name, description, g, now, wid),
            )
        else:
            conn.execute(
                "INSERT INTO workflows (id, name, description, graph, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (wid, name, description, g, now, now),
            )
    return get_workflow(wid)  # type: ignore[return-value]


def delete_workflow(wid: str) -> None:
    with _lock, get_conn() as conn:
        conn.execute("DELETE FROM workflows WHERE id=?", (wid,))


# ---------- runs ----------
def create_run(run_id: str, workflow_id: str, workflow_name: str,
               inputs: dict, source: str = "manual") -> None:
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT INTO runs (id, workflow_id, workflow_name, status, inputs, node_outputs, "
            "started_at, source) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, workflow_id, workflow_name, "running",
             json.dumps(inputs, ensure_ascii=False), "{}", time.time(), source),
        )


def finish_run(run_id: str, status: str, outputs: dict, node_outputs: dict,
               error: str | None = None) -> None:
    with _lock, get_conn() as conn:
        conn.execute(
            "UPDATE runs SET status=?, outputs=?, node_outputs=?, finished_at=?, error=? "
            "WHERE id=?",
            (status, json.dumps(outputs, ensure_ascii=False),
             json.dumps(node_outputs, ensure_ascii=False), time.time(), error, run_id),
        )


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    with _lock, get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_run(run_id: str) -> dict[str, Any] | None:
    with _lock, get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None


# ---------- jobs ----------
def list_jobs() -> list[dict[str, Any]]:
    with _lock, get_conn() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock, get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None


def upsert_job(job_id: str, workflow_id: str, workflow_name: str,
               trigger_type: str, trigger_config: dict, inputs: dict,
               enabled: bool = True) -> dict:
    now = time.time()
    tc = json.dumps(trigger_config, ensure_ascii=False)
    inp = json.dumps(inputs, ensure_ascii=False)
    with _lock, get_conn() as conn:
        existing = conn.execute("SELECT id FROM jobs WHERE id=?", (job_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE jobs SET workflow_id=?, workflow_name=?, trigger_type=?, "
                "trigger_config=?, inputs=?, enabled=? WHERE id=?",
                (workflow_id, workflow_name, trigger_type, tc, inp, int(enabled), job_id),
            )
        else:
            conn.execute(
                "INSERT INTO jobs (id, workflow_id, workflow_name, trigger_type, "
                "trigger_config, inputs, enabled, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (job_id, workflow_id, workflow_name, trigger_type, tc, inp,
                 int(enabled), now),
            )
    return get_job(job_id)  # type: ignore[return-value]


def delete_job(job_id: str) -> None:
    with _lock, get_conn() as conn:
        conn.execute("DELETE FROM jobs WHERE id=?", (job_id,))


def touch_job_run(job_id: str, last_run_at: float, next_run_at: float | None) -> None:
    with _lock, get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET last_run_at=?, next_run_at=? WHERE id=?",
            (last_run_at, next_run_at, job_id),
        )


# ---------- assets ----------
def create_asset(asset_id: str, run_id: str | None, workflow_id: str | None,
                 workflow_name: str, title: str, content: str, kind: str = "text") -> None:
    with _lock, get_conn() as conn:
        conn.execute(
            "INSERT INTO assets (id, run_id, workflow_id, workflow_name, title, content, kind, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (asset_id, run_id, workflow_id, workflow_name, title, content, kind, time.time()),
        )


def list_assets() -> list[dict[str, Any]]:
    with _lock, get_conn() as conn:
        rows = conn.execute(
            "SELECT id, run_id, workflow_id, workflow_name, title, kind, created_at, "
            "length(content) AS size FROM assets ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_asset(asset_id: str) -> dict[str, Any] | None:
    with _lock, get_conn() as conn:
        row = conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone()
        return dict(row) if row else None


def delete_asset(asset_id: str) -> None:
    with _lock, get_conn() as conn:
        conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))

"""FastAPI 主应用。"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import storage
from app.api import jobs, providers, runs, workflows
from app.config import WORKFLOWS_DIR
from app.providers.registry import registry
from app.scheduler import shutdown as sched_shutdown
from app.scheduler import start as sched_start

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


def _load_example_workflows() -> None:
    """把 workflows/ 目录下的 JSON 工作流导入（若同名不存在）。"""
    existing = {w["name"] for w in storage.list_workflows()}
    for f in WORKFLOWS_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[example] 跳过 {f.name}: {e}")
            continue
        name = data.get("name") or f.stem
        if name in existing:
            continue
        graph = data.get("graph", {"nodes": [], "edges": []})
        storage.upsert_workflow(_slug(name), name,
                                data.get("description", ""), graph)
        print(f"[example] 导入工作流: {name}")


def _slug(s: str) -> str:
    import re, hashlib
    base = re.sub(r"[^\w-]", "_", s)[:16]
    return base + "_" + hashlib.md5(s.encode()).hexdigest()[:6]


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    await registry.reload()
    _load_example_workflows()
    await sched_start()
    print("✅ 平台已启动：http://localhost:8000")
    yield
    await sched_shutdown()


app = FastAPI(title="TW 工作流平台", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(providers.router)
app.include_router(workflows.router)
app.include_router(runs.router)
app.include_router(jobs.router)


@app.get("/api/health")
async def health():
    return {"ok": True, "providers": registry.list_provider_names()}


# 前端静态资源（构建后）
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        # 非 /api、非静态文件的路径回退到 index.html（SPA 路由）
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        candidate = FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    async def index():
        return {
            "message": "后端已就绪，前端未构建。请在 frontend/ 目录执行 npm install && npm run build",
            "frontend_dist": str(FRONTEND_DIST),
        }

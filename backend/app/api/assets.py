"""资产库：运行的输出结果，可复制/下载/删除。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app import storage

router = APIRouter(prefix="/api", tags=["assets"])


@router.get("/assets")
async def list_assets():
    return {"assets": storage.list_assets()}


@router.get("/assets/{aid}")
async def get_asset(aid: str):
    a = storage.get_asset(aid)
    if not a:
        raise HTTPException(404, "资产不存在")
    return a


@router.get("/assets/{aid}/raw")
async def get_asset_raw(aid: str):
    a = storage.get_asset(aid)
    if not a:
        raise HTTPException(404, "资产不存在")
    return PlainTextResponse(a["content"], media_type="text/plain; charset=utf-8")


@router.delete("/assets/{aid}")
async def delete_asset(aid: str):
    storage.delete_asset(aid)
    return {"ok": True}

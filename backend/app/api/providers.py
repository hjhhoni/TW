"""供应商 / 模型 / 设置 相关接口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import load_settings, save_settings
from app.providers.base import ChatParams, Message
from app.providers.registry import registry

router = APIRouter(prefix="/api", tags=["providers"])


class ChatTestReq(BaseModel):
    provider: str
    model: str
    message: str
    system: str = ""


@router.get("/providers")
async def list_providers():
    settings = load_settings()
    return {"providers": settings.get("providers", [])}


@router.get("/providers/models")
async def list_models():
    return {"providers": await registry.list_all_models()}


@router.post("/providers/reload")
async def reload_providers():
    await registry.reload()
    return {"ok": True, "providers": registry.list_provider_names()}


@router.get("/settings")
async def get_settings():
    return load_settings()


class SettingsUpdate(BaseModel):
    settings: dict


@router.put("/settings")
async def update_settings(body: SettingsUpdate):
    save_settings(body.settings)
    await registry.reload()
    return {"ok": True}


@router.post("/providers/chat")
async def test_chat(req: ChatTestReq):
    try:
        msgs = ([Message("system", req.system)] if req.system else []) + [Message("user", req.message)]
        res = await registry.chat(req.provider, req.model, msgs, ChatParams(temperature=0.7))
        return {"ok": True, "text": res.text, "usage": res.usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

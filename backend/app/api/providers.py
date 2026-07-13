"""供应商 / 模型 / 设置 相关接口。"""
from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import load_settings, save_settings
from app.providers.base import ChatParams, Message
from app.providers.registry import build_from_dict
from app.providers.registry import registry

router = APIRouter(prefix="/api", tags=["providers"])


class ChatTestReq(BaseModel):
    provider: str
    model: str
    message: str
    system: str = ""


class ProviderTestReq(BaseModel):
    type: str
    base_url: str
    api_key: str = ""
    model: str | None = None     # 传入则额外做一次生成测速


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


@router.post("/providers/test")
async def test_provider(req: ProviderTestReq):
    """测试连接 + 拉取模型 + 测速（可选）。

    用前端「未保存」的内联配置即时构造一个临时供应商，无需先保存。
    返回: {ok, connect_ms, models, model_count, chat_ms?, sample?, chat_error?}
    """
    if not req.base_url and req.type != "ollama":
        return {"ok": False, "error": "请先填写 Base URL"}
    provider = build_from_dict({
        "type": req.type, "base_url": req.base_url, "api_key": req.api_key,
    })
    try:
        t0 = time.perf_counter()
        models = await provider.list_models()
        connect_ms = round((time.perf_counter() - t0) * 1000)
    except Exception as e:
        await provider.aclose()
        return {"ok": False, "error": f"连接失败: {e}"}

    clean = [m for m in models if not m.get("error")]
    result = {
        "ok": True,
        "connect_ms": connect_ms,
        "models": clean,
        "model_count": len(clean),
        "has_error_models": any(m.get("error") for m in models),
    }

    if req.model:
        try:
            t1 = time.perf_counter()
            res = await provider.chat(
                req.model, [Message("user", "请只回复两个字：你好")],
                ChatParams(max_tokens=16, temperature=0.3),
            )
            result["chat_ms"] = round((time.perf_counter() - t1) * 1000)
            result["sample"] = (res.text or "")[:200]
        except Exception as e:
            result["chat_error"] = str(e)

    await provider.aclose()
    return result

"""Anthropic Messages API 供应商（Claude）。

与 OpenAI 兼容接口的差异：
- 鉴权用 x-api-key + anthropic-version 头，不是 Bearer。
- system 是顶层字段，不在 messages 里。
- max_tokens 必填。
"""
from __future__ import annotations

import httpx

from .base import ChatParams, ChatResult, LLMProvider, Message, ProviderConfig

# 当 /v1/models 不可用时（部分代理不支持）回退用这些已知模型 ID
_FALLBACK_MODELS = [
    "claude-opus-4-8",
    "claude-sonnet-5",
    "claude-haiku-4-5-20251001",
    "claude-fable-5",
]


class AnthropicProvider(LLMProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        base = config.base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = base + "/v1"
        self._base = base
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=15.0),
            headers={
                "x-api-key": config.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )

    async def list_models(self) -> list[dict]:
        try:
            r = await self._client.get(f"{self._base}/models", params={"limit": 100})
            r.raise_for_status()
            data = r.json()
            items = data.get("data", []) if isinstance(data, dict) else data
            out = []
            for it in items:
                mid = it.get("id")
                if mid:
                    out.append({"id": mid, "name": it.get("display_name") or mid})
            if out:
                return out
            return [{"id": m, "name": m} for m in _FALLBACK_MODELS]
        except Exception as e:
            # /models 不可用就回退已知模型，并附一条错误提示
            return [{"id": m, "name": m} for m in _FALLBACK_MODELS] + \
                [{"id": "_error", "name": f"/models 不可用({e})，已用回退列表", "error": True}]

    async def chat(self, model: str, messages: list[Message], params: ChatParams) -> ChatResult:
        system_parts = [m.content for m in messages if m.role == "system"]
        user_msgs = [{"role": m.role, "content": m.content}
                     for m in messages if m.role in ("user", "assistant")]
        body: dict = {
            "model": model,
            "max_tokens": params.max_tokens or 4096,
            "messages": user_msgs,
            "stream": False,
        }
        if system_parts:
            body["system"] = "\n\n".join(system_parts)
        if params.temperature is not None:
            body["temperature"] = params.temperature
        body.update(params.extra or {})

        r = await self._client.post(f"{self._base}/messages", json=body)
        r.raise_for_status()
        data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")
        return ChatResult(text=text, usage=data.get("usage"), raw=data)

    async def aclose(self) -> None:
        await self._client.aclose()

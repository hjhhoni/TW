"""Ollama 本地模型供应商（原生 /api 接口）。"""
from __future__ import annotations

import httpx

from .base import ChatParams, ChatResult, LLMProvider, Message, ProviderConfig


class OllamaProvider(LLMProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._base = config.base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=15.0),
        )

    async def list_models(self) -> list[dict]:
        try:
            r = await self._client.get(f"{self._base}/api/tags")
            r.raise_for_status()
            data = r.json()
            out = []
            for m in data.get("models", []):
                name = m.get("name") or m.get("model")
                out.append({
                    "id": name,
                    "name": name,
                    "context": (m.get("parameters") or {}).get("num_ctx")
                    if isinstance(m.get("parameters"), dict)
                    else m.get("size"),
                })
            return out
        except Exception as e:
            return [{"id": "_error", "name": f"获取失败（Ollama 是否已启动？）: {e}", "error": True}]

    async def chat(self, model: str, messages: list[Message], params: ChatParams) -> ChatResult:
        body = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": params.temperature,
                **({"num_predict": params.max_tokens} if params.max_tokens else {}),
                **({"top_p": params.top_p} if params.top_p is not None else {}),
            },
        }
        body["options"].update(params.extra)
        r = await self._client.post(f"{self._base}/api/chat", json=body)
        r.raise_for_status()
        data = r.json()
        return ChatResult(
            text=data.get("message", {}).get("content", ""),
            usage={
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            },
            raw=data,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

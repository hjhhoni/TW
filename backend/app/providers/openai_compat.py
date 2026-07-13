"""OpenAI 兼容供应商：适配 OpenAI / DeepSeek / Moonshot / 智谱 / 通用 v1 接口 / Ollama 的 /v1。"""
from __future__ import annotations

import httpx

from .base import ChatParams, ChatResult, LLMProvider, Message, ProviderConfig


class OpenAICompatProvider(LLMProvider):
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        base = config.base_url.rstrip("/")
        # 统一以 /v1 结尾
        if not base.endswith("/v1"):
            base = base + "/v1"
        self._base = base
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=15.0),
            headers=self._auth_headers(),
        )

    def _auth_headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.config.api_key:
            h["Authorization"] = f"Bearer {self.config.api_key}"
        return h

    async def list_models(self) -> list[dict]:
        try:
            r = await self._client.get(f"{self._base}/models")
            r.raise_for_status()
            data = r.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            out = []
            for it in items:
                mid = it.get("id") or it.get("name")
                if mid:
                    out.append({"id": mid, "name": mid, "context": it.get("context_length")})
            return out
        except Exception as e:
            return [{"id": "_error", "name": f"获取失败: {e}", "error": True}]

    async def chat(self, model: str, messages: list[Message], params: ChatParams) -> ChatResult:
        body: dict = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": params.temperature,
            "stream": False,
        }
        if params.max_tokens:
            body["max_tokens"] = params.max_tokens
        if params.top_p is not None:
            body["top_p"] = params.top_p
        body.update(params.extra)

        r = await self._client.post(f"{self._base}/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return ChatResult(text=text, usage=data.get("usage"), raw=data)

    async def aclose(self) -> None:
        await self._client.aclose()

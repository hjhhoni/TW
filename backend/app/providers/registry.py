"""供应商注册表：从 settings 构建所有供应商，统一调度 chat / list_models。"""
from __future__ import annotations

import asyncio
from typing import Any

from app.config import load_settings

from .anthropic import AnthropicProvider
from .base import ChatParams, ChatResult, LLMProvider, Message, ProviderConfig
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatProvider


def _build_provider(config: ProviderConfig) -> LLMProvider:
    if config.type == "ollama":
        return OllamaProvider(config)
    if config.type == "anthropic":
        return AnthropicProvider(config)
    # 默认走 OpenAI 兼容（也覆盖各类 v1 接口）
    return OpenAICompatProvider(config)


def build_from_dict(pcfg: dict) -> LLMProvider:
    """根据内联配置构建一个临时供应商（用于「测试连接/拉取模型」）。"""
    config = ProviderConfig(
        type=pcfg.get("type", "openai_compat"),
        name=pcfg.get("name", "test"),
        base_url=pcfg.get("base_url", ""),
        api_key=pcfg.get("api_key", ""),
    )
    return _build_provider(config)


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LLMProvider] = {}
        self._lock = asyncio.Lock()

    async def reload(self) -> None:
        async with self._lock:
            for p in self._providers.values():
                try:
                    await p.aclose()
                except Exception:
                    pass
            self._providers = {}
            settings = load_settings()
            for pcfg in settings.get("providers", []):
                try:
                    config = ProviderConfig(**pcfg)
                    self._providers[config.name] = _build_provider(config)
                except Exception as e:  # 配置项缺失字段等
                    print(f"[providers] 跳过配置 {pcfg.get('name')}: {e}")

    def list_provider_names(self) -> list[str]:
        return list(self._providers.keys())

    def get(self, name: str) -> LLMProvider:
        if name not in self._providers:
            raise KeyError(f"供应商不存在: {name}")
        return self._providers[name]

    async def list_all_models(self) -> list[dict[str, Any]]:
        """并行列出每个供应商的模型。"""
        async def one(name: str, p: LLMProvider) -> dict[str, Any]:
            try:
                models = await p.list_models()
            except Exception as e:
                models = [{"id": "_error", "name": str(e), "error": True}]
            return {"provider": name, "models": models}

        tasks = [one(n, p) for n, p in self._providers.items()]
        return await asyncio.gather(*tasks)

    async def chat(
        self, provider: str, model: str, messages: list[Message], params: ChatParams
    ) -> ChatResult:
        p = self.get(provider)
        return await p.chat(model, messages, params)


registry = ProviderRegistry()

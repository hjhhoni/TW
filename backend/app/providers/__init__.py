"""模型供应商统一抽象。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Message:
    role: str  # system | user | assistant
    content: str


@dataclass
class ChatParams:
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResult:
    text: str
    usage: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None


@dataclass
class ProviderConfig:
    type: str            # openai_compat | ollama
    name: str
    base_url: str
    api_key: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def list_models(self) -> list[dict[str, Any]]:
        """返回 [{"id": ..., "name": ..., "context": ...}, ...]"""

    @abstractmethod
    async def chat(
        self, model: str, messages: list[Message], params: ChatParams
    ) -> ChatResult:
        ...

    async def aclose(self) -> None:
        pass

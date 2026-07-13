"""全局配置。

API key / provider 配置存在 backend/data/settings.json（运行时写入，gitignore）。
首次启动若不存在则生成默认空配置。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 路径
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WORKFLOWS_DIR = DATA_DIR / "workflows"          # 导入/导出的工作流 JSON
RUNS_DIR = DATA_DIR / "runs"                    # 每次运行的详细产物（可选落盘）
SETTINGS_FILE = DATA_DIR / "settings.json"
DB_PATH = DATA_DIR / "platform.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _default_settings() -> dict[str, Any]:
    return {
        "providers": [
            {
                "type": "openai_compat",
                "name": "OpenAI",
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
            },
            {
                "type": "anthropic",
                "name": "Anthropic (Claude)",
                "base_url": "https://api.anthropic.com",
                "api_key": "",
            },
            {
                "type": "ollama",
                "name": "Ollama (本地)",
                "base_url": "http://localhost:11434",
                "api_key": "",
            },
        ],
        "browser": {
            "headless": True,
            "search_engine": "bing",          # bing | google | baidu
            "timeout_ms": 30000,
            "proxy": "",                       # 例: http://127.0.0.1:7890
        },
    }


def load_settings() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        save_settings(_default_settings())
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = _default_settings()
        save_settings(data)
    return data


def save_settings(settings: dict[str, Any]) -> None:
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )

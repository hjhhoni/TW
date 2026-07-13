"""Playwright 浏览器生命周期管理（单例）。"""
from __future__ import annotations

import asyncio
from typing import Any

from app.config import load_settings

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class BrowserManager:
    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Any = None
        self._lock = asyncio.Lock()

    def _cfg(self) -> dict:
        return load_settings().get("browser", {})

    async def _ensure(self) -> None:
        if self._browser is not None:
            return
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        cfg = self._cfg()
        launch_kwargs: dict[str, Any] = {"headless": cfg.get("headless", True)}
        proxy = cfg.get("proxy")
        if proxy:
            launch_kwargs["proxy"] = {"server": proxy}
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)

    async def new_context(self) -> Any:
        async with self._lock:
            await self._ensure()
            cfg = self._cfg()
            browser = self._browser
        context = await browser.new_context(
            user_agent=_UA,
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            viewport={"width": 1366, "height": 800},
            extra_http_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
        )
        # 反爬基础：去掉 webdriver 标记
        await context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        return context

    async def close(self) -> None:
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
            self._browser = None
            self._playwright = None


browser_manager = BrowserManager()

"""真实浏览器搜索：Bing / Baidu / Google。

返回结构化结果 [{title, url, snippet, engine}]，不做任何 LLM 摘要，
保证拿到的都是搜索引擎真实返回的链接与摘要。
"""
from __future__ import annotations

import asyncio
import urllib.parse
from typing import Any

from . import browser_manager

_ENGINES: dict[str, dict[str, Any]] = {
    "bing": {
        "url": "https://www.bing.com/search?q={q}&setlang=zh-CN&ensearch=0",
        "wait_sel": "li.b_algo, .b_results",
        "extract": """
        () => {
          const out = [];
          document.querySelectorAll('li.b_algo').forEach(li => {
            const a = li.querySelector('h2 a');
            const sn = li.querySelector('.b_caption p, p');
            if (a && a.href) out.push({title: a.innerText.trim(), url: a.href, snippet: sn ? sn.innerText.trim() : ''});
          });
          return out;
        }""",
    },
    "baidu": {
        "url": "https://www.baidu.com/s?wd={q}&rn=20",
        "wait_sel": ".result, .c-container",
        "extract": """
        () => {
          const out = [];
          document.querySelectorAll('.result.c-container, .c-container').forEach(c => {
            const a = c.querySelector('h3 a');
            const sn = c.querySelector('.c-abstract, [class*="abstract"], span');
            if (a && a.href) out.push({title: a.innerText.trim(), url: a.href, snippet: sn ? sn.innerText.trim() : ''});
          });
          return out;
        }""",
    },
    "google": {
        "url": "https://www.google.com/search?q={q}&hl=zh-CN&num=20",
        "wait_sel": "div.g, #search",
        "extract": """
        () => {
          const out = [];
          document.querySelectorAll('div.g').forEach(g => {
            const a = g.querySelector('a');
            const h = g.querySelector('h3');
            if (a && h && a.href && !a.href.includes('google.com')) {
              const sn = g.querySelector('div[data-sncf], div.VwiC3b, span');
              out.push({title: h.innerText.trim(), url: a.href, snippet: sn ? sn.innerText.trim() : ''});
            }
          });
          return out;
        }""",
    },
}


async def search(
    query: str,
    engine: str = "bing",
    max_results: int = 10,
    extra_selectors: list[str] | None = None,
) -> list[dict[str, Any]]:
    engine = engine.lower()
    if engine not in _ENGINES:
        engine = "bing"
    spec = _ENGINES[engine]
    url = spec["url"].format(q=urllib.parse.quote(query))

    context = await browser_manager.new_context()
    page = await context.new_page()
    results: list[dict[str, Any]] = []
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # 等结果渲染
        try:
            await page.wait_for_selector(spec["wait_sel"], timeout=8000)
        except Exception:
            await asyncio.sleep(1.5)
        await asyncio.sleep(0.8)
        raw = await page.evaluate(spec["extract"])
        seen = set()
        for it in raw:
            u = it.get("url", "")
            if not u or u in seen:
                continue
            seen.add(u)
            results.append({
                "title": it.get("title", ""),
                "url": u,
                "snippet": it.get("snippet", ""),
                "engine": engine,
            })
            if len(results) >= max_results:
                break
    finally:
        await context.close()

    if not results:
        results.append({
            "title": "（无结果）",
            "url": url,
            "snippet": f"{engine} 未返回结构化结果，可能被验证码拦截或选择器失效。",
            "engine": engine,
            "empty": True,
        })
    return results


async def multi_search(
    query: str, engines: list[str], max_per_engine: int = 8
) -> list[dict[str, Any]]:
    """多引擎并发搜索 + 去重。"""
    tasks = [search(query, e, max_per_engine) for e in engines]
    batches = await asyncio.gather(*tasks, return_exceptions=True)
    merged: list[dict[str, Any]] = []
    seen = set()
    for b in batches:
        if isinstance(b, Exception):
            continue
        for it in b:
            if it.get("empty"):
                continue
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            merged.append(it)
    return merged

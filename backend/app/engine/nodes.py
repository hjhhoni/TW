"""节点处理器实现。每个处理器签名:
    async def(node: NodeSpec, cfg: dict, outputs: dict, ctx: RunContext) -> dict
cfg 已经过模板解析（除 'code' 键外）。
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.browser.extractor import fetch_and_extract
from app.browser.searcher import multi_search, search
from app.providers.base import ChatParams, Message
from app.providers.registry import registry

from .context import RunContext
from .schema import NodeSpec


# ---------------- helpers ----------------
def _normalize_date_key(s: str | None) -> str | None:
    if not s:
        return None
    m = re.search(r"(20\d{2})\D+(\d{1,2})(?:\D+(\d{1,2}))?", s)
    if not m:
        return None
    y, mo, d = m.groups()
    return f"{int(y):04d}-{int(mo):02d}-{int(d) if d else 1:02d}"


def _in_range(pub: str | None, date_from: str | None, date_to: str | None) -> bool | None:
    if not (date_from or date_to):
        return None
    k = _normalize_date_key(pub)
    if not k:
        return None
    lo = _normalize_date_key(date_from + "-01") if date_from and len(date_from) == 7 else _normalize_date_key(date_from)
    hi = _normalize_date_key(date_to + "-28") if date_to and len(date_to) == 7 else _normalize_date_key(date_to)
    if lo and k < lo:
        return False
    if hi and k > hi:
        return False
    return True


def _collect_urls(val: Any) -> list[str]:
    """从任意结构（str/list/dict）递归收集 url 字符串。"""
    urls: list[str] = []
    if isinstance(val, str):
        s = val.strip()
        if s.startswith("["):
            try:
                return _collect_urls(json.loads(s))
            except Exception:
                pass
        for ln in s.splitlines():
            ln = ln.strip()
            if ln.startswith("http"):
                urls.append(ln)
    elif isinstance(val, list):
        for it in val:
            urls.extend(_collect_urls(it))
    elif isinstance(val, dict):
        if isinstance(val.get("url"), str):
            urls.append(val["url"])
        for v in val.values():
            if isinstance(v, (list, dict)):
                urls.extend(_collect_urls(v))
    # 去重保序
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


# ---------------- handlers ----------------
async def h_input(node: NodeSpec, cfg: dict, outputs: dict, ctx: RunContext) -> dict:
    key = cfg.get("key") or node.id
    default = cfg.get("default", "")
    val = ctx.inputs.get(key, ctx.inputs.get(node.id, default))
    return {"text": str(val), "value": val, "key": key}


async def h_search(node: NodeSpec, cfg: dict, outputs: dict, ctx: RunContext) -> dict:
    q = cfg.get("query")
    if q is None:
        q = cfg.get("queries", "")
    if isinstance(q, list):
        queries = [str(x).strip() for x in q if str(x).strip()]
    else:
        queries = [ln.strip() for ln in str(q).splitlines() if ln.strip()]

    engines = cfg.get("engines") or cfg.get("engine") or "bing"
    if isinstance(engines, str):
        engines = [e.strip() for e in engines.split(",") if e.strip()]
    engines = engines or ["bing"]
    maxq = int(cfg.get("max_per_query", 5))

    groups: list[dict] = []
    for query in queries:
        try:
            items = await multi_search(query, engines, maxq) if len(engines) > 1 \
                else await search(query, engines[0], maxq)
        except Exception as e:
            items = [{"title": "搜索出错", "url": "", "snippet": str(e), "engine": "?", "error": True}]
        groups.append({"query": query, "items": items})

    urls = [it["url"] for g in groups for it in g["items"] if it.get("url")]
    lines = []
    for g in groups:
        lines.append(f"【{g['query']}】")
        for it in g["items"]:
            lines.append(f"- {it.get('title','')}\n  {it.get('url','')}\n  {it.get('snippet','')}")
    return {"results": groups, "urls": urls, "text": "\n".join(lines)}


async def h_fetch(node: NodeSpec, cfg: dict, outputs: dict, ctx: RunContext) -> dict:
    urls = _collect_urls(cfg.get("urls", ""))
    date_from = (cfg.get("date_from") or "").strip() or None
    date_to = (cfg.get("date_to") or "").strip() or None
    max_total = int(cfg.get("max_total", 20))
    max_chars = int(cfg.get("max_chars_per", 4000))
    # 多抓一些以便按日期过滤后仍有足够数量
    fetch_cap = min(len(urls), max_total * 2 if (date_from or date_to) else max_total, 40)

    pages: list[dict] = []
    for u in urls[:fetch_cap]:
        try:
            p = await fetch_and_extract(u, max_chars)
        except Exception as e:
            p = {"url": u, "ok": False, "error": str(e), "text": "", "title": "", "publish_date": None}
        if not p.get("ok") or not p.get("text"):
            continue
        p["in_range"] = _in_range(p.get("publish_date"), date_from, date_to)
        pages.append(p)

    # 在范围内的优先；若没有任何在范围内，保留全部（标注）
    dated = [p for p in pages if p.get("in_range") is True]
    primary = dated if dated else pages
    primary = primary[:max_total]

    lines = []
    for p in primary:
        flag = "" if p.get("in_range") is None else ("✓" if p["in_range"] else "✗")
        lines.append(
            f"[{p.get('publish_date') or '日期未知'} {flag}] {p.get('title','')}\n"
            f"{p.get('url','')}\n{p['text'][:1200]}"
        )
    return {"pages": primary, "dated": dated, "text": "\n\n".join(lines)}


async def h_llm(node: NodeSpec, cfg: dict, outputs: dict, ctx: RunContext) -> dict:
    provider = cfg.get("provider", "")
    model = cfg.get("model", "")
    if not provider or not model:
        raise ValueError("LLM 节点未配置 provider / model")
    system = cfg.get("system", "")
    user = cfg.get("user", "")
    temperature = float(cfg.get("temperature", 0.7))
    max_tokens = cfg.get("max_tokens")
    msgs: list[Message] = []
    if system:
        msgs.append(Message("system", system))
    msgs.append(Message("user", user))
    res = await registry.chat(
        provider, model, msgs,
        ChatParams(temperature=temperature, max_tokens=int(max_tokens) if max_tokens else None),
    )
    return {"text": res.text, "usage": res.usage}


async def h_transform(node: NodeSpec, cfg: dict, outputs: dict, ctx: RunContext) -> dict:
    code = (cfg.get("code") or "").strip()
    if code:
        glb: dict[str, Any] = {"nodes": outputs, "json": json, "re": re, "result": None}
        try:
            exec(compile(code, "<transform>", "exec"), glb)
        except Exception as e:
            return {"text": f"[代码执行出错] {e}", "value": None}
        res = glb.get("result")
        if isinstance(res, str):
            text = res
        elif res is None:
            text = ""
        else:
            text = json.dumps(res, ensure_ascii=False, indent=2)
        return {"text": text, "value": res}
    text = cfg.get("template", "")
    return {"text": str(text), "value": text}


async def h_condition(node: NodeSpec, cfg: dict, outputs: dict, ctx: RunContext) -> dict:
    expr = str(cfg.get("expr", "")).strip().lower()
    passed = expr not in ("", "0", "false", "no", "none", "null")
    return {"text": str(passed), "pass": passed}


async def h_output(node: NodeSpec, cfg: dict, outputs: dict, ctx: RunContext) -> dict:
    val = cfg.get("value", "")
    return {"text": str(val)}


NODE_HANDLERS = {
    "input": h_input,
    "search": h_search,
    "fetch": h_fetch,
    "llm": h_llm,
    "transform": h_transform,
    "condition": h_condition,
    "output": h_output,
}

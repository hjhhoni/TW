"""正文与发布时间提取：抓取单个 URL，返回 {title, text, publish_date, url, ok}。

发布时间检测优先级：
  1) meta 标签（article:published_time / og:* / datePublished / pubdate 等）
  2) JSON-LD 结构化数据
  3) 正文正则（2026-07-15 / 2026年7月15日 / 07-15 等）
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import browser_manager

_DATE_PATTERNS = [
    r"20\d{2}[-/.年]\s*\d{1,2}[-/.月]\s*\d{1,2}",
    r"20\d{2}[-/.年]\s*\d{1,2}",
]

_META_DATES = [
    "article:published_time",
    "og:published_time",
    "datePublished",
    "publishdate",
    "pubdate",
    "dc.date",
    "itemprop:datePublished",
    "weibo:article:create_at",
]

_EXTRACT_JS = """
(url) => {
  const meta = {};
  document.querySelectorAll('meta').forEach(m => {
    const k = (m.getAttribute('property') || m.getAttribute('name') || m.getAttribute('itemprop') || '').toLowerCase();
    const v = m.getAttribute('content');
    if (k && v) meta[k] = v;
  });
  // JSON-LD
  let ldDate = null;
  document.querySelectorAll('script[type="application/ld+json"]').forEach(s => {
    try {
      const o = JSON.parse(s.textContent);
      const arr = Array.isArray(o) ? o : [o];
      for (const it of arr) {
        const d = it.datePublished || (it.mainEntity && it.mainEntity.datePublished);
        if (d) { ldDate = d; }
      }
    } catch (e) {}
  });
  // 正文
  document.querySelectorAll('script,style,noscript,nav,footer,header,aside').forEach(e => e.remove());
  let root = document.querySelector('article') || document.querySelector('main') || document.body;
  const paragraphs = Array.from(root.querySelectorAll('p,li,h1,h2,h3'))
      .map(e => e.innerText.trim())
      .filter(t => t.length > 8);
  const text = paragraphs.join('\\n');
  const title = (document.querySelector('h1') && document.querySelector('h1').innerText.trim())
      || document.title || '';
  return {title, text: text.slice(0, 8000), meta, ldDate, rawDateText: (text.match(/20\\d{2}[\\-/.年]\\s*\\d{1,2}[\\-/.月]?\\s*\\d{0,2}/g) || []).join(' | ')};
}
"""


def _normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    # ISO 形如 2026-07-15T08:00:00+08:00
    m = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    m = re.search(r"(20\d{2})[-/.年](\d{1,2})", s)
    if m:
        y, mo = m.groups()
        return f"{int(y):04d}-{int(mo):02d}"
    return None


async def fetch_and_extract(url: str, max_chars: int = 6000) -> dict[str, Any]:
    context = await browser_manager.new_context()
    page = await context.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        status = resp.status if resp else None
        try:
            await page.wait_for_load_state("networkidle", timeout=4000)
        except Exception:
            pass
        data = await page.evaluate(_EXTRACT_JS)
    except Exception as e:
        await context.close()
        return {"url": url, "ok": False, "error": str(e), "title": "", "text": "",
                "publish_date": None}
    await context.close()

    # 取发布时间
    pub = None
    for key in _META_DATES:
        v = data.get("meta", {}).get(key)
        if v:
            pub = _normalize_date(v) or v
            if pub:
                break
    if not pub and data.get("ldDate"):
        pub = _normalize_date(data["ldDate"])
    if not pub:
        pub = _normalize_date(data.get("rawDateText"))

    text = (data.get("text") or "")[:max_chars]
    return {
        "url": url,
        "ok": True,
        "status": status,
        "title": data.get("title", ""),
        "text": text,
        "publish_date": pub,
    }

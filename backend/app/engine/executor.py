"""工作流执行器：模板解析 + 依赖拓扑排序 + 节点调度。

数据流模型：节点通过在 config 里写 {{nodeId}} 或 {{nodeId.key}} 引用上游输出，
执行器按引用依赖自动排序并解析。前端画的边作为可视提示，也参与排序。
"""
from __future__ import annotations

import json
import re
from typing import Any

from .context import RunContext
from .nodes import NODE_HANDLERS
from .schema import WorkflowGraph

_REF_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


# ---------------- 模板解析 ----------------
def _lookup(ref: str, outputs: dict[str, Any]) -> Any:
    parts = ref.split(".")
    nid = parts[0]
    if nid not in outputs:
        return None
    val = outputs[nid]
    rest = parts[1:]
    if not rest and isinstance(val, dict):
        # 无路径引用 -> 默认取 text
        return val.get("text", val)
    for p in rest:
        if isinstance(val, dict):
            val = val.get(p)
        elif isinstance(val, list):
            try:
                val = val[int(p)]
            except Exception:
                return None
        else:
            return None
        if val is None:
            return None
    return val


def _resolve_str(s: str, outputs: dict[str, Any]) -> Any:
    stripped = s.strip()
    m = _REF_RE.fullmatch(stripped)
    if m:
        v = _lookup(m.group(1), outputs)
        return v if v is not None else ""

    def repl(mm: re.Match) -> str:
        v = _lookup(mm.group(1), outputs)
        if v is None:
            return ""
        if isinstance(v, (dict, list)):
            return json.dumps(v, ensure_ascii=False)
        return str(v)

    return _REF_RE.sub(repl, s)


def _resolve_value(v: Any, outputs: dict[str, Any]) -> Any:
    if isinstance(v, str):
        return _resolve_str(v, outputs)
    if isinstance(v, list):
        return [_resolve_value(x, outputs) for x in v]
    if isinstance(v, dict):
        # code 段保持原文（可能含花括号）
        return {k: (val if k == "code" else _resolve_value(val, outputs))
                for k, val in v.items()}
    return v


# ---------------- 依赖与拓扑 ----------------
def _ref_deps(node_id: str, config: dict, node_ids: set[str]) -> set[str]:
    deps: set[str] = set()
    blob = json.dumps(config, ensure_ascii=False)
    for m in _REF_RE.finditer(blob):
        nid = m.group(1).split(".")[0]
        if nid in node_ids and nid != node_id:
            deps.add(nid)
    return deps


def _topo(graph: WorkflowGraph) -> list[str]:
    node_ids = {n.id for n in graph.nodes}
    preds: dict[str, set[str]] = {n.id: set() for n in graph.nodes}
    for n in graph.nodes:
        preds[n.id] |= _ref_deps(n.id, n.config, node_ids)
    for e in graph.edges:
        if e.source in node_ids and e.target in node_ids and e.source != e.target:
            preds[e.target].add(e.source)

    # Kahn
    order: list[str] = []
    ready = sorted([nid for nid, p in preds.items() if not p])
    # 保持稳定：按 nodes 列表原始顺序排序
    pos = {n.id: i for i, n in enumerate(graph.nodes)}
    ready = sorted([nid for nid, p in preds.items() if not p], key=lambda x: pos[x])
    remaining = dict(preds)
    while ready:
        nid = ready.pop(0)
        order.append(nid)
        del remaining[nid]
        for other in list(remaining):
            if nid in remaining[other]:
                remaining[other].discard(nid)
                if not remaining[other]:
                    ready.append(other)
        ready.sort(key=lambda x: pos[x])
    if len(order) != len(graph.nodes):
        cyclic = [nid for nid in preds if nid not in order]
        raise ValueError(f"存在循环依赖: {cyclic}")
    return order


# ---------------- 执行 ----------------
def _preview(out: dict, n: int = 300) -> str:
    t = out.get("text", "")
    if isinstance(t, str):
        return t[:n]
    return str(t)[:n]


async def execute(graph: WorkflowGraph, ctx: RunContext) -> dict[str, Any]:
    node_map = {n.id: n for n in graph.nodes}
    order = _topo(graph)
    outputs: dict[str, Any] = {}
    errors: list[list[str]] = []

    for nid in order:
        node = node_map[nid]
        # run_if 条件跳过
        rif = node.config.get("_run_if")
        if rif:
            resolved = str(_resolve_str(str(rif), outputs)).strip().lower()
            if resolved in ("", "0", "false", "no", "none", "null"):
                outputs[nid] = {"text": "", "skipped": True}
                await ctx.emit(nid, "skipped")
                continue

        await ctx.emit(nid, "start")
        handler = NODE_HANDLERS.get(node.type)
        if not handler:
            msg = f"未知节点类型: {node.type}"
            outputs[nid] = {"text": "", "error": msg}
            errors.append([nid, msg])
            await ctx.emit(nid, "error", {"error": msg})
            continue

        try:
            cfg = _resolve_value(node.config, outputs)
            out = await handler(node, cfg, outputs, ctx)
            outputs[nid] = out
            await ctx.emit(nid, "success", {"preview": _preview(out)})
        except Exception as e:
            outputs[nid] = {"text": "", "error": str(e)}
            errors.append([nid, str(e)])
            await ctx.emit(nid, "error", {"error": str(e)})

    final: dict[str, str] = {}
    for n in graph.nodes:
        if n.type == "output":
            final[n.label or n.id] = str(outputs.get(n.id, {}).get("text", ""))

    return {
        "outputs": final,
        "node_outputs": outputs,
        "errors": errors,
        "order": order,
    }

"""工作流图的数据模型（与前端 React Flow 对齐）。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class NodePosition(BaseModel):
    x: float = 0
    y: float = 0


class NodeSpec(BaseModel):
    id: str
    type: str                       # input | llm | search | fetch | transform | condition | output
    label: str = ""
    position: NodePosition = Field(default_factory=NodePosition)
    config: dict = {}               # 节点参数；可含模板 {{nodeId.key}}；特殊键 _run_if / code


class EdgeSpec(BaseModel):
    id: str
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None


class WorkflowGraph(BaseModel):
    nodes: list[NodeSpec] = []
    edges: list[EdgeSpec] = []


class WorkflowSpec(BaseModel):
    id: str
    name: str
    description: str = ""
    graph: WorkflowGraph = Field(default_factory=WorkflowGraph)


# 前端节点面板用的元信息
NODE_TYPES = {
    "input": {
        "label": "输入",
        "color": "#3b82f6",
        "desc": "定义工作流输入变量（如目标月份）",
        "fields": [
            {"key": "key", "label": "变量名", "type": "text", "default": "month"},
            {"key": "default", "label": "默认值", "type": "text", "default": ""},
        ],
    },
    "search": {
        "label": "联网搜索",
        "color": "#10b981",
        "desc": "本地浏览器真实搜索，多行=多个查询",
        "fields": [
            {"key": "query", "label": "查询词（多行多个）", "type": "textarea", "default": ""},
            {"key": "engines", "label": "搜索引擎", "type": "text", "default": "bing,baidu"},
            {"key": "max_per_query", "label": "每查询结果数", "type": "number", "default": 5},
        ],
    },
    "fetch": {
        "label": "抓取网页",
        "color": "#14b8a6",
        "desc": "抓取正文+发布时间，可按月份过滤",
        "fields": [
            {"key": "urls", "label": "URL（{{node.urls}} 或每行一个）", "type": "textarea", "default": ""},
            {"key": "date_from", "label": "起始月份 YYYY-MM", "type": "text", "default": ""},
            {"key": "date_to", "label": "截止月份 YYYY-MM", "type": "text", "default": ""},
            {"key": "max_total", "label": "最多抓取数", "type": "number", "default": 20},
        ],
    },
    "llm": {
        "label": "LLM",
        "color": "#f59e0b",
        "desc": "调用模型，prompt 支持 {{node}} 引用",
        "fields": [
            {"key": "provider", "label": "供应商", "type": "provider"},
            {"key": "model", "label": "模型", "type": "model"},
            {"key": "system", "label": "System Prompt", "type": "textarea", "default": ""},
            {"key": "user", "label": "User Prompt", "type": "textarea", "default": ""},
            {"key": "temperature", "label": "Temperature", "type": "number", "default": 0.7},
        ],
    },
    "transform": {
        "label": "转换",
        "color": "#8b5cf6",
        "desc": "模板拼接 或 Python 代码处理",
        "fields": [
            {"key": "template", "label": "模板（{{node}} 拼接）", "type": "textarea", "default": ""},
            {"key": "code", "label": "或 Python 代码（result=... 可用 nodes）", "type": "code", "default": ""},
        ],
    },
    "condition": {
        "label": "条件",
        "color": "#ef4444",
        "desc": "输出 pass 布尔，配合节点的 run_if",
        "fields": [
            {"key": "expr", "label": "条件（已解析的文本，非空为真）", "type": "text", "default": ""},
        ],
    },
    "output": {
        "label": "输出",
        "color": "#6366f1",
        "desc": "标记最终输出",
        "fields": [
            {"key": "value", "label": "输出内容（{{node}}）", "type": "textarea", "default": ""},
        ],
    },
}

# TW 工作流平台

一个**轻量、本地、可拖拽**的 AI 工作流平台：接入任意 AI 模型（OpenAI 兼容 / Anthropic / 本地 Ollama），用**本地真实浏览器**联网搜索，可视化搭建工作流，支持定时任务、资产库。

核心能力：**先联网查证真实素材，再让模型只用查到的素材写稿** —— 保证输出信息真实、可溯源、时间对得上。

## 特性

- 🤖 **模型接入**：OpenAI 兼容（OpenAI / DeepSeek / Moonshot / 智谱 / 硅基流动…）、Anthropic（Claude）、本地 Ollama。设置页可**测试连接 / 拉取模型 / 测速**。
- 🌐 **本地浏览器搜索**：Playwright 真实浏览器，Bing/Baidu/Google 多引擎并发，抓正文 + 提取**发布时间**。
- 🧩 **可视化工作流**：React Flow 拖拽建图。节点：输入 / 联网搜索 / 抓取网页 / LLM / 转换(模板或Python) / 条件 / 输出。
- 🚀 **后台非阻塞运行**：点运行后立即返回，**可自由操作页面**；右下角浮动面板看进度，完成后 toast 提示。
- 📦 **资产库**：每次运行的输出自动存档，可随时**预览 / 复制 / 下载 / 删除**。
- 🔁 **导入 / 导出 / 复制**工作流（JSON 粘贴或上传文件）。
- ⏰ **定时任务**：APScheduler，cron / 间隔。

## 一键运行

**首次安装（跑一次即可）**：双击 `install.bat`（装后端依赖 + chromium + 前端构建）。

**日常启动**：双击 `start.bat` → 自动打开 `http://localhost:8000`。
（`start.bat` 也会在依赖缺失时自动补装，所以直接双击它也行。）

> 分发给其他用户：把整个文件夹打包（确保含已构建的 `frontend/dist`），对方装好 Python 后双击 `start.bat` 即可；Node 仅在需要重新构建前端时才装。

开发模式（热更新，`http://localhost:5173`，自动代理后端）：
```bash
cd backend && python run.py        # 终端1：后端
cd frontend && npm run dev          # 终端2：前端
```

## 使用流程

1. **设置模型**：「设置」页填 base_url + api_key → 点「测试连接 / 拉取模型」验证 → 选模型「⚡ 测速」。**自动保存**，切走也不丢。
2. **工作流**：选「游戏月报生成」（内置示例）→「撰写月报」节点选 provider/model → 💾保存。
3. **运行**：▶ 运行 → 填月份（如 `2026-07`）→ 点「开始运行（后台）」。**此时可随意切页面**，右下角面板看进度。
4. **结果**：完成后 toast 提示；输出自动进「资产库」，可预览/复制/下载。
5. **定时**：「定时任务」页，如「每月 1 号 9:00」自动生成。

## 「游戏月报」如何保证真实

```
输入月份 → 解析日期范围 → 8游戏联网搜索 → 抓取正文+按月过滤 → 结构化素材 → LLM按模板写稿
```

- **时间对得上**：`抓取网页`节点按 `date_from/date_to` 只保留目标月份内的页面（✓在范围 / ✗范围外不用）。
- **真实不编撰**：LLM 红线规则——只用 `[在范围内]` 素材，无素材则跳过，绝不编造。
- **可溯源**：每条素材带来源+可信度级，成稿每段标注「信息来源，可信度：N级」。

模板抽自 `第一期游戏月报文案提示词模板.docx`，存于 `templates/game_monthly_report.md`。

## 目录结构

```
TW/
├── start.bat / install.bat        # 一键启动 / 首次安装
├── backend/
│   ├── app/
│   │   ├── providers/             # 模型供应商（OpenAI兼容/Anthropic/Ollama）
│   │   ├── browser/               # Playwright 真实浏览器搜索/抓取
│   │   ├── engine/                # 工作流引擎（图执行 + 节点处理器）
│   │   ├── scheduler/             # APScheduler 定时任务
│   │   ├── storage/               # sqlite（工作流/运行/任务/资产）
│   │   ├── api/                   # FastAPI 路由（providers/workflows/runs/jobs/assets）
│   │   ├── broker.py              # 运行事件分发（SSE，缓冲+多订阅）
│   │   ├── config.py / main.py
│   ├── data/                      # 运行时数据（已 gitignore）
│   └── run.py
├── frontend/                      # React + React Flow
├── templates/                     # 游戏月报模板
└── scripts/build_example_workflow.py
```

## 数据流引用语法

| 写法 | 含义 |
|---|---|
| `{{nodeId}}` | 上游文本输出（取 `text`） |
| `{{nodeId.results}}` | 上游某字段（列表/字典可继续 `.0` 下标） |
| `{{nodeId.value.from}}` | 转换节点代码返回 dict 的嵌套字段 |

## 安全提示

- `transform` 节点的 Python 代码在服务端执行（可访问上游 `nodes`）。本地自用无妨；若对外部署，需禁用 code 节点或加沙箱。
- 平台无鉴权，仅适合本地单用户；若暴露到公网请加反向代理+鉴权。

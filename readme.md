# TW 工作流平台

一个**轻量、本地、可拖拽**的 AI 工作流平台：接入任意 AI 模型（OpenAI 兼容 API 或本地 Ollama），用**本地真实浏览器**联网搜索，可视化搭建工作流，支持定时任务。

核心能力：**先联网查证真实素材，再让模型只用查到的素材写稿** —— 保证输出信息真实、可溯源、时间对得上。

## 特性

- 🤖 **模型接入**：OpenAI 兼容接口（OpenAI / DeepSeek / Moonshot / 智谱 / 硅基流动 等）+ 本地 Ollama，可在 UI 切换。
- 🌐 **本地浏览器搜索**：Playwright 驱动真实浏览器，支持 Bing / Baidu / Google 多引擎并发，抓取正文 + 自动提取**发布时间**。
- 🧩 **可视化工作流**：React Flow 拖拽建图。节点类型：输入 / 联网搜索 / 抓取网页 / LLM / 转换(模板或Python) / 条件 / 输出。
- 🔗 **数据流**：节点用 `{{节点ID}}` 或 `{{节点ID.字段}}` 引用上游输出，引擎按引用依赖自动排序。
- ⏰ **定时任务**：APScheduler，支持 cron（每月几号几点）和间隔调度。
- 📊 **运行历史 + 实时进度**：SSE 推送每个节点的运行状态。

## 快速开始

### 1. 后端

```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium     # 安装浏览器内核（搜索/抓取用）
python run.py                              # 启动 → http://localhost:8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run build      # 构建到 frontend/dist，后端会自动托管
```

开发模式（热更新，访问 http://localhost:5173 ，自动代理到后端）：

```bash
npm run dev
```

打开 http://localhost:8000 即可使用。内置「游戏月报生成」示例工作流会自动导入。

## 使用流程

1. **设置模型**：进入「设置」页，填好供应商的 `base_url` 和 `api_key`（或确保 Ollama 在 `localhost:11434` 运行），保存。
2. **打开工作流**：「工作流」页选中「游戏月报生成」。
3. **选模型**：点「撰写月报」节点，在属性面板选 provider / model。
4. **运行**：点右上角「▶ 运行」，输入目标月份（如 `2026-07`），查看实时进度与成稿。
5. **定时**：进「定时任务」页，比如设置「每月 1 号 9:00」自动生成上月月报。

## 「游戏月报」工作流是如何保证真实的

```
输入月份 → 解析日期范围 → 8个游戏联网搜索 → 抓取正文+按月份过滤 → 结构化素材 → LLM按模板写稿
```

- **时间对得上**：`抓取网页` 节点设了 `date_from/date_to`，只保留发布日期在目标月份内的页面（标 ✓），范围外的标 ✗ 不用。
- **真实不编撰**：LLM 的 system prompt 是红线规则，明确「只能用 [在范围内] 素材，无素材则跳过该板块，绝不编造」。
- **可溯源**：每条素材带来源链接 + 可信度建议级（1级官方/2级媒体/3级社区），成稿每段标注「信息来源，可信度：N级」。

模板规则抽自 `第一期游戏月报文案提示词模板.docx`，存于 `templates/game_monthly_report.md`。

## 目录结构

```
TW/
├── backend/
│   ├── app/
│   │   ├── providers/      # 模型供应商（OpenAI兼容 + Ollama）
│   │   ├── browser/        # Playwright 真实浏览器搜索/抓取
│   │   ├── engine/         # 工作流引擎（图执行 + 节点处理器）
│   │   ├── scheduler/      # APScheduler 定时任务
│   │   ├── storage/        # sqlite 持久化
│   │   ├── api/            # FastAPI 路由
│   │   ├── broker.py       # 运行事件分发（SSE）
│   │   ├── config.py / main.py
│   ├── data/               # 运行时数据（db / settings / 示例工作流，已 gitignore）
│   └── run.py
├── frontend/               # React + React Flow 可视化前端
├── templates/              # 游戏月报模板（Markdown）
├── scripts/build_example_workflow.py   # 重新生成示例工作流 JSON
└── readme.md
```

## 数据流引用语法

任何节点的配置文本里都能引用上游：

| 写法 | 含义 |
|---|---|
| `{{nodeId}}` | 上游节点的文本输出（取 `text` 字段） |
| `{{nodeId.results}}` | 上游输出的某个字段（列表/字典可继续 `.` 或 `.0` 下标） |
| `{{nodeId.value.from}}` | 转换节点代码返回的 dict 的嵌套字段 |

## API 速览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 健康检查 |
| GET/PUT | `/api/settings` | 读取/保存供应商与浏览器配置 |
| GET | `/api/providers/models` | 列出所有供应商的模型 |
| GET/POST/PUT/DELETE | `/api/workflows` | 工作流 CRUD |
| POST | `/api/workflows/{id}/run` | 运行（`{stream:true}` 返回 SSE 实时进度） |
| GET | `/api/runs` | 运行历史 |
| GET/POST/DELETE | `/api/jobs` | 定时任务 |

## 备注

- 浏览器搜索偶发会被搜索引擎验证码拦截（结果会标注「无结果」）。可换引擎、加代理、或调低并发。设置里可关掉无头模式观察实际浏览器。
- `transform` 节点的 Python 代码在服务端执行（有 `nodes` 字典可访问上游输出），仅用于数据处理，请勿运行不受信工作流。

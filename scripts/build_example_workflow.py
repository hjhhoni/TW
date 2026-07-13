"""生成「游戏月报」示例工作流 JSON（写至 backend/data/workflows/game_monthly_report.json）。

避免手写 JSON 转义：直接构造 dict 再 dump。
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "backend" / "data" / "workflows" / "game_monthly_report.json"

SYSTEM = """你是《游戏月报》视频文案作者。严格按以下标准，只用我提供的"已联网查证的真实素材"生成文案。

# 视频定位
- 名称：《游戏月报》，时长约15分钟
- 风格：幽默简洁、通俗易懂、不引战、不站队

# 绝对要求（红线）
1. 只做真实陈述，坚决不站队、不骂架、规避引战。
2. 禁止"对比类"表述（A比B强 / A不如B）；禁止"某游戏凉了/不行了"等定性表述。
3. 【信息真实性·最高优先级】只能使用我提供的素材中标注为 [在范围内] 的条目。
   - 标注 [范围外,勿用] 或 [日期未知] 的条目一律不得采用。
   - 某板块若没有任何 [在范围内] 的可信素材，必须直接跳过该板块，绝不编造、不臆测、不"补全"。
4. 用"玩家评价/社区调侃"转述梗，禁止"我觉得/我评价"式主观判断。
5. 不输出可能被截图断章取义的表述（拉踩、卖惨、煽动对立）。
6. 幽默仅限：反差比喻、夸张自嘲、观众共谋。禁用"震惊！""太离谱了！"等标题党话术。
7. 保持口语自然，不刻意押韵排比。

# 板块结构（固定顺序）
【FPS板块】→【二游板块】→【圈层热议板块】（无素材则省略对应板块）
- 板块间用"OK，XX聊完。换换口味，看XX这边"等自然口语过渡。
- 开场固定语："欢迎兄弟们收看游戏月报，X月游戏圈发生了这些事"
  → 1-2句整体印象（FPS/二游各一句）→ 快速罗列本月大事（一句一件）→ "一个一个来，先说XX"过渡。
- 结尾：一句话总结核心关键词 → 一句话预告下月趋势 → 互动引导"X月哪件最离谱？下月想看哪款？评论区说" → 固定署名"感谢兄弟们收看游戏月报，我们是TW社，我们X+1月底见。"

# 板块处理规则
- FPS：一句话快讯汇总 + 挑1-2个重磅深讲；重点讲赛事（冠军战队+决赛比分+MVP带ID绰号）；名场面引用弹幕/网友梗突出观赏性；非Major/非国际邀请赛/非顶级联赛决赛一句话带过。
- 二游：单游戏本月≥3条用详版、＜3条用简版。鸣潮讲联动角色+评价、前瞻新区域+新角色；原神按时间顺序，有PV则含发布内容+角色+反响，无PV则更新内容+玩家反馈，结尾转述社区调侃；异环/终末地讲版本+新角色+福利，强调更新频率。

# 可信度标注（每段讲解末尾必标）
1级=官方一手（官网/赛事官网/财报/发布会）；2级=权威媒体/数据站；3级=多方交叉验证社区信息（需注明"玩家热议/社区讨论"）；4级单一来源；5级存疑。4、5级原则上不采用。
标注格式示例：（信息来源：赛事官网，可信度：1级）

# 字数
信息饱满约3000字；素材不足则精简，不硬凑。

直接输出成稿，不要任何额外说明。"""

DATE_RANGE_CODE = '''import re as _re
m = nodes['n_month']['text'].strip()
# 解析 "2026-07" 或 "2026年7月" 或 "2026年07月"
mt = _re.search(r'(20\\d{2})\\D+(\\d{1,2})', m)
if not mt:
    result = "无法解析月份：" + m
else:
    y, mo = int(mt.group(1)), int(mt.group(2))
    from calendar import monthrange
    last = monthrange(y, mo)[1]
    label = f"{y}年{mo}月"
    d = {"label": label, "from": f"{y:04d}-{mo:02d}-01", "to": f"{y:04d}-{mo:02d}-{last:02d}"}
    result = d'''

MATERIAL_CODE = '''search = nodes.get('n_search', {}).get('results', [])
pages = nodes.get('n_fetch', {}).get('pages', [])
url2page = {p.get('url'): p for p in pages}
OFFICIAL = ['hoyoverse','mihoyo','bhvr','bilibili.com','weibo.com','tencent','yo-star','hypergryph','鹰角','kurogames','库洛','叠纸','papergames','leiting','雷霆','gameduchy','curve','终极','tencent.com']
MEDIA = ['36kr.com','sina.','163.com','ifanr','zhihu','gamersky','游民','17173','gcores','机核','baidu.com','sohu','ithome','游研','触乐']
def cred(u):
    u = (u or '').lower()
    if any(k in u for k in OFFICIAL): return 1
    if any(k in u for k in MEDIA): return 2
    return 3
out = ['（以下为已联网查证素材，每条含发布日期/是否在目标月份范围/可信度建议级/来源/正文节选）']
total_in = 0
for g in search:
    q = g.get('query',''); items = g.get('items', [])
    out.append('\\n### ' + q)
    shown = 0
    for it in items[:6]:
        p = url2page.get(it.get('url'))
        if not p: continue
        date = p.get('publish_date') or '日期未知'
        rng = '[在范围内]' if p.get('in_range') is True else ('[范围外,勿用]' if p.get('in_range') is False else '[日期未知]')
        lvl = cred(it.get('url'))
        if p.get('in_range') is True: total_in += 1
        out.append(f'- {date} {rng} 可信度{lvl}级 | {p.get("title") or it.get("title")}')
        out.append(f'  来源: {it.get("url")}')
        out.append(f'  正文: {(p.get("text") or "")[:380]}')
        shown += 1
    if shown == 0:
        out.append('  （本月未查到可信素材 → 本板块跳过，禁止编造）')
out.append(f'\\n[统计] 在目标月份范围内的素材条目数: {total_in}')
result = '\\n'.join(out)'''

USER_PROMPT = """【目标月份】{{n_daterange.value.label}}
【日期范围】{{n_daterange.value.from}} ~ {{n_daterange.value.to}}

【本月已联网查证的真实素材】
（★ 只能使用 [在范围内] 条目；[范围外,勿用] 与 [日期未知] 不得采用；某板块无在范围素材则跳过该板块，绝不编造）
{{n_material}}

请严格按系统提示标准，只用以上真实素材生成《游戏月报 · {{n_daterange.value.label}}》文案，直接输出成稿。"""

QUERIES = """CSGO {{n_daterange.value.label}} Major 赛事 冠军 MVP
无畏契约 VCT {{n_daterange.value.label}} 大师赛 冠军 比分
三角洲行动 {{n_daterange.value.label}} 赛事 冠军 新赛季
鸣潮 {{n_daterange.value.label}} 联动 前瞻 新角色
原神 {{n_daterange.value.label}} PV 前瞻 新角色
异环 {{n_daterange.value.label}} 版本 新角色 福利
明日方舟终末地 {{n_daterange.value.label}} 新版本 新地图 新角色
恋与深空 {{n_daterange.value.label}} 活动 官方公告 玩家"""

nodes = [
    {"id": "n_month", "type": "input",
     "label": "输入·目标月份", "position": {"x": 30, "y": 60},
     "config": {"key": "month", "default": "2026-07"}},
    {"id": "n_daterange", "type": "transform",
     "label": "解析月份范围", "position": {"x": 290, "y": 60},
     "config": {"template": "", "code": DATE_RANGE_CODE}},
    {"id": "n_search", "type": "search",
     "label": "8游戏联网搜索", "position": {"x": 560, "y": 60},
     "config": {"query": QUERIES, "engines": "bing,baidu", "max_per_query": 4}},
    {"id": "n_fetch", "type": "fetch",
     "label": "抓取正文+按月过滤", "position": {"x": 560, "y": 300},
     "config": {"urls": "{{n_search.urls}}",
                "date_from": "{{n_daterange.value.from}}",
                "date_to": "{{n_daterange.value.to}}",
                "max_total": 18, "max_chars_per": 4000}},
    {"id": "n_material", "type": "transform",
     "label": "结构化素材", "position": {"x": 560, "y": 540},
     "config": {"template": "", "code": MATERIAL_CODE}},
    {"id": "n_writer", "type": "llm",
     "label": "撰写月报", "position": {"x": 900, "y": 320},
     "config": {"provider": "", "model": "", "system": SYSTEM,
                "user": USER_PROMPT, "temperature": 0.6}},
    {"id": "n_report", "type": "output",
     "label": "月报成稿", "position": {"x": 1180, "y": 320},
     "config": {"value": "{{n_writer}}"}},
]
edges = [
    {"id": "e1", "source": "n_month", "target": "n_daterange"},
    {"id": "e2", "source": "n_daterange", "target": "n_search"},
    {"id": "e3", "source": "n_search", "target": "n_fetch"},
    {"id": "e4", "source": "n_fetch", "target": "n_material"},
    {"id": "e5", "source": "n_material", "target": "n_writer"},
    {"id": "e6", "source": "n_writer", "target": "n_report"},
]

doc = {
    "name": "游戏月报生成",
    "description": "依据模板对8个板块联网查证当月真实素材 → 按月份过滤 → 模型按风格红线写稿（带可信度标注）。运行前请在「设置」配好模型，并选中撰写节点的 provider/model。",
    "graph": {"nodes": nodes, "edges": edges},
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
print("written:", OUT)

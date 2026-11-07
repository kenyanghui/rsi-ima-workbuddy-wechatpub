# 九步流水线详细编排（rsi-wechat-publisher v1.2.0，主控必读）

> **闭环说明**：九步不是单向线——Step 6 成稿回存 IMA 之外，群发后的阅读/点赞数据经
> `fetch_stats.sh`（采集）+ `stats_to_ima.py`（回写 IMA「公众号运营数据」目录）流回知识库，
> 供下一轮 Step 0 预热加权、Step 0.5 热点选题、Step 3 QA 质量对账消费。
> 「发布 → 数据回流 → 影响下一轮选题与质量基线」——九步跑完，圈闭上。

> 主控（WorkBuddy 会话）的动作手册。所有个人参数从 `config.json` 读取，禁止硬编码。

## 核心纪律（先读）

1. **执行前先读 config.json**：作者名/知识库 ID/每日篇数/persona 全部从配置取，拼进子代理提示词。
2. **产物目录**：`<项目根>/pipeline/<YYYY-MM-DD>/p1|p2|p3/`（项目根 = 当前工作区）。
3. **磁盘为准**：子代理返回后必须 Read 验证产物文件存在；缺 → 携失败原因补 spawn 一次。
4. **断点续跑**：启动先看近 2 天 `_status.json`，`finished!=true` 则缺哪步补哪步，禁止覆盖已验证产物。
5. **Truth-first**：素材不足允许减产（3→2→1→0），台账留痕，绝不凑数。
6. **绝不群发**：post_draft.py 只进草稿箱；本地降级包也只是让人工手动发。
7. 凭证只在 `~/.config/`，绝不写进提示词、台账或 git 提交内容。

## 编排总览

```
主控
 ├── Step 0  预热：date 实测 → 断点盘点 → 建目录 → 读 config.json + _rsi_ledger.md 提炼硬约束
 ├── Step 0.5 热点采集：WebSearch（config.hotspot_queries）→ 热点候选池
 ├── Step 0.7 素材运营（可选，IMA 凭证在时）：搜库摸底 + 热点精品入库
 ├── Step 1  spawn topic ×N（并行）→ 各篇 01_topics.md
 ├── Step 2  spawn writer ×N（并行）→ 各篇 02_drafts.json
 ├── Step 3  spawn qa ×N → 03_qa_scores.md（<85 打回 writer，同篇 ≤2 次）
 ├── Step 4  spawn format ×N → 封面/插图 + article.html + CTA + post_draft.py 推草稿箱 → 04_publish_queue.md + format/manifest.json
 ├── Step 5  archive：bash scripts/archive_article.sh <日期> <产物目录>
 ├── Step 6  sync-ima：python3 scripts/sync_to_ima_wb.py <articles目录> <日期>
 └── Step 7  复盘：回写台账 + 质量对账（QA 分 × 运营数据）+ check_drift + _status.json finished:true + 日报简报
      ↻ 回流段：群发次日 bash scripts/fetch_stats.sh（采集阅读/点赞 → meta.json + 台账 + stats_to_ima.py 回写 IMA「公众号运营数据」）→ 下一轮 Step 0/0.5/3 消费 → 圈闭上
```

子代理提示词模板：`references/agent-prompts.md`（填充后 spawn，subagent_type=general-purpose）。

## Step 0 预热

1. `date '+%Y-%m-%d %H:%M %Z'` 实测日期。
2. 断点盘点近 2 天。
3. `mkdir -p pipeline/<日期>/p{1..N}`。
4. 读 config.json：拿到 kb_id、author、persona、articles_per_day。
5. 读 `_rsi_ledger.md` 提炼：素材避重（7 天内/累计≥2 次）、风格偏好结论、金句库、硬约束修正。
6. 读 IMA「公众号运营数据」目录最新周报（`stats_to_ima.py` 产物）：提炼强/弱标题模式——强模式（阅读 ≥2× 均值）优先同类角度，弱模式（<0.5× 均值）规避；作为本轮 topic/Step 0.5 的加权输入。无数据（<3 篇）跳过防过拟合。
7. IMA/公众号凭证探测：`python3 scripts/diagnose.py --check` 可选；缺 IMA → Step 0.7/6 跳过；缺公众号 → format 降级本地包（简报标注）。

## Step 0.5 热点采集（WebSearch）

跑 config.hotspot_queries 的 2-3 条查询 → 挑 5-10 条形成候选池（标题+一句摘要）。**候选池排序先过运营数据加权**：与 IMA「公众号运营数据」最新周报的强模式标题同类的热点排前，弱模式同类降权或剔除；无数据按原始序。热点仅作钩子，主体观点必须来自知识库。失败不阻断（纯库存选题）。

## Step 0.7 素材运营（IMA 凭证在时）

 ima-mcp 可用则用 MCP 工具（get_knowledge_list / import_urls）；否则跳过（不强求）。目的：摸清库内素材结构，供 topic 参考；可选把 1-3 条当日相关热点文章 import_urls 入库（folder_id 必填）。

## Step 1-3（子代理执行，提示词见 agent-prompts.md）

- qa 规则：`references/qa-rubric.json`（七维加权 + 四条一票否决：compliance / content_hollow / source_dup / unsourced_claim）。
- 质量对账（v1.2.0）：QA 分不是终点——Step 7 复盘时把本轮各篇 QA 分与 IMA「公众号运营数据」周报的篇均阅读/点赞率并排：QA 高分但阅读低 → 下轮 topic 降权该类选题；QA 低分但阅读高 → 提炼亮点回写风格偏好。质量基线随真实传播数据浮动，而非静态分数。
- 打回流程：qa REVISE → 携修改建议补 spawn writer（改 02_drafts.json 原地覆盖）→ qa 复检（追加到 03_qa_scores.md）；同篇 ≤2 次，仍不过换选题（回到 topic，单篇处理）。

## Step 4 format（子代理执行）

动作序列（提示词已内置，主控验收以下产物）：
1. `format/article.md`（微调后正文，[配图：…] 占位**必须全部替换为真实图片**——ImageGen 生成或删除占位段，禁止把占位框留在终稿）
2. `format/imgs/cover.png`（ImageGen 2.35:1；不可用 PIL 兜底）→ `bash scripts/compress_image.sh <cover> --max-kb 500`
3. `format/article.html`：`python3 scripts/md_to_html.py article.md article.html --title <标题> --theme <config.theme>`
4. CTA 注入（`templates/format/cta.md`）：有 `config/wecom-qr.png` 用图；没有用文字「微信搜索：`config.wechat_account_name`」
5. 推草稿箱：`python3 scripts/post_draft.py article.html --cover <cover绝对路径> --title <标题> --digest <摘要> --author <config.author_name>`
6. `04_publish_queue.md` + **标准结构** `format/manifest.json`：

```json
{"date": "<日期>", "articles": [{"title": "...", "article": "article.md", "html": "article.html", "cover": "imgs/cover.png", "media_id": "...", "qa_score": 88}]}
```

⚠️ manifest 的 article/html/cover 字段**相对 manifest 所在目录**（不要再带 `format/` 前缀）。

## Step 5 归档

`bash scripts/archive_article.sh <日期> <pipeline/日期目录>`——读 manifest → 写 `articles/<日期>[-n]/`（article.md + article.html + cover + meta.json）→ git commit（SKILL 目录内自动 init；配了 remote 自动 push，3 次重试）。

## Step 6 同步回 IMA

`python3 scripts/sync_to_ima_wb.py <技能目录>/articles <日期>`——读 config.json 的 kb_id/folder，create_media → COS（sha1 签名含 host，绕过代理）→ add_knowledge。失败不阻断。

## Step 7 复盘（不可跳过）

1. 回写 `_rsi_ledger.md`：素材避重 +1 行/源；风格偏好（标题模式+质检分）；金句候选；RSI 回路快照（本轮强在哪/下轮重点）。
2. **质量对账（v1.2.0）**：本轮 QA 分 × IMA「公众号运营数据」周报并排（见 Step 1-3 质量对账条），结论回写风格偏好；已群发文章跑 `bash scripts/fetch_stats.sh --all`（内部自动触发 `stats_to_ima.py` 回写 IMA）。
3. `bash scripts/check_drift.sh` FAIL 当场修。
4. 写 `_status.json`：`finished:true` + stages + media_id 列表。
5. 向用户发日报（固定字段）：

```
【RSI 流水线日报 <日期>】
1. 产出：计划 N / 实际 M（M<N 给减产原因）
2. 选题与质检：各篇标题、角度、QA 分、过审/打回
3. 待发布清单：media_id（或 local-only 包路径）
4. 归档状态：git commit；IMA 同步数
5. 素材动态：新增源 / 复用源 / 热点使用
6. 人工修正 diff：无（首轮）/ 摘要
7. 漂移自检：PASS/FAIL
8. 发布数据：暂无（群发后次日可跑 fetch_stats.sh）
```

## 加急文模式（活动纪实/复盘，v1.1.0）

当天活动当天发（工作坊复盘、活动纪实）**不走三翼流水线**，精简路径（2026-11-01 首期工作坊复盘实战验证）：

1. **素材三源**：活动页 WebFetch 课纲 → 用户的讨论纪要/口头要点（人数/反馈基调等事实以此为准）→ IMA 真实照片（folder 逐级下钻 + get_media_info 下载，坑见 ima-api-mechanics.md）
2. **写作**：spawn 单个 writer 子代理（提示词含全部素材要点+照片文件名清单+验收标准：字数/照片数/观点条数/归属脱敏/无真名），跳过 topic/qa
3. **配图**：真实照片走 `python3 scripts/wx_upload_img.py --map url_map.json <照片>` 换 URL；网络配图走 `python3 scripts/stock_image.py --suggest <主题>` → `--query-id` 下载 → 同样上传换 URL；封面用现场大图 `sips` 裁 2.35:1
4. **迭代修稿**（用户反馈后）：改 02_drafts.json → 重建 article.md（按 url_map.json 批量替换本地路径）→ md_to_html → 注入 CTA → **先删旧草稿**（draft/delete）→ 重跑 post_draft.py——草稿箱始终只有一份终版
5. **纪律**：事实全部来自用户输入（人数/引述/时间），学员观点归属明确无真名；台账照样回写（「加急」条目）

## 配图工具链（v1.1.0，网络图优先）

```
选图: python3 scripts/stock_image.py --suggest workflow|laptop|teamwork|growth|ai
下载: python3 scripts/stock_image.py --query-id 546819,373543 --out <目录>
上传: python3 scripts/wx_upload_img.py --map url_map.json <图片路径...>   # 图文内图必须换 wx URL
嵌入: article.md 用 ![](url_map 中的 wx URL)
⚠️ CTA 企微二维码同样必须上传换 URL（--map 一并入 url_map.json）——本地路径在公众号草稿中不显示（v1.1.0b 实战修复）
```

## manifest schema 容错（v1.1.0）

archive_article.sh 已内置归一化：标准 articles 数组 / dict 直平结构（title 在顶层、media_id 在 publish 嵌套、qa 分数在 qa.score）/ 双前缀路径（format/format/article.md）均可正确解析。format 子代理仍按标准结构输出，但归档不再因结构偏差丢稿。

## 定时任务

用户说「建定时」时用 automation_update：scheduleType=recurring，`FREQ=DAILY;BYHOUR=7;BYMINUTE=20`（用户可改点），prompt 复述：加载本技能 → 读 pipeline.md 执行当日九步 → 断点续跑 → 红线（绝不群发/truth-first/风险提示）→ 日报。prompt 必须自包含技能绝对路径。

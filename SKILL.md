---
name: rsi-wechat-publisher
aliases:
  - 公众号流水线
  - 微信公众号内容管线
  - rsi内容管线
  - 公众号AI写作
description: RSI 自进化微信公众号内容流水线（人人可用版）。九步全自动：热点采集(WebSearch) → 素材运营(IMA知识库) → topic 选题 → writer 写作 → qa 质检 → format 排版配图 → 推草稿箱 → 归档 → 同步回 IMA。从自己的 IMA 知识库挖素材，每天产出 3 篇角度互不重复的公众号长文，全部进草稿箱由人工选择群发（绝不自动群发）。每轮回写 RSI 进化台账（素材避重/风格偏好/金句库），越用越聪明。Use when user mentions "发公众号", "公众号文章", "内容流水线", "rsi-wechat", "每天三篇", "跑流水线", "文章归档", "采集入库", "整理知识库".
version: 1.2.0
platforms: [darwin, linux]
prerequisites:
  commands: [git, python3]
  optional_connectors: [ima-mcp]
---

# RSI 公众号内容流水线（rsi-wechat-publisher）

> **一句话**：把你自己的 IMA 知识库变成公众号内容工厂——每天自动产 3 篇原创长文进草稿箱，你只管审和发。
> 本技能由杨辉老师的 rsi-wechat（OpenClaw 版）移植为 WorkBuddy 通用版，开箱需 5 分钟配置。

## 语言

跟随用户语言（默认中文）。

## ⚡ 首次使用：5 分钟配置（必须完成，否则流水线降级）

**第一步：准备两个凭证**

| 凭证 | 哪里拿 | 放哪里 | 没配会怎样 |
|------|--------|--------|-----------|
| ① IMA 开放 API | ima.qq.com → 设置 → 开放 API（或 ima.qq.com/openapi 入口）创建，得 `Client ID` + `API Key` | `~/.config/ima/client_id` 和 `~/.config/ima/api_key`（每文件一行纯文本） | 素材采集/文章回存 IMA 跳过，只能靠热点写 |
| ② 微信公众号 API | mp.weixin.qq.com → 设置与开发 → 基本配置：拿 `AppID` + `AppSecret`；**并把本机出口 IP 加入「IP 白名单」**（跑 `python3 scripts/diagnose.py` 可查出本机 IP） | `~/.config/wechat/appid` 和 `~/.config/wechat/secret` | 文章打包成本地 HTML（手动粘贴发布） |

```bash
mkdir -p ~/.config/ima ~/.config/wechat
echo -n '你的IMA_ClientID' > ~/.config/ima/client_id
echo -n '你的IMA_APIKey'    > ~/.config/ima/api_key
echo -n '你的公众号AppID'   > ~/.config/wechat/appid
echo -n '你的公众号Secret'  > ~/.config/wechat/secret
chmod 600 ~/.config/ima/* ~/.config/wechat/*
```

**第二步：运行配置向导**

对 WorkBuddy 说「**配置公众号流水线**」，或手动跑：

```bash
python3 scripts/setup_wizard.py
```

向导会：探测两个凭证 → 用你的 IMA 凭证列出你的知识库让你选 → 把选择写进 `config.json` → 实测公众号 token（IP 白名单不通过会告诉你加哪个 IP）→ 生成专属 `_rsi_ledger.md` 台账。

**第三步（可选但推荐）**：
- 配 WorkBuddy 的 **ima-mcp 连接器**（设置→连接器里添加 ima）：topic 选题环节搜索素材更顺。
- 准备**企微获客二维码**放 `config/wecom-qr.png`（文末 CTA 用；没有就用文字兜底「微信搜索：你的号名」，同时改 `config.json` 的 `wechat_account_name`）。
- 建每日定时：对 WorkBuddy 说「**给公众号流水线建每天 07:20 的定时任务**」。

## 配置文件（config.json，向导生成，可手改）

```json
{
  "ima_kb_id": "",            // 你的 IMA 知识库 ID（向导填）
  "ima_kb_name": "",          // 知识库名（台账/简报显示用）
  "ima_folder_articles": "",  // 成稿回存的文件夹 ID（空=知识库根目录；可后续 create_folder 建了再填）
  "author_name": "杨教练",     // 改成你的笔名
  "wechat_account_name": "AI量化杨教练",  // 无二维码时的文字 CTA 兜底
  "articles_per_day": 3,      // 每天几篇（1-3）
  "theme": "default",         // default=深蓝 / blue=亮蓝
  "persona": {                // 你的内容定位——越具体选题越准
    "positioning": "AI量化投资教练，帮投资者用系统战胜情绪",
    "target_readers": "30-55岁投资者、高净值人群、二代传承场景",
    "tone": "专业但不说教，像资深教练做一对一复盘，第二人称"
  },
  "topic_domains": ["量化投资", "AI与投资", "财富认知", "投资者行为"],
  "hotspot_queries": ["今日AI人工智能财经热点", "36氪 AI 快讯"]
}
```

**换知识库/改人设/改定位：改 config.json 即可，不动技能其他文件。**

## Workflow Router（本文件是入口，只做路由）

| 任务意图 | 路由到 |
|---------|--------|
| 首次配置 / 换配置 | `scripts/setup_wizard.py`（说「配置公众号流水线」） |
| 跑完整流水线 / 每天三篇 | `references/pipeline.md`（九步编排手册，**执行前必读**） |
| topic/writer/qa/format 提示词模板 | `references/agent-prompts.md`（**所有 {{占位符}} 从 config.json 取**） |
| 只做素材采集 / 整理知识库 | pipeline.md § Step 0.7 |
| 找配图（网络图优先） | `python3 scripts/stock_image.py --suggest <主题>` 下载 → `python3 scripts/wx_upload_img.py --map url_map.json <图>` 换 URL |
| 修稿重发（草稿迭代） | 改 02_drafts.json/article.md → 重建 HTML+CTA → 删旧草稿(draft/delete) → 重跑 post_draft.py |
| 发活动纪实/加急文 | pipeline.md § 加急文模式（跳过三翼，writer 单发 + 手工编排） |
| 诊断（IP/凭证/连通性） | `python3 scripts/diagnose.py` |
| 换企微二维码 | 直接覆盖 `config/wecom-qr.png`（文末 CTA 自动用新图） |
| 版本/口径漂移排查 | `bash scripts/check_drift.sh` |

**路由纪律**：改流程改 references/scripts，不动本文件；个人配置只放 config.json。

## 九步流水线（概览）

```
Step0 预热(读台账+断点续跑) → Step0.5 热点采集(WebSearch) → Step0.7 素材运营(IMA)
  → topic(选题) → writer(写作2200-2600字) → qa(七维质检,≥85过) → format(封面配图+排版+CTA+推草稿箱)
  → archive(本地git归档) → sync-ima(成稿回存知识库) → Step7 复盘(回写台账+日报)
```

- topic/writer/qa/format 由主控用 **Agent 工具** spawn 子代理执行（提示词模板已备好）。
- 产物：`<项目根>/pipeline/<日期>/p1|p2|p3/`；归档：`articles/<日期>[-n]/`。

## 安全红线（不可违反）

1. **只进草稿箱，绝不自动群发**——post_draft.py 物理上无群发能力。
2. 投资/财经内容必含风险提示；无收益承诺、无绝对化用语、无无源数据（qa 一票否决）。
3. IMA 写操作必带 folder_id（防落根目录）；凭证只放 `~/.config/`，绝不进提示词/不提交 git。
4. Truth-first：素材不足允许减产留痕，绝不凑数发空心文。

## 配图偏好（用户定稿 2026-11-01，v1.1.0 工具化）

**网络免费图库（Pexels/Unsplash 高赞图）优先于 AI 生图**；活动/纪实类文章优先用真实照片。所有配图必须上传公众号素材库换 URL 后嵌入（本地路径在草稿中不显示）。

工具链：`stock_image.py`（--suggest 选主题 → --query-id 下载）→ `wx_upload_img.py --map url_map.json`（上传换 URL）→ article.md 重建时按 url_map 批量替换本地路径。

## 加急文模式（活动纪实/复盘，v1.1.0）

当天活动当天发的场景（工作坊复盘、活动纪实）**不走三翼流水线**，走精简路径：

1. **素材**：活动页 WebFetch 课纲 + 用户提供讨论纪要/口头要点 + IMA 真实照片（`get_knowledge_list` 按 folder_id 逐级下钻定位文件夹——注意：直调 API 的 folder 子列表可能空返回，用 ima-mcp 工具传 folder_id 才可靠）
2. **写作**：spawn 单个 writer（提示词给全素材要点+照片清单+验收标准），跳过 topic/qa 子代理
3. **配图**：真实照片 `wx_upload_img.py` 换 URL + 封面用现场大图 sips 裁 2.35:1
4. **迭代**：用户反馈修改 → 改 02_drafts.json → 重建 article.md（按 url_map 换图）→ md_to_html → 注入 CTA → **删旧草稿再推**（draft/delete + post_draft.py，避免草稿箱多版本并存）
5. **事实纪律不变**：人数/引述/数字以用户口头为准；学员观点归属明确（「一位做XX的学员」），无真名

## 故障速查

| 症状 | 原因 | 解法 |
|------|------|------|
| token 报 40164 | 本机 IP 不在公众号白名单 | 跑 `scripts/diagnose.py` 拿 IP → 公众号后台加白 |
| IMA API 403/无响应 | 代理干扰或域名变化 | 脚本已内置绕过代理；仍失败跑 diagnose.py |
| 文章进了 local-package | 公众号凭证缺失或 API 失败 | 按包内 README 手动发，或修好凭证重跑 |
| COS 上传 SignatureDoesNotMatch | 签名格式 | 已修复版本勿改 cos_put 函数 |

## 目录结构

```
rsi-wechat-publisher/
├── SKILL.md                 # 本文件
├── SETUP.md                 # 图文配置指南（给非技术用户）
├── config.json              # 你的个人配置（向导生成）
├── _rsi_ledger.md           # RSI 进化台账（向导生成空白版）
├── config/                  # wecom-qr.png（可选二维码）
├── references/
│   ├── pipeline.md          # 九步编排手册（主控必读）
│   ├── agent-prompts.md     # 四个子代理提示词模板
│   ├── ima-api-mechanics.md # IMA API 实测速查（踩坑记录）
│   └── qa-rubric.json       # 质检规则引擎（七维+四否决）
├── templates/               # 产物模板 + CTA 组件
└── scripts/                 # 全部脚本（详见各文件头注释）
    ├── setup_wizard.py      # 配置向导（首次必跑）
    ├── diagnose.py          # 一键诊断
    ├── stock_image.py       # Pexels 网络配图下载（v1.1.0）
    ├── wx_upload_img.py     # 图片上传公众号素材库换 URL（v1.1.0）
    ├── md_to_html.py        # 微信内联样式转换
    ├── post_draft.py        # 草稿箱推送（无群发能力）
    ├── sync_to_ima_wb.py    # 成稿回存 IMA（含COS签名）
    ├── archive_article.sh   # git 归档
    ├── compress_image.sh    # sips/cwebp 图片压缩
    ├── fetch_stats.sh       # 发布数据回流：采集阅读/点赞 → meta.json + 台账 + 触发 stats_to_ima
    ├── stats_to_ima.py      # 运营数据周报回写 IMA「公众号运营数据」（v1.2.0，强弱模式信号）
    └── check_drift.sh       # 防漂移自检
```

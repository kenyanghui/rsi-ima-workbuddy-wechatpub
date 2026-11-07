# wechat-pub-workbuddy

> **把自己的 IMA 知识库变成公众号内容工厂** —— WorkBuddy 技能，每天自动产 3 篇原创长文进草稿箱，你只管审和发。

[![WorkBuddy Skill](https://img.shields.io/badge/WorkBuddy-Skill-blue)](https://www.workbuddy.cn) [![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)]() [![Version](https://img.shields.io/badge/version-1.2.0-green)]()

## 这是什么

一个可分享的 **WorkBuddy 技能**（skill），把 [rsi-wechat](https://github.com/kenyanghui/rsi-wechat-pub) 流水线（RSI = Recursive Self-Improvement，递归自改进）移植到 WorkBuddy 上，人人可用：

```
你的 IMA 知识库 ──→ 热点采集 ──→ 选题 ──→ 写作(2200-2600字) ──→ 七维质检 ──→ 排版配图
                                                                              ↓
你的 IMA 知识库 ←── 成稿回存 ←── git 归档 ←── 公众号草稿箱（人工闸门，绝不自动群发）
        ↑                    RSI 进化台账（素材避重/风格偏好/金句库）—— 越用越聪明
```

**核心特性**

- 🔄 **九步全自动**：热点采集 → 素材运营 → topic 选题 → writer 写作 → qa 质检（≥85 分过审，四条一票否决）→ format 排版配图 → 推草稿箱 → git 归档 → 成稿回存 IMA
- 🧠 **RSI 自进化**：每轮回写进化台账（素材避重、风格偏好、金句库、人工修正分级），下一轮把上轮教训作为硬约束——越跑越懂你的账号
- 🛡️ **安全红线**：只进草稿箱**绝不自动群发**；投资内容必含风险提示；无收益承诺/绝对化用语/无源数据一票否决
- ⏱️ **5 分钟配置**：一个向导搞定你的知识库、公众号、人设定位
- 🎯 **truth-first**：素材不足自动减产并留痕，绝不凑数发空心文

## 安装（二选一）

### 方式一：git clone（推荐，可随时 `git pull` 升级）

```bash
git clone https://github.com/kenyanghui/wechat-pub-workbuddy.git ~/.workbuddy/skills/wechat-pub-workbuddy
```

### 方式二：下载 zip

1. 下载本仓库 zip 并解压
2. 把文件夹移到 `~/.workbuddy/skills/wechat-pub-workbuddy`

装好后**重启 WorkBuddy**（或新开对话）即可。

## 配置（5 分钟，只用一次）

对 WorkBuddy 说：**「配置公众号流水线」**

向导会引导你完成（详细图文见 [SETUP.md](SETUP.md)）：

| 步骤 | 做什么 | 哪里拿 |
|------|--------|--------|
| 1 | 放 IMA 开放 API 凭证（Client ID + API Key） | ima.qq.com → 设置 → 开放 API |
| 2 | 放公众号凭证（AppID + AppSecret）并把本机 IP 加白名单 | mp.weixin.qq.com → 设置与开发 → 基本配置 |
| 3 | 跑向导：选你的知识库、填笔名/定位/每天篇数 | 自动生成 `config.json` |

没配公众号 API 也能用——文章打包成本地 HTML，手动粘贴发布。

## 使用

| 你说 | 它做 |
|------|------|
| 「跑流水线」 | 立即产 3 篇进草稿箱（10-20 分钟） |
| 「配置公众号流水线」 | 重跑配置向导 |
| 「诊断公众号流水线」 | 一键体检（凭证/IP/连通性） |
| 「给公众号流水线建每天 07:20 定时任务」 | 建每日 automation |

跑完你会收到固定格式日报：各篇标题/质检分/media_id、归档状态、素材动态。去公众号后台草稿箱审核群发。

## 目录结构

```
wechat-pub-workbuddy/          # 本仓库 = 技能本体，clone 即安装
├── SKILL.md                   # 技能入口（WorkBuddy 自动识别）
├── SETUP.md                   # 5 分钟图文配置指南
├── config.json                # 你的个人配置（向导生成，勿提交个人值）
├── _rsi_ledger.md             # RSI 进化台账（向导生成）
├── references/                # 编排手册 + 子代理提示词 + QA 规则
├── templates/                 # 产物模板 + CTA 组件
├── config/                    # 企微二维码放这里（可选）
└── scripts/                   # 向导/诊断/排版/发文/归档/回存 全套脚本
```

## 常见问题

- **会自动群发吗？** 永远不会。发文脚本物理上无群发能力，只进草稿箱。
- **凭证安全吗？** 只存你电脑的 `~/.config/`，不进对话、不进 git（见 `.gitignore`）。
- **内容质量谁把关？** 七维质检 + 四条一票否决（合规/空心化/重复素材/无源数据），不过自动打回重写（同篇 ≤2 次）。
- **支持哪些系统？** macOS（sips 压缩）与 Linux（cwebp）。
- **出问题？** 说「诊断公众号流水线」或跑 `python3 scripts/diagnose.py`。

## 致谢与来源

由 [kenyanghui/rsi-wechat-pub](https://github.com/kenyanghui/rsi-wechat-pub)（OpenClaw 版 v1.5.2）移植为 WorkBuddy 通用技能。RSI 流水线方法论与 QA 规则引擎源自原项目。

## License

MIT

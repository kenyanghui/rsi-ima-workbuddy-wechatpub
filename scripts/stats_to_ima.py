#!/usr/bin/env python3
"""stats_to_ima.py — 发布数据回写 IMA（v1.2.0 新增，工作流质量闭环）.

把 fetch_stats.sh 采集的群发阅读/点赞数据，按周汇总成 Markdown 报告，
上传到 IMA 知识库「公众号运营数据」文件夹——与 sync_to_ima_wb.py（成稿回存）
构成一出一进两条 IMA 通路：
  出：素材 → 文章 → IMA「AI 生产文章」（sync_to_ima_wb.py）
  进：文章 → 群发数据 → IMA「公众号运营数据」（本脚本）
进的数据被 Step 0.5 热点采集加权、Step 5 QA 质量对账消费，形成
「发布 → 数据回流 → 影响下一轮选题与质量基线」的自进化圈。

用法:
    python3 scripts/stats_to_ima.py [articles根目录] [--weeks 4] [--dry-run]
读取:
    articles/<日期>[-n]/meta.json 的 stats 字段（read_num/like_num/fetched_at）
    + published_at 标记（哪些真的群发了）
凭据: ~/.config/ima/{client_id,api_key}；库与目录读 config.json
    （ima_kb_id / ima_folder_stats，目录不存在自动新建）
"""
import datetime
import json
import os
import statistics
import sys
import urllib.parse
import urllib.request

CRED = os.path.expanduser("~/.config/ima")
try:
    CLIENT_ID = open(os.path.join(CRED, "client_id")).read().strip()
    API_KEY = open(os.path.join(CRED, "api_key")).read().strip()
except Exception:
    CLIENT_ID = API_KEY = ""

_CFG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
try:
    _CFG = json.load(open(_CFG_PATH, encoding="utf-8"))
except Exception:
    _CFG = {}
KB_ID = os.environ.get("IMA_KB_ID") or _CFG.get("ima_kb_id") or ""
DIR_NAME = _CFG.get("ima_stats_dir") or "公众号运营数据"

BASE = "https://ima.qq.com/openapi/wiki/v1/"
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(path, body):
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=payload, method="POST", headers={
        "Content-Type": "application/json",
        "ima-openapi-clientid": CLIENT_ID,
        "ima-openapi-apikey": API_KEY,
    })
    with _OPENER.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_stats_folder():
    """找（或新建）「公众号运营数据」目录，返回 folder_id。"""
    folders = api("get_folder_list", {"knowledge_base_id": KB_ID})
    if folders.get("code") != 0:
        raise RuntimeError(f"get_folder_list: {folders.get('msg')}")
    for f in folders.get("data", []):
        if f.get("folder_name") == DIR_NAME:
            return f["folder_id"]
    created = api("create_folder", {"knowledge_base_id": KB_ID, "folder_name": DIR_NAME})
    if created.get("code") != 0:
        raise RuntimeError(f"create_folder: {created.get('msg')}")
    return created["data"]["folder_id"]


def collect(articles_root, weeks):
    """收近 N 周已群发文章的 stats，按周分桶。"""
    since = datetime.date.today() - datetime.timedelta(weeks=weeks)
    rows = []
    if not os.path.isdir(articles_root):
        return rows
    for d in sorted(os.listdir(articles_root)):
        mp = os.path.join(articles_root, d, "meta.json")
        if not os.path.isfile(mp):
            continue
        try:
            meta = json.load(open(mp, encoding="utf-8"))
        except Exception:
            continue
        pub = meta.get("published_at")
        stats = meta.get("stats")
        if not pub or not stats:
            continue
        try:
            pub_d = datetime.date.fromisoformat(pub)
        except ValueError:
            continue
        if pub_d < since:
            continue
        rows.append({
            "date": pub, "title": meta.get("title", d),
            "read": int(stats.get("read_num") or 0),
            "like": int(stats.get("like_num") or 0),
            "fetched_at": stats.get("fetched_at", ""),
        })
    rows.sort(key=lambda r: r["date"])
    return rows


def build_report(rows, weeks):
    """周粒度 Markdown：周表 + 标题模式洞察（Step 0.5/Step 5 消费）。"""
    today = datetime.date.today()
    lines = [f"# 公众号运营数据 · 近 {weeks} 周（{today.isoformat()} 自动生成）", ""]
    if not rows:
        lines += ["（该时段无已群发文章数据——群发后由 fetch_stats.sh 采集，隔天回流）", ""]
        return "\n".join(lines)
    total_r = sum(r["read"] for r in rows)
    total_l = sum(r["like"] for r in rows)
    lines += [f"**{len(rows)} 篇群发 · 总阅读 {total_r} · 总点赞 {total_l}**", ""]
    # 周分桶（ISO 周一为首日）
    weeks_map = {}
    for r in rows:
        d = datetime.date.fromisoformat(r["date"])
        monday = d - datetime.timedelta(days=d.weekday())
        weeks_map.setdefault(monday, []).append(r)
    lines += ["| 周起始 | 篇数 | 阅读 | 点赞 | 篇均阅读 |", "|---|---|---|---|---|"]
    for mon in sorted(weeks_map):
        wk = weeks_map[mon]
        r_sum = sum(x["read"] for x in wk)
        lines.append(f"| {mon.isoformat()} | {len(wk)} | {r_sum} | "
                     f"{sum(x['like'] for x in wk)} | {r_sum // max(len(wk), 1)} |")
    # 高低分界：阅读 ≥ 均值 2 倍 = 强模式；< 均值 1/2 = 弱模式
    mean_r = total_r / len(rows)
    strong = [r for r in rows if r["read"] >= 2 * mean_r]
    weak = [r for r in rows if r["read"] < mean_r / 2]
    lines += ["", "## 标题/选题模式信号（供下一轮 Step 0.5 热点加权与选题参考）", ""]
    if strong:
        lines += ["**强模式（阅读 ≥ 2× 均值，优先同类角度）**："]
        lines += [f"- 《{r['title']}》阅读 {r['read']}（{r['date']}）" for r in strong]
    if weak:
        lines += ["", "**弱模式（阅读 < 0.5× 均值，规避同类角度）**："]
        lines += [f"- 《{r['title']}》阅读 {r['read']}（{r['date']}）" for r in weak]
    if not strong and not weak:
        lines += [f"- 近 {weeks} 周阅读分布均匀（均值 {mean_r:.0f}），无明显强弱模式"]
    lines += ["", "## 质量对账基线（供 Step 5 QA 分数校准）", "",
              f"- 篇均阅读 {mean_r:.0f}；点赞率 {(total_l / total_r * 100 if total_r else 0):.2f}%",
              "- QA 高分但阅读低 → 检查选题与标题模式；QA 低分但阅读高 → 提炼可复用亮点回写风格偏好",
              "", "> 本报告由 stats_to_ima.py 自动生成，回流 IMA 后成为下一轮九步流水线的输入。"]
    return "\n".join(lines)


def upload(report, dry):
    fname = f"运营数据-{today_iso()}.md"
    if dry:
        print(f"[dry-run] 将上传 IMA「{DIR_NAME}」/{fname}（{len(report.encode())}B）")
        return None
    folder_id = ensure_stats_folder()
    # check_repeated_names 查重（同日重跑幂等：重名即视为已同步）
    dup = api("check_repeated_names", {"knowledge_base_id": KB_ID, "file_name": fname, "folder_id": folder_id})
    if dup.get("code") == 0 and dup.get("data", {}).get("is_repeated"):
        print(f"↩ IMA 已有 {fname}（同日幂等跳过）")
        return None
    import hashlib, hmac, base64
    tmp = "/tmp/.ima_stats_upload.md"
    open(tmp, "w", encoding="utf-8").write(report)
    content = report.encode("utf-8")
    size = len(content)
    cm = api("create_media", {"knowledge_base_id": KB_ID, "media_type": 7,
                              "file_name": fname, "file_size": size})
    if cm.get("code") != 0:
        raise RuntimeError(f"create_media: {cm.get('msg')}")
    cos = cm["data"]
    # COS 签名 PUT（与 sync_to_ima_wb.py 同协议：host+content-length 入签）
    sig = cos.get("authorization", "")
    url = cos["tmp_url"] if "tmp_url" in cos else cos.get("url", "")
    req = urllib.request.Request(url, data=content, method="PUT", headers={
        "Host": urllib.parse.urlparse(url).netloc,
        "Authorization": sig,
        "Content-Length": str(size),
        "Content-Type": "text/markdown",
    })
    _OPENER.open(req, timeout=60)
    ak = api("add_knowledge", {"knowledge_base_id": KB_ID, "folder_id": folder_id,
                               "file_info": {"cos_key": cos.get("cos_key", fname),
                                             "file_size": size, "file_name": fname}})
    if ak.get("code") != 0:
        raise RuntimeError(f"add_knowledge: {ak.get('msg')}")
    os.remove(tmp)
    return fname


def today_iso():
    return datetime.date.today().isoformat()


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    weeks = 4
    if "--weeks" in args:
        weeks = int(args[args.index("--weeks") + 1])
    rest = [a for a in args if not a.startswith("--")]
    root = rest[0] if rest else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "articles")
    if not CLIENT_ID or not API_KEY:
        print("⚠️  IMA 凭证缺失（~/.config/ima/{client_id,api_key}），跳过发布数据回写")
        sys.exit(0)  # 优雅降级，不阻断
    if not KB_ID:
        print("❌ 未配置 ima_kb_id（跑 scripts/setup_wizard.py）")
        sys.exit(2)
    rows = collect(root, weeks)
    print(f"近 {weeks} 周已群发带数据: {len(rows)} 篇")
    report = build_report(rows, weeks)
    name = upload(report, dry)
    if name:
        print(f"✅ 已回写 IMA「{DIR_NAME}」/{name}")
    print("→ 该报告供 Step 0.5 热点加权（强/弱模式）与 Step 5 QA 质量对账消费")


if __name__ == "__main__":
    main()

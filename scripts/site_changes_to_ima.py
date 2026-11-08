#!/usr/bin/env python3
"""site_changes_to_ima.py — 网站内容变更回流 IMA（v1.2.1 新增，内容进化信号闭环）.

网站（或任何 git 仓）每次内容修改都是重要的内容进化信号：改了什么、
为什么改、哪些页面被反复打磨——这些关注点应回流知识库，让下一轮
选题/CTA/热点与网站现状保持一致，而不是凭旧印象写作。

用法（可在任何 git 仓上跑，也可同时回流多个仓）:
    python3 scripts/site_changes_to_ima.py <git仓路径> [更多仓路径...] [--days 7] [--dry-run]
产物:
    「网站变更-<仓名>-<日期>.md」→ IMA「网站变更记录」目录
    （按日分桶的提交摘要：日期/提交主题/改动文件聚类 + 反复修改热点页信号）
消费方:
    九步流水线 Step 0 预热：读最新变更记录 → 选题与 CTA 对齐网站现状
凭据: IMA_CLIENT_ID/IMA_API_KEY 环境变量，或 ~/.config/ima/{client_id,api_key}；
      库读 config.json 的 ima_kb_id。缺失时优雅退出（exit 0，不阻断）。
幂等: 同日同仓重跑，IMA 已有同名文件即跳过（check_repeated_names）。
"""
import datetime
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

CLIENT_ID = os.environ.get("IMA_CLIENT_ID", "")
API_KEY = os.environ.get("IMA_API_KEY", "")
if not CLIENT_ID or not API_KEY:
    CRED = os.path.expanduser("~/.config/ima")
    try:
        CLIENT_ID = CLIENT_ID or open(os.path.join(CRED, "client_id")).read().strip()
        API_KEY = API_KEY or open(os.path.join(CRED, "api_key")).read().strip()
    except Exception:
        pass

_CFG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
try:
    _CFG = json.load(open(_CFG_PATH, encoding="utf-8"))
except Exception:
    _CFG = {}
KB_ID = os.environ.get("IMA_KB_ID") or _CFG.get("ima_kb_id") or ""
DIR_NAME = _CFG.get("ima_site_changes_dir") or "网站变更记录"

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


def ensure_folder():
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


def git(repo, *args):
    out = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()[:200]}")
    return out.stdout.strip()


def collect(repo, days):
    """近 N 天提交：[(date, subject, [files])]；越近权重越高（天然，log 倒序）。
    注：不用 git --since（部分环境过滤异常），全量 log 后 Python 侧按日期过滤。"""
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    log = git(repo, "log", "--no-merges", "-500",
              "--pretty=format:%ad%x00%s", "--date=short", "--name-only")
    commits, cur = [], None
    for line in log.splitlines():
        if not line.strip():
            continue
        if "\x00" in line:  # 提交头 date\0subject
            d, s = line.split("\x00", 1)
            cur = {"date": d, "subject": s, "files": []}
            if d >= since:  # 只留窗口内（date=short 可字符串比较）
                commits.append(cur)
        elif cur is not None:
            cur["files"].append(line.strip())
    return commits


def build_report(repo_name, commits, days):
    today = datetime.date.today().isoformat()
    lines = [f"# 网站变更 · {repo_name} · 近 {days} 天（{today} 自动生成）", ""]
    if not commits:
        lines += [f"（近 {days} 天无内容提交——网站稳定，无新进化信号）", ""]
        return "\n".join(lines)
    # 按日分桶
    by_day = {}
    for c in commits:
        by_day.setdefault(c["date"], []).append(c)
    lines += [f"**{len(commits)} 次内容修改 · {len(by_day)} 天有改动**", "",
              "## 修改关注点（按日倒序，选题/CTA 对齐这些变化）", ""]
    for d in sorted(by_day, reverse=True):
        lines.append(f"### {d}（{len(by_day[d])} 次）")
        for c in by_day[d]:
            lines.append(f"- {c['subject']}")
            # 文件聚类：目录级归并，避免逐文件刷屏
            dirs = {}
            for f in c["files"]:
                k = "/".join(f.split("/")[:-1]) or "(根)"
                dirs.setdefault(k, 0)
                dirs[k] += 1
            if dirs:
                top = "、".join(f"{k}×{v}" for k, v in sorted(dirs.items(), key=lambda x: -x[1])[:5])
                lines.append(f"  - 改动：{top}")
        lines.append("")
    # 反复修改热点页 = 被打磨最多的路径（内容进化信号最强）
    freq = {}
    for c in commits:
        for f in c["files"]:
            freq[f] = freq.get(f, 0) + 1
    hot = sorted(freq.items(), key=lambda x: -x[1])[:8]
    if hot:
        lines += ["## 反复打磨的热点页（修改频次 Top，最强内容进化信号）", ""]
        lines += [f"- {f}（{n} 次）" for f, n in hot if n >= 2]
        singles = [f for f, n in hot if n == 1]
        if singles and not any(n >= 2 for _, n in hot):
            lines += [f"- 各文件均只改 1 次（{len(freq)} 个文件），无反复打磨页"]
        lines.append("")
    lines += ["", "> 本报告由 site_changes_to_ima.py 自动生成；回流 IMA 后供九步流水线 Step 0 预热消费——"
              "网站在打磨什么，下一篇就写什么、CTA 就指向什么。"]
    return "\n".join(lines)


def upload(repo_name, report, dry, day=None):
    fname = f"网站变更-{repo_name}-{(day or datetime.date.today()).isoformat()}.md"
    if dry:
        print(f"[dry-run] {repo_name}: 将上传 IMA「{DIR_NAME}」/{fname}（{len(report.encode())}B）")
        return None
    folder_id = ensure_folder()
    dup = api("check_repeated_names", {"knowledge_base_id": KB_ID, "file_name": fname, "folder_id": folder_id})
    if dup.get("code") == 0 and dup.get("data", {}).get("is_repeated"):
        print(f"↩ {repo_name}: IMA 已有 {fname}（同日幂等跳过）")
        return None
    content = report.encode("utf-8")
    size = len(content)
    cm = api("create_media", {"knowledge_base_id": KB_ID, "media_type": 7,
                              "file_name": fname, "file_size": size})
    if cm.get("code") != 0:
        raise RuntimeError(f"create_media: {cm.get('msg')}")
    cos = cm["data"]
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
    return fname


STASH_DIR = os.path.join(os.path.expanduser("~"), ".config", "ima", "site-changes-stash")


def stash(repo_name, report, day=None):
    """本地留痕（ima 不可达时信号不丢）：~/.config/ima/site-changes-stash/"""
    os.makedirs(STASH_DIR, exist_ok=True)
    d = (day or datetime.date.today()).isoformat()
    open(os.path.join(STASH_DIR, f"网站变更-{repo_name}-{d}.md"), "w", encoding="utf-8").write(report)


def unstash(repo_name, day=None):
    """上传成功后清当日留痕。"""
    d = (day or datetime.date.today()).isoformat()
    p = os.path.join(STASH_DIR, f"网站变更-{repo_name}-{d}.md")
    if os.path.exists(p):
        os.remove(p)


def backfill(repo_name, dry):
    """补传积压：把留痕目录里非今日的旧报告按日上传（ima 恢复后自动消化）。"""
    if not os.path.isdir(STASH_DIR):
        return 0
    today = datetime.date.today().isoformat()
    n = 0
    for fn in sorted(os.listdir(STASH_DIR)):
        if not fn.startswith(f"网站变更-{repo_name}-") or not fn.endswith(".md"):
            continue
        d = fn[len(f"网站变更-{repo_name}-"):-3]
        if d >= today:
            continue  # 今日的由主流程处理
        try:
            report = open(os.path.join(STASH_DIR, fn), encoding="utf-8").read()
            if upload(repo_name, report, dry, day=datetime.date.fromisoformat(d)):
                os.remove(os.path.join(STASH_DIR, fn))
                n += 1
        except Exception:
            return n  # ima 仍不可达：停止补传，下次再试
    return n


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    days = 7
    repos = []
    skip_next = False
    for a in args:
        if skip_next:
            days = int(a)
            skip_next = False
            continue
        if a == "--days":
            skip_next = True  # 值在下个参数
        elif a.startswith("--days="):
            days = int(a.split("=", 1)[1])
        elif a.startswith("--"):
            continue
        else:
            repos.append(a)
    if not repos or skip_next:
        print("用法: site_changes_to_ima.py <git仓路径>... [--days 7] [--dry-run]")
        sys.exit(1)
    if not CLIENT_ID or not API_KEY or not KB_ID:
        print("⚠️  IMA 凭证缺失（IMA_CLIENT_ID/IMA_API_KEY 或 ~/.config/ima/），本地留痕后退出")
        for repo in repos:  # 凭据缺失也留痕：信号不许丢
            name = os.path.basename(os.path.abspath(repo))
            try:
                stash(name, build_report(name, collect(repo, days), days))
            except Exception as e:
                print(f"⚠️  {name}: 留痕失败 {e}")
        sys.exit(0)  # 优雅降级，不阻断
    ok = 0
    for repo in repos:
        name = os.path.basename(os.path.abspath(repo))
        try:
            # ① 先补传错过的日子（ima 故障期间留痕的积压）
            backfilled = backfill(name, dry)
            if backfilled:
                print(f"↩ {name}: 补传 {backfilled} 天积压")
            # ② 当日报告：留痕 → 上传 → 成功才清留痕（先写本地，防上传成功但进程被杀的重复）
            commits = collect(repo, days)
            report = build_report(name, commits, days)
            stash(name, report)
            fn = upload(name, report, dry)
            if fn:
                unstash(name)
                print(f"✅ {name}: {len(commits)} 次修改 → IMA「{DIR_NAME}」/{fn}")
            elif not dry:
                print(f"⏸ {name}: 当日报告已本地留痕（ima 不可达时次日补传）")
            ok += 1
        except Exception as e:
            print(f"⚠️  {name}: {e}（不阻断其他仓）")
    print(f"── 网站变更回流完成：{ok}/{len(repos)} 仓")


if __name__ == "__main__":
    main()

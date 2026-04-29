#!/usr/bin/env python3
"""
MisakaNet Feedback Reporter (节点侧)
=====================================
收集近期 skill 使用记录，通过 GitHub Issues 上报到 Hub。

运行方式:
  1. 手动: python3 scripts/feedback_report.py
  2. Cron: */30 * * * * cd /path/to/MisakaNet && python3 scripts/feedback_report.py

依赖: gh CLI (需已登录, 对 MisakaNet 仓库有 issues:write 权限)
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO = "Ikalus1988/MisakaNet"
NODE_ID = "hermes_wsl"

# 节点自身注册的偏好的 domain — 这些 domain 下的 skill 优先上报
PREFERRED_DOMAINS = [
    "rag-retrieval",
    "patent-writing",
    "software-development",
    "code-review",
    "devops",
]


def gh_run(*args):
    """运行 gh CLI 命令，返回 stdout"""
    result = subprocess.run(
        ["gh"] + list(args),
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"[warn] gh {' '.join(args)} failed: {result.stderr.strip()}", file=sys.stderr)
        return None
    return result.stdout.strip()


def create_feedback_issue(skill_name, result, scenario, tags=None, related_skills=None, session_ref=None):
    """上报一条 skill 使用反馈 (创建 GitHub Issue)"""

    title = f"feedback: {skill_name} {'✓' if result == 'success' else '⚠' if result == 'partial' else '✗'}"

    extra = {}
    if tags:
        extra["tags"] = tags
    if related_skills:
        extra["related_skills"] = related_skills
    if session_ref:
        extra["session_ref"] = session_ref

    body = json.dumps({
        "node_id": NODE_ID,
        "skill": skill_name,
        "result": result,
        "scenario": scenario,
        "extra": extra,
    }, ensure_ascii=False)

    labels = [
        "feedback",
        "unprocessed",
        f"node:{NODE_ID}",
        f"skill:{skill_name}",
    ]
    labels_str = ",".join(labels)

    print(f"[上报] {skill_name} → {result}")
    print(f"  scenario: {scenario}")

    out = gh_run(
        "issue", "create",
        "--repo", REPO,
        "--title", title,
        "--body", body,
        "--label", labels_str,
    )

    if out:
        print(f"  Issue: {out}")
        # 同时写本地缓存
        _write_local_cache(skill_name, result, scenario, extra, out)
    return out


def _write_local_cache(skill_name, result, scenario, extra, issue_url):
    """写入本地 .feedback/ 目录作为备份"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    feedback_dir = os.path.join(script_dir, "..", ".feedback", NODE_ID)
    os.makedirs(feedback_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(feedback_dir, f"{ts}_{skill_name}.json")

    record = {
        "node_id": NODE_ID,
        "skill": skill_name,
        "result": result,
        "scenario": scenario,
        "extra": extra,
        "issue_url": issue_url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    print(f"  cached: {path}")


def report_static_example():
    """
    示例：手工写入一条测试反馈。
    确认脚本能否正常工作后，后续可扩展自动从 session_search 读取。
    """
    create_feedback_issue(
        skill_name="rag-retrieval-quality",
        result="success",
        scenario="FANUC R-2000iC 系列机器人速度查询 — 文档在库但检索混淆（KUKA Series 2000混入），通过关键词强制召回修复",
        tags=["fanuc", "r-2000ic", "retrieval-fix"],
        related_skills=["systematic-debugging"],
        session_ref="20260429_111121",
    )


def main():
    print(f"=== MisakaNet Feedback Reporter (node: {NODE_ID}) ===")

    # 检查 gh CLI
    try:
        gh_run("--version")
    except FileNotFoundError:
        print("[error] gh CLI 未安装。请先安装 https://cli.github.com", file=sys.stderr)
        sys.exit(1)

    # 检查 gh auth
    whoami = gh_run("auth", "status")
    if whoami is None:
        print("[error] gh CLI 未登录。请先运行 gh auth login", file=sys.stderr)
        sys.exit(1)

    report_static_example()
    print("=== done ===")


if __name__ == "__main__":
    main()

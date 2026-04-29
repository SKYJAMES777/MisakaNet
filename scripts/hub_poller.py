#!/usr/bin/env python3
"""
MisakaNet Hub Poller (Hub 侧)
==============================
从 GitHub Issues 消费节点上报的反馈，更新 Knowledge Graph。

部署:
  放在 C:\Users\Eric Jia\hermes-hub\scripts\hub_poller.py
  定期运行: python scripts/hub_poller.py

依赖:
  pip install requests
  环境变量: MISAKANET_TOKEN (GitHub Personal Access Token with issues:read, issues:write)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

REPO = "Ikalus1988/MisakaNet"
TOKEN = os.environ.get("MISAKANET_TOKEN") or os.environ.get("GITHUB_TOKEN")

# Hub API 端点 - 如果 Hub 在本机运行
HUB_GRAPH_STATS_URL = "http://localhost:8080/graph/stats"  # 可选: 读取 Hub 状态

API_BASE = "https://api.github.com"


def gh_api(method, path, data=None):
    """调用 GitHub REST API"""
    import requests

    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MisakaNet-HubPoller",
    }

    url = f"{API_BASE}/{path.lstrip('/')}"

    if method == "GET":
        resp = requests.get(url, headers=headers, timeout=15)
    elif method == "POST":
        resp = requests.post(url, headers=headers, json=data, timeout=15)
    elif method == "PATCH":
        resp = requests.patch(url, headers=headers, json=data, timeout=15)
    else:
        raise ValueError(f"unsupported method: {method}")

    if resp.status_code >= 400:
        print(f"  [warn] API error {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return None

    if resp.status_code == 204:
        return {"status": "ok"}

    return resp.json()


def fetch_unprocessed_feedback():
    """获取所有未处理的反馈 Issues"""
    issues = gh_api("GET", f"/repos/{REPO}/issues?labels=feedback,unprocessed&state=open&sort=created&per_page=20")
    if issues is None:
        print("  [error] 无法获取 Issues。检查 TOKEN 和仓库权限。", file=sys.stderr)
        return []

    print(f"  未处理反馈: {len(issues)} 条")
    return issues


def parse_feedback(issue):
    """从 Issue body 解析反馈数据"""
    try:
        body = json.loads(issue["body"])
    except (json.JSONDecodeError, TypeError):
        print(f"  [warn] Issue #{issue['number']} body 解析失败，跳过", file=sys.stderr)
        return None

    required = ["node_id", "skill", "result", "scenario"]
    for field in required:
        if field not in body:
            print(f"  [warn] Issue #{issue['number']} 缺少字段 {field}，跳过", file=sys.stderr)
            return None

    return {
        "issue_number": issue["number"],
        "issue_url": issue["html_url"],
        "node_id": body["node_id"],
        "skill": body["skill"],
        "result": body["result"],
        "scenario": body["scenario"],
        "extra": body.get("extra", {}),
        "created_at": issue["created_at"],
    }


def update_knowledge_graph(feedback):
    """
    更新 Hub 的 Knowledge Graph。
    这里调用 Hub 内部的图更新逻辑。
    如果 Hub 图没有可用的 import 路径，则写一个 event 到本地日志。
    """
    skill = feedback["skill"]
    result = feedback["result"]
    node_id = feedback["node_id"]
    scenario = feedback["scenario"]

    # --- 尝试集成到 Hub 的 KnowledgeGraph ---
    try:
        # 如果 poller 在 Hub 进程内或同目录下运行
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from storage.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph()  # 假设已持久化
        
        # 更新 skill 节点权重
        weight_map = {"success": 1.0, "partial": 0.5, "failure": -0.2}
        delta = weight_map.get(result, 0)
        
        # 更新 skill 节点的 usage_count 和 avg_weight
        if kg.graph.has_node(skill):
            old = kg.graph.nodes[skill].get("weight", 0)
            count = kg.graph.nodes[skill].get("usage_count", 0) + 1
            new_weight = (old * (count - 1) + delta) / count  # 移动平均
            kg.graph.nodes[skill]["weight"] = round(new_weight, 4)
            kg.graph.nodes[skill]["usage_count"] = count
            kg.graph.nodes[skill]["last_used"] = datetime.now(timezone.utc).isoformat()
        else:
            kg.graph.add_node(skill, weight=delta, usage_count=1, last_used=datetime.now(timezone.utc).isoformat())

        # 更新 node → skill 边的权重
        if kg.graph.has_edge(node_id, skill):
            old_edge = kg.graph.edges[node_id, skill].get("weight", 0)
            edge_count = kg.graph.edges[node_id, skill].get("count", 0) + 1
            kg.graph.edges[node_id, skill]["weight"] = (old_edge * (edge_count - 1) + delta) / edge_count
            kg.graph.edges[node_id, skill]["count"] = edge_count
            kg.graph.edges[node_id, skill]["last_result"] = result
        else:
            kg.graph.add_edge(node_id, skill, weight=delta, count=1, last_result=result)

        kg.save()
        print(f"  [graph] {skill}: weight={kg.graph.nodes[skill]['weight']}, count={kg.graph.nodes[skill]['usage_count']}")
        return True

    except ImportError:
        print("  [graph] 未找到 storage.knowledge_graph，跳过图更新", file=sys.stderr)
        print(f"  → 模拟更新: skill={skill}, node={node_id}, result={result}, weight_delta={delta}")
        return False

    except Exception as e:
        print(f"  [error] 图更新失败: {e}", file=sys.stderr)
        return False


def mark_processed(issue_number, feedback, graph_ok):
    """回复 Issue 并标记为已处理"""
    summary = f"✅ **Processed** by Hub (`{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}`)\n\n"
    summary += f"- Skill: `{feedback['skill']}`\n"
    summary += f"- Result: {feedback['result']}\n"
    summary += f"- Node: `{feedback['node_id']}`\n"
    summary += f"- Scenario: {feedback['scenario']}\n\n"

    if graph_ok:
        summary += "Knowledge Graph updated accordingly."
    else:
        summary += "Graph update simulated (Hub Graph not integrated yet)."

    # 回复 comment
    gh_api("POST", f"/repos/{REPO}/issues/{issue_number}/comments", {"body": summary})

    # 去掉 unprocessed 标签，加上 processed
    gh_api("PATCH", f"/repos/{REPO}/issues/{issue_number}", {
        "labels": ["feedback", "processed", f"node:{feedback['node_id']}", f"skill:{feedback['skill']}"],
        "state": "closed",
    })

    print(f"  [issue #{issue_number}] 已回复并关闭")


def main():
    print("=" * 55)
    print(f"  MisakaNet Hub Poller v0.2")
    print(f"  repo: {REPO}")
    print(f"  time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 55)

    if not TOKEN:
        print("[error] 请设置 MISAKANET_TOKEN 或 GITHUB_TOKEN 环境变量", file=sys.stderr)
        sys.exit(1)

    issues = fetch_unprocessed_feedback()
    if not issues:
        print("  没有未处理的反馈")
        return

    for issue in issues:
        print(f"\n─ Issue #{issue['number']}: {issue['title']}")
        feedback = parse_feedback(issue)
        if not feedback:
            continue

        print(f"  node: {feedback['node_id']}, skill: {feedback['skill']}, result: {feedback['result']}")
        print(f"  scenario: {feedback['scenario'][:60]}...")

        graph_ok = update_knowledge_graph(feedback)
        mark_processed(issue["number"], feedback, graph_ok)

    print(f"\n=== 完成: 处理 {len(issues)} 条反馈 ===")


if __name__ == "__main__":
    main()

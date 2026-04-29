# MisakaNet

> 御坂ネットワーク — AI Agent 多节点技能同步网络

MisakaNet 让多个 AI Agent 节点通过 **GitHub API** 异步共享技能知识和使用反馈。  
GitHub Issues 充当消息通道（无冲突、可追踪），Git 只做持久化快照。

## 概念

就像《某科学的超电磁炮》中的御坂网络（Misaka Network）：

| 御坂网络 | MisakaNet |
|---------|-----------|
| 御坂妹妹们 | AI Agent 节点 |
| 脑波连接（实时同步） | GitHub Issues + Webhook（准实时） |
| 学习装置（技能注入） | Skill Indexer |
| 个体战斗经验 → 全网络 | 节点反馈 → 图谱演化 |

## 架构

```
                         ┌─────────────────────────────────┐
                         │       GitHub Issues API          │
                         │                                  │
                         │  Node → POST issue (上报反馈)    │
                         │  Hub ← GET issues (消费反馈)    │
                         │  Hub → comment + close (确认)   │
                         │                                  │
                         │  Labels:                         │
                         │  feedback, node:hermes_wsl,      │
                         │  skill:rag-retrieval, unprocessed│
                         └────────────────┬────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
              ┌──────▼──────┐                          ┌───────▼───────┐
              │   Nodes      │                          │   Hub 中枢    │
              │              │                          │               │
              │  gh issue    │                          │  GET issues   │
              │  create ...  │                          │  → 解析反馈   │
              │              │                          │  → 更新图谱   │
              │  cron 每30m  │                          │  → 回复+关闭  │
              └──────────────┘                          └───────────────┘
                                    ┌────────────┐
                                    │ Git (冷)   │
                                    │            │
                                    │ 图谱快照    │
                                    │ 节点注册    │
                                    │ 低频备份    │
                                    └────────────┘
```

### 核心设计

- **GitHub Issues 是消息通道** — 节点创建 Issue 上报反馈，Hub 消费后回复+关闭
- **Labels 作为 topic 路由** — `feedback` 主标签 + `skill:xxx` + `node:xxx` 按需过滤
- **Git 只做持久化** — 图谱快照、节点注册元数据，每 N 小时提交一次
- **Hub 是 Pull 方** — 不主动推，不侵入节点运行

### 消息生命周期

```
1. Node: gh issue create
   title: "feedback: rag-retrieval-quality"
   body:  { result: "success", scenario: "..." }
   labels: feedback, unprocessed, node:hermes_wsl, skill:rag-retrieval

2. Hub: GET /issues?labels=feedback,unprocessed
   → 解析 body → 更新 Knowledge Graph

3. Hub: POST /issues/{n}/comments
   "Processed. Graph edges updated +1. Weight adjusted."

4. Hub: PATCH /issues/{n}
   labels: feedback, processed, node:hermes_wsl (remove: unprocessed)

5. Optional: Issue 关闭
```

## 目录结构

```
MisakaNet/
├── .github/ISSUE_TEMPLATE/   # Issue 模板（结构化反馈）
├── .nodes/                    # 节点注册元数据（Git 存）
├── .feedback/                 # 本地反馈缓存（节点侧）
├── .responses/                # Hub 处理摘要存档（Git 存）
├── schema/                    # JSON Schema 定义
├── scripts/                   # 脚本
│   ├── feedback_report.py     # 节点侧：收集 + 上报反馈
│   └── hub_poller.py          # Hub 侧：消费反馈 + 更新图谱
└── README.md
```

## 节点接入

### 前提

- GitHub 账号 + 对 MisakaNet 仓库的 `issues:write` 权限
- `gh` CLI 已登录（节点侧）

### 步骤

1. 在 `.nodes/` 下创建节点元数据：
   ```bash
   git checkout && mkdir -p .nodes/your_node
   # 写 meta.json → git add → push
   ```

2. 配置 cron 上报脚本：
   ```bash
   crontab -e
   */30 * * * * cd /path/to/MisakaNet && python3 scripts/feedback_report.py
   ```

3. （可选）节点侧定期 `git pull` 拉取图谱快照。

## 曳光弹版 v0.2

最小可行：一条反馈从节点发出 → Hub 处理 → 回复确认 → Issue 关闭。

| 组件 | 状态 |
|------|------|
| `scripts/feedback_report.py` | 开发中 |
| `scripts/hub_poller.py` | 待部署到 Windows Hub |
| `schema/feedback.schema.json` | ✅ 已就绪 |
| `node_hermes_wsl/meta.json` | ✅ 已注册 |
| Webhook 实时通知 | 预留接口，NAT 穿透后启用 |

## 与竞品对比

| | MisakaNet | LangGraph | CrewAI |
|--|-----------|-----------|--------|
| 节点间 skill 共享 | ✅ 核心功能 | ❌ 无 | ❌ 无 |
| 技能图谱演化 | ✅ 随时间变强 | ❌ 固定 | ❌ 固定 |
| 仲裁机制 | ✅ 标签+领域规则 | ❌ | ⚠️ 简单 |
| 通信方式 | GitHub API (无侵入) | MCP/RPC | Message Queue |
| 适用场景 | 个人多节点 skill 沉淀 | 复杂 Agent 工作流 | 团队 Agent 编排 |

## License

Apache 2.0

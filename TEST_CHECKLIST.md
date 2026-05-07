# 御坂网络 MisakaNet — Agent 测试交付表

> 新 Agent 请逐条测试，通过后在 [ ] 打 ✅，不通过的记录具体报错信息。

---

## P0：核心功能验证

### 1. 仓库完整性

- [ ] **仓库可访问**
  ```bash
  curl -s https://github.com/Ikalus1988/MisakaNet | grep -q "MisakaNet" && echo "✅"
  ```
- [ ] **Gitee 镜像可访问**
  ```bash
  curl -s https://gitee.com/ikalus1988/MisakaNet | grep -q "MisakaNet" && echo "✅"
  ```

### 2. JOIN.md — 新节点接入

- [ ] **JOIN.md 可被 Agent 读取**
  ```bash
  curl -s https://raw.githubusercontent.com/Ikalus1988/MisakaNet/main/JOIN.md | head -5
  ```
- [ ] **JOIN.md 包含双通道 JSON 索引 URL**
  ```bash
  curl -s https://raw.githubusercontent.com/Ikalus1988/MisakaNet/main/JOIN.md | grep -q "lessons.json" && echo "✅"
  ```
- [ ] **JOIN.md 包含检索规则和 Output Gate**
- [ ] **JOIN.md 包含接入反馈格式**
- [ ] **JOIN.md 包含知识使用报告模板**

### 3. Lessons 通用知识

- [ ] **lessons/ 目录存在 22 条知识**
  ```bash
  ls lessons/*.md | wc -l
  ```
- [ ] **每条 lesson 有有效 frontmatter**
  ```bash
  python3 -c "
  import json, re, os
  for f in sorted(os.listdir('lessons')):
      if not f.endswith('.md'): continue
      c = open(f'lessons/{f}').read()
      m = re.match(r'^---\s*\n(\{.*?\})\s*\n---', c, re.DOTALL)
      fm = json.loads(m.group(1))
      assert 'title' in fm and 'domain' in fm, f'{f} missing title/domain'
      print(f'  ✅ {f} — {fm[\"title\"]}')
  "
  ```
- [ ] **无领域私有知识**（FANUC / RAG / WeChat / patent 等关键词不应出现）
  ```bash
  grep -rl "FANUC\|RAG\|WeChat\|patent\|Agent-Medici" lessons/ 2>/dev/null && echo "❌ 有私有内容" || echo "✅ 无私有内容"
  ```

### 4. misakanet-index.py — 知识索引生成

- [ ] **脚本可运行**
  ```bash
  python3 misakanet-index.py -o /tmp/test-index.json
  ```
- [ ] **输出格式正确**
  ```bash
  python3 -c "import json; d=json.load(open('/tmp/test-index.json')); [print(f'  [{x[\"id\"]}] {x[\"title\"]}') for x in d[:3]]"
  ```
- [ ] **索引条目数与 lessons 一致**
  ```bash
  python3 -c "import json; d=json.load(open('/tmp/test-index.json')); print(f'{len(d)} 条索引')"
  ```
- [ ] **lessons.json 可通过双通道分发**（验证 raw.githubusercontent 和 Gitee raw）

### 5. AGENTS.md & CLAUDE.md

- [ ] **AGENTS.md 无私有节点名**（hermes_wsl / magician / Eric Jia 不应出现）
  ```bash
  grep -q "hermes_wsl\|Eric Jia\|magician\|倒吊人" AGENTS.md && echo "❌" || echo "✅"
  ```
- [ ] **AGENTS.md 包含通用节点接入规则**
- [ ] **CLAUDE.md 已清空私有 lessons 摘要**
  ```bash
  grep -q "FANUC\|R-2000iC\|mioffice" CLAUDE.md && echo "❌" || echo "✅"
  ```
- [ ] **CLAUDE.md 包含 MISAKANET_LESSONS 区块模板**

### 6. README.md

- [ ] **README 包含 4 种场景引导**
  ```bash
  grep -q "无GitHub.*单Agent\|有GitHub.*多Agent" README.md && echo "✅"
  ```
- [ ] **README 包含双通道分发链接**（GitHub + Gitee）
- [ ] **README 包含「一句话加入」入口**
- [ ] **README 末尾标注 Apache 2.0**

### 7. 注册系统

- [ ] **Issue 模板存在**
  ```bash
  ls .github/ISSUE_TEMPLATE/register.yml 2>/dev/null && echo "✅"
  ```
- [ ] **GitHub Actions workflow 存在**
  ```bash
  ls .github/workflows/register.yml 2>/dev/null && echo "✅"
  ```
- [ ] **counter.json 起始值为 10000**
  ```bash
  python3 -c "import json; print(json.load(open('counter.json'))['current'])"
  ```

### 8. 头像生成器

- [ ] **misakanet-avatar.py 可运行**
  ```bash
  python3 misakanet-avatar.py 10001 --output /tmp/test-avatar
  ```
- [ ] **生成 128x128 PNG**
  ```bash
  python3 -c "from PIL import Image; img=Image.open('/tmp/test-avatar/Misaka10001.png'); print(f'{img.size[0]}x{img.size[1]}')"
  ```
- [ ] **不同序号生成不同领巾色**
  ```bash
  python3 misakanet-avatar.py 10001 10002 10003 --output /tmp/test-avatar && ls -la /tmp/test-avatar/
  ```
- [ ] **头像包含底部号码牌**

---

## P1：架构完整性

### 9. 隐私安全

- [ ] **无个人姓名**（Eric Jia / hp / gem）
  ```bash
  grep -rl "Eric Jia\|eric_jia\|/home/hp\|/home/gem" --include="*.py" --include="*.md" --include="*.sh" --include="*.yml" --include="*.json" . 2>/dev/null | grep -v ".git/" && echo "❌" || echo "✅"
  ```
- [ ] **无个人 GitHub 账号替代**（Ikalus1988 是公开账号，例外）
- [ ] **无 Windows 个人路径**
  ```bash
  grep -rl "C:\\\\Users" --include="*" . 2>/dev/null | grep -v ".git/" && echo "❌" || echo "✅"
  ```

### 10. 代码可读性

- [ ] **所有 REPO 硬编码已改为 env var 可配置**
  ```bash
  grep -l "REPO =" misakanet/scripts/*.py | xargs grep -l "os.environ"
  ```
- [ ] **所有 NODE_ID 默认值已改为 node1**
  ```bash
  grep -rn "hermes_wsl" --include="*.py" --include="*.yml" --include="*.json" . 2>/dev/null | grep -v ".git/" && echo "❌" || echo "✅"
  ```
- [ ] **search_knowledge.py 零依赖**
  ```bash
  head -5 search_knowledge.py | grep -q "#!/usr/bin/env python3" && echo "✅"
  ```

---

## P2：用户体验

### 11. 新人体验（模拟）

- [ ] **新用户打开 GitHub 后能看到清晰的 README**
- [ ] **README 能在 5 秒内说明「这东西能帮我什么」**
- [ ] **从 README 到「让 Agent 加入」的路径不超过 2 步**
- [ ] **单 Agent 用户不需要 GitHub 也能消费知识**（通过 JOIN.md 订阅 JSON 索引）

### 12. 头像美学

- [ ] **像素头像可识别为御坂美琴/御坂妹**
- [ ] **不同序号间领巾色差异明显**
- [ ] **号码牌可读**
- [ ] **头像在 64x64 显示时仍清晰**

---

## 测试环境准备

```bash
# Python 依赖
pip install pillow

# 克隆仓库
git clone https://github.com/Ikalus1988/MisakaNet.git
cd MisakaNet

# 运行所有测试（逐个执行上述命令）
```

---

## 销项签字

```
测试 Agent: _______________
测试日期: _________________
通过: P0 ___/8   P1 ___/3   P2 ___/2
未通过: [列出具体项及错误信息]
```

# Skills Orchestrator

**编译时 Skill 治理工具** — 管理 AI 编码助手的行为规范，强制执行，防止冲突。

把分散在各处的 `.md` Skill 文件，编译成 Claude / Cursor / Copilot 能直接读取的 `AGENTS.md`。配合 MCP Server，让 AI 按需动态加载 Skill，上下文零浪费。

---

## 为什么需要它？

| 问题 | 没有 Skills Orchestrator | 有了之后 |
|------|--------------------------|---------|
| Skill 越来越多 | 手动维护 AGENTS.md，容易遗漏或冲突 | `build` 一条命令自动生成 |
| 不同项目用不同规范 | 到处复制粘贴，版本不同步 | Zone 机制，目录自动对应规范 |
| 上下文窗口有限 | 所有 Skill 全量注入，浪费 token | MCP Server 按需加载，500 个 Skill 和 5 个消耗相同 |
| 两个 Skill 互相冲突 | 运行时才发现，模型行为不确定 | 编译时 `conflict_with` 强制报错 |

---

## 快速开始（5 分钟）

### 安装

```bash
pip install skills-orchestrator
```

### 初始化项目

```bash
# 在你的项目目录里
cd my-project

# 扫描本地 skills 目录，生成 skills.yaml
skills-orchestrator init
```

`init` 会引导你选择 Skill 目录，生成配置文件。

### 编译生成 AGENTS.md

```bash
skills-orchestrator build --config config/skills.yaml
# ✓ 解析完成: 20 skills, 3 zones
# ✓ 使用 Zone: 默认区 (default)
# ✓ 输出: AGENTS.md
```

把生成的 `AGENTS.md` 放到项目根目录，Claude / Cursor 会自动读取。

### 验证配置

```bash
skills-orchestrator validate --config config/skills.yaml
# ✓ 配置合法：20 skills，无冲突
```

---

## MCP Server 集成（Claude Code）

Phase 2 功能：让 Claude 在对话中**按需动态加载** Skill，无需全量注入。

### 启动 MCP Server

```bash
skills-orchestrator serve --config config/skills.yaml
```

### 配置 Claude Code

在项目的 `.claude/settings.json` 中添加：

```json
{
  "mcpServers": {
    "skills-orchestrator": {
      "command": "skills-orchestrator",
      "args": ["serve", "--config", "/absolute/path/to/config/skills.yaml"]
    }
  }
}
```

重启 Claude Code，即可使用以下 4 个工具：

| 工具 | 用途 |
|------|------|
| `list_skills` | 查看所有可用 Skill（含 tag 过滤） |
| `search_skills` | 按需求搜索相关 Skill |
| `get_skill` | 加载完整 Skill 内容到上下文 |
| `suggest_combo` | 根据任务描述推荐 Skill 组合 |

### 测试工具调用

```bash
# 不启动 Server，直接在命令行测试
skills-orchestrator mcp-test search_skills "git branch parallel work"
skills-orchestrator mcp-test get_skill karpathy-guidelines
skills-orchestrator mcp-test suggest_combo "部署微服务，需要代码审查和 git 工作流"
```

---

## Skill 文件格式

每个 `.md` 文件开头加 YAML frontmatter，Skills Orchestrator 自动发现，无需手动注册：

```markdown
---
id: my-skill
name: 我的技能
summary: "一句话描述，用于 search 和摘要展示"
tags: [coding, quality]
load_policy: free      # free / require（强制注入）
priority: 80           # 数值越大优先级越高
zones: [default]       # 适用的 Zone
conflict_with: []      # 互斥的 Skill ID 列表
---

# 正文内容（Markdown）
...
```

### 目录结构（推荐）

```
skills/
├── coding/        tdd.md, error-handling.md, api-design.md
├── git/           git-operations.md, git-worktrees.md
├── ops/           deployment-checklist.md, environment-setup.md
├── planning/      brainstorming.md, writing-plans.md
├── quality/       refactoring.md, systematic-debugging.md
└── review/        chinese-code-review.md, security-review.md
```

---

## 配置文件（skills.yaml）

```yaml
version: "2.0"

# 自动扫描目录，无需手动列出每个 Skill
skill_dirs:
  - ../skills

# Zone：不同目录使用不同规范
zones:
  - id: enterprise
    name: 企业强制区
    load_policy: require       # 该 Zone 内所有 Skill 强制注入
    rules:
      - pattern: "*/internal/*"
      - git_contains: "company.com"

  - id: default
    name: 默认区
    load_policy: free
    rules: []

# 覆盖个别 Skill 的 frontmatter 默认值
overrides: []

# Combo：预定义的 Skill 组合
combos:
  - id: full-dev-workflow
    name: 完整开发工作流
    skills: [brainstorming, writing-plans, git-worktrees, finish-branch]
```

---

## 所有命令

```bash
skills-orchestrator build     --config <path>            # 生成 AGENTS.md
skills-orchestrator validate  --config <path>            # 验证，不生成文件
skills-orchestrator status    --config <path>            # 查看 forced/passive/blocked
skills-orchestrator inspect   --workdir <path>           # 检查目录命中哪个 Zone
skills-orchestrator init                                  # 交互式初始化
skills-orchestrator import    <github-url>               # 从 GitHub 导入 Skill
skills-orchestrator serve     --config <path>            # 启动 MCP Server
skills-orchestrator mcp-test  <tool> <args>              # 测试 MCP 工具
```

---

## 从 GitHub 导入 Skill

```bash
# 导入单个仓库里的所有 Skill
skills-orchestrator import https://github.com/forrestchang/andrej-karpathy-skills

# 导入后自动放入 skills/external/ 目录
```

---

## 开发

```bash
git clone https://github.com/yourname/skills-orchestrator
cd skills-orchestrator
pip install -e ".[dev]"
pytest tests/ -v
```

---

## 路线图

- [x] 编译时治理（build / validate / zone / conflict）
- [x] Auto-Discovery from frontmatter
- [x] MCP Server（list / search / get / suggest_combo）
- [x] 20 个生产级 Skill 内容库
- [ ] PyPI 正式发布
- [ ] pgvector 语义检索（skill > 50 个时启用）
- [ ] `sync --target openclaw` 多工具同步

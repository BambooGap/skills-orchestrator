# Skills Orchestrator

**编译时 Skill 治理工具** — 管理 AI 编码助手的行为规范，强制执行冲突检测，按需加载，流程编排。

把分散在各处的 `.md` Skill 文件，编译成 Claude / Cursor / Copilot 能直接读取的 `AGENTS.md`。配合 MCP Server，让 AI 按需动态加载 Skill。通过 Pipeline 编排多个 Skill 成有序工作流，质量门禁保证每步产出。

```
pip install skills-orchestrator
```

---

## 为什么需要它？

| 问题 | 没有 Skills Orchestrator | 有了之后 |
|------|--------------------------|----------|
| Skill 越来越多 | 手动维护 AGENTS.md，容易遗漏或冲突 | `build` 一条命令自动生成 |
| 不同项目用不同规范 | 到处复制粘贴，版本不同步 | Zone 机制，目录自动对应规范 |
| 上下文窗口有限 | 所有 Skill 全量注入，浪费 token | MCP Server 按需加载，500 个 Skill 和 5 个消耗相同 |
| 两个 Skill 互相冲突 | 运行时才发现，模型行为不确定 | 编译时 `conflict_with` 强制报错 |
| 多步骤工作流无保证 | AI 靠自觉推进，容易跳步或遗漏 | Pipeline 编排 + 质量门禁，每步必须产出 |
| Skill 内容重复 | 相似 Skill 各自维护，改一处忘另一处 | Skill Inheritance，子 Skill 继承父 Skill |

---

## 快速开始（5 分钟）

### 安装

```bash
pip install skills-orchestrator
```

> **注意**：`pip` 包仅提供 CLI / MCP / Pipeline 能力，不内置 skills 模板。
> 需要 clone 本仓库获取示例 `config/` 和 `skills/` 目录，或自行创建。

### 初始化项目

```bash
cd my-project

# 非交互式：直接从 frontmatter 生成配置（推荐）
skills-orchestrator init --non-interactive

# 交互式：逐个确认每个 Skill 的配置
skills-orchestrator init
```

### 编译生成 AGENTS.md

```bash
skills-orchestrator build --config config/skills.yaml
# ✓ 解析完成: N skills, N zones
# ✓ 使用 Zone: 默认区 (default)
# ✓ 输出: AGENTS.md
```

把生成的 `AGENTS.md` 放到项目根目录，Claude / Cursor 会自动读取。

### 验证配置

```bash
skills-orchestrator validate --config config/skills.yaml
# ✓ 配置合法：21 skills，无冲突
```

---

## 核心功能

### 1. 编译时治理

解析 Skill 的 YAML frontmatter，检测冲突，按 Zone 生成 `AGENTS.md`。

- **Zone 机制**：不同目录自动应用不同规范（企业强制区 vs 个人自由区）
- **冲突检测**：编译时 `conflict_with` 强制报错，不会运行时才发现
- **Auto-Discovery**：从 frontmatter 自动发现 Skill，无需手动注册

### 2. MCP Server（8 个工具）

让 Claude 在对话中按需动态加载 Skill，上下文零浪费。

| 工具 | 用途 |
|------|------|
| `list_skills` | 查看所有可用 Skill（含 tag 过滤） |
| `search_skills` | 按需求搜索相关 Skill |
| `get_skill` | 加载完整 Skill 内容到上下文 |
| `suggest_combo` | 根据任务描述推荐 Skill 组合 |
| `pipeline_start` | 启动一个工作流，注入当前步骤指导 |
| `pipeline_status` | 查看工作流进度和当前步骤 |
| `pipeline_advance` | 完成当前步骤，推进到下一步 |
| `pipeline_resume` | 恢复中断的工作流 |

启动方式：

```bash
skills-orchestrator serve --config config/skills.yaml
```

在 `.claude/settings.json` 中配置：

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

### 3. Pipeline 编排

把多个 Skill 编排成有序工作流，质量门禁保证每步产出。

```yaml
# config/pipelines/quick-fix.yaml
id: quick-fix
name: 快速修复流程
steps:
  - skill: systematic-debugging
    gate:
      must_produce: [root_cause]
      min_length: 50
  - skill: tdd
    gate:
      must_produce: [test_code]
      min_length: 100
  - skill: pr-review
    skip_if: trivial_fix
```

```bash
# 启动工作流
skills-orchestrator pipeline start quick-fix

# 查看进度
skills-orchestrator pipeline status

# 推进到下一步
skills-orchestrator pipeline advance

# 恢复中断的工作流
skills-orchestrator pipeline resume
```

**关键设计**：
- `pipeline_start` / `pipeline_advance` / `pipeline_resume` 返回时自动注入当前步骤 Skill 的完整内容，AI 无需额外调用 `get_skill`
- Gate 质量门禁：`must_produce` 检查上下文中 key 的存在性，`min_length` 检查最小长度
- `skip_if` 条件跳过：满足条件时自动跳过该步骤
- RunState 持久化：工作流状态存到 `~/.skills-orchestrator/runs/`，中断后可恢复

### 4. Skill Inheritance

子 Skill 继承父 Skill 的内容，避免重复维护。

```markdown
---
id: chinese-code-review
name: 中文代码审查
base: code-review          # 继承父 Skill
tags: [review, coding, chinese]
---

## 额外规则（追加到父内容之后）

- 审查意见用中文撰写
- 遵循国内团队 commit 规范
```

编译时 Resolver 校验继承链（循环引用、缺失父 Skill），运行时 `get_skill` 返回合并后的完整内容。

### 5. Sync 多工具同步

将 Skill 同步到不同 AI 工具的目录格式。

```bash
# 同步到 Hermes Agent（全量，默认）
skills-orchestrator sync hermes

# 同步到 OpenClaw（全量，默认）
skills-orchestrator sync openclaw

# 同步到 AGENTS.md（摘要模式，默认）
skills-orchestrator sync agents-md

# 同步到 Cursor（摘要模式，默认）
skills-orchestrator sync cursor

# 同步到 Copilot（摘要模式，默认）
skills-orchestrator sync copilot

# 全量导出到指定文件
skills-orchestrator sync agents-md --full -o AGENTS.md
```

| 目标 | 默认模式 | 说明 |
|------|----------|------|
| `hermes` | 全量 | 写入 `~/.hermes/skills/` 目录 |
| `openclaw` | 全量 | 写入 `~/.openclaw/workspace/skills/` 目录 |
| `agents-md` | 摘要 | 生成 `AGENTS.md`，Required Skills 完整内容 + Available Skills 表格 |
| `cursor` | 摘要 | 生成 `.cursor/rules/*.mdc`，每个 Skill 对应一个文件 |
| `copilot` | 摘要 | 生成 `.github/copilot-instructions.md` |

AGENTS.md 输出格式：

```markdown
<!-- sync | 2026-05-02 -->

## Required Skills

---
id: systematic-debugging
...

（完整 Skill 内容）

---

## Available Skills

| Skill | 描述 | Tags |
|-------|------|------|
| brainstorming | 在任何创造性工作之前必须使用... | planning, creative |
| writing-plans | 当你有规格说明或需求时使用... | planning |
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
base: parent-skill     # 可选：继承父 Skill
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
    load_policy: require       # 该 Zone 内所有 Skill 强制注入（free 自动升级为 forced）
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
# 编译 & 验证
skills-orchestrator build     --config <path>            # 生成 AGENTS.md
skills-orchestrator validate  --config <path>            # 验证，不生成文件
skills-orchestrator status    --config <path>            # 查看 forced/passive/blocked
skills-orchestrator inspect   --workdir <path>           # 检查目录命中哪个 Zone

# 初始化 & 导入
skills-orchestrator init                                 # 交互式初始化
skills-orchestrator init --non-interactive                # 非交互式，从 frontmatter 自动生成
skills-orchestrator import    <github-url>                # 从 GitHub 导入 Skill

# MCP Server
skills-orchestrator serve     --config <path>            # 启动 MCP Server
skills-orchestrator mcp-test  <tool> <args>              # 测试 MCP 工具

# Pipeline 编排
skills-orchestrator pipeline start    <pipeline-id>      # 启动工作流
skills-orchestrator pipeline status                       # 查看进度
skills-orchestrator pipeline advance                     # 推进到下一步
skills-orchestrator pipeline resume                      # 恢复中断的工作流

# Sync 同步
skills-orchestrator sync hermes                          # 同步到 Hermes Agent
skills-orchestrator sync openclaw                        # 同步到 OpenClaw
skills-orchestrator sync agents-md [-o FILE]             # 同步到 AGENTS.md
skills-orchestrator sync cursor                          # 同步到 Cursor (.cursor/rules/*.mdc)
skills-orchestrator sync copilot [-o FILE]               # 同步到 Copilot

# Lock 可复现性
skills-orchestrator build --lock                         # 编译时同时生成 skills.lock.json
skills-orchestrator validate --check-lock skills.lock.json  # 检查 lock 是否过期
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
git clone https://github.com/BambooGap/skills-orchestrator
cd skills-orchestrator
pip install -e ".[dev]"
pytest tests/ -v
ruff check skills_orchestrator/ tests/
```

CI 运行：ruff lint + format check + Python 3.10/3.11/3.12 矩阵测试。

---

## 路线图

### v1.0 — 编译时治理

- [x] 编译时治理（build / validate / zone / conflict）
- [x] Auto-Discovery from frontmatter
- [x] 21 个生产级 Skill 内容库

### v1.1 — 动态加载 & 继承

- [x] MCP Server（list / search / get / suggest_combo）
- [x] Skill Inheritance（base 字段 + 编译时校验 + 运行时合并）
- [x] Sync 多工具同步（hermes / openclaw / agents-md / copilot）

### v1.2 — 流程编排

- [x] Pipeline 编排（YAML 定义 + 质量门禁 + 步骤注入 + 状态持久化）
- [x] MCP Pipeline 工具（pipeline_start / status / advance / resume）
- [x] init --non-interactive（从 frontmatter 自动生成配置）
- [x] CI 增强（ruff lint + format check + 多版本矩阵）
- [x] PyPI 正式发布

### v1.3+ — 规模化

- [ ] pgvector 语义检索（skill > 50 个时启用）
- [ ] Skill 版本管理 & lock file
- [ ] watch 模式（文件变更自动 build / sync）
- [ ] `sync --prefix` 命名空间隔离
- [ ] 中文搜索 bigram 分词优化

---

## License

MIT

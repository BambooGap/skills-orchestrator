# Skills Orchestrator

[![PyPI](https://img.shields.io/pypi/v/skills-orchestrator.svg)](https://pypi.org/project/skills-orchestrator/)
[![CI](https://github.com/BambooGap/skills-orchestrator/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/BambooGap/skills-orchestrator/actions/workflows/ci.yml)
[![CodeQL](https://github.com/BambooGap/skills-orchestrator/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/BambooGap/skills-orchestrator/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/BambooGap/skills-orchestrator/badge)](https://securityscorecards.dev/viewer/?uri=github.com/BambooGap/skills-orchestrator)
[![Release](https://img.shields.io/github/v/release/BambooGap/skills-orchestrator)](https://github.com/BambooGap/skills-orchestrator/releases/latest)
[![GitHub Action](https://img.shields.io/badge/GitHub%20Action-v4.8.25-blue?logo=githubactions&logoColor=white)](docs/github-action.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**开源 SkillOps / AI instruction governance system** — 用 policy packs、组织级 registry、证据包、SARIF/CI、SBOM、生态 adapter 和 MCP bridge，把分散的 `.md` skills 变成可治理、可审计、可接入团队流水线的工程资产。

它不替代 Codex、Claude Code、Omnigent、CodeGraph、Superpowers 或业务记忆系统；它位于这些工具之间，负责回答团队最实际的问题：哪些 skills 可以用、谁负责、来源是否可信、CI 是否能阻断、审计证据在哪里，以及下游 agent runtime 应消费哪些经过治理的指令资产。

| Surface | Current status | Entry point |
|---------|----------------|-------------|
| OSS CLI | `v4.8.25` on PyPI | `python3.12 -m pip install skills-orchestrator` |
| GitHub Action | `v4.8.25` release tag | `BambooGap/skills-orchestrator@v4.8.25` |
| Container image | Published on GHCR | `ghcr.io/bamboogap/skills-orchestrator:v4.8.25` |
| SkillOps Contract | v1 executable spec | [`SPEC.md`](SPEC.md), [`CONFORMANCE.md`](CONFORMANCE.md) |
| Adoption pilots | Copyable repo starter packs | [`docs/adoption-playbook.md`](docs/adoption-playbook.md), `examples/pilot-repos/` |
| Open-core contracts | Schema-backed examples | `examples/commercial-handoff/` |

```bash
python3.12 -m pip install skills-orchestrator
skills-orchestrator init --template team-standard
skills-orchestrator check --config config/skills.yaml
```

The default PyPI install is the lightweight CI governance CLI. Install the optional MCP runtime only
when you want `serve` or `mcp-test`:

```bash
python3.12 -m pip install "skills-orchestrator[mcp]"
```

---

## 为什么需要它？

| 问题 | 没有 Skills Orchestrator | 有了之后 |
|------|--------------------------|----------|
| Skill 越来越多 | 手动维护 AGENTS.md，容易遗漏或冲突 | `build` 一条命令自动生成 |
| 不同项目用不同规范 | 到处复制粘贴，版本不同步 | Zone 机制，目录自动对应规范 |
| CI 只能看退出码 | 终端输出无法被工具链消费 | `check --format json/sarif` 生成机器可读报告和 rule-level trace |
| Instruction 没有清单 | 供应链工具看不到 agent 规则资产 | `manifest --format json/cyclonedx` 导出 instruction inventory |
| Policy 团队无法审计 | Resolver 结果只在 CLI 里可见 | `policy export --format opa-input/rego-test` 导出 OPA/Rego proof |
| 团队规则不可执行 | owner/source/version/license 只写在文档里 | `check --policy-pack builtin/team-standard` 强制团队治理元数据 |
| 外部 Skill 来源不可信 | 只知道复制自 URL，不知道 commit、hash、抓取时间 | `import` 写入 provenance，`builtin/engineering-grade` 检查来源证据 |
| 多仓 Skill 无法盘点 | 每个 repo 各查各的 | `registry build` / `registry diff` / `registry graph` 导出组织级 skill registry 和治理关系图 |
| 外部平台难以接入 | Hosted/GitHub App 重写 CLI 语义 | `examples/external-consumer` 固化 hosted registry、GitHub App、multi-repo artifact 输入边界 |
| 商用审计缺证据包 | 发布时到处找 CI、manifest、SARIF | `evidence export` 一次导出审计证据和 hash ledger |
| 上下文窗口有限 | 所有 Skill 全量注入，浪费 token | MCP Server 按需加载，500 个 Skill 和 5 个消耗相同 |
| 两个 Skill 互相冲突 | 运行时才发现，模型行为不确定 | 编译时 `conflict_with` 强制报错 |
| 多步骤工作流无保证 | AI 靠自觉推进，容易跳步或遗漏 | Pipeline 编排 + 质量门禁，每步必须产出 |
| Skill 内容重复 | 相似 Skill 各自维护，改一处忘另一处 | Skill Inheritance，子 Skill 继承父 Skill |

---

## 快速开始（5 分钟）

### 安装

```bash
python3.12 -m pip install skills-orchestrator
```

Skills Orchestrator requires Python 3.12 or newer. On macOS, `/usr/bin/python3` is often
Python 3.9, which can make `pip install skills-orchestrator` look like the package is missing.
Use `python3.12`, `pipx --python python3.12`, `uvx --python 3.12`, or the Docker image.

> `pip` 包内置 `team-standard` starter kit；需要更多 examples 时再 clone 本仓库。

`serve` and `mcp-test` need the optional MCP runtime extra:

```bash
python3.12 -m pip install "skills-orchestrator[mcp]"
```

不想在 CI host 上安装 Python 包时，也可以直接使用已发布容器：

```bash
docker run --rm ghcr.io/bamboogap/skills-orchestrator:v4.8.25 --version
```

### 初始化项目

```bash
cd my-project

# 生产 bootstrap：生成 config、示例 skills、CI workflow 和 evidence 目录
skills-orchestrator init --template team-standard

# 严格供应链 bootstrap：生成 pinned checkout 的 CI workflow
skills-orchestrator init --template team-standard --hardened-workflow

# 兼容旧流程：从已有 skills/*.md frontmatter 生成配置
skills-orchestrator init --non-interactive

# 交互式：逐个确认每个 Skill 的配置
skills-orchestrator init
```

### 检查 Skills

```bash
skills-orchestrator check --config config/skills.yaml
# Skills check
#   Findings: 0 errors, 0 warnings, 0 infos
```

启用团队标准规则：

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning
```

启用工程级治理规则：

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning
```

CI 或 GitHub Code Scanning 可以使用机器可读输出：

```bash
skills-orchestrator check --config config/skills.yaml --format json > check.json
skills-orchestrator check --config config/skills.yaml --format sarif
skills-orchestrator explainability build \
  --check-json check.json \
  --config config/skills.yaml \
  --output ci-explainability.json \
  --force
skills-orchestrator schema validate --kind check --input check.json
skills-orchestrator schema validate --kind ci-explainability --input ci-explainability.json
```

JSON check output includes `policy_trace`: an explainable CI trace for rule evaluation. It traces
SkillOps rules and policy packs, not agent reasoning or runtime model behavior.
`ci-explainability.json` turns the same trace into PR/CI-ready failure explanations: rule id,
blocking status, file/line, skill id, severity, and suggested fix.

也可以直接在 GitHub Actions 中运行：

```yaml
permissions:
  contents: read
  security-events: write
  pull-requests: write

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: BambooGap/skills-orchestrator@v4.8.25
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          upload-sarif: true
          reviewer-summary: true
          dashboard-snapshot: true
          comment-registry-diff: true
```

`reviewer-summary: true` 会生成 check JSON、policy trace、registry graph、evidence
ledger 和 reviewer summary artifact；`dashboard-snapshot: true` 会从同一份 evidence
bundle 派生 dashboard-ready JSON。如果同时启用 `comment-registry-diff`，PR comment
会使用更适合 reviewer 阅读的汇总内容。

更多输入参数见 [GitHub Action 文档](docs/github-action.md)。团队文档入口见
[Documentation Index](docs/INDEX.md)。

Docker 运行方式见 [Docker Usage](docs/docker.md)。

### 15 分钟试点接入

如果你是在一个真实仓库里第一次试点，优先走 adoption playbook，而不是直接启用最严格的
enterprise gate：

1. 用 `init --template team-standard` 生成 starter kit。
2. 先跑 `check`，再跑 `build --lock` 生成 `AGENTS.md` 和 `skills.lock.json`。
3. 再跑 `doctor --profile adopter --fail-under 100` 和 `conformance run --profile core`。
4. 在 GitHub Action 里先用 advisory 或 warning gate。
5. 等 registry diff 和 SARIF 对 reviewer 有用后，再升级到 `builtin/engineering-grade`。

完整步骤见 [Adoption Playbook](docs/adoption-playbook.md)。可复制的真实仓库形态示例见
[Pilot Repository Examples](examples/pilot-repos/README.md)。

### 规范、一致性与可运行 Demo

- [SkillOps Contract v1](SPEC.md): skill metadata、registry、diff、evidence、adapter 的机器可测试规范。
- [Conformance](CONFORMANCE.md): 如何用 `conformance run`、`schema validate`、`check`、`registry`、`evidence` 验证兼容性。
- [Third-party Implementation Guide](docs/third-party-implementation.md): 如何只依赖 schema、conformance 和负例 fixtures 实现兼容工具。
- [Security Policy](SECURITY.md): MCP trust model、HMAC audit、import provenance 和漏洞报告流程。
- [Demo Repository](examples/demo-repo/README.md): 可复制到独立 repo 的端到端场景，覆盖 PR diff comment、SARIF、evidence bundle 和 adapter inspect。
- [Negative Conformance Fixtures](examples/negative-conformance/README.md): 可复制的坏输入样本，证明高风险 instruction artifacts 会稳定失败。
- [Adoption Playbook](docs/adoption-playbook.md): 从 advisory CI 到 blocking gate 的试点路径。
- [Production Adoption](docs/production-adoption.md): 生产 CI 接入的 SHA pin、Docker digest、PyPI version pin、证据保留和 runtime 边界。
- [Supply Chain Verification](docs/supply-chain-verification.md): 验证 PyPI wheel/sdist attestations、GHCR provenance/SBOM attestations、digest 和 hash-lock 边界。
- [External Pilot Intake](docs/external-pilot-intake.md): 外部仓库试点前的 go / no-go 清单。
- [Adoption Maturity Model](docs/adoption-maturity-model.md): 从本地试点到多仓治理的分级准入标准。
- [Agent Fleet Governance](docs/agent-fleet-governance.md): 多 Agent、多租户、多项目指令资产治理边界。
- [Supervisor Governance](docs/supervisor-governance.md): 总控 Agent、子 Agent、交接、权限和证据的治理模型。
- [Agent Handoff Contract Example](examples/agent-handoff/README.md): 可验证的 supervisor/worker handoff、tenant scope、tool boundary 和 evaluation gate 示例。
- [Agent Runtime Image Contract Example](examples/agent-runtime-image/README.md): 可验证的外部 agent runtime 容器镜像、权限边界、证据和 handoff gate 示例。
- [Pilot Repository Examples](examples/pilot-repos/README.md): Healthchecks、Umami、Woodpecker 风格仓库的最小接入包。
- [External Consumer Example](examples/external-consumer/): hosted registry、GitHub App 和 multi-repo artifact 输入边界。
- [Commercial And Foundation Readiness](docs/foundation-readiness.md): 商用试点、外部 adoption、基金会候选之间的真实门槛。
- [Release Rollback Playbook](docs/release-rollback.md): 发布错误时如何处理 PyPI、GHCR、GitHub Release 和证据包。

### SkillOps Readiness 与证据包

```bash
skills-orchestrator doctor --profile adopter --config config/skills.yaml

skills-orchestrator doctor --profile maintainer --config config/skills.yaml

skills-orchestrator conformance run \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade

skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --format json \
  > check.json

skills-orchestrator explainability build \
  --check-json check.json \
  --config config/skills.yaml \
  --output ci-explainability.json \
  --force

skills-orchestrator evidence export \
  --config config/skills.yaml \
  --out evidence

skills-orchestrator evidence index \
  --manifest "repo-a=../repo-a/evidence/evidence-manifest.json" \
  --manifest "repo-b=../repo-b/evidence/evidence-manifest.json" \
  --scope-name platform-pilot \
  --output multi-repo-artifacts.json

skills-orchestrator registry build \
  --config-glob "config/skills.yaml" \
  --output skill-registry.json

skills-orchestrator registry graph \
  --config-glob "config/skills.yaml" \
  --output registry-graph.json

skills-orchestrator registry diff registry-before.json registry-after.json \
  --format json \
  --output registry-diff.json \
  --force

skills-orchestrator registry diff registry-before.json registry-after.json \
  --format markdown \
  --output registry-diff.md \
  --force

skills-orchestrator reviewer summary \
  --check-json check.json \
  --registry-diff-json registry-diff.json \
  --registry-diff-markdown registry-diff.md \
  --registry-graph registry-graph.json \
  --evidence-manifest evidence/evidence-manifest.json \
  --output skillops-review-summary.md

skills-orchestrator dashboard snapshot \
  --evidence-dir evidence \
  --repository BambooGap/skills-orchestrator \
  --ref refs/heads/main \
  --commit "$(git rev-parse HEAD)" \
  --output dashboard-snapshot.json

skills-orchestrator dashboard rollup \
  --snapshot dashboard-snapshot.json \
  --organization BambooGap \
  --output dashboard-rollup.json

skills-orchestrator registry comment-body registry-diff.md \
  --output registry-diff-comment.md

skills-orchestrator schema validate \
  --kind registry \
  --input skill-registry.json

skills-orchestrator schema validate \
  --kind registry-graph \
  --input registry-graph.json

skills-orchestrator schema validate \
  --kind enterprise-dashboard-snapshot \
  --input dashboard-snapshot.json

skills-orchestrator schema validate \
  --kind enterprise-dashboard-rollup \
  --input dashboard-rollup.json

skills-orchestrator schema list --format json > schema-catalog.json
skills-orchestrator schema validate \
  --kind schema-catalog \
  --input schema-catalog.json
skills-orchestrator schema audit --format json > schema-audit.json
skills-orchestrator schema validate \
  --kind schema-audit \
  --input schema-audit.json

skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/release-review-handoff.json

skills-orchestrator schema validate \
  --kind agent-runtime-image \
  --input examples/agent-runtime-image/codex-worker-image.json

skills-orchestrator integrations list
skills-orchestrator adapters inspect --format json
skills-orchestrator supply-chain sbom --output package-sbom.cdx.json
```

`doctor` 默认使用 `adopter` profile，检查接入仓库真正需要的 config、policy、
SkillOps CI workflow、lock 和 `AGENTS.md` 证据；`maintainer` profile 才额外检查
本项目发版用的 `action.yml`、`Dockerfile` 和版本化测试报告；`enterprise` profile
读取 evidence bundle 并验证核心 artifact schema，适合平台团队试点。`evidence export` 写出
`check.json`、`check.sarif`、`ci-explainability.json`、`instruction-manifest.json`、
`policy-opa-input.json`、`policy-proof.rego`、`doctor.json`、`skill-registry.json`、
`registry-graph.json`、`adapter-inspect.json` 和 `package-sbom.cdx.json`，并在
`evidence-manifest.json` 中记录 artifact SHA-256、`bundle_hash` 和可选
`previous_bundle_hash`，适合 CI artifact、审计归档或客户交付。
多仓场景下，`evidence index` 会把多个仓库的 evidence manifest 聚合成
`multi-repo-artifacts.json`，供平台团队和 hosted registry 类外部消费者读取。
`schema validate` 可单独验证 config、check、CI explainability、manifest、policy OPA input、
doctor、registry、registry graph、registry diff、multi-repo artifacts、adapter inspection、
Claude Skills export manifest、SBOM、dashboard snapshot/rollup、agent handoff、agent runtime image
和 commercial handoff 文件合同。`schema list --format json` 现在输出可验证的
`schema-catalog`，包含每个合同的 `contract_id`、`stability`、`since` 和目标消费者，
适合平台团队做自动发现和兼容性审计；`schema audit` 会自检所有打包 schema 和
catalog 元数据，是 v4 线的合同自审计 gate。
`builtin/engineering-grade` 在 v3.2 起额外检查 `license`、外部 skill `provenance`
和 review-window 元数据；外部导入应保留 observed `source_url`、`source_ref`、
`source_commit`、`content_hash` 和 `fetched_at`，不要把未验证 frontmatter 当成可信来源。

### 生态适配与 Open-core Handoff

```bash
skills-orchestrator adapters inspect --path . --format json \
  > adapter-inspect.json

skills-orchestrator adapters export mcp-client-config \
  --config config/skills.yaml \
  --output mcp-client.json

skills-orchestrator adapters export claude-skills \
  --config config/skills.yaml \
  --output-dir .claude/skills \
  --manifest-output claude-skills-export.json \
  --force

skills-orchestrator schema validate \
  --kind claude-skills-export \
  --input claude-skills-export.json

skills-orchestrator adapters export openai-agents-sdk \
  --config config/skills.yaml \
  --output openai_skillops_agent.py

skills-orchestrator schema validate \
  --kind hosted-registry-ingest \
  --input examples/commercial-handoff/registry-ingest.json
```

开源核心只负责产出本地 artifact 与机器可读合同。后续 GitHub App、hosted registry
和 enterprise dashboard 应消费这些文件，而不是在 SaaS 后端里重新实现 resolver 或
registry 语义。

### 导出 Instruction Manifest

Native JSON 保留 Skills Orchestrator 的完整语义，CycloneDX 输出是实验性映射，用于进入现有 BOM / supply-chain 词汇体系。

```bash
skills-orchestrator manifest --config config/skills.yaml --format json
skills-orchestrator manifest --config config/skills.yaml --format cyclonedx
```

### 导出 Policy Proof

OPA/Rego 是对外审计和集成表面，不是第二套运行时 backend。Resolver 仍然是权威决策系统。

```bash
skills-orchestrator policy export --config config/skills.yaml --format opa-input
skills-orchestrator policy export --config config/skills.yaml --format rego-test
```

### 编译生成 AGENTS.md

```bash
skills-orchestrator build --config config/skills.yaml
# ✓ 解析完成: N skills, N zones
# ✓ 使用 Zone: 默认区 (default)
# ✓ 输出: AGENTS.md
```

把生成的 `AGENTS.md` 放到项目根目录，Claude / Cursor 会在会话启动或项目重新加载时读取。

---

## 核心功能

### Runtime Model

Skills Orchestrator 把“启动时引导”和“运行时加载”分开：

| 层 | 作用 | 典型入口 |
|----|------|----------|
| `AGENTS.md` | Bootstrap。告诉 Agent 当前项目有哪些 required / available skills，以及如何按需请求更多内容。多数 Agent 只在会话启动或项目重新加载时读取它。 | `build`, `sync agents-md` |
| Check Reports | Static diagnostics。检查 metadata、重复 id、冲突声明、lock drift，并输出 text / JSON / SARIF。 | `check`, `validate --format json` |
| Policy Packs | Team governance。把 owner/source/version/lifecycle/approver 等团队规则变成可执行检查。 | `check --policy-pack builtin/team-standard` |
| Instruction Manifest | Inventory export。导出 native JSON 和实验性 CycloneDX BOM，便于把 agent instructions 纳入供应链资产清单。 | `manifest` |
| Policy Export | Policy proof。导出 OPA input 和 Rego test fixture，证明 resolver 事实可被 policy-as-code 审计。 | `policy export` |
| Registry & Evidence | SkillOps evidence。生成组织级 registry、doctor readiness 报告和发布审计证据包。 | `registry`, `doctor`, `evidence export` |
| MCP Server | Runtime skill loading。对话过程中通过 `prepare_context` / `search_skills` / `get_skill` 动态选择并获取本轮 Skill 内容，避免一次性塞满上下文。 | `serve`, `mcp-test` |
| Pipeline | Runtime workflow orchestration。把多个 Skill 串成有状态流程，并在每一步自动注入当前步骤 Skill。 | `pipeline start`, MCP pipeline tools |

团队落地建议见 [Team Standardization Guide](docs/team-standardization.md)。

### 同一会话内如何动态切换 Skills

`AGENTS.md` 不是热更新文件。多数 Agent 只会在 `/new`、新会话、项目重新加载时读取一次它。Skills Orchestrator 的动态能力来自 MCP：`AGENTS.md` 只告诉 Agent 一条固定协议，真正的 Skill 选择在每个任务开始时通过 `prepare_context` 完成。

```text
/new
  ↓
Agent 读取一次 AGENTS.md
  ↓
AGENTS.md 提供固定协议：
  - 不要把所有 available skills 全量塞进上下文
  - 每个新任务开始或任务目标明显变化时，先调用 MCP prepare_context(task)
  - 本轮只遵循 prepare_context 返回的 active_skills
  - 上一轮加载过但本轮未返回的 skills 视为 inactive
  ↓
任务 1：用户说“帮我做安全审查”
  ↓
Agent 调用：
  prepare_context({"task": "帮我做安全审查", "max_skills": 3})
  ↓
MCP 返回本轮 active_skills，例如：
  - security-review（安全代码审查）
  - pr-review（PR Review）
  - error-handling（错误处理规范）
  ↓
Agent 按这组 Skills 执行任务 1
  ↓
任务 2：用户说“现在帮我写发版流程”
  ↓
Agent 再次调用：
  prepare_context({"task": "写发版流程", "max_skills": 3})
  ↓
MCP 返回新的 active_skills，例如：
  - deployment-checklist（部署检查清单）
  - git-commit-conventions（Git 提交规范）
  - documentation（写文档）
  ↓
Agent 按新这组 Skills 执行任务 2，任务 1 的安全审查 Skills 不再作为本轮规则
```

`prepare_context` 默认会直接返回 active skills 的完整内容，适合让 Agent 立即进入任务。如果只想先看路由结果，可以传 `include_content: false`，再对需要的条目调用 `get_skill(id)`。

```bash
skills-orchestrator mcp-test prepare_context \
  '{"task": "帮我做安全审查", "max_skills": 3, "include_content": false}' \
  --config config/skills.yaml
```

返回结果包含四类信息：

| 字段 | 含义 |
|------|------|
| `active_skills` | 本轮任务应该遵循的 Skill ID 列表 |
| `inactive_skills` | 当前 Registry 中未被本轮选中的 Skill，本轮任务不应受其约束 |
| `Decision Record (JSON)` | 结构化路由记录，包含 `routing_id`、`task_hash_alg`、registry generation、active/inactive skills、内容哈希和截断信息 |
| `Execution Rule` | 明确告诉 Agent：旧 Skill 与本轮 active skills 冲突时，以本轮为准 |
| `Active Skill Content` | 当 `include_content=true` 时，直接注入本轮所需 Skill 全文 |

这意味着同一个会话可以连续处理多个不同任务，但每个任务边界都要重新路由一次。`prepare_context` 不能删除模型历史上下文里的旧文字，所以它会显式输出 inactive 规则，让 Agent 在行为上切换到新的一组 Skills。

因此，修改 Skill 后通常需要重新 `build` / `sync` 并重启或刷新对应 Agent 会话；如果使用 MCP Server，运行中的 server 也需要重启才能重新加载配置和 Skill 内容。

### 1. 编译时治理

解析 Skill 的 YAML frontmatter，检测冲突，按 Zone 生成 `AGENTS.md`。

- **Zone 机制**：不同目录自动应用不同规范（企业强制区 vs 个人自由区）
- **冲突检测**：编译时 `conflict_with` 强制报错，不会运行时才发现
- **Auto-Discovery**：从 frontmatter 自动发现 Skill，无需手动注册

### 2. MCP Server（10 个工具）

让 Claude 在对话中按需动态加载 Skill，上下文零浪费。

MCP serving is optional. Install `skills-orchestrator[mcp]` before running `serve` or `mcp-test`.

| 工具 | 用途 |
|------|------|
| `list_skills` | 查看所有可用 Skill（含 tag 过滤） |
| `search_skills` | 按需求搜索相关 Skill |
| `get_skill` | 加载完整 Skill 内容到上下文 |
| `suggest_combo` | 根据任务描述推荐 Skill 组合 |
| `prepare_context` | 每个新任务动态选择本轮 active skills，并可直接注入完整内容 |
| `pipeline_start` | 启动一个工作流，注入当前步骤指导 |
| `pipeline_status` | 查看工作流进度和当前步骤 |
| `pipeline_list_runs` | 列出已保存的 Pipeline 运行记录 |
| `pipeline_advance` | 完成当前步骤，推进到下一步 |
| `pipeline_resume` | 恢复中断的工作流 |

推荐在 `AGENTS.md` 中固定写入这条规则：每次新任务开始或任务目标明显变化时，先调用 `prepare_context(task)`；本轮只遵循返回的 `active_skills`，之前任务加载过但本次未返回的 Skill 视为 inactive。

启动方式：

```bash
skills-orchestrator serve --config config/skills.yaml
```

需要运行期审计时，指定 audit 目录。审计事件是 JSONL，只记录 tool、参数 key、routing
hash、active skill id 等治理字段，不记录任务原文或 Skill 正文。

```bash
skills-orchestrator serve --config config/skills.yaml --audit-dir .skills-audit
skills-orchestrator usage report --audit-dir .skills-audit
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
skills-orchestrator pipeline advance quick-fix

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
# 示例：为一个新任务动态选择本轮 skills
skills-orchestrator mcp-test prepare_context '{"task": "做安全审查", "max_skills": 3}'

# Pipeline 编排
skills-orchestrator pipeline start    <pipeline-id>      # 启动工作流
skills-orchestrator pipeline status                       # 查看进度
skills-orchestrator pipeline advance <pipeline-id>       # 推进到下一步
skills-orchestrator pipeline resume                      # 恢复中断的工作流

# Sync 同步
skills-orchestrator sync hermes                          # 同步到 Hermes Agent
skills-orchestrator sync openclaw                        # 同步到 OpenClaw
skills-orchestrator sync agents-md [-o FILE]             # 同步到 AGENTS.md
skills-orchestrator sync cursor                          # 同步到 Cursor (.cursor/rules/*.mdc)
skills-orchestrator sync copilot [-o FILE]               # 同步到 Copilot

# Lock 可复现性
skills-orchestrator build --lock                         # 编译时同时生成 skills.lock.json
skills-orchestrator check --check-lock skills.lock.json      # 检查 lock 是否过期
```

---

## 从 GitHub 导入 Skill

```bash
# 导入受信任仓库里的所有 Skill
skills-orchestrator import https://github.com/example/your-reviewed-skills

# 导入后记录 observed source/provenance；加入默认 skill_dirs 前先复核 license 与内容安全
```

---

## 开发

```bash
git clone https://github.com/BambooGap/skills-orchestrator
cd skills-orchestrator
python3.12 -m pip install -e ".[dev]"
pytest tests/ -v
ruff check skills_orchestrator/ tests/
```

CI 运行：ruff lint + format check + Python 3.12/3.13 矩阵测试。

---

## 路线图

### 已完成主线

- v2.0.x：稳定了 build / validate / zone / conflict、frontmatter discovery、MCP Server、Skill Inheritance、sync targets、Pipeline 编排、PyPI 发布和基础安全边界。
- 检查诊断与机器报告阶段：补齐 `check` 诊断面，输出 JSON / SARIF，并把项目定位收敛到 SkillOps 和 instruction supply chain。
- v2.3.x：发布 GitHub Action、CycloneDX / native manifest、OPA/Rego proof export、Action SHA pinning、artifact attestation 和 PyPI 发布防护。
- v2.4.x：补齐 Docker 交付、团队标准化文档、MCP routing decision record、usage audit、pipeline recovery 和本地运行证据。
- v2.5.x：补齐 `builtin/team-standard` policy pack、治理元数据、`doctor` readiness、组织级 `registry`、`evidence export`、integration catalog、MCP 内容上限、audit HMAC 和 pipeline 状态脱敏。
- v2.6.x：补齐稳定 JSON Schema、`schema validate`、`init --template team-standard` 和 `registry diff --format markdown`，降低团队 bootstrap 与 PR review 摩擦。
- v3.0.x：补齐 PR registry diff comment automation、package SBOM、CodeQL/GHCR workflows、生态 adapter inspect/scaffold、open-core commercial handoff schemas 和 GitHub App / hosted registry / dashboard 蓝图。
- v4.x：补齐 CI explainability、schema audit、digest-bound container SBOM/provenance、GHCR attestation、Claude Skills round-trip export、release evidence polish、multi-repo artifact index 和 external consumer adoption fixtures。
- v4.7.x：补齐公开 negative conformance fixtures、adoption maturity model、第三方实现指南、release rollback playbook 和 v4.x 兼容性口径。
- v4.8.x：补齐 lightweight 默认安装、post-release smoke、外部试点 intake、negative fixture 语义、agent fleet governance、supervisor governance 边界、agent handoff preview contract 和当前 release hygiene。
- v4.8.11：补齐外部 agent runtime container image 的 preview contract；项目不内置 agent 镜像，而是验证镜像 digest、SBOM/provenance、权限边界、adapter surfaces、handoff 和 evaluation gate。
- v4.8.12：清理 Post-release Smoke 公开日志中的 Node.js 20 deprecation 噪音，升级 artifact upload 到 v7 pinned SHA。
- v4.8.13：修正公开 README / PyPI 长描述中的版本归因，让 runtime image contract 和 release hygiene 的阶段记录保持可信。
- v4.8.14：打磨新用户 onboarding，明确 `init --template team-standard` 后需要先 `build --lock` 再期待 `doctor` 满分。
- v4.8.15：收紧 `agent-handoff` preview contract，增加 privileged worker / production handoff 负例 fixtures 和 schema 测试。
- v4.8.16：补齐 production adoption 文档，把生产 CI 的 Action SHA、Docker digest、PyPI version pin、advisory→blocking 和 runtime 边界写成可执行接入标准。
- v4.8.17：补齐 supply-chain verification 文档，把 PyPI artifact attestation、GHCR provenance/SBOM attestation、offline bundle 和 consumer-side hash lock 写成可执行验证路径。
- v4.8.18：修正 supply-chain verification 的 PyPI 下载命令，明确 wheel 和 sdist 需要分别下载后再验证 attestation。
- v4.8.19：把 consumer-side hash-locked PyPI install 纳入 post-release smoke，可验证发布包能通过 `--require-hashes` 从本地 wheelhouse 安装。
- v4.8.20：给 GHCR release digest 增加 Sigstore Cosign keyless image signature，并把签名验证纳入 full post-release smoke。
- v4.8.21：给 GHCR release digest 增加 Syft 生成的 container OS-layer CycloneDX SBOM，并把 OS SBOM attestation 验证纳入 full post-release smoke。
- v4.8.22：放宽 CycloneDX component `version` schema 要求，兼容真实 Syft OS/image SBOM 中无版本号的组件。
- v4.8.23：新增 `supply-chain slsa-readiness` 和 preview schema，把 PyPI/GHCR/signature/smoke
  证据映射到非认证 SLSA build-track readiness report。
- v4.8.24：修正 workflow-dispatched Post-release Smoke 的源码导入路径，让 `slsa-readiness-report`
  在 GitHub Actions full smoke 中真实通过。
- v4.8.25：给 workflow-dispatched Post-release Smoke 安装 constrained local smoke dependencies，
  让 `slsa-readiness-report` 在 GitHub runner 上也能使用 schema/runtime dependencies。

### 下一阶段

- 增加更多真实生态 adapter examples，包括跨仓 MCP client config、OpenAI Agents SDK scaffold 和 Claude Skills bundle 的负例 fixtures。
- 继续推进 formal SLSA 前置条件、OS SBOM 漏洞扫描策略和 OpenSSF Scorecard hygiene；SLSA readiness
  map 已可生成和 schema validate，但不等同于 formal SLSA level。
- 围绕 [Agent Fleet Governance](docs/agent-fleet-governance.md) 增加真实 adopter 需要的 adapter fixtures，
  但不把 CLI 扩展成 agent runtime、tenant admin tool 或 multi-agent queue。
- 围绕 [Supervisor Governance](docs/supervisor-governance.md) 继续完善真实 adopter 需要的 lead/worker/handoff
  证据 fixtures；`agent-handoff` 已作为 preview schema 提供，但仍由下游 runtime 负责调度、权限执行和租户隔离。
- 围绕 [Agent Runtime Image Contract Example](examples/agent-runtime-image/README.md) 继续收集外部 runtime
  消费场景；只有当两个以上真实下游需要同一字段时，才把 preview 字段提升为 stable contract。
- 在外部仓库实现 GitHub App / hosted registry / dashboard，继续消费 OSS artifact contracts；核心 CLI 只维护 artifact contracts、schema 和验证命令。

---

## License

MIT

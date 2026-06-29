# 示例项目

这个目录包含多个示例项目，帮助你快速上手 skills-orchestrator。

## 📚 示例列表

### [基础示例](basic/)

**适合**：个人开发者

**展示内容**：
- 如何初始化项目
- 如何编写 Skill 文件
- 如何生成 AGENTS.md
- 如何同步到多平台

**时间**：5 分钟

---

### [团队协作示例](team-collab/)

**适合**：团队负责人、团队协作

**展示内容**：
- 如何配置 Zone 隔离不同团队
- 如何使用 `conflict_with` 防止冲突
- 如何使用 Pipeline 编排工作流
- 如何统一团队的 Skills 版本

**时间**：15 分钟

---

### [多平台同步示例](multi-platform/)

**适合**：使用多个 IDE 的开发者、团队成员使用不同工具

**展示内容**：
- 如何同步到 5 个不同的平台
- 如何选择摘要模式 vs 全量模式
- 如何确保 Skills 版本一致

**时间**：10 分钟

---

### [SkillOps Demo Repo](demo-repo/)

**适合**：外部评估者、平台团队、安全团队

**展示内容**：
- 如何跑通 SkillOps Contract v1 的 conformance checks
- 如何生成 SARIF、registry diff、PR comment body 和 evidence bundle
- 如何验证 AGENTS.md、Claude Skills、MCP config、OpenAI Agents SDK adapter surface
- 如何把同一套流程复制到独立 GitHub repo

**时间**：20 分钟

---

### [Negative Conformance Fixtures](negative-conformance/)

**适合**：平台团队、安全团队、第三方实现者

**展示内容**：
- 如何验证坏输入会稳定失败
- 如何复用缺治理元数据、错误 load_policy、过期 review-window、缺外部 provenance 等样本
- 如何把负例规则集纳入下游 CI 或兼容性测试

**时间**：10 分钟

---

### [Adapter Evidence Example](adapter-evidence/)

**适合**：agent runtime owner、平台团队、生态适配评估

**展示内容**：
- 如何从同一份 SkillOps config 生成 Claude Skills bundle
- 如何生成 MCP client config 和 OpenAI Agents SDK scaffold
- 如何编译 scaffold 并生成 adapter inspection evidence
- 如何证明 adapter surface 是 artifact contract，而不是运行时模型调用

**时间**：10 分钟

---

### [Adapter Negative Fixtures](adapter-negative/)

**适合**：平台团队、安全团队、第三方实现者

**展示内容**：
- 如何验证坏 Claude Skills entrypoint 不会被误识别为有效 skill
- 如何验证坏 MCP JSON config 会进入 `invalid_paths`
- 如何验证 OpenAI-looking project files 不会被误判成 OpenAI Agents SDK surface
- 如何保持 adapter 检测是保守的 artifact contract，而不是猜测式 runtime discovery

**时间**：5 分钟

---

### [Release Trust Example](release-trust/)

**适合**：release owner、安全团队、平台团队

**展示内容**：
- 如何验证外部 skill 的 license、review-window 和 import provenance
- 如何用 `engineering-grade` 区分可接受外部 skill 和缺信任元数据的外部 skill
- 如何生成并本地验证 digest-bound container SBOM / provenance

**时间**：10 分钟

---

### [Multi-repo Artifacts Example](multi-repo-artifacts/)

**适合**：平台团队、组织级接入、安全/审计负责人

**展示内容**：
- 如何把多个仓库的 `evidence-manifest.json` 聚合成一个 `multi-repo-artifacts.json`
- 如何验证组织级 artifact index 的 schema
- 如何保持多仓治理仍然是 artifact-first，而不是 dashboard 或 runtime 系统

**时间**：10 分钟

---

### [External Consumer Example](external-consumer/)

**适合**：平台团队、GitHub App / hosted registry / dashboard 产品边界设计

**展示内容**：
- 如何验证 hosted registry ingest payload
- 如何验证 GitHub App installation payload
- 如何把 `multi-repo-artifacts.json` 作为外部消费者输入
- 如何保持外部产品只消费 OSS artifact contracts，而不是重新实现 CLI 语义

**时间**：10 分钟

---

### [External Adoption Record Example](external-adoption-record/)

**适合**：平台团队、外部接入评估、开源采用审查

**展示内容**：
- 如何把真实仓库 adoption 的 owner、gate、artifact 状态和 promotion decision 记录成 schema-valid artifact
- 如何把技术接入成功和公开 adopter listing consent 分开
- 如何避免把 demo 或 generic reference example 误写进 `ADOPTERS.md`

**时间**：5 分钟

---

### [Agent Handoff Contract Example](agent-handoff/)

**适合**：多 Agent runtime owner、平台团队、安全团队

**展示内容**：
- 如何把 supervisor/worker handoff 表达成机器可验证 artifact
- 如何声明 tenant scope、worker permission mode、tool boundary 和 evaluation gates
- 如何用负例验证 privileged worker 必须有人类批准和 human-review gate
- 如何用负例验证 production handoff 必须带 CI explainability evidence
- 如何让 Skills Orchestrator 治理 handoff contract，而不是运行子 Agent

**时间**：10 分钟

---

### [Agent Runtime Image Contract Example](agent-runtime-image/)

**适合**：多 Agent runtime owner、平台团队、安全团队、供应链审查负责人

**展示内容**：
- 如何把外部 agent runtime 容器镜像表达成机器可验证 artifact
- 如何声明 image digest、SBOM/provenance、tenant scope、网络/文件/secret 边界
- 如何用负例验证 floating tag、特权文件系统、无限制网络和 secret access 不能绕过审批 gate
- 如何让 Skills Orchestrator 治理 runtime image contract，而不是运行或调度 Agent 容器

**时间**：10 分钟

---

### [Reference Repository Examples](adoption-repos/)

**适合**：平台团队、开源采用评估、真实仓库接入

**展示内容**：
- Healthchecks / Umami / Woodpecker 风格仓库的最小接入包
- `config/skills.yaml`、sample skills、GitHub Action workflow 和 evidence 目录
- advisory → warning gate → engineering gate 的迁移路径
- 如何把 SkillOps 放进真实 PR review，而不是只跑 demo

**时间**：15 分钟

---

## 🚀 快速开始

1. 选择一个适合你的示例
2. 按照示例中的步骤操作
3. 遇到问题？查看 [文档](../docs/) 或提交 [Issue](https://github.com/BambooGap/skills-orchestrator/issues)

## 📖 推荐阅读顺序

**新手**：
1. [基础示例](basic/) → 理解基本概念
2. [多平台同步示例](multi-platform/) → 学会同步到多个平台
3. [团队协作示例](team-collab/) → 学会团队协作

**团队负责人**：
1. [团队协作示例](team-collab/) → 理解团队配置
2. [基础示例](basic/) → 了解基本用法
3. [多平台同步示例](multi-platform/) → 支持团队成员的不同工具

**外部评估者**：
1. [SkillOps Demo Repo](demo-repo/) → 直接跑 conformance 和证据导出
2. [Adapter Evidence Example](adapter-evidence/) → 验证 Claude Skills / MCP / OpenAI Agents SDK adapter evidence
3. [Release Trust Example](release-trust/) → 验证外部 skill provenance 和 release artifact 绑定
4. [Multi-repo Artifacts Example](multi-repo-artifacts/) → 聚合多个仓库的 evidence manifest
5. [External Consumer Example](external-consumer/) → 验证 hosted/GitHub App consumer 输入
6. [External Adoption Record Example](external-adoption-record/) → 验证外部接入交接记录
7. [Agent Handoff Contract Example](agent-handoff/) → 验证 supervisor/worker handoff 边界
8. [Agent Runtime Image Contract Example](agent-runtime-image/) → 验证外部 agent runtime 镜像边界
9. [Reference Repository Examples](adoption-repos/) → 复制真实仓库接入包
10. [SPEC.md](../SPEC.md) → 检查合同字段
11. [CONFORMANCE.md](../CONFORMANCE.md) → 对照验证命令

## 💡 提示

- 所有示例都假设你已经安装了 `skills-orchestrator`
- 如果你还没有安装，运行 `pip install skills-orchestrator`
- 示例中的命令可以直接复制粘贴运行

## 🔗 相关资源

- [官方文档](../docs/)
- [GitHub 仓库](https://github.com/BambooGap/skills-orchestrator)
- [问题反馈](https://github.com/BambooGap/skills-orchestrator/issues)

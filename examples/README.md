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

### [Pilot Repository Examples](pilot-repos/)

**适合**：平台团队、开源采用评估、真实仓库试点

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
2. [Pilot Repository Examples](pilot-repos/) → 复制真实仓库接入包
3. [SPEC.md](../SPEC.md) → 检查合同字段
4. [CONFORMANCE.md](../CONFORMANCE.md) → 对照验证命令

## 💡 提示

- 所有示例都假设你已经安装了 `skills-orchestrator`
- 如果你还没有安装，运行 `pip install skills-orchestrator`
- 示例中的命令可以直接复制粘贴运行

## 🔗 相关资源

- [官方文档](../docs/)
- [GitHub 仓库](https://github.com/BambooGap/skills-orchestrator)
- [问题反馈](https://github.com/BambooGap/skills-orchestrator/issues)

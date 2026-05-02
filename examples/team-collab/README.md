# 团队协作示例

这个示例展示如何在团队中使用 skills-orchestrator 统一代码规范。

## 项目结构

```
team-project/
├── config/
│   ├── skills.yaml
│   └── pipelines/
│       └── code-review.yaml
├── skills/
│   ├── zones/
│   │   ├── frontend.md
│   │   └── backend.md
│   ├── team-debugging.md
│   ├── team-review.md
│   └── team-tdd.md
├── .cursor/
│   └── rules/          # 自动生成
├── AGENTS.md           # 自动生成
└── skills.lock         # 自动生成
```

## 团队工作流

### 1. 团队负责人初始化

```bash
# 克隆项目
git clone team-project
cd team-project

# 初始化配置（如果还没有）
skills-orchestrator init --non-interactive

# 同步到所有平台
skills-orchestrator sync agents-md
skills-orchestrator sync cursor
skills-orchestrator sync openclaw

# 提交生成的文件
git add AGENTS.md skills.lock .cursor/
git commit -m "chore: 更新 skills 配置"
git push
```

### 2. 团队成员同步

```bash
# 拉取最新代码
git pull

# 同步到本地平台
skills-orchestrator sync agents-md
skills-orchestrator sync cursor
skills-orchestrator sync openclaw

# 现在所有人的 Skills 版本完全一致！
```

## Zone 配置

### config/skills.yaml

```yaml
zones:
  - id: frontend
    description: 前端强制规范
    path: src/frontend/
    priority: 100
    mode: forced

  - id: backend
    description: 后端强制规范
    path: src/backend/
    priority: 100
    mode: forced

  - id: default
    description: 默认区（个人自由区）
    path: .
    priority: 50
    mode: passive
```

### skills/zones/frontend.md

```markdown
---
id: frontend
name: 前端开发规范
summary: 前端团队必须遵守的代码规范
tags: [frontend, standards]
load_policy: require
conflict_with: [backend]
---

# 前端开发规范

## 代码风格

- 使用 TypeScript strict mode
- 组件命名：PascalCase
- 文件命名：kebab-case
- 必须编写单元测试

## 禁止事项

- ❌ 禁止直接操作 DOM
- ❌ 禁止使用 any 类型
- ❌ 禁止内联样式（使用 Tailwind CSS）
```

### skills/zones/backend.md

```markdown
---
id: backend
name: 后端开发规范
summary: 后端团队必须遵守的代码规范
tags: [backend, standards]
load_policy: require
conflict_with: [frontend]
---

# 后端开发规范

## API 设计

- RESTful API 设计
- 使用 OpenAPI 文档
- 统一错误格式

## 数据库

- 必须使用 migration
- 禁止直接修改生产库
- 查询必须加索引
```

## Pipeline 编排

### config/pipelines/code-review.yaml

```yaml
id: code-review
name: 代码审查流程
steps:
  - skill: team-debugging
    gate:
      must_produce: [root_cause]
      min_length: 50

  - skill: team-tdd
    gate:
      must_produce: [test_code]
      min_length: 100

  - skill: team-review
    gate:
      must_produce: [review_comments]
```

## 使用 MCP Server

团队可以启动 MCP Server，让 AI 按需加载 Skill：

```bash
# 启动服务
skills-orchestrator serve --config config/skills.yaml
```

团队成员在各自的 Claude Desktop 配置：

```json
// .claude/settings.json
{
  "mcpServers": {
    "team-skills": {
      "command": "skills-orchestrator",
      "args": ["serve", "--config", "/path/to/team-project/config/skills.yaml"]
    }
  }
}
```

## 版本管理

`skills.lock` 文件记录所有 Skill 的版本：

```yaml
version: 1
generated_at: "2026-05-02T21:00:00Z"
skills:
  - id: frontend
    hash: abc123...
    load_policy: require
  - id: backend
    hash: def456...
    load_policy: require
  - id: team-debugging
    hash: ghi789...
    load_policy: free
```

## 冲突检测

如果两个团队成员同时修改同一个 Skill：

```bash
skills-orchestrator build --config config/skills.yaml

# ✗ 检测到冲突: frontend 和 backend 不能同时激活
# frontend 要求: TypeScript strict mode
# backend 要求: Python type hints
```

## 最佳实践

1. **统一 Skills 版本**
   - 使用 `skills.lock` 锁定版本
   - 定期更新，团队同步

2. **强制规范隔离**
   - 使用 Zone 隔离不同团队
   - 使用 `conflict_with` 防止冲突

3. **工作流自动化**
   - 使用 Pipeline 编排流程
   - 使用 Gate 保证质量

4. **文档化**
   - 每个 Skill 必须有清晰的 summary
   - 使用 tags 分类

## 下一步

- 了解 [Zone 机制](../../docs/ZONES.md)
- 查看 [Pipeline 配置](../../docs/PIPELINES.md)
- 配置 [CI/CD 集成](../../docs/CI_CD.md)
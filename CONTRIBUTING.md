# Contributing to Skills Orchestrator

## 贡献方式

有两类贡献同等欢迎：

1. **贡献 Skill 内容**：添加新的 `.md` Skill 文件
2. **贡献代码**：改进治理层、MCP Server、CLI

---

## 贡献 Skill

### Skill 文件结构

每个 Skill 是一个 `.md` 文件，放在 `skills/<category>/` 下，开头必须有 frontmatter：

```markdown
---
id: your-skill-id          # 全局唯一，kebab-case
name: Skill 显示名称
summary: "一句话描述，50 字以内，用于搜索和摘要"
tags: [tag1, tag2]         # 便于过滤和搜索
load_policy: free          # free（按需）或 require（强制）
priority: 80               # 0-200，越高越优先
zones: [default]           # 适用 zone
conflict_with: []          # 与哪些 skill 互斥
---

# Skill 正文
```

### Skill 内容质量标准

每个 Skill 应包含：

- **触发场景**：什么情况下使用这个 Skill
- **操作步骤**：具体的操作流程或检查清单
- **输出模板**：给出可复用的输出格式
- **与其他 Skill 的关系**：和哪些 Skill 配合使用

参考 `skills/quality/systematic-debugging.md` 作为示例。

### 提交 Skill PR 的检查清单

- [ ] frontmatter 字段完整
- [ ] `id` 全局唯一（`skills-orchestrator validate` 通过）
- [ ] `summary` 不超过 50 字
- [ ] 正文包含触发场景、操作步骤、输出模板
- [ ] `与其他 Skill 的关系` 章节存在

---

## 贡献代码

### 本地开发

```bash
git clone https://github.com/yourname/skills-orchestrator
cd skills-orchestrator
pip install -e ".[dev]"
pytest tests/ -v
```

### 测试要求

- 新功能必须附带测试
- `pytest tests/` 全部通过才能合并
- MCP 相关改动需要通过 `TestToolExecutor` 和 `TestSkillRegistryIntegration`

### 提交规范

```
feat: 添加新功能
fix: 修复 bug
refactor: 重构（不改变行为）
test: 添加或修改测试
docs: 文档改动
```

### PR 要求

- 标题清晰说明做了什么
- 描述包含：改了什么 + 为什么 + 如何测试
- CI 全绿才合并

---

## 项目结构

```
src/
├── compiler/     # 编译时治理（Parser → Resolver → Compressor）
├── mcp/          # MCP Server（Registry、Search、Tools）
├── models/       # 数据模型（SkillMeta、Zone、Config）
└── main.py       # CLI 入口

skills/           # Skill 内容文件（按领域分目录）
config/           # skills.yaml 配置
tests/            # pytest 测试
```

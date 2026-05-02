# 基础示例：个人开发者

这个示例展示如何为个人项目配置 skills-orchestrator。

## 项目结构

```
my-project/
├── config/
│   └── skills.yaml
├── skills/
│   ├── my-debugging.md
│   └── my-review.md
└── README.md
```

## 步骤

### 1. 初始化配置

```bash
cd my-project
skills-orchestrator init --non-interactive
```

这会：
- 扫描 `skills/` 目录下的所有 `.md` 文件
- 从 frontmatter 自动提取元数据
- 生成 `config/skills.yaml`

### 2. 编译生成 AGENTS.md

```bash
skills-orchestrator build --config config/skills.yaml
```

输出：
```
✓ 解析完成: 2 skills, 1 zone
✓ 使用 Zone: 默认区 (default)
✓ 输出: AGENTS.md
```

### 3. 同步到多平台

```bash
# 同步到 Claude Desktop
skills-orchestrator sync agents-md

# 同步到 Cursor
skills-orchestrator sync cursor

# 同步到 OpenClaw
skills-orchestrator sync openclaw
```

## 示例 Skill 文件

### skills/my-debugging.md

```markdown
---
id: my-debugging
name: 我的调试流程
summary: 适用于本项目的系统化调试方法
tags: [debug, process]
load_policy: free
---

# 我的调试流程

## 步骤

1. **复现问题**：确保能稳定复现
2. **隔离范围**：定位到具体模块
3. **提出假设**：猜测可能的原因
4. **验证假设**：通过日志、断点验证
5. **修复验证**：确保修复后测试通过

## 本项目特定规则

- 必须更新 CHANGELOG.md
- 修复后必须添加测试用例
```

## 验证

```bash
# 检查配置
skills-orchestrator validate --config config/skills.yaml

# 查看版本
skills-orchestrator --version
```

## 下一步

- 查看 [团队协作示例](../team-collab/)
- 了解 [Pipeline 编排](../../docs/PIPELINES.md)
- 配置 [MCP Server](../../docs/MCP_SERVER.md)
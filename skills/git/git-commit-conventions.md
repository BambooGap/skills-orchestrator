---
id: git-commit-conventions
name: Git 提交规范
summary: "基于 git-operations 扩展的提交信息规范，强调 Conventional Commits 格式"
tags: [git, commit, convention]
load_policy: free
priority: 55
zones: [default]
conflict_with: []
base: git-operations
---
# Git 提交规范

> 本 skill 继承自 git-operations，在此基础上补充 Conventional Commits 格式规范。

## Conventional Commits 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 列表

| Type | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档更新 |
| style | 代码格式（不影响逻辑） |
| refactor | 重构（不新增功能也不修复） |
| test | 测试相关 |
| chore | 构建/工具/依赖 |

### 示例

```
feat(auth): 添加 OAuth2 登录支持

- 实现 Google OAuth2 provider
- 添加 token 刷新逻辑
- 更新登录页面 UI

Closes #123
```

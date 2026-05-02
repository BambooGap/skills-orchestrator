---
id: git-worktrees
name: Git Worktrees 工作流
summary: "git worktree 使用方法，同时在多个分支工作，无需 stash 或切换分支"
tags: [git, workflow, parallel]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
---
# Git Worktrees 工作流 Skill

## 概述

本 skill 介绍 git worktree 的使用方法和最佳实践。Worktree 允许同时在多个分支工作，无需 stash 或切换分支，特别适合需要在修 bug 的同时开发新功能的场景。

---

## 核心概念

Git worktree 让你把同一个仓库 checkout 到多个目录，每个目录独立跟踪一个分支：

```
my-project/           ← 主工作目录（main 分支）
my-project-hotfix/    ← worktree（hotfix/critical-bug 分支）
my-project-feature/   ← worktree（feature/new-api 分支）
```

每个目录有独立的工作区，但共享同一个 `.git` 历史。

---

## 基础命令

### 创建 worktree

```bash
# 从现有分支创建 worktree
git worktree add ../my-project-hotfix hotfix/critical-bug

# 创建新分支并建 worktree（最常用）
git worktree add -b feature/new-api ../my-project-feature main

# 简写：在父目录创建同名目录
git worktree add ../$(basename $(pwd))-hotfix hotfix/critical-bug
```

### 查看所有 worktree

```bash
git worktree list
# 输出：
# /path/to/my-project          abc1234 [main]
# /path/to/my-project-hotfix   def5678 [hotfix/critical-bug]
```

### 删除 worktree

```bash
# 先删目录，再清理引用
git worktree remove ../my-project-hotfix

# 如果目录已手动删除，清理悬空引用
git worktree prune
```

---

## 典型场景

### 场景一：开发中突然需要修 hotfix

```bash
# 当前在 feature/new-api 分支开发，不想 stash
cd ~/projects/my-project

# 创建 hotfix worktree
git worktree add -b hotfix/login-crash ../my-project-hotfix main

# 切到 hotfix 目录修 bug
cd ../my-project-hotfix
# ... 修复代码，测试，提交 ...
git add . && git commit -m "fix: login crash on empty password"
git push origin hotfix/login-crash

# 回到原来的功能开发
cd ../my-project
# feature/new-api 完全没动过
```

### 场景二：同时处理多个 PR review

```bash
# 为每个 PR 建一个 worktree
git worktree add -b review/pr-123 ../review-123 origin/feature/pr-123
git worktree add -b review/pr-456 ../review-456 origin/feature/pr-456

# 在不同目录分别运行测试，不互相干扰
cd ../review-123 && npm test
cd ../review-456 && npm test
```

### 场景三：对比两个版本行为

```bash
git worktree add ../version-old v1.2.0
git worktree add ../version-new v2.0.0-rc

# 同时运行两个版本，对比结果
cd ../version-old && node server.js --port 3000 &
cd ../version-new && node server.js --port 3001 &
```

---

## 注意事项

| 限制 | 说明 |
|------|------|
| 一个分支只能有一个 worktree | 不能同时 checkout 同一分支到两个目录 |
| `.git` 目录是软链接 | worktree 目录里的 `.git` 是文件而非目录 |
| lock 文件 | `package-lock.json` 等 lock 文件各自独立，不共享 `node_modules` |
| submodule | submodule 在 worktree 里需要单独初始化 |

### 依赖安装

每个 worktree 需要独立安装依赖：

```bash
# Python 项目
cd ../my-project-hotfix && pip install -e .

# Node 项目
cd ../my-project-hotfix && npm install
```

---

## 推荐目录结构

```
~/projects/
├── my-project/          ← 主开发目录（main）
├── my-project-hotfix/   ← hotfix worktree（临时，用完删）
└── my-project-review/   ← review worktree（临时，用完删）
```

命名约定：`<repo>-<用途>`，用完后 `git worktree remove` 清理。

---

## 与其他 Skill 的关系

- `finish-branch`：worktree 里的分支完成后，使用 finish-branch 清单提 PR
- `git-operations`：worktree 内的 git 操作与普通 git 操作相同
- `writing-plans`：计划中涉及并行开发时，规划 worktree 策略

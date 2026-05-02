---
id: finish-branch
name: 完成分支清单
summary: "提 PR 前的完整检查清单：代码质量、测试、commit 历史、PR 描述、文档"
tags: [git, pr, checklist]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
---
# 完成分支 Skill

## 概述

本 skill 定义在将功能分支合并到主干之前的完整检查清单。目标是：**让 PR 一次通过审查，避免来回修改**。

---

## 提 PR 前强制清单

### 代码质量

- [ ] 没有调试用的 `print` / `console.log` / `debugger`
- [ ] 没有被注释掉的死代码
- [ ] 没有 TODO 变成永久注释（要么做，要么删，要么建 issue）
- [ ] 函数/变量命名清晰，不需要注释才能理解
- [ ] 没有硬编码的密钥、密码、内部 URL

### 测试

- [ ] 新增的逻辑有对应的单元测试
- [ ] 修改了已有逻辑时，相关测试已更新
- [ ] 本地运行全部测试通过：`pytest` / `npm test` / etc.
- [ ] 测试覆盖了边界情况（空输入、最大值、并发）

### 提交历史

- [ ] commit message 格式正确（`feat:` / `fix:` / `refactor:` 等）
- [ ] 没有"WIP"、"fix fix"、"asd"这样的 commit
- [ ] 单个 commit 只做一件事
- [ ] 如有必要，已用 `git rebase -i` 整理 commit 历史

### PR 描述

- [ ] 标题格式：`<type>: <简短描述>`
- [ ] 描述包含：做了什么 + 为什么这样做 + 如何测试
- [ ] 关联了相关 issue（`Closes #123`）
- [ ] 如有 UI 改动，附上截图或录屏
- [ ] 标注了破坏性变更（breaking change）

### 文档

- [ ] README 更新（如有新命令/配置/接口）
- [ ] API 文档更新（如有接口变更）
- [ ] 迁移说明（如有数据库变更或配置变更）
- [ ] CHANGELOG 更新

---

## 自我 Review 流程

提 PR 前，先自己做一次完整 review：

```
1. 打开 git diff main 或 GitHub PR diff 视图
2. 假装你是另一个人，逐行读改动
3. 标记所有"我看到这段会问问题"的地方
4. 把这些问题在 PR 描述里提前说明
```

**目标**：review 者问的问题，你在 PR 描述里都已经回答了。

---

## 分支清理

合并后执行：

```bash
# 删除远程分支
git push origin --delete feature/your-branch

# 删除本地分支
git branch -d feature/your-branch

# 同步主干
git checkout main
git pull origin main

# 清理已合并的本地分支
git branch --merged | grep -v "main\|master\|develop" | xargs git branch -d
```

---

## 常见 PR 被打回的原因

| 原因 | 预防方式 |
|------|---------|
| 缺少测试 | 提 PR 前跑一次测试覆盖率检查 |
| PR 太大 | 超过 400 行改动时，考虑拆分 |
| commit 历史乱 | 提 PR 前 rebase 整理 |
| 描述不清楚 | 用模板写，包含 why |
| 存在合并冲突 | 提 PR 前先 rebase main |
| 破坏了已有功能 | 提 PR 前跑完整测试套件 |

---

## 与其他 Skill 的关系

- 本 skill 是 `writing-plans` 计划的最后一步
- 代码质量检查参考 `chinese-code-review`
- 分支管理配合 `git-operations` 和 `git-worktrees`

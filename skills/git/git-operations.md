---
id: git-operations
name: Git 操作规范
summary: "常用 git 操作规范：提交信息格式、分支命名约定、PR 描述模板"
tags: [git, base]
load_policy: free
priority: 50
zones: [default]
conflict_with: []
---
# Git 操作规范 Skill

## 概述

本 skill 定义 Git 操作的标准规范，包括提交信息格式、分支命名约定、PR 描述模板、常用命令速查。适用于所有使用 Git 进行版本控制的项目。

---

## Commit Message 格式规范

### 基本格式

```
<type>: <subject>

[optional body]

[optional footer]
```

### Type 枚举

| Type | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | feat: 添加用户登录接口 |
| `fix` | Bug 修复 | fix: 修复订单金额计算错误 |
| `docs` | 文档变更 | docs: 更新 API 文档 |
| `style` | 代码格式（不影响逻辑） | style: 统一缩进为 4 空格 |
| `refactor` | 重构（非新功能、非修复） | refactor: 抽取用户服务为独立模块 |
| `perf` | 性能优化 | perf: 优化列表查询性能 |
| `test` | 测试相关 | test: 添加订单服务单元测试 |
| `chore` | 构建/工具/依赖 | chore: 升级 pytest 到 7.0 |
| `ci` | CI/CD 配置 | ci: 添加自动部署 workflow |
| `revert` | 回滚提交 | revert: 回滚 feat: 添加用户登录接口 |

### Subject 规则

- 使用中文或英文，项目内保持一致
- 不超过 50 个字符
- 不以句号结尾
- 使用祈使句（添加而非添加了）

### Body 规则（可选）

- 解释为什么做这个改动
- 与之前行为的对比

### 示例

```
feat: 添加用户注册功能

- 支持邮箱和手机号两种注册方式
- 密码强度校验：至少 8 位，包含字母和数字
- 注册成功发送欢迎邮件

Closes #123
```

---

## 分支命名约定

### 分支前缀

| 前缀 | 说明 | 示例 |
|------|------|------|
| `feature/` | 新功能开发 | feature/user-login |
| `fix/` | Bug 修复 | fix/order-amount-calc |
| `hotfix/` | 紧急生产修复 | hotfix/payment-timeout |
| `chore/` | 非功能性改动 | chore/upgrade-deps |
| `refactor/` | 重构 | refactor/user-service |
| `docs/` | 文档 | docs/api-reference |
| `test/` | 测试 | test/order-service |

### 命名规则

- 使用小写字母和连字符
- 包含 issue 编号（如有）：`feature/123-user-login`
- 描述简洁明确，避免过长

### 分支生命周期

```
main (生产)
  └── develop (开发)
        ├── feature/xxx → 合并回 develop
        ├── fix/xxx → 合并回 develop
        └── hotfix/xxx → 合并回 main 和 develop
```

---

## PR 描述模板

```markdown
## 变更类型
- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 重构 (refactor)
- [ ] 文档 (docs)
- [ ] 其他：___

## 变更说明
[描述本次 PR 的主要内容]

## 关联 Issue
Closes #xxx
Related #yyy

## 测试情况
- [ ] 单元测试已通过
- [ ] 集成测试已通过
- [ ] 手动测试已完成

测试覆盖率：xx%

## 风险评估
- 影响范围：xxx
- 是否需要回滚方案：是/否
- 回滚方案：xxx

## Checklist
- [ ] 代码已自审
- [ ] 无新增 lint 警告
- [ ] 文档已更新
- [ ] 变更日志已更新
```

---

## 常用 Git 命令速查

### Rebase 操作

```bash
# 交互式 rebase 最近 3 个提交
git rebase -i HEAD~3

# rebase 到目标分支
git rebase develop

# 中途遇到冲突，解决后继续
git add .
git rebase --continue

# 放弃 rebase
git rebase --abort
```

### Cherry-pick 操作

```bash
# 挑选单个提交到当前分支
git cherry-pick <commit-hash>

# 挑选多个提交
git cherry-pick <hash1> <hash2>

# 挑选提交范围
git cherry-pick <start-hash>..<end-hash>

# 只挑选变更但不提交
git cherry-pick -n <commit-hash>
```

### Reset 三种模式

| 模式 | 命令 | 效果 |
|------|------|------|
| Soft | `git reset --soft HEAD~1` | 撤销提交，保留变更在暂存区 |
| Mixed | `git reset --mixed HEAD~1` | 撤销提交，保留变更在工作区（默认） |
| Hard | `git reset --hard HEAD~1` | 撤销提交，丢弃所有变更 |

**使用场景**：
- Soft：想重新组织提交内容
- Mixed：想重新选择哪些文件提交
- Hard：想完全丢弃最近的改动

### 其他常用命令

```bash
# 查看提交历史（图形化）
git log --oneline --graph --all

# 查看某个文件的变更历史
git log -p -- path/to/file

# 撤销工作区变更
git checkout -- path/to/file

# 撤销暂存区变更
git reset HEAD path/to/file

# 暂存当前工作
git stash
git stash pop

# 查看远程分支
git branch -r

# 删除已合并的本地分支
git branch -d feature/xxx

# 强制删除未合并的分支
git branch -D feature/xxx
```

---

## 最佳实践

1. **提交原子性**：每个提交只做一件事
2. **提交前检查**：`git diff` 和 `git status` 确认变更
3. **保持分支更新**：开发前先 `git pull --rebase`
4. **避免强制推送**：除非明确知道后果，否则不用 `--force`
5. **及时清理分支**：定期删除已合并的分支
6. **写好提交信息**：未来的你会感谢现在的你

---

## 与其他 Skill 的关系

- 与 `chinese-code-review` 配合：PR 需要经过代码审查
- 与 `systematic-debugging` 配合：修复 bug 后提交代码

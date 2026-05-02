# Skills-Orchestrator 实战使用指南

## 🎯 开始实战使用

从现在开始，在实际项目中强制使用这些 Pipeline。两周后根据真实反馈优化。

## 📋 5个现成模板

### 1. **bug-fix** - 系统性 Bug 修复
```bash
# 遇到 bug 时使用
skills-orchestrator pipeline start bug-fix --context '{
  "issue": "描述 bug 现象",
  "repo_url": "https://github.com/xxx/xxx",
  "skip_review": true
}'
```

### 2. **security-audit** - 安全审查
```bash
# 提 PR 前使用
skills-orchestrator pipeline start security-audit --context '{
  "code_url": "https://github.com/xxx/xxx/pull/123",
  "review_focus": ["认证", "授权", "输入验证"]
}'
```

### 3. **full-dev** - 完整开发流程
```bash
# 新功能开发时使用
skills-orchestrator pipeline start full-dev --context '{
  "feature": "功能描述",
  "tech_stack": "使用的技术栈",
  "business_value": "商业价值"
}'
```

### 4. **quick-fix** - 快速修复
```bash
# 小 bug 快速修复
skills-orchestrator pipeline start quick-fix --context '{
  "issue": "简单的 bug 描述",
  "expected_behavior": "期望的行为"
}'
```

### 5. **review-only** - 代码审查
```bash
# 已有代码的审查
skills-orchestrator pipeline start review-only --context '{
  "code_url": "代码链接",
  "review_scope": "审查重点"
}'
```

## 🛠️ 实用技巧

### 1. **查看所有模板**
```bash
# 简洁版（默认）
skills-orchestrator pipeline list

# 详细版（带分类和预览）
skills-orchestrator pipeline list --detail

# 紧凑版（窄终端）
skills-orchestrator pipeline list --compact
```

### 2. **使用文件传递 context**
```bash
# 创建 context 文件
echo '{"issue": "描述", "repo_url": "..."}' > ctx.json

# 使用文件启动
skills-orchestrator pipeline start bug-fix --context @ctx.json
```

### 3. **Pipeline 状态管理**
```bash
# 启动后会自动显示 run_id，或者
skills-orchestrator pipeline advance bug-fix  # 自动找最新运行
```

## 📊 两周后要回答的问题

### **用户体验**
1. 哪个 pipeline 用得最多？
2. JSON context 构建有多痛苦？
3. 在哪一步最容易放弃？

### **门禁约束**
1. 哪些步骤的门禁太严？
2. 哪些步骤的门禁太松？
3. 哪些地方应该有门禁但没有？

### **Skill 适配**
1. 哪些 skill 在 pipeline 中使用不顺畅？
2. 需要哪些新的 skill？
3. skill 之间是否有配合问题？

### **模板完整性**
1. 5个模板是否足够覆盖需求？
2. 两周后真的需要第6个模板吗？
3. 哪些模板需要优化步骤顺序？

## 🎯 使用原则

1. **强制使用** - 遇到相应场景就强制使用，不要跳过
2. **记录反馈** - 遇到问题立即记录
3. **真实需求** - 基于真实使用决定优化方向，而不是猜测

---

**两周后见！基于真实反馈，我们再来优化。**
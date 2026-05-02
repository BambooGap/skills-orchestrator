---
id: environment-setup
name: 环境管理规范
summary: "开发/测试/生产三环境隔离：配置管理、密钥安全、环境一致性"
tags: [ops, environment, config, security]
load_policy: free
priority: 75
zones: [default]
conflict_with: []
---
# 环境管理规范 Skill

## 概述

多环境管理的核心原则：**代码一份，配置分离；环境越高，保护越强**。
适用场景：新项目搭建、CI/CD 流水线配置、秘钥泄露应急处理。

---

## 三环境架构

```
Dev（本地开发）
  └── 目的：快速迭代，可以破坏
  └── 数据：本地数据库，测试数据
  └── 权限：开发者完全控制

Staging（预发）
  └── 目的：上线前完整验证
  └── 数据：脱敏的生产数据快照 或 固定测试集
  └── 权限：团队内部，不对外

Production（生产）
  └── 目的：真实用户使用
  └── 数据：真实数据
  └── 权限：最小权限，操作需审批
```

---

## 配置管理规范

### 原则：12-Factor App Config

```
代码仓库中：
  ✓ 配置的 key（环境变量名）
  ✓ 配置的默认值（Dev 可用）
  ✗ 任何生产密钥/密码/连接串

不在代码仓库中：
  ✓ .env.local（本地）
  ✓ CI/CD 的 Secret Variables
  ✓ 密钥管理服务（Vault/AWS Secrets Manager）
```

### .env 文件管理

```bash
# 项目根目录
.env.example      # 提交到 git：模板，含说明，不含真实值
.env.local        # 不提交：本地真实值
.env.test         # 可提交：测试用的固定值
.env              # 不提交：本地默认（被 .env.local 覆盖）
```

```ini
# .env.example 示例
DATABASE_URL=postgresql://localhost:5432/myapp_dev  # 开发默认值
REDIS_URL=redis://localhost:6379
STRIPE_SECRET_KEY=sk_test_xxx    # 填写你的 Stripe 测试密钥
OPENAI_API_KEY=                  # 必填，从 platform.openai.com 获取
```

---

## 密钥安全规范

### 绝对禁止

```
✗ 密钥硬编码在代码里
✗ 密钥提交到 git（即使是私有仓库）
✗ 密钥出现在日志里
✗ 生产密钥在 Slack/邮件里传递
✗ 多个服务共用同一个密钥
```

### 密钥轮换流程

```
发现密钥泄露 →
  1. 立即在服务商处吊销泄露的密钥（< 5 分钟）
  2. 生成新密钥
  3. 更新所有使用该密钥的环境
  4. 确认服务正常
  5. 审查日志，评估泄露期间的访问情况
  6. 记录事故报告
```

---

## 环境一致性检查

### Docker 化（推荐）

```dockerfile
# 用相同的镜像跑所有环境，配置通过环境变量注入
FROM python:3.12-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ src/
CMD ["python", "-m", "skills_orchestrator.main"]
```

```yaml
# docker-compose.yml (Dev)
services:
  app:
    build: .
    env_file: .env.local
    volumes:
      - ./src:/app/src   # Hot reload
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp_dev
```

### 依赖版本锁定

```bash
# Python
pip freeze > requirements.txt    # 或用 poetry.lock / uv.lock

# Node.js
package-lock.json / yarn.lock    # 提交到 git

# 禁止：
pip install requests   # 不锁版本
npm install express    # 不锁版本（除非是最终应用）
```

---

## 新开发者 Onboarding 检查

```
- [ ] clone 仓库
- [ ] 复制 .env.example → .env.local，填写本地值
- [ ] docker-compose up（或按 README 步骤）
- [ ] 运行测试全绿
- [ ] 预计时间：< 30 分钟
```

> "新人 30 分钟内本地跑通"是环境管理质量的基本验收标准。

---

## 与其他 Skill 的关系

- 与 `deployment-checklist` 配合：部署前的环境变量检查
- 与 `systematic-debugging` 配合：环境问题是常见根因之一
- 与 `error-handling` 配合：配置缺失的错误处理（启动时 fast-fail）
